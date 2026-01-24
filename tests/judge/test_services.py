"""Judge サービス層のテスト。

仕様: judge_impl.md に基づく。
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from src.bridge_agentic_generate.designer.models import (
    BridgeDesign,
    Components,
    CrossbeamSection,
    Deck,
    DependencyRule,
    Dimensions,
    GirderSection,
    Sections,
)
from src.bridge_agentic_generate.judge.models import (
    GoverningCheck,
    JudgeInput,
    PatchAction,
    PatchActionOp,
    PatchPlan,
)
from src.bridge_agentic_generate.judge.services import (
    apply_dependency_rules,
    apply_patch_plan,
    calc_allowable_deflection,
    calc_dead_load,
    calc_dead_load_effects,
    calc_girder_section_area,
    calc_girder_section_properties,
    calc_live_load_effects,
    calc_required_deck_thickness,
    judge_v1,
    judge_v1_lightweight,
)
from src.bridge_agentic_generate.llm_client import LlmModel

# =============================================================================
# テスト用フィクスチャ
# =============================================================================


@pytest.fixture
def sample_girder_section() -> GirderSection:
    """テスト用の主桁断面（非対称 I 断面）。"""
    return GirderSection(
        web_height=1400.0,
        web_thickness=16.0,
        top_flange_width=350.0,
        top_flange_thickness=25.0,
        bottom_flange_width=450.0,
        bottom_flange_thickness=30.0,
    )


@pytest.fixture
def sample_bridge_design() -> BridgeDesign:
    """テスト用の BridgeDesign（fixture JSON ベース）。"""
    return BridgeDesign(
        dimensions=Dimensions(
            bridge_length=30000.0,
            total_width=10000.0,
            num_girders=4,
            girder_spacing=2667.0,
            panel_length=5000.0,
            num_panels=6,
        ),
        sections=Sections(
            girder_standard=GirderSection(
                web_height=1400.0,
                web_thickness=16.0,
                top_flange_width=350.0,
                top_flange_thickness=25.0,
                bottom_flange_width=450.0,
                bottom_flange_thickness=30.0,
            ),
            crossbeam_standard=CrossbeamSection(
                total_height=1120.0,
                web_thickness=10.0,
                flange_width=280.0,
                flange_thickness=12.0,
            ),
        ),
        components=Components(
            deck=Deck(thickness=217.0),
        ),
    )


# =============================================================================
# 単体テスト: 断面計算
# =============================================================================


class TestGirderSectionArea:
    """主桁断面積の計算テスト。"""

    def test_calc_area(self, sample_girder_section: GirderSection) -> None:
        """断面積が正しく計算されること。"""
        area = calc_girder_section_area(sample_girder_section)

        # 手計算:
        # A_web = 1400 * 16 = 22400 mm²
        # A_tf = 350 * 25 = 8750 mm²
        # A_bf = 450 * 30 = 13500 mm²
        # Total = 44650 mm²
        expected = 22400 + 8750 + 13500
        assert area == pytest.approx(expected, rel=1e-6)


class TestGirderSectionProperties:
    """主桁断面諸量の計算テスト。"""

    def test_calc_properties(self, sample_girder_section: GirderSection) -> None:
        """中立軸・断面二次モーメント・縁距離が正しく計算されること。"""
        ybar, moment_of_inertia, y_top, y_bottom, total_height = calc_girder_section_properties(sample_girder_section)

        # 全高
        # H = 30 + 1400 + 25 = 1455 mm
        expected_total_height = 30 + 1400 + 25
        assert total_height == pytest.approx(expected_total_height, rel=1e-6)

        # 各部材の面積
        a_bf = 450 * 30  # 13500
        a_web = 1400 * 16  # 22400
        a_tf = 350 * 25  # 8750
        total_area = a_bf + a_web + a_tf  # 44650

        # 各部材の図心位置（下端基準）
        y_bf_center = 30 / 2  # 15
        y_web_center = 30 + 1400 / 2  # 730
        y_tf_center = 30 + 1400 + 25 / 2  # 1442.5

        # 中立軸位置
        expected_ybar = (a_bf * y_bf_center + a_web * y_web_center + a_tf * y_tf_center) / total_area
        assert ybar == pytest.approx(expected_ybar, rel=1e-6)

        # 縁距離
        assert y_bottom == pytest.approx(ybar, rel=1e-6)
        assert y_top == pytest.approx(expected_total_height - ybar, rel=1e-6)

        # 断面二次モーメント（平行軸の定理）
        i_bf = 450 * 30**3 / 12
        i_web = 16 * 1400**3 / 12
        i_tf = 350 * 25**3 / 12

        expected_i = (
            i_bf
            + a_bf * (expected_ybar - y_bf_center) ** 2
            + i_web
            + a_web * (expected_ybar - y_web_center) ** 2
            + i_tf
            + a_tf * (expected_ybar - y_tf_center) ** 2
        )
        assert moment_of_inertia == pytest.approx(expected_i, rel=1e-6)


# =============================================================================
# 単体テスト: 死荷重計算
# =============================================================================


class TestDeadLoad:
    """死荷重計算のテスト。"""

    def test_calc_dead_load(self, sample_girder_section: GirderSection) -> None:
        """死荷重線荷重が正しく計算されること。"""
        deck_thickness = 217.0  # mm
        girder_spacing = 2667.0  # mm
        gamma_steel = 78.5e-6  # N/mm³
        gamma_concrete = 25.0e-6  # N/mm³

        w_deck, w_steel = calc_dead_load(
            girder_section=sample_girder_section,
            deck_thickness_mm=deck_thickness,
            girder_spacing_mm=girder_spacing,
            gamma_steel=gamma_steel,
            gamma_concrete=gamma_concrete,
        )

        # 手計算:
        # w_deck = 25e-6 * 217 * 2667 = 14.46 N/mm
        expected_w_deck = gamma_concrete * deck_thickness * girder_spacing
        assert w_deck == pytest.approx(expected_w_deck, rel=1e-6)

        # w_steel = 78.5e-6 * 44650 = 3.505 N/mm
        expected_area = 22400 + 8750 + 13500
        expected_w_steel = gamma_steel * expected_area
        assert w_steel == pytest.approx(expected_w_steel, rel=1e-6)

    def test_calc_dead_load_effects(self) -> None:
        """死荷重断面力が正しく計算されること。"""
        w_dead = 18.0  # N/mm（仮定値）
        bridge_length = 30000.0  # mm

        m_dead, v_dead = calc_dead_load_effects(w_dead, bridge_length)

        # 手計算:
        # M_dead = w * L² / 8 = 18 * 30000² / 8 = 2.025e9 N·mm
        expected_m_dead = w_dead * bridge_length**2 / 8
        assert m_dead == pytest.approx(expected_m_dead, rel=1e-6)

        # V_dead = w * L / 2 = 18 * 30000 / 2 = 270000 N
        expected_v_dead = w_dead * bridge_length / 2
        assert v_dead == pytest.approx(expected_v_dead, rel=1e-6)


# =============================================================================
# 単体テスト: 活荷重計算
# =============================================================================


class TestLiveLoad:
    """活荷重計算のテスト。"""

    def test_calc_live_load_effects(self) -> None:
        """活荷重断面力が正しく計算されること。"""
        p_live = 12.0  # kN/m²
        girder_spacing = 2667.0  # mm
        bridge_length = 30000.0  # mm

        m_live, v_live = calc_live_load_effects(
            p_live_equiv_kn_m2=p_live,
            girder_spacing_mm=girder_spacing,
            bridge_length_mm=bridge_length,
        )

        # 手計算:
        b_tr_m = girder_spacing / 1000
        # w_live = 12 * 2.5 = 30 kN/m
        w_live_kn_m = p_live * b_tr_m
        # L = 30 m
        l_m = bridge_length / 1000
        # M_live = 30 * 30² / 8 = 3375 kN·m = 3.375e9 N·mm
        expected_m = w_live_kn_m * l_m**2 / 8 * 1e6
        assert m_live == pytest.approx(expected_m, rel=1e-6)
        # V_live = 30 * 30 / 2 = 450 kN = 450000 N
        expected_v = w_live_kn_m * l_m / 2 * 1e3
        assert v_live == pytest.approx(expected_v, rel=1e-6)


# =============================================================================
# 単体テスト: 床版厚計算
# =============================================================================


class TestDeckThickness:
    """床版厚計算のテスト。"""

    def test_calc_required_deck_thickness(self) -> None:
        """必要床版厚が正しく計算されること。"""
        # girder_spacing = 2667 mm = 2.667 m
        girder_spacing = 2667.0

        required = calc_required_deck_thickness(girder_spacing)

        # 手計算:
        # max(30 * 2.667 + 110, 160) = max(190.01, 160) = 190.01 mm
        l_support_m = girder_spacing / 1000
        expected = max(30 * l_support_m + 110, 160)
        assert required == pytest.approx(expected, rel=1e-6)

    def test_minimum_deck_thickness(self) -> None:
        """最小床版厚（160mm）が適用されること。"""
        # girder_spacing = 1000 mm = 1.0 m
        girder_spacing = 1000.0

        required = calc_required_deck_thickness(girder_spacing)

        # 手計算:
        # max(30 * 1.0 + 110, 160) = max(140, 160) = 160 mm
        assert required == pytest.approx(160.0, rel=1e-6)


# =============================================================================
# 単体テスト: 許容たわみ計算
# =============================================================================


class TestAllowableDeflection:
    """許容たわみ計算のテスト。"""

    def test_boundary_10m(self) -> None:
        """L=10m の境界値。"""
        assert calc_allowable_deflection(10000) == pytest.approx(5.0)

    def test_boundary_40m(self) -> None:
        """L=40m の境界値。"""
        assert calc_allowable_deflection(40000) == pytest.approx(80.0)

    def test_case_under_10m(self) -> None:
        """L < 10m のケース。"""
        # L=5m: 5/2000 * 1000 = 2.5mm
        assert calc_allowable_deflection(5000) == pytest.approx(2.5)

    def test_case_between_10_and_40m(self) -> None:
        """10m < L < 40m のケース。"""
        # L=25m: 25²/20000 * 1000 = 31.25mm
        assert calc_allowable_deflection(25000) == pytest.approx(31.25)

    def test_case_over_40m(self) -> None:
        """L > 40m のケース。"""
        # L=50m: 50/500 * 1000 = 100mm
        assert calc_allowable_deflection(50000) == pytest.approx(100.0)


# =============================================================================
# 統合テスト: judge_v1
# =============================================================================


class TestJudgeV1:
    """judge_v1 統合テスト。"""

    def test_judge_v1_report_structure(self, sample_bridge_design: BridgeDesign) -> None:
        """JudgeReport の構造が正しく生成されること。"""
        judge_input = JudgeInput(bridge_design=sample_bridge_design)

        # LLM をモック（この設計は不合格なので PatchPlan が必要）
        mock_patch_plan = PatchPlan(
            actions=[
                PatchAction(
                    op=PatchActionOp.INCREASE_WEB_HEIGHT,
                    path="sections.girder_standard.web_height",
                    delta_mm=300.0,
                    reason="たわみ util 改善のため",
                ),
            ]
        )

        with patch(
            "src.bridge_agentic_generate.judge.services.generate_patch_plan",
            return_value=(mock_patch_plan, []),  # タプルで返す
        ):
            report = judge_v1(judge_input, model=LlmModel.GPT_5_MINI)

        # report の構造を確認
        assert report.utilization is not None
        assert report.diagnostics is not None
        assert report.patch_plan is not None

        # util が数値で埋まっていること
        assert isinstance(report.utilization.deck, float)
        assert isinstance(report.utilization.bend, float)
        assert isinstance(report.utilization.shear, float)
        assert isinstance(report.utilization.deflection, float)
        assert isinstance(report.utilization.max_util, float)

        # governing_check が決まっていること
        assert report.utilization.governing_check in GoverningCheck

        # 診断情報が埋まっていること
        diag = report.diagnostics
        assert diag.w_dead > 0
        assert diag.M_dead > 0
        assert diag.moment_of_inertia > 0
        assert diag.sigma_allow > 0
        assert diag.delta > 0

    def test_judge_v1_with_passing_design(self) -> None:
        """合格する設計で PatchPlan が空であること。"""
        # 十分に大きい断面を持つ設計を作成
        passing_design = BridgeDesign(
            dimensions=Dimensions(
                bridge_length=20000.0,  # 短い橋
                total_width=8000.0,
                num_girders=4,
                girder_spacing=2000.0,
                panel_length=5000.0,
                num_panels=4,
            ),
            sections=Sections(
                girder_standard=GirderSection(
                    web_height=2000.0,  # 大きい
                    web_thickness=20.0,
                    top_flange_width=500.0,
                    top_flange_thickness=40.0,
                    bottom_flange_width=600.0,
                    bottom_flange_thickness=50.0,
                ),
                crossbeam_standard=CrossbeamSection(
                    total_height=1600.0,
                    web_thickness=12.0,
                    flange_width=350.0,
                    flange_thickness=16.0,
                ),
            ),
            components=Components(
                deck=Deck(thickness=220.0),  # 十分な厚さ
            ),
        )
        judge_input = JudgeInput(bridge_design=passing_design)

        # LLM をモック（合格の場合は呼ばれないはず）
        with patch("src.bridge_agentic_generate.judge.services.generate_patch_plan") as mock_generate:
            report = judge_v1(judge_input, model=LlmModel.GPT_5_MINI)

        # 合格であること
        assert report.pass_fail is True

        # LLM は呼ばれていないこと
        mock_generate.assert_not_called()

        # PatchPlan が空であること
        assert len(report.patch_plan.actions) == 0

    def test_judge_v1_with_failing_design(self) -> None:
        """不合格の設計で PatchPlan が生成されること。"""
        # 極端に小さい断面を作成
        failing_design = BridgeDesign(
            dimensions=Dimensions(
                bridge_length=50000.0,  # 長い
                total_width=12000.0,
                num_girders=3,
                girder_spacing=4000.0,
                panel_length=10000.0,
                num_panels=5,
            ),
            sections=Sections(
                girder_standard=GirderSection(
                    web_height=500.0,  # 小さい
                    web_thickness=10.0,
                    top_flange_width=200.0,
                    top_flange_thickness=12.0,
                    bottom_flange_width=200.0,
                    bottom_flange_thickness=12.0,
                ),
                crossbeam_standard=CrossbeamSection(
                    total_height=400.0,
                    web_thickness=8.0,
                    flange_width=150.0,
                    flange_thickness=10.0,
                ),
            ),
            components=Components(
                deck=Deck(thickness=150.0),  # 不足
            ),
        )
        judge_input = JudgeInput(bridge_design=failing_design)

        # LLM をモック
        mock_patch_plan = PatchPlan(
            actions=[
                PatchAction(
                    op=PatchActionOp.INCREASE_WEB_HEIGHT,
                    path="sections.girder_standard.web_height",
                    delta_mm=200.0,
                    reason="たわみ util 改善のため",
                ),
            ]
        )

        with patch(
            "src.bridge_agentic_generate.judge.services.generate_patch_plan",
            return_value=(mock_patch_plan, []),  # タプルで返す
        ) as mock_generate:
            report = judge_v1(judge_input, model=LlmModel.GPT_5_MINI)

        # 不合格であること
        assert report.pass_fail is False

        # LLM が呼ばれたこと
        mock_generate.assert_called_once()

        # PatchPlan にアクションがあること
        assert len(report.patch_plan.actions) > 0

    def test_judge_v1_crossbeam_layout_check(self) -> None:
        """横桁配置チェックが機能すること。"""
        # panel_length * num_panels != bridge_length となる設計
        bad_layout_design = BridgeDesign(
            dimensions=Dimensions(
                bridge_length=30000.0,
                total_width=10000.0,
                num_girders=4,
                girder_spacing=2667.0,
                panel_length=5000.0,
                num_panels=5,  # 5 * 5000 = 25000 != 30000
            ),
            sections=Sections(
                girder_standard=GirderSection(
                    web_height=1400.0,
                    web_thickness=16.0,
                    top_flange_width=350.0,
                    top_flange_thickness=25.0,
                    bottom_flange_width=450.0,
                    bottom_flange_thickness=30.0,
                ),
                crossbeam_standard=CrossbeamSection(
                    total_height=1120.0,
                    web_thickness=10.0,
                    flange_width=280.0,
                    flange_thickness=12.0,
                ),
            ),
            components=Components(
                deck=Deck(thickness=217.0),
            ),
        )
        judge_input = JudgeInput(bridge_design=bad_layout_design)

        # LLM をモック
        mock_patch_plan = PatchPlan(
            actions=[
                PatchAction(
                    op=PatchActionOp.FIX_CROSSBEAM_LAYOUT,
                    path="dimensions.num_panels",
                    delta_mm=0.0,
                    reason="横桁配置を修正",
                ),
            ]
        )

        with patch(
            "src.bridge_agentic_generate.judge.services.generate_patch_plan",
            return_value=(mock_patch_plan, []),  # タプルで返す
        ):
            report = judge_v1(judge_input, model=LlmModel.GPT_5_MINI)

        # 横桁配置 NG
        assert report.diagnostics.crossbeam_layout_ok is False
        # governing_check が CROSSBEAM_LAYOUT になること
        assert report.utilization.governing_check == GoverningCheck.CROSSBEAM_LAYOUT


class TestJudgeV1WithFixture:
    """fixture JSON を使用した統合テスト。"""

    def test_judge_with_fixture_json(self) -> None:
        """fixture JSON で JudgeReport が正しく生成されること。"""
        fixture_path = Path(
            "/Users/abehiroki/AgenticGenBrim/data/generated_simple_bridge_json/design_L30_B10_20260117_204222.json"
        )

        if not fixture_path.exists():
            pytest.skip(f"Fixture file not found: {fixture_path}")

        with open(fixture_path) as f:
            design_dict = json.load(f)

        bridge_design = BridgeDesign.model_validate(design_dict)
        judge_input = JudgeInput(bridge_design=bridge_design)

        # LLM をモック（fixture 設計は不合格なので PatchPlan が必要）
        mock_patch_plan = PatchPlan(
            actions=[
                PatchAction(
                    op=PatchActionOp.INCREASE_WEB_HEIGHT,
                    path="sections.girder_standard.web_height",
                    delta_mm=300.0,
                    reason="たわみ/曲げ util 改善のため",
                ),
            ]
        )
        with patch(
            "src.bridge_agentic_generate.judge.services.generate_patch_plan",
            return_value=(mock_patch_plan, []),  # タプルで返す
        ):
            report = judge_v1(judge_input, model=LlmModel.GPT_5_MINI)

        # report が出る
        assert report is not None

        # util が数値で埋まる
        assert report.utilization.deck > 0
        assert report.utilization.bend > 0
        assert report.utilization.shear > 0
        assert report.utilization.deflection > 0

        # governing_check が決まる
        assert report.utilization.governing_check in GoverningCheck

        # 主要中間量が説明可能
        diag = report.diagnostics
        assert diag.w_dead > 0, "w_dead should be positive"
        assert diag.M_dead > 0, "M_dead should be positive"
        assert diag.moment_of_inertia > 0, "I should be positive"
        assert diag.sigma_allow > 0, "sigma_allow should be positive"
        assert diag.delta > 0, "delta should be positive"

        # ログ出力用に診断情報を表示
        print("\n=== Fixture Test Results ===")
        print(f"pass_fail: {report.pass_fail}")
        print(f"util_deck: {report.utilization.deck:.4f}")
        print(f"util_bend: {report.utilization.bend:.4f}")
        print(f"util_shear: {report.utilization.shear:.4f}")
        print(f"util_deflection: {report.utilization.deflection:.4f}")
        print(f"max_util: {report.utilization.max_util:.4f}")
        print(f"governing_check: {report.utilization.governing_check}")
        print(f"w_dead: {diag.w_dead:.4f} N/mm")
        print(f"M_dead: {diag.M_dead:.2e} N·mm")
        print(f"I: {diag.moment_of_inertia:.2e} mm⁴")
        print(f"sigma_allow: {diag.sigma_allow:.2f} N/mm²")
        print(f"delta: {diag.delta:.2f} mm (allow: {diag.delta_allow:.2f} mm)")


# =============================================================================
# 単体テスト: apply_patch_plan
# =============================================================================


class TestApplyPatchPlan:
    """apply_patch_plan のテスト。"""

    def test_apply_patch_plan_increase_web_height(self, sample_bridge_design: BridgeDesign) -> None:
        """web_height の増加が正しく適用されること。"""
        patch_plan = PatchPlan(
            actions=[
                PatchAction(
                    op=PatchActionOp.INCREASE_WEB_HEIGHT,
                    path="sections.girder_standard.web_height",
                    delta_mm=100.0,
                    reason="たわみ改善のため",
                ),
            ]
        )

        original_height = sample_bridge_design.sections.girder_standard.web_height
        new_design = apply_patch_plan(sample_bridge_design, patch_plan)

        assert new_design.sections.girder_standard.web_height == pytest.approx(original_height + 100.0)
        # 他のフィールドは変更されていないこと
        assert (
            new_design.sections.girder_standard.web_thickness
            == sample_bridge_design.sections.girder_standard.web_thickness
        )

    def test_apply_patch_plan_set_deck_thickness(self, sample_bridge_design: BridgeDesign) -> None:
        """床版厚の設定が正しく適用されること。"""
        patch_plan = PatchPlan(
            actions=[
                PatchAction(
                    op=PatchActionOp.SET_DECK_THICKNESS_TO_REQUIRED,
                    path="components.deck.thickness",
                    delta_mm=0.0,
                    reason="必要床版厚に設定",
                ),
            ]
        )

        required_thickness = 250.0
        new_design = apply_patch_plan(sample_bridge_design, patch_plan, deck_thickness_required=required_thickness)

        assert new_design.components.deck.thickness == pytest.approx(required_thickness)

    def test_apply_patch_plan_set_deck_thickness_without_required_raises(
        self, sample_bridge_design: BridgeDesign
    ) -> None:
        """deck_thickness_required が指定されていない場合にエラーが発生すること。"""
        patch_plan = PatchPlan(
            actions=[
                PatchAction(
                    op=PatchActionOp.SET_DECK_THICKNESS_TO_REQUIRED,
                    path="components.deck.thickness",
                    delta_mm=0.0,
                    reason="必要床版厚に設定",
                ),
            ]
        )

        with pytest.raises(ValueError, match="deck_thickness_required"):
            apply_patch_plan(sample_bridge_design, patch_plan)

    def test_apply_patch_plan_fix_crossbeam_layout(self, sample_bridge_design: BridgeDesign) -> None:
        """横桁配置修正が正しく適用されること。"""
        # panel_length * num_panels != bridge_length になる設計を作成
        bad_layout_design = BridgeDesign(
            dimensions=Dimensions(
                bridge_length=30000.0,
                total_width=10000.0,
                num_girders=4,
                girder_spacing=2667.0,
                panel_length=5000.0,
                num_panels=5,  # 5 * 5000 = 25000 != 30000
            ),
            sections=sample_bridge_design.sections,
            components=sample_bridge_design.components,
        )

        patch_plan = PatchPlan(
            actions=[
                PatchAction(
                    op=PatchActionOp.FIX_CROSSBEAM_LAYOUT,
                    path="dimensions.num_panels",
                    delta_mm=0.0,
                    reason="横桁配置を修正",
                ),
            ]
        )

        new_design = apply_patch_plan(bad_layout_design, patch_plan)

        # num_panels = round(30000 / 5000) = 6
        assert new_design.dimensions.num_panels == 6

    def test_apply_patch_plan_multiple_actions(self, sample_bridge_design: BridgeDesign) -> None:
        """複数アクションが正しく適用されること。"""
        patch_plan = PatchPlan(
            actions=[
                PatchAction(
                    op=PatchActionOp.INCREASE_WEB_HEIGHT,
                    path="sections.girder_standard.web_height",
                    delta_mm=200.0,
                    reason="たわみ改善",
                ),
                PatchAction(
                    op=PatchActionOp.INCREASE_TOP_FLANGE_THICKNESS,
                    path="sections.girder_standard.top_flange_thickness",
                    delta_mm=4.0,
                    reason="曲げ改善",
                ),
                PatchAction(
                    op=PatchActionOp.INCREASE_BOTTOM_FLANGE_WIDTH,
                    path="sections.girder_standard.bottom_flange_width",
                    delta_mm=50.0,
                    reason="曲げ改善",
                ),
            ]
        )

        original = sample_bridge_design.sections.girder_standard
        new_design = apply_patch_plan(sample_bridge_design, patch_plan)
        new_girder = new_design.sections.girder_standard

        assert new_girder.web_height == pytest.approx(original.web_height + 200.0)
        assert new_girder.top_flange_thickness == pytest.approx(original.top_flange_thickness + 4.0)
        assert new_girder.bottom_flange_width == pytest.approx(original.bottom_flange_width + 50.0)
        # 変更されていないフィールド
        assert new_girder.web_thickness == pytest.approx(original.web_thickness)
        assert new_girder.top_flange_width == pytest.approx(original.top_flange_width)
        assert new_girder.bottom_flange_thickness == pytest.approx(original.bottom_flange_thickness)

    def test_apply_patch_plan_all_girder_operations(self, sample_bridge_design: BridgeDesign) -> None:
        """すべての主桁操作が正しく適用されること。"""
        patch_plan = PatchPlan(
            actions=[
                PatchAction(
                    op=PatchActionOp.INCREASE_WEB_THICKNESS,
                    path="sections.girder_standard.web_thickness",
                    delta_mm=2.0,
                    reason="せん断改善",
                ),
            ]
        )

        original = sample_bridge_design.sections.girder_standard.web_thickness
        new_design = apply_patch_plan(sample_bridge_design, patch_plan)

        assert new_design.sections.girder_standard.web_thickness == pytest.approx(original + 2.0)

    def test_apply_patch_plan_empty_actions(self, sample_bridge_design: BridgeDesign) -> None:
        """空のアクションリストの場合、設計が変更されないこと。"""
        patch_plan = PatchPlan(actions=[])

        new_design = apply_patch_plan(sample_bridge_design, patch_plan)

        # 値は同じだが、別のインスタンス
        assert (
            new_design.sections.girder_standard.web_height == sample_bridge_design.sections.girder_standard.web_height
        )
        assert new_design.components.deck.thickness == sample_bridge_design.components.deck.thickness


# =============================================================================
# 単体テスト: apply_dependency_rules
# =============================================================================


class TestApplyDependencyRules:
    """apply_dependency_rules のテスト。"""

    def test_apply_dependency_rules_crossbeam_total_height(self, sample_bridge_design: BridgeDesign) -> None:
        """横桁 total_height が主桁 web_height × factor で更新されること。"""
        dependency_rules = [
            DependencyRule(
                rule_id="D1",
                target_field="sections.crossbeam_standard.total_height",
                source_field="sections.girder_standard.web_height",
                factor=0.8,
                source_hit_ranks=[17],
                notes="示方書より横桁高さは主桁の80%程度",
            ),
        ]

        original_girder_web_height = sample_bridge_design.sections.girder_standard.web_height
        expected_crossbeam_height = original_girder_web_height * 0.8

        new_design = apply_dependency_rules(sample_bridge_design, dependency_rules)

        # 横桁高さが更新されていること
        assert new_design.sections.crossbeam_standard.total_height == pytest.approx(expected_crossbeam_height)
        # 主桁は変更されていないこと
        assert new_design.sections.girder_standard.web_height == pytest.approx(original_girder_web_height)
        # 横桁の他のフィールドは変更されていないこと
        assert (
            new_design.sections.crossbeam_standard.web_thickness
            == sample_bridge_design.sections.crossbeam_standard.web_thickness
        )
        assert (
            new_design.sections.crossbeam_standard.flange_width
            == sample_bridge_design.sections.crossbeam_standard.flange_width
        )

    def test_apply_dependency_rules_empty_rules(self, sample_bridge_design: BridgeDesign) -> None:
        """空のルールリストの場合、設計が変更されないこと。"""
        dependency_rules: list[DependencyRule] = []

        new_design = apply_dependency_rules(sample_bridge_design, dependency_rules)

        # 同じインスタンスが返されること
        assert new_design is sample_bridge_design

    def test_apply_dependency_rules_unsupported_rule(self, sample_bridge_design: BridgeDesign) -> None:
        """サポートされていないルールの場合、設計が変更されないこと。"""
        dependency_rules = [
            DependencyRule(
                rule_id="D1",
                target_field="unknown.field",
                source_field="girder.web_height",
                factor=0.8,
                source_hit_ranks=[],
                notes="サポートされていないフィールド",
            ),
        ]

        original_crossbeam_height = sample_bridge_design.sections.crossbeam_standard.total_height
        new_design = apply_dependency_rules(sample_bridge_design, dependency_rules)

        # 同じインスタンスが返されること
        assert new_design is sample_bridge_design
        # 横桁高さは変更されていないこと
        assert new_design.sections.crossbeam_standard.total_height == pytest.approx(original_crossbeam_height)

    def test_apply_dependency_rules_factor_1_0(self, sample_bridge_design: BridgeDesign) -> None:
        """factor=1.0 の場合、横桁高さが主桁 web_height と同じになること。"""
        dependency_rules = [
            DependencyRule(
                rule_id="D1",
                target_field="sections.crossbeam_standard.total_height",
                source_field="sections.girder_standard.web_height",
                factor=1.0,
                source_hit_ranks=[],
                notes="横桁高さを主桁と同じにする",
            ),
        ]

        original_girder_web_height = sample_bridge_design.sections.girder_standard.web_height

        new_design = apply_dependency_rules(sample_bridge_design, dependency_rules)

        assert new_design.sections.crossbeam_standard.total_height == pytest.approx(original_girder_web_height)

    def test_apply_dependency_rules_with_patch_plan(self, sample_bridge_design: BridgeDesign) -> None:
        """PatchPlan 適用後に依存関係ルールが正しく適用されること（統合テスト）。"""
        # 1. PatchPlan で主桁 web_height を増加
        patch_plan = PatchPlan(
            actions=[
                PatchAction(
                    op=PatchActionOp.INCREASE_WEB_HEIGHT,
                    path="sections.girder_standard.web_height",
                    delta_mm=200.0,
                    reason="たわみ改善",
                ),
            ]
        )

        # 2. 依存関係ルール
        dependency_rules = [
            DependencyRule(
                rule_id="D1",
                target_field="sections.crossbeam_standard.total_height",
                source_field="sections.girder_standard.web_height",
                factor=0.8,
                source_hit_ranks=[17],
                notes="示方書より横桁高さは主桁の80%程度",
            ),
        ]

        # 3. PatchPlan 適用
        original_girder_web_height = sample_bridge_design.sections.girder_standard.web_height
        design_after_patch = apply_patch_plan(sample_bridge_design, patch_plan)

        # 主桁 web_height が増加していること
        assert design_after_patch.sections.girder_standard.web_height == pytest.approx(
            original_girder_web_height + 200.0
        )

        # 4. 依存関係ルール適用
        final_design = apply_dependency_rules(design_after_patch, dependency_rules)

        # 横桁高さが更新された主桁高さ × factor になっていること
        expected_crossbeam_height = (original_girder_web_height + 200.0) * 0.8
        assert final_design.sections.crossbeam_standard.total_height == pytest.approx(expected_crossbeam_height)


# =============================================================================
# 単体テスト: judge_v1_lightweight
# =============================================================================


class TestJudgeV1Lightweight:
    """judge_v1_lightweight のテスト。"""

    def test_judge_v1_lightweight_returns_utilization_and_diagnostics(self, sample_bridge_design: BridgeDesign) -> None:
        """Utilization と Diagnostics が正しく返されること。"""
        judge_input = JudgeInput(bridge_design=sample_bridge_design)

        utilization, diagnostics = judge_v1_lightweight(judge_input)

        # Utilization の構造を確認
        assert isinstance(utilization.deck, float)
        assert isinstance(utilization.bend, float)
        assert isinstance(utilization.shear, float)
        assert isinstance(utilization.deflection, float)
        assert isinstance(utilization.max_util, float)
        assert utilization.governing_check in GoverningCheck

        # Diagnostics の構造を確認
        assert diagnostics.w_dead > 0
        assert diagnostics.M_dead > 0
        assert diagnostics.moment_of_inertia > 0
        assert diagnostics.sigma_allow > 0

    def test_judge_v1_lightweight_matches_judge_v1(self, sample_bridge_design: BridgeDesign) -> None:
        """judge_v1_lightweight の結果が judge_v1 と一致すること。"""
        judge_input = JudgeInput(bridge_design=sample_bridge_design)

        # judge_v1_lightweight の結果
        util_lightweight, diag_lightweight = judge_v1_lightweight(judge_input)

        # judge_v1 の結果（モックあり）
        mock_patch_plan = PatchPlan(
            actions=[
                PatchAction(
                    op=PatchActionOp.INCREASE_WEB_HEIGHT,
                    path="sections.girder_standard.web_height",
                    delta_mm=100.0,
                    reason="test",
                ),
            ]
        )
        with patch(
            "src.bridge_agentic_generate.judge.services.generate_patch_plan",
            return_value=(mock_patch_plan, []),  # タプルで返す
        ):
            report = judge_v1(judge_input, model=LlmModel.GPT_5_MINI)

        # util が一致すること
        assert util_lightweight.deck == pytest.approx(report.utilization.deck)
        assert util_lightweight.bend == pytest.approx(report.utilization.bend)
        assert util_lightweight.shear == pytest.approx(report.utilization.shear)
        assert util_lightweight.deflection == pytest.approx(report.utilization.deflection)
        assert util_lightweight.max_util == pytest.approx(report.utilization.max_util)
        assert util_lightweight.governing_check == report.utilization.governing_check

        # diagnostics が一致すること
        assert diag_lightweight.w_dead == pytest.approx(report.diagnostics.w_dead)
        assert diag_lightweight.M_dead == pytest.approx(report.diagnostics.M_dead)
        assert diag_lightweight.moment_of_inertia == pytest.approx(report.diagnostics.moment_of_inertia)

    def test_judge_v1_lightweight_no_llm_call(self, sample_bridge_design: BridgeDesign) -> None:
        """LLM が呼ばれないこと。"""
        judge_input = JudgeInput(bridge_design=sample_bridge_design)

        with patch("src.bridge_agentic_generate.judge.services.generate_patch_plan") as mock_generate:
            judge_v1_lightweight(judge_input)

        # LLM は呼ばれないこと
        mock_generate.assert_not_called()
