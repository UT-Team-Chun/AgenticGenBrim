"""修正ループレポート生成モジュール。

RepairLoopResult の変遷を Markdown 形式でレポートする。
"""

from __future__ import annotations

from pathlib import Path

from src.bridge_agentic_generate.judge.models import (
    RepairIteration,
    RepairLoopResult,
)


def generate_repair_report(
    result: RepairLoopResult,
    output_path: Path | None = None,
) -> str:
    """修正ループの変遷を Markdown レポートとして生成する。

    Args:
        result: 修正ループの結果
        output_path: 出力先ファイルパス（指定時はファイルにも保存）

    Returns:
        Markdown 形式のレポート文字列
    """
    sections = [
        "# 修正ループレポート",
        "",
        _format_summary(result),
        _format_section_dimensions_table(result.iterations),
        _format_judge_results_table(result.iterations),
        _format_diagnostics_table(result.iterations),
    ]

    report = "\n".join(sections)

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")

    return report


def _format_summary(result: RepairLoopResult) -> str:
    """サマリーセクションを生成する。

    Args:
        result: 修正ループの結果

    Returns:
        サマリーセクションの Markdown 文字列
    """
    final_util = result.final_report.utilization
    lines = [
        "## サマリー",
        "",
        f"- **収束**: {result.converged}",
        f"- **イテレーション数**: {len(result.iterations)}",
        f"- **最終 max_util**: {final_util.max_util:.2f}",
        f"- **支配的照査項目**: {final_util.governing_check.value}",
        "",
    ]
    return "\n".join(lines)


def _format_section_dimensions_table(iterations: list[RepairIteration]) -> str:
    """断面量の変遷テーブル（主桁・横桁・床版）を生成する。

    Args:
        iterations: イテレーションのリスト

    Returns:
        断面量テーブルの Markdown 文字列
    """
    lines = ["## 断面量の変遷", ""]

    # 主桁 (GirderSection)
    lines.append("### 主桁 (GirderSection)")
    lines.append("")
    girder_cols = [
        "Iter",
        "web_height",
        "web_thickness",
        "top_flange_width",
        "top_flange_thickness",
        "bottom_flange_width",
        "bottom_flange_thickness",
    ]
    lines.append("| " + " | ".join(girder_cols) + " |")
    girder_sep = (
        "|------|------------|---------------|------------------|"
        "----------------------|---------------------|-------------------------|"
    )
    lines.append(girder_sep)

    for it in iterations:
        g = it.design.sections.girder_standard
        vals = [
            str(it.iteration),
            f"{g.web_height:.0f}",
            f"{g.web_thickness:.0f}",
            f"{g.top_flange_width:.0f}",
            f"{g.top_flange_thickness:.0f}",
            f"{g.bottom_flange_width:.0f}",
            f"{g.bottom_flange_thickness:.0f}",
        ]
        lines.append("| " + " | ".join(vals) + " |")

    lines.append("")

    # 横桁 (CrossbeamSection)
    lines.append("### 横桁 (CrossbeamSection)")
    lines.append("")
    crossbeam_header = "| Iter | total_height | web_thickness | flange_width | flange_thickness |"
    crossbeam_sep = "|------|--------------|---------------|--------------|------------------|"
    lines.append(crossbeam_header)
    lines.append(crossbeam_sep)

    for it in iterations:
        c = it.design.sections.crossbeam_standard
        vals = [
            str(it.iteration),
            f"{c.total_height:.0f}",
            f"{c.web_thickness:.0f}",
            f"{c.flange_width:.0f}",
            f"{c.flange_thickness:.0f}",
        ]
        lines.append("| " + " | ".join(vals) + " |")

    lines.append("")

    # 床版 (Deck)
    lines.append("### 床版 (Deck)")
    lines.append("")
    deck_header = "| Iter | thickness |"
    deck_sep = "|------|-----------|"
    lines.append(deck_header)
    lines.append(deck_sep)

    for it in iterations:
        d = it.design.components.deck
        row = f"| {it.iteration} | {d.thickness:.0f} |"
        lines.append(row)

    lines.append("")

    return "\n".join(lines)


def _format_judge_results_table(iterations: list[RepairIteration]) -> str:
    """照査結果の変遷テーブルを生成する。

    Args:
        iterations: イテレーションのリスト

    Returns:
        照査結果テーブルの Markdown 文字列
    """
    lines = ["## 照査結果の変遷", ""]
    header = "| Iter | deck  | bend  | shear | deflection | max_util | pass_fail | governing_check |"
    sep = "|------|-------|-------|-------|------------|----------|-----------|-----------------|"
    lines.append(header)
    lines.append(sep)

    for it in iterations:
        u = it.report.utilization
        vals = [
            str(it.iteration),
            f"{u.deck:.2f}",
            f"{u.bend:.2f}",
            f"{u.shear:.2f}",
            f"{u.deflection:.2f}",
            f"{u.max_util:.2f}",
            str(it.report.pass_fail),
            u.governing_check.value,
        ]
        lines.append("| " + " | ".join(vals) + " |")

    lines.append("")

    return "\n".join(lines)


def _format_diagnostics_table(iterations: list[RepairIteration]) -> str:
    """Diagnostics 抜粋の変遷テーブルを生成する。

    Args:
        iterations: イテレーションのリスト

    Returns:
        Diagnostics テーブルの Markdown 文字列
    """
    lines = ["## Diagnostics 抜粋", ""]
    header_cols = [
        "Iter",
        "M_total [N-mm]",
        "sigma_bottom [N/mm2]",
        "tau_avg [N/mm2]",
        "delta [mm]",
        "delta_allow [mm]",
    ]
    lines.append("| " + " | ".join(header_cols) + " |")
    lines.append("|------|----------------|----------------------|-----------------|------------|------------------|")

    for it in iterations:
        diag = it.report.diagnostics
        vals = [
            str(it.iteration),
            f"{diag.M_total:.2e}",
            f"{diag.sigma_bottom:.1f}",
            f"{diag.tau_avg:.1f}",
            f"{diag.delta:.1f}",
            f"{diag.delta_allow:.1f}",
        ]
        lines.append("| " + " | ".join(vals) + " |")

    lines.append("")

    return "\n".join(lines)
