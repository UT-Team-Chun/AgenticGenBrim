"""bridge_agentic_generate.main のテスト。"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from src.bridge_agentic_generate.designer.models import (
    BridgeDesign,
    Components,
    CrossbeamSection,
    Deck,
    DesignerRagLog,
    DesignResult,
    Dimensions,
    GirderSection,
    Sections,
)
from src.bridge_agentic_generate.judge.models import (
    Diagnostics,
    GirderLoadResult,
    GoverningCheck,
    JudgeReport,
    LoadEffectsResult,
    PatchAction,
    PatchActionOp,
    PatchPlan,
    Utilization,
)
from src.bridge_agentic_generate.main import run_with_repair_loop

# =============================================================================
# テスト用フィクスチャ
# =============================================================================


@pytest.fixture
def passing_design() -> BridgeDesign:
    """合格する設計のフィクスチャ。"""
    return BridgeDesign(
        dimensions=Dimensions(
            bridge_length=20000.0,
            total_width=8000.0,
            num_girders=4,
            girder_spacing=2000.0,
            panel_length=5000.0,
            num_panels=4,
        ),
        sections=Sections(
            girder_standard=GirderSection(
                web_height=2000.0,
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
            deck=Deck(thickness=220.0),
        ),
    )


@pytest.fixture
def failing_design() -> BridgeDesign:
    """不合格の設計のフィクスチャ。"""
    return BridgeDesign(
        dimensions=Dimensions(
            bridge_length=50000.0,
            total_width=12000.0,
            num_girders=3,
            girder_spacing=4000.0,
            panel_length=10000.0,
            num_panels=5,
        ),
        sections=Sections(
            girder_standard=GirderSection(
                web_height=800.0,
                web_thickness=12.0,
                top_flange_width=300.0,
                top_flange_thickness=16.0,
                bottom_flange_width=300.0,
                bottom_flange_thickness=16.0,
            ),
            crossbeam_standard=CrossbeamSection(
                total_height=600.0,
                web_thickness=10.0,
                flange_width=200.0,
                flange_thickness=12.0,
            ),
        ),
        components=Components(
            deck=Deck(thickness=200.0),
        ),
    )


def _create_load_effects() -> LoadEffectsResult:
    """テスト用の LoadEffectsResult を作成。"""
    girder_results = [
        GirderLoadResult(
            girder_index=i,
            b_i_m=2.5,
            w_dead=18.0,
            M_dead=5.625e9,
            V_dead=450000.0,
            b_eff_m=2.5,
            w_M=30.0,
            w_V=35.0,
            M_live=4.5e9,
            V_live=360000.0,
            M_total=10.125e9,
            V_total=810000.0,
        )
        for i in range(4)
    ]
    return LoadEffectsResult(
        L_m=50.0,
        D_m=10.0,
        p2=3.5,
        p1_M=10.0,
        p1_V=12.0,
        gamma=0.36,
        p_eq_M=7.1,
        p_eq_V=7.82,
        overhang_m=1.25,
        girder_results=girder_results,
        governing_girder_index_bend=1,
        governing_girder_index_shear=1,
        M_total_max=10.125e9,
        V_total_max=810000.0,
    )


def _create_passing_report() -> JudgeReport:
    """合格する JudgeReport を作成。"""
    return JudgeReport(
        pass_fail=True,
        utilization=Utilization(
            deck=0.8,
            bend=0.7,
            shear=0.5,
            deflection=0.6,
            web_slenderness=0.68,
            max_util=0.8,
            governing_check=GoverningCheck.DECK,
        ),
        diagnostics=Diagnostics(
            M_total=3e9,
            V_total=7e5,
            ybar=800.0,
            moment_of_inertia=5e10,
            y_top=700.0,
            y_bottom=800.0,
            sigma_top=80.0,
            sigma_bottom=90.0,
            tau_avg=30.0,
            delta=25.0,
            delta_allow=40.0,
            fy_top_flange=315.0,
            fy_bottom_flange=315.0,
            fy_web=325.0,
            sigma_allow_top=189.0,
            sigma_allow_bottom=189.0,
            tau_allow=112.6,
            deck_thickness_required=200.0,
            web_thickness_min_required=10.8,
            crossbeam_layout_ok=True,
            load_effects=_create_load_effects(),
            governing_girder_index_bend=1,
            governing_girder_index_shear=1,
        ),
        patch_plan=PatchPlan(actions=[]),
    )


def _create_failing_report() -> JudgeReport:
    """不合格の JudgeReport を作成（PatchPlan 付き）。"""
    return JudgeReport(
        pass_fail=False,
        utilization=Utilization(
            deck=0.9,
            bend=1.2,
            shear=0.8,
            deflection=1.5,
            web_slenderness=0.68,
            max_util=1.5,
            governing_check=GoverningCheck.DEFLECTION,
        ),
        diagnostics=Diagnostics(
            M_total=13e9,
            V_total=1.8e6,
            ybar=500.0,
            moment_of_inertia=2e10,
            y_top=400.0,
            y_bottom=500.0,
            sigma_top=180.0,
            sigma_bottom=200.0,
            tau_avg=60.0,
            delta=120.0,
            delta_allow=80.0,
            fy_top_flange=315.0,
            fy_bottom_flange=315.0,
            fy_web=325.0,
            sigma_allow_top=189.0,
            sigma_allow_bottom=189.0,
            tau_allow=112.6,
            deck_thickness_required=230.0,
            web_thickness_min_required=10.8,
            crossbeam_layout_ok=True,
            load_effects=_create_load_effects(),
            governing_girder_index_bend=1,
            governing_girder_index_shear=1,
        ),
        patch_plan=PatchPlan(
            actions=[
                PatchAction(
                    op=PatchActionOp.INCREASE_WEB_HEIGHT,
                    path="sections.girder_standard.web_height",
                    delta_mm=200.0,
                    reason="たわみ改善のため",
                ),
            ]
        ),
    )


# =============================================================================
# テスト: run_with_repair_loop
# =============================================================================


class TestRunWithRepairLoop:
    """run_with_repair_loop のテスト。"""

    def test_converges_on_first_iteration(self, passing_design: BridgeDesign) -> None:
        """初回の照査で合格する場合、1回のイテレーションで終了すること。"""
        mock_design_result = DesignResult(
            design=passing_design,
            rag_log=DesignerRagLog(query="test", top_k=5, hits=[]),
        )

        with (
            patch(
                "src.bridge_agentic_generate.main.generate_design_with_rag_log",
                return_value=mock_design_result,
            ),
            patch(
                "src.bridge_agentic_generate.main.judge_v1",
                return_value=_create_passing_report(),
            ) as mock_judge,
        ):
            result = run_with_repair_loop(
                bridge_length_m=20.0,
                total_width_m=8.0,
                model_name="gpt-5-mini",
                max_iterations=5,
            )

        # 1回だけ照査が呼ばれること
        assert mock_judge.call_count == 1
        # 合格していること
        assert result.converged is True
        assert result.final_report.pass_fail is True
        assert len(result.iterations) == 1

    def test_converges_after_repair(self, failing_design: BridgeDesign, passing_design: BridgeDesign) -> None:
        """修正後に合格する場合、正しく収束すること。"""
        mock_design_result = DesignResult(
            design=failing_design,
            rag_log=DesignerRagLog(query="test", top_k=5, hits=[]),
        )

        # 1回目は不合格、2回目は合格
        judge_results = [_create_failing_report(), _create_passing_report()]

        with (
            patch(
                "src.bridge_agentic_generate.main.generate_design_with_rag_log",
                return_value=mock_design_result,
            ),
            patch(
                "src.bridge_agentic_generate.main.judge_v1",
                side_effect=judge_results,
            ) as mock_judge,
        ):
            result = run_with_repair_loop(
                bridge_length_m=50.0,
                total_width_m=12.0,
                model_name="gpt-5-mini",
                max_iterations=5,
            )

        # 2回照査が呼ばれること
        assert mock_judge.call_count == 2
        # 最終的に合格していること
        assert result.converged is True
        assert result.final_report.pass_fail is True
        assert len(result.iterations) == 2

    def test_raises_on_max_iterations(self, failing_design: BridgeDesign) -> None:
        """max_iterations 回の修正で収束しない場合、RuntimeError が発生すること。"""
        mock_design_result = DesignResult(
            design=failing_design,
            rag_log=DesignerRagLog(query="test", top_k=5, hits=[]),
        )

        # 常に不合格
        with (
            patch(
                "src.bridge_agentic_generate.main.generate_design_with_rag_log",
                return_value=mock_design_result,
            ),
            patch(
                "src.bridge_agentic_generate.main.judge_v1",
                return_value=_create_failing_report(),
            ),
        ):
            result = run_with_repair_loop(
                bridge_length_m=50.0,
                total_width_m=12.0,
                model_name="gpt-5-mini",
                max_iterations=3,
            )

        # 収束しないこと
        assert result.converged is False
        assert result.final_report.pass_fail is False
        # max_iterations=3 の場合、0,1,2の3回修正後に最終照査が入り、合計4回
        assert len(result.iterations) == 4

    def test_applies_patch_plan(self, failing_design: BridgeDesign) -> None:
        """PatchPlan が正しく適用されること。"""
        mock_design_result = DesignResult(
            design=failing_design,
            rag_log=DesignerRagLog(query="test", top_k=5, hits=[]),
        )

        # 1回目は不合格、2回目は合格
        judge_results = [_create_failing_report(), _create_passing_report()]

        def mock_apply_fn(
            design: BridgeDesign,
            patch_plan: PatchPlan,
            deck_thickness_required: float | None = None,
        ) -> BridgeDesign:
            return design

        with (
            patch(
                "src.bridge_agentic_generate.main.generate_design_with_rag_log",
                return_value=mock_design_result,
            ),
            patch(
                "src.bridge_agentic_generate.main.judge_v1",
                side_effect=judge_results,
            ),
            patch(
                "src.bridge_agentic_generate.main.apply_patch_plan",
                side_effect=mock_apply_fn,
            ) as mock_apply,
        ):
            run_with_repair_loop(
                bridge_length_m=50.0,
                total_width_m=12.0,
                model_name="gpt-5-mini",
                max_iterations=5,
            )

        # apply_patch_plan が1回呼ばれること
        assert mock_apply.call_count == 1
