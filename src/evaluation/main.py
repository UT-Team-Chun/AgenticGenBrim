"""評価基盤 CLI エントリーポイント。"""

from __future__ import annotations

from pathlib import Path

import fire

from src.bridge_agentic_generate.config import app_config
from src.bridge_agentic_generate.llm_client import LlmModel
from src.bridge_agentic_generate.logger_config import logger
from src.evaluation.metrics import aggregate_metrics
from src.evaluation.models import AggregatedMetrics, EvaluationCase, TrialResult
from src.evaluation.plot import generate_all_plots
from src.evaluation.runner import EvaluationRunner

# 評価ケース定義（EVALUATION.md より）
DEFAULT_EVALUATION_CASES: list[EvaluationCase] = [
    EvaluationCase(case_id="L20_B8", bridge_length_m=20, total_width_m=8),
    EvaluationCase(case_id="L20_B10", bridge_length_m=20, total_width_m=10),
    EvaluationCase(case_id="L25_B8", bridge_length_m=25, total_width_m=8),
    EvaluationCase(case_id="L25_B10", bridge_length_m=25, total_width_m=10),
    EvaluationCase(case_id="L25_B12", bridge_length_m=25, total_width_m=12),
    EvaluationCase(case_id="L30_B8", bridge_length_m=30, total_width_m=8),
    EvaluationCase(case_id="L30_B10", bridge_length_m=30, total_width_m=10),
    EvaluationCase(case_id="L30_B12", bridge_length_m=30, total_width_m=12),
    EvaluationCase(case_id="L35_B8", bridge_length_m=35, total_width_m=8),
    EvaluationCase(case_id="L35_B10", bridge_length_m=35, total_width_m=10),
    EvaluationCase(case_id="L35_B16", bridge_length_m=35, total_width_m=16),
    EvaluationCase(case_id="L40_B8", bridge_length_m=40, total_width_m=8),
    EvaluationCase(case_id="L40_B10", bridge_length_m=40, total_width_m=10),
    EvaluationCase(case_id="L40_B20", bridge_length_m=40, total_width_m=20),
    EvaluationCase(case_id="L45_B8", bridge_length_m=45, total_width_m=8),
    EvaluationCase(case_id="L45_B10", bridge_length_m=45, total_width_m=10),
    EvaluationCase(case_id="L45_B20", bridge_length_m=45, total_width_m=20),
    EvaluationCase(case_id="L50_B10", bridge_length_m=50, total_width_m=10),
    EvaluationCase(case_id="L50_B16", bridge_length_m=50, total_width_m=16),
    EvaluationCase(case_id="L50_B24", bridge_length_m=50, total_width_m=24),
    EvaluationCase(case_id="L55_B10", bridge_length_m=55, total_width_m=10),
    EvaluationCase(case_id="L55_B16", bridge_length_m=55, total_width_m=16),
    EvaluationCase(case_id="L55_B24", bridge_length_m=55, total_width_m=24),
    EvaluationCase(case_id="L60_B10", bridge_length_m=60, total_width_m=10),
    EvaluationCase(case_id="L60_B16", bridge_length_m=60, total_width_m=16),
    EvaluationCase(case_id="L60_B24", bridge_length_m=60, total_width_m=24),
    EvaluationCase(case_id="L65_B12", bridge_length_m=65, total_width_m=12),
    EvaluationCase(case_id="L65_B16", bridge_length_m=65, total_width_m=16),
    EvaluationCase(case_id="L65_B24", bridge_length_m=65, total_width_m=24),
    EvaluationCase(case_id="L70_B12", bridge_length_m=70, total_width_m=12),
    EvaluationCase(case_id="L70_B16", bridge_length_m=70, total_width_m=16),
    EvaluationCase(case_id="L70_B24", bridge_length_m=70, total_width_m=24),
]


def _save_summary(
    results: list[TrialResult],
    metrics: AggregatedMetrics,
    output_dir: Path,
) -> None:
    """集計結果を summary.json に保存する。

    Args:
        results: 全試行結果
        metrics: 集計結果
        output_dir: 出力ディレクトリ
    """
    # RAG あり/なしで分けて集計
    results_rag_true = [r for r in results if r.use_rag]
    results_rag_false = [r for r in results if not r.use_rag]
    metrics_rag_true = aggregate_metrics(results_rag_true)
    metrics_rag_false = aggregate_metrics(results_rag_false)

    summary = {
        "total_trials": len(results),
        "overall": metrics.model_dump(),
        "rag_true": {
            "total_trials": len(results_rag_true),
            "metrics": metrics_rag_true.model_dump(),
        },
        "rag_false": {
            "total_trials": len(results_rag_false),
            "metrics": metrics_rag_false.model_dump(),
        },
    }

    import json

    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Summary saved to %s", summary_path)


