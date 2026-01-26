"""評価基盤モジュール。

Designer + Judge ループの評価を行うための機能を提供する。
"""

from src.evaluation.metrics import (
    aggregate_metrics,
    calc_avg_iterations,
    calc_convergence_rate,
    calc_final_pass_rate,
    calc_first_pass_rate,
    calc_per_check_first_pass_rate,
)
from src.evaluation.models import (
    AggregatedMetrics,
    EvaluationCase,
    TrialResult,
)
from src.evaluation.runner import EvaluationRunner

__all__ = [
    # Models
    "EvaluationCase",
    "TrialResult",
    "AggregatedMetrics",
    # Metrics
    "calc_first_pass_rate",
    "calc_convergence_rate",
    "calc_avg_iterations",
    "calc_final_pass_rate",
    "calc_per_check_first_pass_rate",
    "aggregate_metrics",
    # Runner
    "EvaluationRunner",
]
