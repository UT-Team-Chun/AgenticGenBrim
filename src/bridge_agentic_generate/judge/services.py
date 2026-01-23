"""Judge サービス層。

仕様: judge_impl.md に基づく決定論的な照査計算。
"""

from __future__ import annotations

import math

from src.bridge_agentic_generate.designer.models import (
    BridgeDesign,
    Components,
    GirderSection,
    Sections,
)
from src.bridge_agentic_generate.judge.models import (
    AllowedActionSpec,
    CurrentDesignValues,
    Diagnostics,
    GoverningCheck,
    JudgeInput,
    JudgeReport,
    PatchActionOp,
    PatchPlan,
    RepairContext,
    Utilization,
)
from src.bridge_agentic_generate.judge.prompts import generate_patch_plan
from src.bridge_agentic_generate.llm_client import LlmModel
from src.bridge_agentic_generate.logger_config import logger

# =============================================================================
# 定数: 許可されるアクションの仕様
# =============================================================================

ALLOWED_ACTIONS: list[AllowedActionSpec] = [
    AllowedActionSpec(op=PatchActionOp.INCREASE_WEB_HEIGHT, allowed_deltas=[100.0, 200.0, 300.0, 500.0]),
    AllowedActionSpec(op=PatchActionOp.INCREASE_WEB_THICKNESS, allowed_deltas=[2.0, 4.0, 6.0]),
    AllowedActionSpec(op=PatchActionOp.INCREASE_TOP_FLANGE_THICKNESS, allowed_deltas=[2.0, 4.0, 6.0]),
    AllowedActionSpec(op=PatchActionOp.INCREASE_BOTTOM_FLANGE_THICKNESS, allowed_deltas=[2.0, 4.0, 6.0]),
    AllowedActionSpec(op=PatchActionOp.INCREASE_TOP_FLANGE_WIDTH, allowed_deltas=[50.0, 100.0]),
    AllowedActionSpec(op=PatchActionOp.INCREASE_BOTTOM_FLANGE_WIDTH, allowed_deltas=[50.0, 100.0]),
    AllowedActionSpec(op=PatchActionOp.SET_DECK_THICKNESS_TO_REQUIRED, allowed_deltas=[0.0]),
    AllowedActionSpec(op=PatchActionOp.FIX_CROSSBEAM_LAYOUT, allowed_deltas=[0.0]),
]

# 横桁配置チェックの許容誤差 [mm]
CROSSBEAM_LAYOUT_TOL_MM = 1.0
# 横桁間隔の上限 [mm]
MAX_PANEL_LENGTH_MM = 20000.0


# =============================================================================
# 断面計算ユーティリティ
# =============================================================================


def calc_girder_section_area(section: GirderSection) -> float:
    """主桁断面積（鋼のみ）を計算する。

    Args:
        section: 主桁断面

    Returns:
        断面積 [mm²]
    """
    a_web = section.web_height * section.web_thickness
    a_tf = section.top_flange_width * section.top_flange_thickness
    a_bf = section.bottom_flange_width * section.bottom_flange_thickness
    return a_web + a_tf + a_bf


def calc_girder_section_properties(
    section: GirderSection,
) -> tuple[float, float, float, float, float]:
    """主桁断面の中立軸・断面二次モーメント・上下縁距離を計算する。

    下端基準で計算。

    Args:
        section: 主桁断面

    Returns:
        (ybar, moment_of_inertia, y_top, y_bottom, total_height) のタプル。
        ybar: 中立軸位置（下端基準）[mm]
        moment_of_inertia: 断面二次モーメント [mm⁴]
        y_top: 上縁距離 [mm]
        y_bottom: 下縁距離 [mm]
        total_height: 全高 [mm]
    """
    # 全高
    total_height = section.bottom_flange_thickness + section.web_height + section.top_flange_thickness

    # 各部材の面積
    a_bf = section.bottom_flange_width * section.bottom_flange_thickness
    a_web = section.web_height * section.web_thickness
    a_tf = section.top_flange_width * section.top_flange_thickness

    # 各部材の図心位置（下端基準）
    y_bf = section.bottom_flange_thickness / 2
    y_web = section.bottom_flange_thickness + section.web_height / 2
    y_tf = section.bottom_flange_thickness + section.web_height + section.top_flange_thickness / 2

    # 中立軸位置（下端基準）
    total_area = a_bf + a_web + a_tf
    ybar = (a_bf * y_bf + a_web * y_web + a_tf * y_tf) / total_area

    # 各部材の自己断面二次モーメント
    i_bf = section.bottom_flange_width * section.bottom_flange_thickness**3 / 12
    i_web = section.web_thickness * section.web_height**3 / 12
    i_tf = section.top_flange_width * section.top_flange_thickness**3 / 12

    # 平行軸の定理
    moment_of_inertia = (
        i_bf + a_bf * (ybar - y_bf) ** 2 + i_web + a_web * (ybar - y_web) ** 2 + i_tf + a_tf * (ybar - y_tf) ** 2
    )

    # 上下縁距離
    y_bottom = ybar
    y_top = total_height - ybar

    return ybar, moment_of_inertia, y_top, y_bottom, total_height


