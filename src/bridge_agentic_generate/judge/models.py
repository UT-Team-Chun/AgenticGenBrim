"""Judge 用の Pydantic モデル定義。

仕様: judge_impl.md に基づく。
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from src.bridge_agentic_generate.designer.models import BridgeDesign

# =============================================================================
# 入力モデル
# =============================================================================


class JudgeParams(BaseModel):
    """Judge の許容応力度・たわみ制限パラメータ。

    Attributes:
        alpha_bend: 曲げ許容応力度係数。sigma_allow = alpha_bend * fy。
        alpha_shear: せん断許容応力度係数。tau_allow = alpha_shear * (fy / sqrt(3))。
        deflection_ratio: たわみ制限比。delta_allow = L / deflection_ratio。
    """

    alpha_bend: float = Field(default=0.6, description="曲げ許容応力度係数")
    alpha_shear: float = Field(default=0.6, description="せん断許容応力度係数")
    deflection_ratio: float = Field(default=600.0, description="たわみ制限比")


class MaterialsSteel(BaseModel):
    """鋼材の材料特性。

    Attributes:
        E: ヤング率 [N/mm²]
        fy: 降伏点 [N/mm²]
        unit_weight: 単位体積重量 [N/mm³]（kN/m³ から変換済み）
    """

    E: float = Field(default=2.0e5, description="ヤング率 [N/mm²]")
    fy: float = Field(default=235.0, description="降伏点 [N/mm²]")
    unit_weight: float = Field(default=78.5e-6, description="単位体積重量 [N/mm³]（78.5 kN/m³ = 78.5e-6 N/mm³）")


class MaterialsConcrete(BaseModel):
    """コンクリートの材料特性。

    Attributes:
        unit_weight: 単位体積重量 [N/mm³]（kN/m³ から変換済み）
    """

    unit_weight: float = Field(default=25.0e-6, description="単位体積重量 [N/mm³]（25 kN/m³ = 25e-6 N/mm³）")


class LoadInput(BaseModel):
    """活荷重入力。

    Attributes:
        p_live_equiv: 等価活荷重面圧 [kN/m²]。デフォルト12。
    """

    p_live_equiv: float = Field(
        default=12.0,
        description="等価活荷重面圧 [kN/m²]。デフォルト12、感度解析で6〜12を振る。",
    )


class JudgeInput(BaseModel):
    """Judge に渡す入力。

    Attributes:
        bridge_design: BridgeDesign（既存スキーマ）
        load_input: 活荷重入力
        materials_steel: 鋼材の材料特性
        materials_concrete: コンクリートの材料特性
        judge_params: Judge パラメータ
    """

    bridge_design: BridgeDesign
    load_input: LoadInput = Field(default_factory=LoadInput)
    materials_steel: MaterialsSteel = Field(default_factory=MaterialsSteel)
    materials_concrete: MaterialsConcrete = Field(default_factory=MaterialsConcrete)
    judge_params: JudgeParams = Field(default_factory=JudgeParams)


# =============================================================================
# 出力モデル
# =============================================================================


class GoverningCheck(StrEnum):
    """支配的なチェック項目。"""

    DECK = "deck"
    BEND = "bend"
    SHEAR = "shear"
    DEFLECTION = "deflection"
    CROSSBEAM_LAYOUT = "crossbeam_layout"


class Utilization(BaseModel):
    """各項目の util（需要/許容）。

    Attributes:
        deck: 床版厚 util（required/provided）
        bend: 曲げ応力度 util
        shear: せん断応力度 util（平均せん断）
        deflection: たわみ util
        max_util: 最大 util
        governing_check: 支配的なチェック項目
    """

    deck: float = Field(..., description="床版厚 util（required/provided）")
    bend: float = Field(..., description="曲げ応力度 util")
    shear: float = Field(..., description="せん断応力度 util（平均せん断）")
    deflection: float = Field(..., description="たわみ util")
    max_util: float = Field(..., description="最大 util")
    governing_check: GoverningCheck = Field(..., description="支配的なチェック項目")


class Diagnostics(BaseModel):
    """Judge の中間計算量（デバッグ・説明用）。"""

    b_tr: float = Field(..., description="受け持ち幅 [mm]")
    w_dead: float = Field(..., description="死荷重線荷重 [N/mm]")
    M_dead: float = Field(..., description="死荷重曲げモーメント [N·mm]")
    V_dead: float = Field(..., description="死荷重せん断力 [N]")
    M_live_max: float = Field(..., description="活荷重最大曲げモーメント [N·mm]")
    V_live_max: float = Field(..., description="活荷重最大せん断力 [N]")
    M_total: float = Field(..., description="合計曲げモーメント [N·mm]")
    V_total: float = Field(..., description="合計せん断力 [N]")
    ybar: float = Field(..., description="中立軸位置（下端基準）[mm]")
    moment_of_inertia: float = Field(..., description="断面二次モーメント [mm⁴]")
    y_top: float = Field(..., description="上縁距離 [mm]")
    y_bottom: float = Field(..., description="下縁距離 [mm]")
    sigma_top: float = Field(..., description="上縁応力度 [N/mm²]")
    sigma_bottom: float = Field(..., description="下縁応力度 [N/mm²]")
    tau_avg: float = Field(..., description="平均せん断応力度 [N/mm²]")
    delta: float = Field(..., description="たわみ [mm]")
    delta_allow: float = Field(..., description="許容たわみ [mm]")
    sigma_allow: float = Field(..., description="許容曲げ応力度 [N/mm²]")
    tau_allow: float = Field(..., description="許容せん断応力度 [N/mm²]")
    deck_thickness_required: float = Field(..., description="必要床版厚 [mm]")
    crossbeam_layout_ok: bool = Field(..., description="横桁配置の整合性")


class PatchActionOp(StrEnum):
    """許可される修正操作。"""

    INCREASE_WEB_HEIGHT = "increase_web_height"
    INCREASE_WEB_THICKNESS = "increase_web_thickness"
    INCREASE_TOP_FLANGE_THICKNESS = "increase_top_flange_thickness"
    INCREASE_BOTTOM_FLANGE_THICKNESS = "increase_bottom_flange_thickness"
    INCREASE_TOP_FLANGE_WIDTH = "increase_top_flange_width"
    INCREASE_BOTTOM_FLANGE_WIDTH = "increase_bottom_flange_width"
    SET_DECK_THICKNESS_TO_REQUIRED = "set_deck_thickness_to_required"
    FIX_CROSSBEAM_LAYOUT = "fix_crossbeam_layout"


class PatchAction(BaseModel):
    """修正アクション 1 件。

    Attributes:
        op: 操作種別
        path: 対象フィールドパス（例: "sections.girder_standard.web_height"）
        delta_mm: 変更量 [mm]
        reason: 変更理由
    """

    op: PatchActionOp = Field(..., description="操作種別")
    path: str = Field(..., description="対象フィールドパス")
    delta_mm: float = Field(..., description="変更量 [mm]")
    reason: str = Field(..., description="変更理由")


class PatchPlan(BaseModel):
    """修正計画（LLM が生成）。

    Attributes:
        actions: 修正アクションのリスト（最大3件）
    """

    actions: list[PatchAction] = Field(default_factory=list, description="修正アクションのリスト")


class JudgeReport(BaseModel):
    """Judge の出力。

    Attributes:
        pass_fail: 合否（全 util ≤ 1.0 かつ crossbeam_layout_ok）
        utilization: 各項目の util
        diagnostics: 中間計算量
        patch_plan: 修正計画
    """

    pass_fail: bool = Field(..., description="合否")
    utilization: Utilization = Field(..., description="各項目の util")
    diagnostics: Diagnostics = Field(..., description="中間計算量")
    patch_plan: PatchPlan = Field(..., description="修正計画")


# =============================================================================
# RepairContext（LLM に渡すコンテキスト）
# =============================================================================


class AllowedActionSpec(BaseModel):
    """許可されるアクションの仕様。"""

    op: PatchActionOp = Field(..., description="操作種別")
    allowed_deltas: list[float] = Field(..., description="許可される変更量 [mm]")


class CurrentDesignValues(BaseModel):
    """現在の設計値（LLM に渡す）。"""

    web_height: float
    web_thickness: float
    top_flange_width: float
    top_flange_thickness: float
    bottom_flange_width: float
    bottom_flange_thickness: float
    deck_thickness: float
    panel_length: float
    num_panels: int


class RepairContext(BaseModel):
    """LLM に渡す修正コンテキスト。"""

    utilization: Utilization = Field(..., description="各項目の util")
    crossbeam_layout_ok: bool = Field(..., description="横桁配置の整合性")
    governing_check: GoverningCheck = Field(..., description="支配的なチェック項目")
    diagnostics: Diagnostics = Field(..., description="主要中間量")
    current_design: CurrentDesignValues = Field(..., description="現在の設計値")
    allowed_actions: list[AllowedActionSpec] = Field(..., description="許可されるアクション")
    deck_thickness_required: float = Field(..., description="必要床版厚 [mm]")
    priorities: str = Field(
        default="1. 安全: すべての util ≤ 1.0。2. 施工性: 急激な変更を避ける。3. 鋼重最小: 同等なら軽い案。",
        description="修正の優先順位",
    )


# =============================================================================
# RepairLoop 結果モデル
# =============================================================================


class RepairIteration(BaseModel):
    """修正ループの1イテレーション結果。

    Attributes:
        iteration: イテレーション番号（0から開始、0は初期設計）
        design: このイテレーション時点の BridgeDesign
        report: このイテレーションの JudgeReport（照査結果）
    """

    iteration: int = Field(..., description="イテレーション番号（0から開始）")
    design: BridgeDesign = Field(..., description="この時点の設計")
    report: JudgeReport = Field(..., description="照査結果")


class RepairLoopResult(BaseModel):
    """修正ループの全体結果。

    Attributes:
        converged: 収束したかどうか（pass_fail=True に到達したか）
        iterations: 各イテレーションの結果リスト
        final_design: 最終設計
        final_report: 最終照査結果
    """

    converged: bool = Field(..., description="収束したかどうか")
    iterations: list[RepairIteration] = Field(..., description="各イテレーションの結果")
    final_design: BridgeDesign = Field(..., description="最終設計")
    final_report: JudgeReport = Field(..., description="最終照査結果")
