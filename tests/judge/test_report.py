"""修正ループレポート生成モジュールのテスト。"""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from src.bridge_agentic_generate.designer.models import (
    BridgeDesign,
    Components,
    CrossbeamSection,
    Deck,
    DesignerRagLog,
    Dimensions,
    GirderSection,
    Sections,
)
from src.bridge_agentic_generate.judge.models import (
    Diagnostics,
    GoverningCheck,
    JudgeReport,
    PatchPlan,
    RepairIteration,
    RepairLoopResult,
    Utilization,
)
from src.bridge_agentic_generate.judge.report import (
    _format_diagnostics_table,
    _format_judge_results_table,
    _format_section_dimensions_table,
    _format_summary,
    generate_repair_report,
)


@pytest.fixture
def sample_iterations() -> list[RepairIteration]:
    """テスト用のイテレーションリスト。"""

    def make_design(
        web_height: float,
        crossbeam_height: float,
        deck_thickness: float,
    ) -> BridgeDesign:
        return BridgeDesign(
            dimensions=Dimensions(
                bridge_length=50000.0,
                total_width=10000.0,
                num_girders=4,
                girder_spacing=2500.0,
                panel_length=10000.0,
                num_panels=5,
            ),
            sections=Sections(
                girder_standard=GirderSection(
                    web_height=web_height,
                    web_thickness=16.0,
                    top_flange_width=350.0,
                    top_flange_thickness=25.0,
                    bottom_flange_width=450.0,
                    bottom_flange_thickness=30.0,
                ),
                crossbeam_standard=CrossbeamSection(
                    total_height=crossbeam_height,
                    web_thickness=10.0,
                    flange_width=280.0,
                    flange_thickness=12.0,
                ),
            ),
            components=Components(deck=Deck(thickness=deck_thickness)),
        )

    def make_report(
        deck_util: float,
        bend_util: float,
        shear_util: float,
        deflection_util: float,
        m_total: float,
        sigma_bottom: float,
        tau_avg: float,
        delta: float,
        delta_allow: float,
        web_slenderness_util: float = 0.68,
        web_thickness_min_required: float = 10.8,
    ) -> JudgeReport:
        max_util = max(deck_util, bend_util, shear_util, deflection_util, web_slenderness_util)
        governing = GoverningCheck.DEFLECTION
        if max_util == deck_util:
            governing = GoverningCheck.DECK
        elif max_util == bend_util:
            governing = GoverningCheck.BEND
        elif max_util == shear_util:
            governing = GoverningCheck.SHEAR
        elif max_util == web_slenderness_util:
            governing = GoverningCheck.WEB_SLENDERNESS

        return JudgeReport(
            pass_fail=max_util <= 1.0,
            utilization=Utilization(
                deck=deck_util,
                bend=bend_util,
                shear=shear_util,
                deflection=deflection_util,
                web_slenderness=web_slenderness_util,
                max_util=max_util,
                governing_check=governing,
            ),
            diagnostics=Diagnostics(
                b_tr=2500.0,
                w_dead=18.0,
                M_dead=5.625e9,
                V_dead=450000.0,
                M_live_max=4.5e9,
                V_live_max=360000.0,
                M_total=m_total,
                V_total=810000.0,
                ybar=700.0,
                moment_of_inertia=1.5e10,
                y_top=755.0,
                y_bottom=700.0,
                sigma_top=150.0,
                sigma_bottom=sigma_bottom,
                tau_avg=tau_avg,
                delta=delta,
                delta_allow=delta_allow,
                fy_top_flange=315.0,
                fy_bottom_flange=315.0,
                fy_web=325.0,
                sigma_allow_top=189.0,
                sigma_allow_bottom=189.0,
                tau_allow=112.6,
                deck_thickness_required=185.0,
                web_thickness_min_required=web_thickness_min_required,
                crossbeam_layout_ok=True,
            ),
            patch_plan=PatchPlan(actions=[]),
        )

    return [
        RepairIteration(
            iteration=0,
            design=make_design(1400.0, 1120.0, 217.0),
            report=make_report(0.92, 1.15, 0.73, 1.42, 4.5e9, 162.3, 61.2, 28.4, 20.0),
        ),
        RepairIteration(
            iteration=1,
            design=make_design(1600.0, 1280.0, 217.0),
            report=make_report(0.91, 0.98, 0.68, 1.12, 4.5e9, 138.7, 57.1, 22.4, 20.0),
        ),
        RepairIteration(
            iteration=2,
            design=make_design(1800.0, 1440.0, 220.0),
            report=make_report(0.91, 0.89, 0.62, 0.95, 4.5e9, 121.5, 52.3, 19.0, 20.0),
        ),
    ]