# =============================================================================
# 活荷重計算
# =============================================================================


def calc_live_load_effects(
    p_live_equiv_kn_m2: float,
    girder_spacing_mm: float,
    bridge_length_mm: float,
) -> tuple[float, float]:
    """活荷重断面力を計算する（内部計算）。

    Args:
        p_live_equiv_kn_m2: 等価活荷重面圧 [kN/m²]
        girder_spacing_mm: 主桁間隔（受け持ち幅）[mm]
        bridge_length_mm: 橋長 [mm]

    Returns:
        (M_live_max, V_live_max) のタプル。
        M_live_max: 活荷重最大曲げモーメント [N·mm]
        V_live_max: 活荷重最大せん断力 [N]
    """
    # 受け持ち幅 [m]
    b_tr_m = girder_spacing_mm / 1000

    # 等価線荷重 [kN/m]
    w_live_kn_m = p_live_equiv_kn_m2 * b_tr_m

    # 橋長 [m]
    bridge_length_m = bridge_length_mm / 1000

    # 単純桁の最大断面力
    m_live_max_kn_m = w_live_kn_m * bridge_length_m**2 / 8  # [kN·m]
    v_live_max_kn = w_live_kn_m * bridge_length_m / 2  # [kN]

    # 単位変換: kN·m → N·mm, kN → N
    m_live_max = m_live_max_kn_m * 1e6  # [N·mm]
    v_live_max = v_live_max_kn * 1e3  # [N]

    return m_live_max, v_live_max


# =============================================================================
# 死荷重計算
# =============================================================================


def calc_dead_load(
    girder_section: GirderSection,
    deck_thickness_mm: float,
    girder_spacing_mm: float,
    gamma_steel: float,
    gamma_concrete: float,
) -> tuple[float, float]:
    """死荷重の線荷重を計算する。

    Args:
        girder_section: 主桁断面
        deck_thickness_mm: 床版厚 [mm]
        girder_spacing_mm: 主桁間隔（受け持ち幅）[mm]
        gamma_steel: 鋼の単位体積重量 [N/mm³]
        gamma_concrete: コンクリートの単位体積重量 [N/mm³]

    Returns:
        (w_deck, w_steel) のタプル。両方とも [N/mm]。
    """
    # 床版自重
    w_deck = gamma_concrete * deck_thickness_mm * girder_spacing_mm

    # 鋼桁自重
    a_steel = calc_girder_section_area(girder_section)
    w_steel = gamma_steel * a_steel

    return w_deck, w_steel


def calc_dead_load_effects(w_dead: float, bridge_length_mm: float) -> tuple[float, float]:
    """死荷重断面力を計算する（単純桁・等分布）。

    Args:
        w_dead: 死荷重線荷重 [N/mm]
        bridge_length_mm: 橋長 [mm]

    Returns:
        (M_dead, V_dead) のタプル。
        M_dead: 死荷重曲げモーメント [N·mm]
        V_dead: 死荷重せん断力 [N]
    """
    m_dead = w_dead * bridge_length_mm**2 / 8
    v_dead = w_dead * bridge_length_mm / 2
    return m_dead, v_dead


# =============================================================================
# 床版厚計算
# =============================================================================


def calc_required_deck_thickness(girder_spacing_mm: float) -> float:
    """必要床版厚を計算する。

    道路橋示方書の式: max(30 * L_support_m + 110, 160)

    Args:
        girder_spacing_mm: 主桁間隔 [mm]

    Returns:
        必要床版厚 [mm]
    """
    l_support_m = girder_spacing_mm / 1000
    return max(30 * l_support_m + 110, 160)