class EvaluationCLI:
    """評価基盤の CLI コマンド。

    Usage:
        # 全ケース実行
        uv run python -m src.evaluation.main run

        # 単一ケースのテスト実行
        uv run python -m src.evaluation.main single_case --bridge_length_m 50 --total_width_m 10

        # RAG なしで単一ケースのテスト実行
        uv run python -m src.evaluation.main single_case --bridge_length_m 50 --total_width_m 10 --use_rag False
    """

    def run(
        self,
        output_dir: str | None = "data/evaluation_v5",
        model_name: LlmModel = LlmModel.GPT_5_1,
        max_iterations: int = 5,
        num_trials: int = 3,
        max_workers: int = 3,
    ) -> None:
        """全評価ケースを実行する。

        Args:
            output_dir: 出力ディレクトリ（None の場合は data/evaluation/）
            model_name: 使用する LLM モデル名
            max_iterations: 修正ループの最大反復回数
            num_trials: 同一条件での試行回数
            max_workers: 並列ワーカー数
        """
        logger.info(
            "EvaluationCLI.run: 開始 model=%s, max_iterations=%d, num_trials=%d, max_workers=%d",
            model_name,
            max_iterations,
            num_trials,
            max_workers,
        )

        output_path = Path(output_dir) if output_dir else app_config.evaluation_dir

        runner = EvaluationRunner(
            model_name=LlmModel(model_name),
            max_iterations=max_iterations,
            num_trials=num_trials,
            max_workers=max_workers,
            output_dir=output_path,
        )

        results = runner.run_all(cases=DEFAULT_EVALUATION_CASES)

        # 集計
        metrics = aggregate_metrics(results)
        _save_summary(results, metrics, output_path)

        # 結果表示
        logger.info("=== 評価結果 ===")
        logger.info("Total trials: %d", len(results))
        logger.info("First pass rate: %.1f%%", metrics.first_pass_rate * 100)
        logger.info("Convergence rate: %.1f%%", metrics.convergence_rate * 100)
        logger.info("Avg iterations: %.2f", metrics.avg_iterations)
        logger.info("Final pass rate: %.1f%%", metrics.final_pass_rate * 100)
        logger.info("Per-check first pass rates:")
        for key, rate in metrics.per_check_first_pass_rate.items():
            logger.info("  %s: %.1f%%", key, rate * 100)

    def single_case(
        self,
        bridge_length_m: float,
        total_width_m: float,
        use_rag: bool = True,
        output_dir: str | None = None,
        model_name: str = "gpt-5.1",
        max_iterations: int = 5,
    ) -> None:
        """単一ケースのテスト実行。

        Args:
            bridge_length_m: 橋長 [m]
            total_width_m: 幅員 [m]
            use_rag: RAG を使用するかどうか
            output_dir: 出力ディレクトリ（None の場合は data/evaluation/）
            model_name: 使用する LLM モデル名
            max_iterations: 修正ループの最大反復回数
        """
        logger.info(
            "EvaluationCLI.single_case: L=%.0fm, B=%.0fm, use_rag=%s, model=%s",
            bridge_length_m,
            total_width_m,
            use_rag,
            model_name,
        )

        output_path = Path(output_dir) if output_dir else app_config.evaluation_dir

        case = EvaluationCase(
            case_id=f"L{int(bridge_length_m)}_B{int(total_width_m)}",
            bridge_length_m=bridge_length_m,
            total_width_m=total_width_m,
        )

        runner = EvaluationRunner(
            model_name=LlmModel(model_name),
            max_iterations=max_iterations,
            num_trials=1,  # 単一ケースなので1回
            max_workers=1,
            output_dir=output_path,
        )

        result = runner.run_single_trial(case=case, use_rag=use_rag, trial=1)

        # 結果表示
        logger.info("=== 試行結果 ===")
        logger.info("Case ID: %s", result.case_id)
        logger.info("Converged: %s", result.converged)
        logger.info("Num iterations: %d", result.num_iterations)
        logger.info("First pass: %s (max_util=%.3f)", result.first_pass, result.first_max_util)
        logger.info("Final pass: %s (max_util=%.3f)", result.final_pass, result.final_max_util)
        logger.info("First utilization: %s", result.first_utilization)
        logger.info("Per-check first pass: %s", result.per_check_first_pass)

    def plot(
        self,
        data_dir: str = "data/evaluation_v5",
        output_dir: str | None = None,
    ) -> None:
        """評価結果のグラフを生成する。

        Args:
            data_dir: 評価データのルートディレクトリ（results/ を含む）
            output_dir: グラフ出力先ディレクトリ（デフォルトは data_dir と同じ）
        """
        data_path = Path(data_dir)
        output_path = Path(output_dir) if output_dir else data_path

        logger.info("Generating plots from %s to %s", data_path, output_path)
        generate_all_plots(data_dir=data_path, output_dir=output_path)
        logger.info("Plot generation completed")


def main() -> None:
    """CLI エントリーポイント。"""
    fire.Fire(EvaluationCLI)


if __name__ == "__main__":
    main()
