"""bridge-llm-mvp のメインエントリーポイント。"""

from __future__ import annotations

from datetime import datetime
from typing import Sequence

import fire

from src.bridge_agentic_generate.config import app_config
from src.bridge_agentic_generate.designer.models import DesignerInput
from src.bridge_agentic_generate.designer.services import generate_design_with_rag_log
from src.bridge_agentic_generate.judge.models import (
    JudgeInput,
    RepairIteration,
    RepairLoopResult,
)
from src.bridge_agentic_generate.judge.services import apply_patch_plan, judge_v1
from src.bridge_agentic_generate.llm_client import LlmModel
from src.bridge_agentic_generate.logger_config import logger
from src.bridge_agentic_generate.rag.embedding_config import TOP_K

DEFAULT_BRIDGE_LENGTH_M: float = 50.0
DEFAULT_BRIDGE_LENGTHS_M: Sequence[float] = (30.0, 40.0, 50.0, 60.0, 70.0)
DEFAULT_TOTAL_WIDTH_M: float = 10.0
DEFAULT_MAX_ITERATIONS: int = 5


def run_batch(
    model_name: LlmModel,
    bridge_lengths_m: Sequence[float] = DEFAULT_BRIDGE_LENGTHS_M,
    total_width_m: float = DEFAULT_TOTAL_WIDTH_M,
    top_k: int = TOP_K,
) -> None:
    """代表ケースの Designer→Judge を run_single_case 経由で実行する。

    Args:
        model_name: 使用する LLM モデル名。
        bridge_lengths_m: 実行する橋長のリスト [m]。
        total_width_m: 橋幅員 B [m]（全ケース共通）。
        top_k: RAG で取得するチャンク数。
    """
    for bridge_length_m in bridge_lengths_m:
        run_single_case(
            bridge_length_m=bridge_length_m,
            total_width_m=total_width_m,
            model_name=model_name,
            top_k=top_k,
            judge_enabled=True,
        )


def run_single_case(
    bridge_length_m: float,
    total_width_m: float,
    model_name: LlmModel = LlmModel.GPT_5_MINI,
    top_k: int = TOP_K,
    judge_enabled: bool = False,
) -> None:
    """単一ケースの Designer→(任意で Judge) を実行し、結果を保存する。

    Args:
        bridge_length_m: 橋長 L [m]。
        total_width_m: 幅員 B [m]。
        model_name: 使用する LLM モデル名。
        top_k: RAG で取得するチャンク数。
        judge_enabled: True の場合、Judge も実行する。
    """
    simple_json_dir = app_config.generated_simple_bridge_json_dir
    simple_json_dir.mkdir(parents=True, exist_ok=True)
    raglog_json_dir = app_config.generated_bridge_raglog_json_dir
    raglog_json_dir.mkdir(parents=True, exist_ok=True)
    inputs = DesignerInput(bridge_length_m=bridge_length_m, total_width_m=total_width_m)
    result = generate_design_with_rag_log(inputs=inputs, top_k=top_k, model_name=model_name)
    design = result.design
    rag_log = result.rag_log

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"design_L{int(inputs.bridge_length_m)}_B{int(inputs.total_width_m)}_{timestamp}"

    design_path = simple_json_dir / f"{base_name}.json"
    raglog_path = raglog_json_dir / f"{base_name}_design_log.json"

    design_path.write_text(design.model_dump_json(indent=2, ensure_ascii=False), encoding="utf-8")
    raglog_path.write_text(rag_log.model_dump_json(indent=2, ensure_ascii=False), encoding="utf-8")

    logger.info("Saved design to %s", design_path)
    logger.info("Saved RAG log to %s", raglog_path)

    if judge_enabled:
        judge_input = JudgeInput(bridge_design=design)
        report = judge_v1(judge_input)
        logger.info("Judge result: pass_fail=%s, max_util=%.3f", report.pass_fail, report.utilization.max_util)


def run_with_repair_loop(
    bridge_length_m: float,
    total_width_m: float,
    model_name: LlmModel = LlmModel.GPT_5_MINI,
    top_k: int = TOP_K,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
) -> RepairLoopResult:
    """Designer → Judge → (必要なら修正) のループを実行する。

    Args:
        bridge_length_m: 橋長 L [m]
        total_width_m: 幅員 B [m]
        model_name: 使用する LLM モデル名
        top_k: RAG で取得するチャンク数
        max_iterations: 最大反復回数

    Returns:
        RepairLoopResult: 全イテレーションの結果を含む結果オブジェクト
    """
    iterations: list[RepairIteration] = []

    # 1. 初期設計を生成
    inputs = DesignerInput(bridge_length_m=bridge_length_m, total_width_m=total_width_m)
    result = generate_design_with_rag_log(inputs=inputs, top_k=top_k, model_name=model_name)
    design = result.design

    logger.info(
        "run_with_repair_loop: 初期設計生成完了 L=%.0fm, B=%.0fm",
        bridge_length_m,
        total_width_m,
    )

    # 2. Judge → 修正ループ
    for iteration in range(max_iterations):
        logger.info("run_with_repair_loop: イテレーション %d/%d", iteration + 1, max_iterations)

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
                "run_with_repair_loop: 合格（max_util=%.3f, iteration=%d）",
                report.utilization.max_util,
                iteration + 1,
            )
            return RepairLoopResult(
                converged=True,
                iterations=iterations,
                final_design=design,
                final_report=report,
            )

        # 不合格かつ PatchPlan が空の場合は ValueError（サービス層で送出済み）
        # ここに到達する場合は patch_plan.actions が空でないことが保証されている

        # PatchPlan を適用
        deck_thickness_required = report.diagnostics.deck_thickness_required
        design = apply_patch_plan(
            design=design,
            patch_plan=report.patch_plan,
            deck_thickness_required=deck_thickness_required,
        )

        logger.info(
            "run_with_repair_loop: PatchPlan 適用完了（%d アクション）",
            len(report.patch_plan.actions),
        )

    # 最大イテレーション後も収束しなかった場合
    # 最後の照査結果を取得
    judge_input = JudgeInput(bridge_design=design)
    final_report = judge_v1(judge_input, model=model_name)

    # 最終イテレーション結果を記録
    iterations.append(
        RepairIteration(
            iteration=max_iterations,
            design=design.model_copy(deep=True),
            report=final_report,
        )
    )

    if final_report.pass_fail:
        logger.info("run_with_repair_loop: 最終照査で合格")
        return RepairLoopResult(
            converged=True,
            iterations=iterations,
            final_design=design,
            final_report=final_report,
        )

    logger.warning(
        "run_with_repair_loop: %d 回の修正で収束しませんでした。 max_util=%.3f, governing_check=%s",
        max_iterations,
        final_report.utilization.max_util,
        final_report.utilization.governing_check,
    )
    return RepairLoopResult(
        converged=False,
        iterations=iterations,
        final_design=design,
        final_report=final_report,
    )


