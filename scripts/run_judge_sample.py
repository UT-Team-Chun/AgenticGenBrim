"""Judge v1 のサンプル実行スクリプト。

使い方:
    uv run python scripts/run_judge_sample.py
"""

from __future__ import annotations

import json
from pathlib import Path

from src.bridge_agentic_generate.designer.models import BridgeDesign
from src.bridge_agentic_generate.judge import JudgeInput, judge_v1


def main() -> None:
    """Judge v1 をサンプル実行する（LLM 呼び出しあり）。"""
    # fixture JSON を読み込む
    fixture_path = Path("data/generated_simple_bridge_json/design_L30_B10_20260117_204222.json")

    if not fixture_path.exists():
        print(f"Fixture ファイルが見つかりません: {fixture_path}")
        print("代わりにハードコードした設計を使用します。")
        design_dict = {
            "dimensions": {
                "bridge_length": 30000.0,
                "total_width": 10000.0,
                "num_girders": 4,
                "girder_spacing": 2667.0,
                "panel_length": 5000.0,
                "num_panels": 6,
            },
            "sections": {
                "girder_standard": {
                    "web_height": 1400.0,
                    "web_thickness": 16.0,
                    "top_flange_width": 350.0,
                    "top_flange_thickness": 25.0,
                    "bottom_flange_width": 450.0,
                    "bottom_flange_thickness": 30.0,
                },
                "crossbeam_standard": {
                    "total_height": 1120.0,
                    "web_thickness": 10.0,
                    "flange_width": 280.0,
                    "flange_thickness": 12.0,
                },
            },
            "components": {"deck": {"thickness": 217.0}},
        }
    else:
        with open(fixture_path) as f:
            design_dict = json.load(f)
        print(f"Fixture 読み込み完了: {fixture_path}")

    # BridgeDesign を作成
    bridge_design = BridgeDesign.model_validate(design_dict)

    # JudgeInput を作成
    judge_input = JudgeInput(bridge_design=bridge_design)

    print("\n" + "=" * 60)
    print("Judge v1 実行（LLM で PatchPlan 生成）")
    print("=" * 60)

    # 実際に LLM を呼び出して照査実行
    report = judge_v1(judge_input)

    # 結果を表示
    print("\n【照査結果】")
    print(f"  合否: {'合格' if report.pass_fail else '不合格'}")

    print("\n【util 値】")
    print(f"  deck (床版厚):     {report.utilization.deck:.4f}")
    print(f"  bend (曲げ):       {report.utilization.bend:.4f}")
    print(f"  shear (せん断):    {report.utilization.shear:.4f}")
    print(f"  deflection (たわみ): {report.utilization.deflection:.4f}")
    print(f"  max_util:          {report.utilization.max_util:.4f}")
    print(f"  支配項目:          {report.utilization.governing_check}")

    print("\n【診断情報（抜粋）】")
    diag = report.diagnostics
    print(f"  w_dead (死荷重):   {diag.w_dead:.4f} N/mm")
    print(f"  M_dead:            {diag.M_dead:.2e} N·mm")
    print(f"  M_live_max:        {diag.M_live_max:.2e} N·mm")
    print(f"  M_total:           {diag.M_total:.2e} N·mm")
    print(f"  I (断面二次モーメント): {diag.moment_of_inertia:.2e} mm⁴")
    print(f"  sigma_top:         {diag.sigma_top:.2f} N/mm² (allow: {diag.sigma_allow:.2f})")
    print(f"  sigma_bottom:      {diag.sigma_bottom:.2f} N/mm² (allow: {diag.sigma_allow:.2f})")
    print(f"  tau_avg:           {diag.tau_avg:.2f} N/mm² (allow: {diag.tau_allow:.2f})")
    print(f"  delta:             {diag.delta:.2f} mm (allow: {diag.delta_allow:.2f} mm)")
    print(f"  deck_required:     {diag.deck_thickness_required:.1f} mm")
    print(f"  crossbeam_layout:  {'OK' if diag.crossbeam_layout_ok else 'NG'}")

    if not report.pass_fail:
        print("\n【修正案 (PatchPlan) - LLM が生成】")
        for i, action in enumerate(report.patch_plan.actions, 1):
            print(f"  {i}. {action.op}")
            print(f"     path: {action.path}")
            print(f"     delta: {action.delta_mm} mm")
            print(f"     理由: {action.reason}")

    print("\n" + "=" * 60)
    print("完了")
    print("=" * 60)


if __name__ == "__main__":
    main()