@pytest.fixture
def sample_repair_loop_result(
    sample_iterations: list[RepairIteration],
) -> RepairLoopResult:
    """テスト用の RepairLoopResult。"""
    return RepairLoopResult(
        converged=True,
        iterations=sample_iterations,
        final_design=sample_iterations[-1].design,
        final_report=sample_iterations[-1].report,
        rag_log=DesignerRagLog(query="test query", top_k=5, hits=[]),
    )


class TestFormatSummary:
    """_format_summary のテスト。"""

    def test_format_summary_content(self, sample_repair_loop_result: RepairLoopResult) -> None:
        """サマリーが正しくフォーマットされること。"""
        summary = _format_summary(sample_repair_loop_result)

        assert "## サマリー" in summary
        assert "**収束**: True" in summary
        assert "**イテレーション数**: 3" in summary
        assert "**最終 max_util**: 0.95" in summary
        assert "**支配的照査項目**: deflection" in summary


class TestFormatSectionDimensionsTable:
    """_format_section_dimensions_table のテスト。"""

    def test_format_girder_section(self, sample_iterations: list[RepairIteration]) -> None:
        """主桁断面テーブルが正しくフォーマットされること。"""
        table = _format_section_dimensions_table(sample_iterations)

        assert "### 主桁 (GirderSection)" in table
        assert "| Iter | web_height |" in table
        assert "| 0 | 1400 |" in table
        assert "| 1 | 1600 |" in table
        assert "| 2 | 1800 |" in table

    def test_format_crossbeam_section(self, sample_iterations: list[RepairIteration]) -> None:
        """横桁断面テーブルが正しくフォーマットされること。"""
        table = _format_section_dimensions_table(sample_iterations)

        assert "### 横桁 (CrossbeamSection)" in table
        assert "| Iter | total_height |" in table
        assert "| 0 | 1120 |" in table
        assert "| 1 | 1280 |" in table
        assert "| 2 | 1440 |" in table

    def test_format_deck(self, sample_iterations: list[RepairIteration]) -> None:
        """床版テーブルが正しくフォーマットされること。"""
        table = _format_section_dimensions_table(sample_iterations)

        assert "### 床版 (Deck)" in table
        assert "| Iter | thickness |" in table
        assert "| 0 | 217 |" in table
        assert "| 2 | 220 |" in table


class TestFormatJudgeResultsTable:
    """_format_judge_results_table のテスト。"""

    def test_format_judge_results(self, sample_iterations: list[RepairIteration]) -> None:
        """照査結果テーブルが正しくフォーマットされること。"""
        table = _format_judge_results_table(sample_iterations)

        assert "## 照査結果の変遷" in table
        assert "| Iter | deck  | bend  | shear | deflection | web_slend | max_util |" in table

        # iter 0: pass_fail=False, max_util=1.42, governing=deflection
        assert "| 0 | 0.92 | 1.15 | 0.73 | 1.42 | 0.68 | 1.42 | False | deflection |" in table

        # iter 2: pass_fail=True, max_util=0.95, governing=deflection
        assert "| 2 | 0.91 | 0.89 | 0.62 | 0.95 | 0.68 | 0.95 | True | deflection |" in table


class TestFormatDiagnosticsTable:
    """_format_diagnostics_table のテスト。"""

    def test_format_diagnostics(self, sample_iterations: list[RepairIteration]) -> None:
        """Diagnostics テーブルが正しくフォーマットされること。"""
        table = _format_diagnostics_table(sample_iterations)

        assert "## Diagnostics 抜粋" in table
        assert "| Iter | M_total [N-mm] | sigma_bottom [N/mm2] |" in table
        assert "web_t_min [mm]" in table

        # iter 0: M_total=4.5e9, sigma_bottom=162.3, tau_avg=61.2, delta=28.4, delta_allow=20.0, web_t_min=10.8
        assert "| 0 | 4.50e+09 | 162.3 | 61.2 | 28.4 | 20.0 | 10.8 |" in table

        # iter 2: delta=19.0, delta_allow=20.0, web_t_min=10.8
        assert "| 2 | 4.50e+09 | 121.5 | 52.3 | 19.0 | 20.0 | 10.8 |" in table