def calc_allowable_deflection(bridge_length_mm: float) -> float:
    """許容たわみを計算する（道路橋示方書に基づく）。

    Args:
        bridge_length_mm: 橋長 [mm]

    Returns:
        許容たわみ [mm]
    """
    L_m = bridge_length_mm / 1000  # m に変換

    if L_m <= 10:
        delta_allow_m = L_m / 2000
    elif L_m <= 40:
        delta_allow_m = L_m**2 / 20000
    else:
        delta_allow_m = L_m / 500

    return delta_allow_m * 1000  # mm に変換


# =============================================================================
# メイン照査関数
# =============================================================================


def judge_v1(judge_input: JudgeInput, model: LlmModel) -> JudgeReport:
    """Judge v1 メイン関数。

    決定論的に util を計算し、合否判定・PatchPlan 生成を行う。

    Args:
        judge_input: Judge 入力
        model: PatchPlan 生成に使用する LLM モデル

    Returns:
        JudgeReport
    """
    design = judge_input.bridge_design
    params = judge_input.judge_params
    steel = judge_input.materials_steel
    concrete = judge_input.materials_concrete
    load_input = judge_input.load_input

    # 寸法・断面
    dims = design.dimensions
    girder = design.sections.girder_standard
    deck_thickness = design.components.deck.thickness

    logger.info("Judge v1: 照査開始 L=%.0fmm, B=%.0fmm", dims.bridge_length, dims.total_width)

    # -------------------------------------------------------------------------
    # 1. 活荷重断面力の内部計算
    # -------------------------------------------------------------------------
    m_live_max, v_live_max = calc_live_load_effects(
        p_live_equiv_kn_m2=load_input.p_live_equiv,
        girder_spacing_mm=dims.girder_spacing,
        bridge_length_mm=dims.bridge_length,
    )

    # -------------------------------------------------------------------------
    # 2. 死荷重計算
    # -------------------------------------------------------------------------
    # 受け持ち幅 = girder_spacing
    b_tr = dims.girder_spacing

    w_deck, w_steel = calc_dead_load(
        girder_section=girder,
        deck_thickness_mm=deck_thickness,
        girder_spacing_mm=b_tr,
        gamma_steel=steel.unit_weight,
        gamma_concrete=concrete.unit_weight,
    )
    w_dead = w_deck + w_steel

    m_dead, v_dead = calc_dead_load_effects(w_dead, dims.bridge_length)

    # -------------------------------------------------------------------------
    # 3. 合計断面力
    # -------------------------------------------------------------------------
    m_total = m_dead + m_live_max
    v_total = v_dead + v_live_max

    # -------------------------------------------------------------------------
    # 4. 断面諸量
    # -------------------------------------------------------------------------
    ybar, moment_of_inertia, y_top, y_bottom, _ = calc_girder_section_properties(girder)

    # -------------------------------------------------------------------------
    # 5. 応力度
    # -------------------------------------------------------------------------
    sigma_top = m_total * y_top / moment_of_inertia
    sigma_bottom = m_total * y_bottom / moment_of_inertia

    sigma_allow = params.alpha_bend * steel.fy
    util_bend = max(abs(sigma_top), abs(sigma_bottom)) / sigma_allow

    # -------------------------------------------------------------------------
    # 6. せん断（平均）
    # -------------------------------------------------------------------------
    tau_avg = v_total / (girder.web_thickness * girder.web_height)
    tau_allow = params.alpha_shear * (steel.fy / math.sqrt(3))
    util_shear = abs(tau_avg) / tau_allow

    # -------------------------------------------------------------------------
    # 7. たわみ（活荷重のみ・道路橋示方書準拠）
    # -------------------------------------------------------------------------
    w_eq_live = 8 * m_live_max / (dims.bridge_length**2)
    delta = 5 * w_eq_live * dims.bridge_length**4 / (384 * steel.E * moment_of_inertia)
    delta_allow = calc_allowable_deflection(dims.bridge_length)
    util_deflection = delta / delta_allow

    # -------------------------------------------------------------------------
    # 8. 床版厚 util
    # -------------------------------------------------------------------------
    deck_thickness_required = calc_required_deck_thickness(dims.girder_spacing)
    util_deck = deck_thickness_required / deck_thickness

    # -------------------------------------------------------------------------
    # 9. 横桁配置チェック
    # -------------------------------------------------------------------------
    # panel_length = crossbeam_spacing（仕様書の通り）
    panel_length = dims.panel_length
    num_panels = dims.num_panels if dims.num_panels is not None else 0
    layout_error = abs(panel_length * num_panels - dims.bridge_length)
    crossbeam_layout_ok = (layout_error <= CROSSBEAM_LAYOUT_TOL_MM) and (panel_length <= MAX_PANEL_LENGTH_MM)

    # -------------------------------------------------------------------------
    # 10. governing_check と max_util
    # -------------------------------------------------------------------------
    util_map = {
        GoverningCheck.DECK: util_deck,
        GoverningCheck.BEND: util_bend,
        GoverningCheck.SHEAR: util_shear,
        GoverningCheck.DEFLECTION: util_deflection,
    }
    max_util = max(util_map.values())
    governing_check = max(util_map, key=lambda k: util_map[k])

    # 横桁配置 NG の場合は governing_check を上書き
    if not crossbeam_layout_ok:
        governing_check = GoverningCheck.CROSSBEAM_LAYOUT

    # -------------------------------------------------------------------------
    # 11. pass_fail
    # -------------------------------------------------------------------------
    pass_fail = (max_util <= 1.0) and crossbeam_layout_ok

    # -------------------------------------------------------------------------
    # 12. Utilization / Diagnostics
    # -------------------------------------------------------------------------
    utilization = Utilization(
        deck=util_deck,
        bend=util_bend,
        shear=util_shear,
        deflection=util_deflection,
        max_util=max_util,
        governing_check=governing_check,
    )

    diagnostics = Diagnostics(
        b_tr=b_tr,
        w_dead=w_dead,
        M_dead=m_dead,
        V_dead=v_dead,
        M_live_max=m_live_max,
        V_live_max=v_live_max,
        M_total=m_total,
        V_total=v_total,
        ybar=ybar,
        moment_of_inertia=moment_of_inertia,
        y_top=y_top,
        y_bottom=y_bottom,
        sigma_top=sigma_top,
        sigma_bottom=sigma_bottom,
        tau_avg=tau_avg,
        delta=delta,
        delta_allow=delta_allow,
        sigma_allow=sigma_allow,
        tau_allow=tau_allow,
        deck_thickness_required=deck_thickness_required,
        crossbeam_layout_ok=crossbeam_layout_ok,
    )

    logger.info(
        "Judge v1: util_deck=%.3f, util_bend=%.3f, util_shear=%.3f, util_deflection=%.3f",
        util_deck,
        util_bend,
        util_shear,
        util_deflection,
    )
    logger.info(
        "Judge v1: max_util=%.3f, governing=%s, pass_fail=%s",
        max_util,
        governing_check,
        pass_fail,
    )

    # -------------------------------------------------------------------------
    # 13. PatchPlan 生成
    # -------------------------------------------------------------------------
    if pass_fail:
        # 合格の場合は空の PatchPlan
        patch_plan = PatchPlan(actions=[])
    else:
        # 不合格の場合は LLM で PatchPlan を生成
        repair_context = _build_repair_context(
            design=design,
            utilization=utilization,
            diagnostics=diagnostics,
            deck_thickness_required=deck_thickness_required,
        )
        patch_plan = generate_patch_plan(repair_context, model)

        # フォールバック: pass_fail = False かつ actions が空の場合はエラー
        if not patch_plan.actions:
            raise ValueError("Judge v1: pass_fail=False だが PatchPlan が空です。LLM が修正案を生成できませんでした。")

    return JudgeReport(
        pass_fail=pass_fail,
        utilization=utilization,
        diagnostics=diagnostics,
        patch_plan=patch_plan,
    )


