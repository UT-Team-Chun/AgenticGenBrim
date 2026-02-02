"""Judge サービス層。

仕様: judge_impl.md に基づく決定論的な照査計算。
"""

from __future__ import annotations

import math

from src.bridge_agentic_generate.designer.models import (
    BridgeDesign,
    Components,
    CrossbeamSection,
    DependencyRule,
    GirderSection,
    Sections,
)
from src.bridge_agentic_generate.judge.models import (
    AllowedActionSpec,
    CurrentDesignValues,
    Diagnostics,
    GirderLoadResult,
    GoverningCheck,
    JudgeInput,
    JudgeReport,
    LoadEffectsResult,
    NotApplicableError,
    PatchActionOp,
    PatchPlan,
    RepairContext,
    SteelGrade,
    Utilization,
    get_fy,
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
    AllowedActionSpec(op=PatchActionOp.INCREASE_NUM_GIRDERS, allowed_deltas=[1.0]),
]

# 横桁配置チェックの許容誤差 [mm]
CROSSBEAM_LAYOUT_TOL_MM = 1.0
# 横桁間隔の上限 [mm]
MAX_PANEL_LENGTH_MM = 20000.0

# 腹板幅厚比照査の除数（鋼種別）
WEB_SLENDERNESS_DIVISOR_SM490 = 130
WEB_SLENDERNESS_DIVISOR_SM400 = 152

# =============================================================================
# L荷重計算定数（B活荷重）
# =============================================================================

# 適用限界支間長 [m]
MAX_APPLICABLE_SPAN_M = 80.0

# 載荷長上限 [m]
MAX_LOADING_LENGTH_M = 10.0

# p1 面圧（曲げ照査用）[kN/m²]
P1_M_KN_M2 = 10.0

# p1 面圧（せん断照査用）[kN/m²]
P1_V_KN_M2 = 12.0

# p2 面圧（支間80m以下）[kN/m²]
P2_KN_M2 = 3.5

# 主載荷幅 [m]
MAIN_LOADING_WIDTH_M = 5.5


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
# 腹板幅厚比照査
# =============================================================================


def get_min_web_thickness(grade: SteelGrade, web_height: float) -> float:
    """鋼種とフランジ間距離から最小腹板厚を返す。

    Args:
        grade: 鋼種
        web_height: フランジ間距離 [mm]

    Returns:
        最小腹板厚 [mm]
    """
    if grade == SteelGrade.SM490:
        return web_height / WEB_SLENDERNESS_DIVISOR_SM490
    elif grade == SteelGrade.SM400:
        return web_height / WEB_SLENDERNESS_DIVISOR_SM400
    else:
        # 未知の鋼種はSM490相当（保守的）
        return web_height / WEB_SLENDERNESS_DIVISOR_SM490


# =============================================================================
# L荷重計算（p1/p2ルール）
# =============================================================================


def calc_overhang(total_width_mm: float, num_girders: int, girder_spacing_mm: float) -> float:
    """張り出し幅を計算する。

    Args:
        total_width_mm: 橋全幅 [mm]
        num_girders: 主桁本数
        girder_spacing_mm: 主桁間隔 [mm]

    Returns:
        張り出し幅 [mm]
    """
    return (total_width_mm - (num_girders - 1) * girder_spacing_mm) / 2


def calc_tributary_width(
    girder_index: int,
    num_girders: int,
    overhang_mm: float,
    girder_spacing_mm: float,
) -> float:
    """主桁 i の受け持ち幅 b_i を計算する。

    Args:
        girder_index: 主桁インデックス（0始まり）
        num_girders: 主桁本数
        overhang_mm: 張り出し幅 [mm]
        girder_spacing_mm: 主桁間隔 [mm]

    Returns:
        受け持ち幅 [mm]
    """
    # 端桁（最初と最後）
    if girder_index == 0 or girder_index == num_girders - 1:
        return overhang_mm + girder_spacing_mm / 2
    # 中間桁
    return girder_spacing_mm


def calc_beff(b_i_m: float) -> float:
    """実効幅を計算する。

    主載荷幅 5.5m（100%）+ 残り（1/2）を、最不利に主載荷をその桁に寄せられるとして計算。

    Args:
        b_i_m: 受け持ち幅 [m]

    Returns:
        実効幅 [m]
    """
    return 0.5 * b_i_m + 0.5 * min(b_i_m, MAIN_LOADING_WIDTH_M)