class CLI:
    """Designer/Judge の CLI コマンド。

    Usage:
        # Designer のみ（Judge なし）
        uv run python -m src.bridge_agentic_generate.main run --bridge_length_m=50 --total_width_m=10

        # Designer + Judge（1回照査のみ）
        uv run python -m src.bridge_agentic_generate.main run --bridge_length_m=50 --total_width_m=10 --judge

        # Designer + Judge + 修正ループ（収束するまで繰り返し）
        uv run python -m src.bridge_agentic_generate.main run_with_repair --bridge_length_m=50 --total_width_m=10

        # バッチ実行
        uv run python -m src.bridge_agentic_generate.main batch
    """

    def run(
        self,
        bridge_length_m: float = DEFAULT_BRIDGE_LENGTH_M,
        total_width_m: float = DEFAULT_TOTAL_WIDTH_M,
        model_name: LlmModel = LlmModel.GPT_5_MINI,
        top_k: int = TOP_K,
        judge: bool = False,
    ) -> None:
        """単一ケースの Designer を実行する。

        Args:
            bridge_length_m: 橋長 L [m]
            total_width_m: 幅員 B [m]
            model_name: 使用する LLM モデル名
            top_k: RAG で取得するチャンク数
            judge: True の場合、Judge も実行する
        """
        run_single_case(
            bridge_length_m=bridge_length_m,
            total_width_m=total_width_m,
            model_name=LlmModel(model_name),
            top_k=top_k,
            judge_enabled=judge,
        )

    def run_with_repair(
        self,
        bridge_length_m: float = DEFAULT_BRIDGE_LENGTH_M,
        total_width_m: float = DEFAULT_TOTAL_WIDTH_M,
        model_name: LlmModel = LlmModel.GPT_5_MINI,
        top_k: int = TOP_K,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
    ) -> None:
        """Designer → Judge → 修正ループを実行する。

        Args:
            bridge_length_m: 橋長 L [m]
            total_width_m: 幅員 B [m]
            model_name: 使用する LLM モデル名
            top_k: RAG で取得するチャンク数
            max_iterations: 最大反復回数
        """
        loop_result = run_with_repair_loop(
            bridge_length_m=bridge_length_m,
            total_width_m=total_width_m,
            model_name=LlmModel(model_name),
            top_k=top_k,
            max_iterations=max_iterations,
        )

        # 結果を保存
        simple_json_dir = app_config.generated_simple_bridge_json_dir
        judge_json_dir = app_config.generated_judge_json_dir
        simple_json_dir.mkdir(parents=True, exist_ok=True)
        judge_json_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"design_L{int(bridge_length_m)}_B{int(total_width_m)}_{timestamp}"

        # 各イテレーションの結果を保存
        for iteration in loop_result.iterations:
            iter_suffix = f"_iter{iteration.iteration}"
            design_path = simple_json_dir / f"{base_name}{iter_suffix}.json"
            judge_path = judge_json_dir / f"{base_name}{iter_suffix}_judge.json"

            design_path.write_text(
                iteration.design.model_dump_json(indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            judge_path.write_text(
                iteration.report.model_dump_json(indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

            logger.info("Saved iteration %d design to %s", iteration.iteration, design_path)
            logger.info("Saved iteration %d judge to %s", iteration.iteration, judge_path)

        # 最終設計を保存
        final_design_path = simple_json_dir / f"{base_name}_final.json"
        final_design_path.write_text(
            loop_result.final_design.model_dump_json(indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info("Saved final design to %s", final_design_path)

        logger.info(
            "Final result: converged=%s, pass_fail=%s, max_util=%.3f, governing=%s",
            loop_result.converged,
            loop_result.final_report.pass_fail,
            loop_result.final_report.utilization.max_util,
            loop_result.final_report.utilization.governing_check,
        )

    def batch(
        self,
        model_name: LlmModel = LlmModel.GPT_5_MINI,
        total_width_m: float = DEFAULT_TOTAL_WIDTH_M,
        top_k: int = TOP_K,
    ) -> None:
        """代表ケース（L=30,40,50,60,70m）をバッチ実行する。

        Args:
            model_name: 使用する LLM モデル名
            total_width_m: 幅員 B [m]（全ケース共通）
            top_k: RAG で取得するチャンク数
        """
        run_batch(
            model_name=LlmModel(model_name),
            total_width_m=total_width_m,
            top_k=top_k,
        )


def main() -> None:
    """CLI エントリーポイント。"""
    fire.Fire(CLI)


if __name__ == "__main__":
    main()
