"""評価バッチ実行ランナー。"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from src.bridge_agentic_generate.config import app_config
from src.bridge_agentic_generate.designer.models import DesignerInput
from src.bridge_agentic_generate.designer.services import generate_design_with_rag_log
from src.bridge_agentic_generate.judge.models import (
    JudgeInput,
    RepairIteration,
    RepairLoopResult,
)
from src.bridge_agentic_generate.judge.services import (
    apply_dependency_rules,
    apply_patch_plan,
    judge_v1,
)
from src.bridge_agentic_generate.llm_client import LlmModel
from src.bridge_agentic_generate.logger_config import logger
from src.bridge_agentic_generate.rag.embedding_config import TOP_K
from src.evaluation.models import EvaluationCase, TrialResult

# 照査項目のキー
CHECK_KEYS = ["deck", "bend", "shear", "deflection", "web_slenderness"]


def _run_repair_loop(
    bridge_length_m: float,
    total_width_m: float,
    model_name: LlmModel,
    use_rag: bool,
    top_k: int,
    max_iterations: int,
) -> RepairLoopResult:
    """Designer → Judge → (必要なら修正) のループを実行する。

    Args:
        bridge_length_m: 橋長 L [m]
        total_width_m: 幅員 B [m]
        model_name: 使用する LLM モデル名
        use_rag: RAG を使用するかどうか
        top_k: RAG で取得するチャンク数
        max_iterations: 最大反復回数

    Returns:
        RepairLoopResult: 全イテレーションの結果を含む結果オブジェクト
    """
    iterations: list[RepairIteration] = []

    # 1. 初期設計を生成
    inputs = DesignerInput(bridge_length_m=bridge_length_m, total_width_m=total_width_m)
    result = generate_design_with_rag_log(
        inputs=inputs,
        top_k=top_k,
        model_name=model_name,
        use_rag=use_rag,
    )
    design = result.design
    rag_log = result.rag_log
    dependency_rules = result.dependency_rules

    logger.info(
        "_run_repair_loop: 初期設計生成完了 L=%.0fm, B=%.0fm, use_rag=%s (dependency_rules=%d件)",
        bridge_length_m,
        total_width_m,
        use_rag,
        len(dependency_rules),
    )

    # 2. Judge → 修正ループ
    for iteration in range(max_iterations):
        logger.info("_run_repair_loop: イテレーション %d/%d", iteration + 1, max_iterations)

        # 照査
        judge_input = JudgeInput(bridge_design=design)
        report = judge_v1(judge_input, model=model_name)

        # イテレーション結果を記録
        iterations.append(
            RepairIteration(
                iteration=iteration,
                design=design.model_copy(deep=True),
                report=report,
            )
        )

        # 合格なら終了
        if report.pass_fail:
            logger.info(
                "_run_repair_loop: 合格（max_util=%.3f, iteration=%d）",
                report.utilization.max_util,
                iteration + 1,
            )
            return RepairLoopResult(
                converged=True,
                iterations=iterations,
                final_design=design,
                final_report=report,
                rag_log=rag_log,
            )

        # PatchPlan を適用
        deck_thickness_required = report.diagnostics.deck_thickness_required
        design = apply_patch_plan(
            design=design,
            patch_plan=report.patch_plan,
            deck_thickness_required=deck_thickness_required,
        )

        # 依存関係ルールを適用
        design = apply_dependency_rules(design=design, dependency_rules=dependency_rules)

        logger.info(
            "_run_repair_loop: PatchPlan 適用完了（%d アクション）",
            len(report.patch_plan.actions),
        )

    # 最大イテレーション後も収束しなかった場合
    judge_input = JudgeInput(bridge_design=design)
    final_report = judge_v1(judge_input, model=model_name)

    iterations.append(
        RepairIteration(
            iteration=max_iterations,
            design=design.model_copy(deep=True),
            report=final_report,
        )
    )

    if final_report.pass_fail:
        logger.info("_run_repair_loop: 最終照査で合格")
        return RepairLoopResult(
            converged=True,
            iterations=iterations,
            final_design=design,
            final_report=final_report,
            rag_log=rag_log,
        )

    logger.warning(
        "_run_repair_loop: %d 回の修正で収束しませんでした。 max_util=%.3f, governing_check=%s",
        max_iterations,
        final_report.utilization.max_util,
        final_report.utilization.governing_check,
    )
    return RepairLoopResult(
        converged=False,
        iterations=iterations,
        final_design=design,
        final_report=final_report,
        rag_log=rag_log,
    )


class EvaluationRunner:
    """評価バッチ実行（ThreadPoolExecutor で並列化）。"""

    def __init__(
        self,
        model_name: LlmModel = LlmModel.GPT_5_1,
        max_iterations: int = 5,
        num_trials: int = 3,
        max_workers: int = 3,
        top_k: int = TOP_K,
        output_dir: Path | None = None,
    ):
        """初期化。

        Args:
            model_name: 使用する LLM モデル名
            max_iterations: 修正ループの最大反復回数
            num_trials: 同一条件での試行回数
            max_workers: 並列ワーカー数
            top_k: RAG で取得するチャンク数
            output_dir: 出力ディレクトリ（None の場合は app_config.evaluation_dir）
        """
        self.model_name = model_name
        self.max_iterations = max_iterations
        self.num_trials = num_trials
        self.max_workers = max_workers
        self.top_k = top_k
        self.output_dir = output_dir or app_config.evaluation_dir

    def _ensure_output_dirs(self) -> None:
        """出力ディレクトリを作成する。"""
        (self.output_dir / "designs").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "judges").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "raglogs").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "senkeis").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "ifcs").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "results").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "design_logs").mkdir(parents=True, exist_ok=True)

    def _build_trial_id(self, case: EvaluationCase, use_rag: bool, trial: int) -> str:
        """試行ID を構築する。

        Args:
            case: 評価ケース
            use_rag: RAG 使用有無
            trial: 試行番号

        Returns:
            試行ID（例: "L50_B10_rag_true_trial_1"）
        """
        rag_str = "rag_true" if use_rag else "rag_false"
        return f"{case.case_id}_{rag_str}_trial_{trial}"

    def run_single_trial(
        self,
        case: EvaluationCase,
        use_rag: bool,
        trial: int,
    ) -> TrialResult:
        """1回の試行を実行（同期）。

        Args:
            case: 評価ケース
            use_rag: RAG 使用有無
            trial: 試行番号

        Returns:
            TrialResult: 試行結果
        """
        trial_id = self._build_trial_id(case, use_rag, trial)
        logger.info("run_single_trial: 開始 %s", trial_id)

        # 出力ディレクトリ確保
        self._ensure_output_dirs()

        # 修正ループ実行
        loop_result = _run_repair_loop(
            bridge_length_m=case.bridge_length_m,
            total_width_m=case.total_width_m,
            model_name=self.model_name,
            use_rag=use_rag,
            top_k=self.top_k,
            max_iterations=self.max_iterations,
        )

        # 初回結果を取得
        first_iteration = loop_result.iterations[0]
        first_report = first_iteration.report
        first_utilization = first_report.utilization

        # 最終結果
        final_report = loop_result.final_report
        final_utilization = final_report.utilization

        # 照査項目別の初回合格を計算
        per_check_first_pass: dict[str, bool] = {}
        for key in CHECK_KEYS:
            util_value = getattr(first_utilization, key, 1.0)
            per_check_first_pass[key] = util_value <= 1.0

        # 初回の utilization を dict に変換
        first_utilization_dict: dict[str, float] = {key: getattr(first_utilization, key, 0.0) for key in CHECK_KEYS}

        # TrialResult を構築
        trial_result = TrialResult(
            case_id=trial_id,
            bridge_length_m=case.bridge_length_m,
            total_width_m=case.total_width_m,
            use_rag=use_rag,
            trial=trial,
            converged=loop_result.converged,
            num_iterations=len(loop_result.iterations) - 1,  # 初回は iteration 0 なのでカウントしない
            first_pass=first_report.pass_fail,
            first_max_util=first_utilization.max_util,
            first_utilization=first_utilization_dict,
            final_pass=final_report.pass_fail,
            final_max_util=final_utilization.max_util,
            per_check_first_pass=per_check_first_pass,
        )

        # 結果をファイルに保存
        self._save_trial_results(trial_id, loop_result, trial_result)

        logger.info(
            "run_single_trial: 完了 %s (converged=%s, num_iterations=%d, first_pass=%s, final_pass=%s)",
            trial_id,
            loop_result.converged,
            trial_result.num_iterations,
            trial_result.first_pass,
            trial_result.final_pass,
        )

        return trial_result

    def _save_trial_results(
        self,
        trial_id: str,
        loop_result: RepairLoopResult,
        trial_result: TrialResult,
    ) -> None:
        """試行結果をファイルに保存する。

        Args:
            trial_id: 試行ID
            loop_result: 修正ループ結果
            trial_result: 試行結果
        """
        # BridgeDesign（最終設計）
        design_path = self.output_dir / "designs" / f"{trial_id}.json"
        design_path.write_text(
            loop_result.final_design.model_dump_json(indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        # JudgeReport（最終照査結果）
        judge_path = self.output_dir / "judges" / f"{trial_id}.json"
        judge_path.write_text(
            loop_result.final_report.model_dump_json(indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        # TrialResult（評価指標）
        result_path = self.output_dir / "results" / f"{trial_id}.json"
        result_path.write_text(
            trial_result.model_dump_json(indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        # RAGログ（初期設計生成時のRAGコンテキスト）
        raglog_path = self.output_dir / "raglogs" / f"{trial_id}.json"
        raglog_path.write_text(
            loop_result.rag_log.model_dump_json(indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        # 各イテレーションの設計を保存（断面量の変遷記録用）
        design_logs_dir = self.output_dir / "design_logs" / trial_id
        design_logs_dir.mkdir(parents=True, exist_ok=True)
        for iteration in loop_result.iterations:
            iter_design_path = design_logs_dir / f"{trial_id}_iter{iteration.iteration}.json"
            iter_design_path.write_text(
                iteration.design.model_dump_json(indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

        logger.info(
            "_save_trial_results: 保存完了 design=%s, judge=%s, result=%s, raglog=%s, design_logs=%s",
            design_path,
            judge_path,
            result_path,
            raglog_path,
            design_logs_dir,
        )

    def run_case(
        self,
        case: EvaluationCase,
        use_rag: bool,
    ) -> list[TrialResult]:
        """1ケース×1条件を num_trials 回並列実行（ThreadPoolExecutor）。

        Args:
            case: 評価ケース
            use_rag: RAG 使用有無

        Returns:
            list[TrialResult]: 試行結果のリスト
        """
        logger.info(
            "run_case: 開始 %s, use_rag=%s, num_trials=%d",
            case.case_id,
            use_rag,
            self.num_trials,
        )

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [
                executor.submit(self.run_single_trial, case, use_rag, trial) for trial in range(1, self.num_trials + 1)
            ]
            results = [f.result() for f in futures]

        logger.info("run_case: 完了 %s, use_rag=%s", case.case_id, use_rag)
        return results

    def run_all(
        self,
        cases: list[EvaluationCase],
    ) -> list[TrialResult]:
        """全ケースを実行（RAG あり/なし両方）。

        ケース間は順次実行（API レート制限考慮）。
        同一条件（ケース×RAG条件）内で ThreadPoolExecutor で並列実行。

        Args:
            cases: 評価ケースのリスト

        Returns:
            list[TrialResult]: 全試行結果のリスト
        """
        logger.info("run_all: 開始 %d ケース", len(cases))

        all_results: list[TrialResult] = []

        for case in cases:
            # RAG あり
            results_rag_true = self.run_case(case, use_rag=True)
            all_results.extend(results_rag_true)

            # RAG なし
            results_rag_false = self.run_case(case, use_rag=False)
            all_results.extend(results_rag_false)

        logger.info("run_all: 完了 %d 試行", len(all_results))
        return all_results