def calc_gamma(L_m: float, D_m: float) -> float:
    """等価係数を計算する（曲げ・せん断共通）。

    部分載荷を等価な全スパン等分布に換算するための係数。

    Args:
        L_m: 支間長 [m]
        D_m: 載荷長 [m]

    Returns:
        等価係数 γ

    Raises:
        ValueError: L_m <= 0 の場合
    """
    if L_m <= 0:
        raise ValueError(f"支間長は正の値である必要があります: L_m={L_m}")
    return D_m * (2 * L_m - D_m) / (L_m**2)


def calc_girder_load_effects(
    bridge_length_mm: float,
    total_width_mm: float,
    num_girders: int,
    girder_spacing_mm: float,
    girder_section: GirderSection,
    deck_thickness_mm: float,
    gamma_steel: float,
    gamma_concrete: float,
) -> LoadEffectsResult:
    """主桁の荷重計算（死荷重・活荷重統合）。

    全主桁をループして各桁の死荷重・活荷重・合計断面力を計算し、
    governing 桁を特定する。

    Args:
        bridge_length_mm: 橋長 [mm]
        total_width_mm: 橋全幅 [mm]
        num_girders: 主桁本数
        girder_spacing_mm: 主桁間隔 [mm]
        girder_section: 主桁断面
        deck_thickness_mm: 床版厚 [mm]
        gamma_steel: 鋼の単位体積重量 [N/mm³]
        gamma_concrete: コンクリートの単位体積重量 [N/mm³]

    Returns:
        LoadEffectsResult: 全主桁の結果と governing 桁

    Raises:
        NotApplicableError: L > 80m の場合
        ValueError: L <= 0 または b_i <= 0 の場合
    """
    # 単位変換: mm → m
    L_m = bridge_length_mm / 1000

    # 適用範囲チェック
    if L_m <= 0:
        raise ValueError(f"支間長は正の値である必要があります: L_m={L_m}")
    if L_m > MAX_APPLICABLE_SPAN_M:
        raise NotApplicableError(f"支間長 {L_m}m は適用範囲外です（上限: {MAX_APPLICABLE_SPAN_M}m）")

    # 載荷長 D
    D_m = min(MAX_LOADING_LENGTH_M, L_m)

    # 等価係数 γ
    gamma = calc_gamma(L_m, D_m)

    # 等価面圧
    p_eq_M = P2_KN_M2 + P1_M_KN_M2 * gamma  # 曲げ用
    p_eq_V = P2_KN_M2 + P1_V_KN_M2 * gamma  # せん断用

    # 張り出し幅
    overhang_mm = calc_overhang(total_width_mm, num_girders, girder_spacing_mm)
    overhang_m = overhang_mm / 1000

    # 鋼桁自重（全桁共通）
    a_steel = calc_girder_section_area(girder_section)
    w_steel = gamma_steel * a_steel

    # 各主桁の計算
    girder_results: list[GirderLoadResult] = []

    for i in range(num_girders):
        # 受け持ち幅
        b_i_mm = calc_tributary_width(i, num_girders, overhang_mm, girder_spacing_mm)
        b_i_m = b_i_mm / 1000

        if b_i_m <= 0:
            raise ValueError(f"主桁 {i} の受け持ち幅が0以下です: b_i_m={b_i_m}")

        # 死荷重
        w_deck = gamma_concrete * deck_thickness_mm * b_i_mm
        w_dead = w_deck + w_steel  # [N/mm]
        M_dead = w_dead * bridge_length_mm**2 / 8  # [N·mm]
        V_dead = w_dead * bridge_length_mm / 2  # [N]

        # 活荷重
        b_eff_m = calc_beff(b_i_m)
        w_M = p_eq_M * b_eff_m  # [kN/m]
        w_V = p_eq_V * b_eff_m  # [kN/m]

        # 単純梁の最大断面力
        M_live_kn_m = w_M * L_m**2 / 8  # [kN·m]
        V_live_kn = w_V * L_m / 2  # [kN]

        # 単位変換: kN·m → N·mm, kN → N
        M_live = M_live_kn_m * 1e6  # [N·mm]
        V_live = V_live_kn * 1e3  # [N]

        # 合計
        M_total = M_dead + M_live
        V_total = V_dead + V_live

        girder_results.append(
            GirderLoadResult(
                girder_index=i,
                b_i_m=b_i_m,
                w_dead=w_dead,
                M_dead=M_dead,
                V_dead=V_dead,
                b_eff_m=b_eff_m,
                w_M=w_M,
                w_V=w_V,
                M_live=M_live,
                V_live=V_live,
                M_total=M_total,
                V_total=V_total,
            )
        )

    # governing 桁を選定（曲げとせん断で別々）
    governing_girder_index_bend = max(range(num_girders), key=lambda i: girder_results[i].M_total)
    governing_girder_index_shear = max(range(num_girders), key=lambda i: girder_results[i].V_total)
    M_total_max = girder_results[governing_girder_index_bend].M_total
    V_total_max = girder_results[governing_girder_index_shear].V_total

    return LoadEffectsResult(
        L_m=L_m,
        D_m=D_m,
        p2=P2_KN_M2,
        p1_M=P1_M_KN_M2,
        p1_V=P1_V_KN_M2,
        gamma=gamma,
        p_eq_M=p_eq_M,
        p_eq_V=p_eq_V,
        overhang_m=overhang_m,
        girder_results=girder_results,
        governing_girder_index_bend=governing_girder_index_bend,
        governing_girder_index_shear=governing_girder_index_shear,
        M_total_max=M_total_max,
        V_total_max=V_total_max,
    )


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
    """必要床版厚を計算する（照査用）。

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
# 計算ロジック抽出
# =============================================================================


def _calculate_utilization_and_diagnostics(
    judge_input: JudgeInput,
) -> tuple[Utilization, Diagnostics, bool]:
    """util と diagnostics を計算する（LLM呼び出しなし）。

    Args:
        judge_input: Judge 入力

    Returns:
        (Utilization, Diagnostics, pass_fail) のタプル
    """
    design = judge_input.bridge_design
    params = judge_input.judge_params
    steel = judge_input.materials_steel
    concrete = judge_input.materials_concrete

    # 寸法・断面
    dims = design.dimensions
    girder = design.sections.girder_standard
    deck_thickness = design.components.deck.thickness

    # -------------------------------------------------------------------------
    # 1. 荷重計算（死荷重・活荷重統合、桁別計算）
    # -------------------------------------------------------------------------
    load_effects = calc_girder_load_effects(
        bridge_length_mm=dims.bridge_length,
        total_width_mm=dims.total_width,
        num_girders=dims.num_girders,
        girder_spacing_mm=dims.girder_spacing,
        girder_section=girder,
        deck_thickness_mm=deck_thickness,
        gamma_steel=steel.unit_weight,
        gamma_concrete=concrete.unit_weight,
    )

    # governing 桁の断面力を取得
    governing_bend_result = load_effects.girder_results[load_effects.governing_girder_index_bend]
    governing_shear_result = load_effects.girder_results[load_effects.governing_girder_index_shear]
    m_total = governing_bend_result.M_total
    v_total = governing_shear_result.V_total

    # -------------------------------------------------------------------------
    # 4. 断面諸量
    # -------------------------------------------------------------------------
    ybar, moment_of_inertia, y_top, y_bottom, _ = calc_girder_section_properties(girder)

    # -------------------------------------------------------------------------
    # 5. 部材ごとの降伏点を計算
    # -------------------------------------------------------------------------
    fy_top = get_fy(steel.grade, girder.top_flange_thickness)
    fy_bottom = get_fy(steel.grade, girder.bottom_flange_thickness)
    fy_web = get_fy(steel.grade, girder.web_thickness)

    # -------------------------------------------------------------------------
    # 6. 応力度（曲げ: 上下フランジ別）
    # -------------------------------------------------------------------------
    sigma_top = m_total * y_top / moment_of_inertia
    sigma_bottom = m_total * y_bottom / moment_of_inertia

    sigma_allow_top = params.alpha_bend * fy_top
    sigma_allow_bottom = params.alpha_bend * fy_bottom

    util_bend_top = abs(sigma_top) / sigma_allow_top
    util_bend_bottom = abs(sigma_bottom) / sigma_allow_bottom
    util_bend = max(util_bend_top, util_bend_bottom)

    # -------------------------------------------------------------------------
    # 7. せん断（平均、ウェブの降伏点を使用）
    # -------------------------------------------------------------------------
    tau_avg = v_total / (girder.web_thickness * girder.web_height)
    tau_allow = params.alpha_shear * (fy_web / math.sqrt(3))
    util_shear = abs(tau_avg) / tau_allow

    # -------------------------------------------------------------------------
    # 8. たわみ（活荷重のみ・道路橋示方書準拠）
    # -------------------------------------------------------------------------
    # M_live が最大の桁を選定（たわみ照査は活荷重のみ）
    m_live_max = max(gr.M_live for gr in load_effects.girder_results)
    w_eq_live = 8 * m_live_max / (dims.bridge_length**2)
    delta = 5 * w_eq_live * dims.bridge_length**4 / (384 * steel.E * moment_of_inertia)
    delta_allow = calc_allowable_deflection(dims.bridge_length)
    util_deflection = delta / delta_allow

    # -------------------------------------------------------------------------
    # 9. 床版厚 util
    # -------------------------------------------------------------------------
    deck_thickness_required = calc_required_deck_thickness(dims.girder_spacing)
    util_deck = deck_thickness_required / deck_thickness

    # -------------------------------------------------------------------------
    # 9.5. 腹板幅厚比 util
    # -------------------------------------------------------------------------
    web_thickness_min_required = get_min_web_thickness(steel.grade, girder.web_height)
    util_web_slenderness = web_thickness_min_required / girder.web_thickness

    # -------------------------------------------------------------------------
    # 10. 横桁配置チェック
    # -------------------------------------------------------------------------
    # panel_length = crossbeam_spacing（仕様書の通り）
    panel_length = dims.panel_length
    num_panels = dims.num_panels if dims.num_panels is not None else 0
    layout_error = abs(panel_length * num_panels - dims.bridge_length)
    crossbeam_layout_ok = (layout_error <= CROSSBEAM_LAYOUT_TOL_MM) and (panel_length <= MAX_PANEL_LENGTH_MM)

    # -------------------------------------------------------------------------
    # 11. governing_check と max_util
    # -------------------------------------------------------------------------
    util_map = {
        GoverningCheck.DECK: util_deck,
        GoverningCheck.BEND: util_bend,
        GoverningCheck.SHEAR: util_shear,
        GoverningCheck.DEFLECTION: util_deflection,
        GoverningCheck.WEB_SLENDERNESS: util_web_slenderness,
    }
    max_util = max(util_map.values())
    governing_check = max(util_map, key=lambda k: util_map[k])

    # 横桁配置 NG の場合は governing_check を上書き
    if not crossbeam_layout_ok:
        governing_check = GoverningCheck.CROSSBEAM_LAYOUT

    # -------------------------------------------------------------------------
    # 12. pass_fail
    # -------------------------------------------------------------------------
    pass_fail = (max_util <= 1.0) and crossbeam_layout_ok

    # -------------------------------------------------------------------------
    # 13. Utilization / Diagnostics
    # -------------------------------------------------------------------------
    utilization = Utilization(
        deck=util_deck,
        bend=util_bend,
        shear=util_shear,
        deflection=util_deflection,
        web_slenderness=util_web_slenderness,
        max_util=max_util,
        governing_check=governing_check,
    )

    diagnostics = Diagnostics(
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
        fy_top_flange=fy_top,
        fy_bottom_flange=fy_bottom,
        fy_web=fy_web,
        sigma_allow_top=sigma_allow_top,
        sigma_allow_bottom=sigma_allow_bottom,
        tau_allow=tau_allow,
        deck_thickness_required=deck_thickness_required,
        web_thickness_min_required=web_thickness_min_required,
        crossbeam_layout_ok=crossbeam_layout_ok,
        load_effects=load_effects,
        governing_girder_index_bend=load_effects.governing_girder_index_bend,
        governing_girder_index_shear=load_effects.governing_girder_index_shear,
    )

    return utilization, diagnostics, pass_fail


def judge_v1_lightweight(judge_input: JudgeInput) -> tuple[Utilization, Diagnostics]:
    """軽量版Judge（LLM呼び出しなし）。PatchPlanの仮適用評価用。

    Args:
        judge_input: Judge 入力

    Returns:
        (Utilization, Diagnostics) のタプル
    """
    utilization, diagnostics, _ = _calculate_utilization_and_diagnostics(judge_input)
    return utilization, diagnostics


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
    dims = design.dimensions

    logger.info("Judge v1: 照査開始 L=%.0fmm, B=%.0fmm", dims.bridge_length, dims.total_width)

    # -------------------------------------------------------------------------
    # 1. util / diagnostics / pass_fail を計算
    # -------------------------------------------------------------------------
    utilization, diagnostics, pass_fail = _calculate_utilization_and_diagnostics(judge_input)

    logger.info(
        "Judge v1: util_deck=%.3f, util_bend=%.3f, util_shear=%.3f, util_deflection=%.3f, util_web_slenderness=%.3f",
        utilization.deck,
        utilization.bend,
        utilization.shear,
        utilization.deflection,
        utilization.web_slenderness,
    )
    logger.info(
        "Judge v1: max_util=%.3f, governing=%s, pass_fail=%s",
        utilization.max_util,
        utilization.governing_check,
        pass_fail,
    )

    # -------------------------------------------------------------------------
    # 2. PatchPlan 生成
    # -------------------------------------------------------------------------
    evaluated_candidates = None
    if pass_fail:
        # 合格の場合は空の PatchPlan
        patch_plan = PatchPlan(actions=[])
    else:
        # 不合格の場合は LLM で PatchPlan を生成
        repair_context = _build_repair_context(
            design=design,
            utilization=utilization,
            diagnostics=diagnostics,
            deck_thickness_required=diagnostics.deck_thickness_required,
        )
        patch_plan, evaluated_candidates = generate_patch_plan(
            context=repair_context,
            model=model,
            design=design,
            judge_input_base=judge_input,
        )

        # フォールバック: pass_fail = False かつ actions が空の場合はエラー
        if not patch_plan.actions:
            raise ValueError("Judge v1: pass_fail=False だが PatchPlan が空です。LLM が修正案を生成できませんでした。")

    return JudgeReport(
        pass_fail=pass_fail,
        utilization=utilization,
        diagnostics=diagnostics,
        patch_plan=patch_plan,
        evaluated_candidates=evaluated_candidates,
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
        num_girders=dims.num_girders,
        girder_spacing=dims.girder_spacing,
        total_width=dims.total_width,
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
            # 10mm単位で切り上げて余裕を持たせる
            new_thickness = math.ceil(deck_thickness_required / 10) * 10
            deck = deck.model_copy(update={"thickness": new_thickness})
            logger.info(
                "apply_patch_plan: deck.thickness = %.0f (required=%.1f, 10mm切り上げ)",
                new_thickness,
                deck_thickness_required,
            )

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

        elif op == PatchActionOp.INCREASE_NUM_GIRDERS:
            # 桁本数を増やす（delta は整数として扱う）
            new_num_girders = dims.num_girders + int(delta)
            # girder_spacing を再計算（overhang は維持）
            # 全幅 B = (num_girders - 1) × girder_spacing + 2 × overhang
            # → girder_spacing = (B - 2 × overhang) / (num_girders - 1)
            overhang = calc_overhang(dims.total_width, dims.num_girders, dims.girder_spacing)
            new_girder_spacing = (dims.total_width - 2 * overhang) / (new_num_girders - 1)
            dims = dims.model_copy(
                update={
                    "num_girders": new_num_girders,
                    "girder_spacing": new_girder_spacing,
                }
            )
            logger.info(
                "apply_patch_plan: num_girders += %d → %d, girder_spacing = %.1f mm (overhang=%.1f mm)",
                int(delta),
                new_num_girders,
                new_girder_spacing,
                overhang,
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


# =============================================================================
# 依存関係ルール適用
# =============================================================================


def apply_dependency_rules(
    design: BridgeDesign,
    dependency_rules: list[DependencyRule],
) -> BridgeDesign:
    """PatchPlan 適用後に依存関係ルールを適用する。

    横桁高さが主桁高さに連動する場合など、部材間の依存関係を自動で反映する。
    ルールが空の場合や、対象外のルールの場合は何もしない（フォールバック）。

    Args:
        design: 元の BridgeDesign
        dependency_rules: 適用する依存関係ルールのリスト

    Returns:
        修正後の新しい BridgeDesign
    """
    if not dependency_rules:
        return design

    # 現在の値を取り出す
    girder = design.sections.girder_standard
    crossbeam = design.sections.crossbeam_standard
    changed = False

    for rule in dependency_rules:
        # スコープ: crossbeam.total_height のみ（v1）
        target_match = rule.target_field == "sections.crossbeam_standard.total_height"
        source_match = rule.source_field == "sections.girder_standard.web_height"
        if target_match and source_match:
            source_value = girder.web_height
            new_value = source_value * rule.factor
            crossbeam = CrossbeamSection(
                total_height=new_value,
                web_thickness=crossbeam.web_thickness,
                flange_width=crossbeam.flange_width,
                flange_thickness=crossbeam.flange_thickness,
            )
            changed = True
            logger.info(
                "apply_dependency_rules: %s = %.0f × %.2f = %.0f",
                rule.target_field,
                source_value,
                rule.factor,
                new_value,
            )

    if not changed:
        return design

    # 新しい BridgeDesign を構築
    new_sections = Sections(
        girder_standard=girder,
        crossbeam_standard=crossbeam,
    )
    return BridgeDesign(
        dimensions=design.dimensions,
        sections=new_sections,
        components=design.components,
    )
