"""評価用 Pydantic モデル定義。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class EvaluationCase(BaseModel):
    """評価ケース定義。

    Attributes:
        case_id: ケースID（例: "L50_B10"）
        bridge_length_m: 橋長 [m]
        total_width_m: 幅員 [m]
    """

    case_id: str = Field(..., description="ケースID（例: L50_B10）")
    bridge_length_m: float = Field(..., description="橋長 [m]")
    total_width_m: float = Field(..., description="幅員 [m]")


class TrialResult(BaseModel):
    """試行結果（1回分）。

    Attributes:
        case_id: 試行ID（例: "L50_B10_rag_true_trial_1"）
        bridge_length_m: 橋長 [m]
        total_width_m: 幅員 [m]
        use_rag: RAG使用有無
        trial: 試行番号
        converged: 収束したかどうか
        num_iterations: 修正ループ回数
        first_pass: 初回合格かどうか
        first_max_util: 初回の max_util
        first_utilization: 初回の各照査項目の util
        final_pass: 最終合格かどうか
        final_max_util: 最終の max_util
        per_check_first_pass: 照査項目別の初回合格
    """

    case_id: str = Field(..., description="試行ID（例: L50_B10_rag_true_trial_1）")
    bridge_length_m: float = Field(..., description="橋長 [m]")
    total_width_m: float = Field(..., description="幅員 [m]")
    use_rag: bool = Field(..., description="RAG使用有無")
    trial: int = Field(..., description="試行番号")
    converged: bool = Field(..., description="収束したかどうか")
    num_iterations: int = Field(..., description="修正ループ回数")
    first_pass: bool = Field(..., description="初回合格かどうか")
    first_max_util: float = Field(..., description="初回の max_util")
    first_utilization: dict[str, float] = Field(
        ...,
        description="初回の各照査項目の util（deck/bend/shear/deflection/web_slenderness）",
    )
    final_pass: bool = Field(..., description="最終合格かどうか")
    final_max_util: float = Field(..., description="最終の max_util")
    per_check_first_pass: dict[str, bool] = Field(
        ...,
        description="照査項目別の初回合格（deck/bend/shear/deflection/web_slenderness）",
    )


class AggregatedMetrics(BaseModel):
    """集計結果。

    Attributes:
        first_pass_rate: 初回合格率
        convergence_rate: 収束率
        avg_iterations: 平均修正回数（収束ケースのみ）
        final_pass_rate: 最終合格率
        per_check_first_pass_rate: 照査項目別の初回合格率
    """

    first_pass_rate: float = Field(..., description="初回合格率")
    convergence_rate: float = Field(..., description="収束率")
    avg_iterations: float = Field(..., description="平均修正回数（収束ケースのみ）")
    final_pass_rate: float = Field(..., description="最終合格率")
    per_check_first_pass_rate: dict[str, float] = Field(
        ...,
        description="照査項目別の初回合格率",
    )
