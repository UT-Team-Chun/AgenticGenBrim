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
    GoverningCheck,
    JudgeReport,
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


def _create_passing_report() -> JudgeReport:
    """合格する JudgeReport を作成。"""
    return JudgeReport(
        pass_fail=True,
        utilization=Utilization(
            deck=0.8,
            bend=0.7,
            shear=0.5,
            deflection=0.6,
            max_util=0.8,
            governing_check=GoverningCheck.DECK,
        ),
        diagnostics=Diagnostics(
            b_tr=2000.0,
            w_dead=15.0,
            M_dead=1e9,
            V_dead=3e5,
            M_live_max=2e9,
            V_live_max=4e5,
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
            sigma_allow=141.0,
            tau_allow=81.0,
            deck_thickness_required=200.0,
            crossbeam_layout_ok=True,
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
            max_util=1.5,
            governing_check=GoverningCheck.DEFLECTION,
        ),
        diagnostics=Diagnostics(
            b_tr=4000.0,
            w_dead=25.0,
            M_dead=5e9,
            V_dead=8e5,
            M_live_max=8e9,
            V_live_max=1e6,
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
            sigma_allow=141.0,
            tau_allow=81.0,
            deck_thickness_required=230.0,
            crossbeam_layout_ok=True,
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
            design, report = run_with_repair_loop(
                bridge_length_m=20.0,
                total_width_m=8.0,
                max_iterations=5,
            )

        # 1回だけ照査が呼ばれること
        assert mock_judge.call_count == 1
        # 合格していること
        assert report.pass_fail is True

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
            design, report = run_with_repair_loop(
                bridge_length_m=50.0,
                total_width_m=12.0,
                max_iterations=5,
            )

        # 2回照査が呼ばれること
        assert mock_judge.call_count == 2
        # 最終的に合格していること
        assert report.pass_fail is True

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
            with pytest.raises(RuntimeError, match="収束しませんでした"):
                run_with_repair_loop(
                    bridge_length_m=50.0,
                    total_width_m=12.0,
                    max_iterations=3,
                )

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
                max_iterations=5,
            )

        # apply_patch_plan が1回呼ばれること
        assert mock_apply.call_count == 1