def _build_repair_context(
    design: BridgeDesign,
    utilization: Utilization,
    diagnostics: Diagnostics,
    deck_thickness_required: float,
) -> RepairContext:
    """RepairContext を構築する。

    Args:
        design: BridgeDesign
        utilization: Utilization
        diagnostics: Diagnostics
        deck_thickness_required: 必要床版厚 [mm]

    Returns:
        RepairContext
    """
    girder = design.sections.girder_standard
    dims = design.dimensions

    current_design = CurrentDesignValues(
        web_height=girder.web_height,
        web_thickness=girder.web_thickness,
        top_flange_width=girder.top_flange_width,
        top_flange_thickness=girder.top_flange_thickness,
        bottom_flange_width=girder.bottom_flange_width,
        bottom_flange_thickness=girder.bottom_flange_thickness,
        deck_thickness=design.components.deck.thickness,
        panel_length=dims.panel_length,
        num_panels=dims.num_panels if dims.num_panels is not None else 0,
    )

    return RepairContext(
        utilization=utilization,
        crossbeam_layout_ok=diagnostics.crossbeam_layout_ok,
        governing_check=utilization.governing_check,
        diagnostics=diagnostics,
        current_design=current_design,
        allowed_actions=ALLOWED_ACTIONS,
        deck_thickness_required=deck_thickness_required,
    )


