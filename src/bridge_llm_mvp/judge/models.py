from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from bridge_llm_mvp.designer.models import BridgeDesign


class CheckStatus(str, Enum):
    OK = "ok"
    MINOR_NG = "minor_ng"
    CRITICAL_NG = "critical_ng"


class OverallStatus(str, Enum):
    OK = "ok"
    OK_WITH_MINOR_ISSUES = "ok_with_minor_issues"
    NG = "ng"


class CheckItem(BaseModel):
    """個々のチェック項目の結果。"""

    item: str = Field(
        ...,
        description="チェック項目名（例: deck_thickness, web_thickness など）",
    )
    status: CheckStatus
    design_value: float | None = Field(
        None,
        description="設計側の値（代表値）。ない場合は None。",
    )
    required_min: float | None = Field(
        None,
        description="下限型の条件のときの必要最小値。ない場合は None。",
    )
    required_max: float | None = Field(
        None,
        description="上限型の条件のときの必要最大値。ない場合は None。",
    )
    margin: float | None = Field(
        None,
        description="余裕度（min の場合: design - required_min, max の場合: required_max - design）。",
    )
    comment: str = Field(
        "",
        description="簡単な日本語コメント。",
    )


class JudgeInput(BaseModel):
    """Judge に渡す入力。

    元の L,B と、Designer の設計結果をまとめて渡す。
    """

    span_length_m: float
    total_width_m: float
    design: BridgeDesign


class JudgeResult(BaseModel):
    """Judge の出力トップレベル。"""

    overall_status: OverallStatus
    checks: list[CheckItem]
