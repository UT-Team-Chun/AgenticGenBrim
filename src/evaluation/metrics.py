"""評価指標計算ロジック。"""

from __future__ import annotations

from src.evaluation.models import AggregatedMetrics, TrialResult

# 照査項目のキー
CHECK_KEYS = ["deck", "bend", "shear", "deflection", "web_slenderness"]


def calc_first_pass_rate(results: list[TrialResult]) -> float:
    """初回合格率を計算する。

    Args:
        results: 試行結果のリスト

    Returns:
        初回合格率（0.0〜1.0）。結果が空の場合は 0.0。
    """
    if not results:
        return 0.0
    first_pass_count = sum(1 for r in results if r.first_pass)
    return first_pass_count / len(results)


def calc_convergence_rate(results: list[TrialResult]) -> float:
    """収束率を計算する。

    Args:
        results: 試行結果のリスト

    Returns:
        収束率（0.0〜1.0）。結果が空の場合は 0.0。
    """
    if not results:
        return 0.0
    converged_count = sum(1 for r in results if r.converged)
    return converged_count / len(results)


def calc_avg_iterations(results: list[TrialResult]) -> float:
    """平均修正回数を計算する（収束ケースのみ）。

    Args:
        results: 試行結果のリスト

    Returns:
        平均修正回数。収束ケースがない場合は 0.0。
    """
    converged_results = [r for r in results if r.converged]
    if not converged_results:
        return 0.0
    total_iterations = sum(r.num_iterations for r in converged_results)
    return total_iterations / len(converged_results)


def calc_final_pass_rate(results: list[TrialResult]) -> float:
    """最終合格率を計算する。

    Args:
        results: 試行結果のリスト

    Returns:
        最終合格率（0.0〜1.0）。結果が空の場合は 0.0。
    """
    if not results:
        return 0.0
    final_pass_count = sum(1 for r in results if r.final_pass)
    return final_pass_count / len(results)


def calc_per_check_first_pass_rate(results: list[TrialResult]) -> dict[str, float]:
    """照査項目別の初回合格率を計算する。

    Args:
        results: 試行結果のリスト

    Returns:
        照査項目別の初回合格率の辞書。
        結果が空の場合は全項目 0.0。
    """
    if not results:
        return {key: 0.0 for key in CHECK_KEYS}

    per_check_rates: dict[str, float] = {}
    for key in CHECK_KEYS:
        pass_count = sum(1 for r in results if r.per_check_first_pass.get(key, False))
        per_check_rates[key] = pass_count / len(results)

    return per_check_rates


def aggregate_metrics(results: list[TrialResult]) -> AggregatedMetrics:
    """全指標を集計する。

    Args:
        results: 試行結果のリスト

    Returns:
        集計結果（AggregatedMetrics）
    """
    return AggregatedMetrics(
        first_pass_rate=calc_first_pass_rate(results),
        convergence_rate=calc_convergence_rate(results),
        avg_iterations=calc_avg_iterations(results),
        final_pass_rate=calc_final_pass_rate(results),
        per_check_first_pass_rate=calc_per_check_first_pass_rate(results),
    )