class TestGenerateRepairReport:
    """generate_repair_report のテスト。"""

    def test_generate_report_returns_string(self, sample_repair_loop_result: RepairLoopResult) -> None:
        """レポートが文字列として返されること。"""
        report = generate_repair_report(sample_repair_loop_result)

        assert isinstance(report, str)
        assert "# 修正ループレポート" in report

    def test_generate_report_contains_all_sections(self, sample_repair_loop_result: RepairLoopResult) -> None:
        """レポートに全セクションが含まれること。"""
        report = generate_repair_report(sample_repair_loop_result)

        assert "## サマリー" in report
        assert "## 断面量の変遷" in report
        assert "### 主桁 (GirderSection)" in report
        assert "### 横桁 (CrossbeamSection)" in report
        assert "### 床版 (Deck)" in report
        assert "## 照査結果の変遷" in report
        assert "## Diagnostics 抜粋" in report

    def test_generate_report_saves_to_file(self, sample_repair_loop_result: RepairLoopResult) -> None:
        """output_path 指定時にファイルに保存されること。"""
        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.md"

            report = generate_repair_report(sample_repair_loop_result, output_path=output_path)

            assert output_path.exists()
            file_content = output_path.read_text(encoding="utf-8")
            assert file_content == report

    def test_generate_report_creates_parent_dirs(self, sample_repair_loop_result: RepairLoopResult) -> None:
        """親ディレクトリが存在しない場合も作成されること。"""
        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "nested" / "dir" / "report.md"

            generate_repair_report(sample_repair_loop_result, output_path=output_path)

            assert output_path.exists()

    def test_generate_report_without_output_path(self, sample_repair_loop_result: RepairLoopResult) -> None:
        """output_path なしでもレポートが返されること。"""
        report = generate_repair_report(sample_repair_loop_result, output_path=None)

        assert isinstance(report, str)
        assert len(report) > 0


class TestGenerateRepairReportEdgeCases:
    """generate_repair_report のエッジケーステスト。"""

    def test_single_iteration(self) -> None:
        """イテレーション1回の場合でも正しく動作すること。"""
        design = BridgeDesign(
            dimensions=Dimensions(
                bridge_length=30000.0,
                total_width=10000.0,
                num_girders=4,
                girder_spacing=2500.0,
                panel_length=10000.0,
                num_panels=3,
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
            components=Components(deck=Deck(thickness=217.0)),
        )

        report_obj = JudgeReport(
            pass_fail=True,
            utilization=Utilization(
                deck=0.85,
                bend=0.90,
                shear=0.65,
                deflection=0.88,
                web_slenderness=0.68,
                max_util=0.90,
                governing_check=GoverningCheck.BEND,
            ),
            diagnostics=Diagnostics(
                b_tr=2500.0,
                w_dead=18.0,
                M_dead=2.025e9,
                V_dead=270000.0,
                M_live_max=2.0e9,
                V_live_max=200000.0,
                M_total=4.025e9,
                V_total=470000.0,
                ybar=700.0,
                moment_of_inertia=1.5e10,
                y_top=755.0,
                y_bottom=700.0,
                sigma_top=120.0,
                sigma_bottom=130.0,
                tau_avg=50.0,
                delta=15.0,
                delta_allow=17.0,
                fy_top_flange=315.0,
                fy_bottom_flange=315.0,
                fy_web=325.0,
                sigma_allow_top=189.0,
                sigma_allow_bottom=189.0,
                tau_allow=112.6,
                deck_thickness_required=185.0,
                web_thickness_min_required=10.8,
                crossbeam_layout_ok=True,
            ),
            patch_plan=PatchPlan(actions=[]),
        )

        result = RepairLoopResult(
            converged=True,
            iterations=[RepairIteration(iteration=0, design=design, report=report_obj)],
            final_design=design,
            final_report=report_obj,
            rag_log=DesignerRagLog(query="test", top_k=5, hits=[]),
        )

        report = generate_repair_report(result)

        assert "# 修正ループレポート" in report
        assert "**イテレーション数**: 1" in report
        assert "| 0 |" in report