# =============================================================================
# PatchPlan 適用
# =============================================================================


def apply_patch_plan(
    design: BridgeDesign,
    patch_plan: PatchPlan,
    deck_thickness_required: float | None = None,
) -> BridgeDesign:
    """PatchPlan を BridgeDesign に適用する。

    Args:
        design: 元の BridgeDesign
        patch_plan: 適用する PatchPlan
        deck_thickness_required: 必要床版厚 [mm]（SET_DECK_THICKNESS_TO_REQUIRED 用）

    Returns:
        修正後の新しい BridgeDesign
    """
    # 現在の値を取り出す
    dims = design.dimensions
    girder = design.sections.girder_standard
    crossbeam = design.sections.crossbeam_standard
    deck = design.components.deck

    # 各アクションを適用
    for action in patch_plan.actions:
        op = action.op
        delta = action.delta_mm

        if op == PatchActionOp.INCREASE_WEB_HEIGHT:
            girder = girder.model_copy(update={"web_height": girder.web_height + delta})
            logger.info("apply_patch_plan: web_height += %.0f → %.0f", delta, girder.web_height)

        elif op == PatchActionOp.INCREASE_WEB_THICKNESS:
            girder = girder.model_copy(update={"web_thickness": girder.web_thickness + delta})
            logger.info("apply_patch_plan: web_thickness += %.0f → %.0f", delta, girder.web_thickness)

        elif op == PatchActionOp.INCREASE_TOP_FLANGE_THICKNESS:
            girder = girder.model_copy(update={"top_flange_thickness": girder.top_flange_thickness + delta})
            logger.info("apply_patch_plan: top_flange_thickness += %.0f → %.0f", delta, girder.top_flange_thickness)

        elif op == PatchActionOp.INCREASE_BOTTOM_FLANGE_THICKNESS:
            girder = girder.model_copy(update={"bottom_flange_thickness": girder.bottom_flange_thickness + delta})
            logger.info(
                "apply_patch_plan: bottom_flange_thickness += %.0f → %.0f", delta, girder.bottom_flange_thickness
            )

        elif op == PatchActionOp.INCREASE_TOP_FLANGE_WIDTH:
            girder = girder.model_copy(update={"top_flange_width": girder.top_flange_width + delta})
            logger.info("apply_patch_plan: top_flange_width += %.0f → %.0f", delta, girder.top_flange_width)

        elif op == PatchActionOp.INCREASE_BOTTOM_FLANGE_WIDTH:
            girder = girder.model_copy(update={"bottom_flange_width": girder.bottom_flange_width + delta})
            logger.info("apply_patch_plan: bottom_flange_width += %.0f → %.0f", delta, girder.bottom_flange_width)

        elif op == PatchActionOp.SET_DECK_THICKNESS_TO_REQUIRED:
            if deck_thickness_required is None:
                raise ValueError("deck_thickness_required が指定されていません")
            deck = deck.model_copy(update={"thickness": deck_thickness_required})
            logger.info("apply_patch_plan: deck.thickness = %.0f (required)", deck_thickness_required)

        elif op == PatchActionOp.FIX_CROSSBEAM_LAYOUT:
            # num_panels を調整する方式（仕様推奨）
            new_num_panels = round(dims.bridge_length / dims.panel_length)
            dims = dims.model_copy(update={"num_panels": new_num_panels})
            logger.info(
                "apply_patch_plan: num_panels = round(%.0f / %.0f) = %d",
                dims.bridge_length,
                dims.panel_length,
                new_num_panels,
            )

        else:
            logger.warning("apply_patch_plan: 未知の操作 %s をスキップ", op)

    # 新しい BridgeDesign を構築
    new_sections = Sections(
        girder_standard=girder,
        crossbeam_standard=crossbeam,
    )
    new_components = Components(
        deck=deck,
    )
    return BridgeDesign(
        dimensions=dims,
        sections=new_sections,
        components=new_components,
    )
