"""Judge 用プロンプト定義と LLM 連携。

仕様: judge_impl.md に基づく PatchPlan 生成。
"""

from __future__ import annotations

from src.bridge_agentic_generate.designer.models import BridgeDesign
from src.bridge_agentic_generate.judge.models import (
    EvaluatedCandidate,
    JudgeInput,
    PatchPlan,
    PatchPlanCandidates,
    RepairContext,
)
from src.bridge_agentic_generate.llm_client import LlmModel, call_llm_with_structured_output
from src.bridge_agentic_generate.logger_config import logger


def build_repair_system_prompt() -> str:
    return """あなたは鋼プレートガーダー橋の設計を、照査結果に基づいて修正する担当です。
目的は「全util ≤ 1.0（できれば0.98以下）に最短で入れる」ことです。

## あなたの役割
あなたは修正案の探索者です。次のイテレーションで max_util を最も下げる PatchPlan を提案してください。
3案を提示し、それぞれ異なるアプローチを取ってください。

## 判断の方針
- 診断値（sigma_top, sigma_bottom, tau_avg, delta, I 等）に基づいて判断する
- 曲げが支配なら、sigma_top と sigma_bottom の大きい側を見て、効く変更を選ぶ
- たわみが支配なら、I（断面二次モーメント）を増やす方向を優先する
- せん断が支配なら、web_thickness を優先する
- deck は util_deck が 1.0 を明確に超えるときだけ触る（1.00〜1.02 程度の丸め誤差では触らない）

## 変更量の目安
- util が大きく超えているとき（> 1.50）: 大きめの刻み
- util が少し超えているとき（1.10 < util ≤ 1.50）: 中程度の刻み
- util がギリギリのとき（util ≤ 1.10）: 最小刻み

## 制約
- actions は各案で最大3件
- allowed_actions と allowed_deltas の範囲内のみ使用可能
- 同じ目的の変更を1つの案に重ねない（例: web+100 と web+200 を同時に入れない）

## 出力
PatchPlanCandidates（3案のリスト）をJSONで返す。
各案の approach_summary には「何を支配と見て、どれくらい下げる狙いか」を短く書く。
"""


def build_repair_user_prompt(context: RepairContext) -> str:
    """PatchPlan 生成用のユーザープロンプトを構築する。

    Args:
        context: RepairContext

    Returns:
        ユーザープロンプト文字列
    """
    # util 情報
    util = context.utilization
    util_info = f"""## 照査結果（util）
- deck: {util.deck:.4f} {"(NG)" if util.deck > 1.0 else "(OK)"}
- bend: {util.bend:.4f} {"(NG)" if util.bend > 1.0 else "(OK)"}
- shear: {util.shear:.4f} {"(NG)" if util.shear > 1.0 else "(OK)"}
- deflection: {util.deflection:.4f} {"(NG)" if util.deflection > 1.0 else "(OK)"}
- max_util: {util.max_util:.4f}
- governing_check: {util.governing_check}
- crossbeam_layout_ok: {context.crossbeam_layout_ok}"""

    # 現在の設計値
    design = context.current_design
    design_info = f"""## 現在の設計値
### 主桁断面 (girder_standard)
- web_height: {design.web_height:.1f} mm
- web_thickness: {design.web_thickness:.1f} mm
- top_flange_width: {design.top_flange_width:.1f} mm
- top_flange_thickness: {design.top_flange_thickness:.1f} mm
- bottom_flange_width: {design.bottom_flange_width:.1f} mm
- bottom_flange_thickness: {design.bottom_flange_thickness:.1f} mm

### 床版
- deck_thickness: {design.deck_thickness:.1f} mm
- deck_thickness_required: {context.deck_thickness_required:.1f} mm

### 横桁配置
- panel_length: {design.panel_length:.1f} mm
- num_panels: {design.num_panels}"""

    # 診断情報（主要なもののみ）
    diag = context.diagnostics
    diag_info = f"""## 診断情報
- M_total: {diag.M_total:.2e} N·mm
- V_total: {diag.V_total:.2e} N
- I (moment_of_inertia): {diag.moment_of_inertia:.2e} mm⁴
- fy_top_flange: {diag.fy_top_flange:.1f} N/mm²
- fy_bottom_flange: {diag.fy_bottom_flange:.1f} N/mm²
- fy_web: {diag.fy_web:.1f} N/mm²
- sigma_top: {diag.sigma_top:.2f} N/mm² (allow: {diag.sigma_allow_top:.2f})
- sigma_bottom: {diag.sigma_bottom:.2f} N/mm² (allow: {diag.sigma_allow_bottom:.2f})
- tau_avg: {diag.tau_avg:.2f} N/mm² (allow: {diag.tau_allow:.2f})
- delta: {diag.delta:.2f} mm (allow: {diag.delta_allow:.2f} mm)"""
    bend_side = "top" if abs(diag.sigma_top) >= abs(diag.sigma_bottom) else "bottom"
    extra = f"- bend_governing_side: {bend_side}\n- target_util: 0.98\n"

    # diag_info の末尾とかに追加
    diag_info += "\n" + extra

    # 許可されるアクション
    actions_info = "## 許可されるアクション\n"
    for action_spec in context.allowed_actions:
        deltas_str = ", ".join(f"{d:.0f}" for d in action_spec.allowed_deltas)
        actions_info += f"- {action_spec.op}: delta_mm ∈ {{{deltas_str}}}\n"

    # 優先順位
    priorities_info = f"## 修正の優先順位\n{context.priorities}"

    return f"""{util_info}

{design_info}

{diag_info}

{actions_info}
{priorities_info}

上記の情報を元に、合格（全 util ≤ 1.0 かつ crossbeam_layout_ok = true）となる PatchPlan を提案してください。"""


def generate_patch_plan(
    context: RepairContext,
    model: LlmModel,
    design: BridgeDesign,
    judge_input_base: JudgeInput,
) -> tuple[PatchPlan, list[EvaluatedCandidate]]:
    """LLM を使用して PatchPlan を生成する（複数候補方式）。

    1. LLMに PatchPlanCandidates（3案）を生成させる
    2. 各案を apply_patch_plan → judge_v1_lightweight で評価
    3. max_util が最も低い案を採用

    Args:
        context: RepairContext
        model: 使用する LLM モデル
        design: 現在の BridgeDesign
        judge_input_base: 評価用の JudgeInput ベース

    Returns:
        (PatchPlan, list[EvaluatedCandidate]) のタプル。最良案と全候補の評価結果。

    Raises:
        ValueError: LLM が有効な出力を返さなかった場合
    """
    # 循環インポート回避のため遅延インポート
    from src.bridge_agentic_generate.judge.services import apply_patch_plan, judge_v1_lightweight

    system_prompt = build_repair_system_prompt()
    user_prompt = build_repair_user_prompt(context)

    full_prompt = f"{system_prompt}\n\n---\n\n{user_prompt}"

    logger.info("PatchPlan 生成: LLM 呼び出し開始 (model=%s)", model)
    logger.debug("RepairContext: governing=%s, max_util=%.3f", context.governing_check, context.utilization.max_util)

    # 1. LLMに3案を生成させる
    candidates = call_llm_with_structured_output(
        input=full_prompt,
        model=model,
        text_format=PatchPlanCandidates,
    )

    logger.info("PatchPlan 候補: %d案を生成", len(candidates.candidates))

    # 2. 各案を評価
    current_max_util = context.utilization.max_util
    evaluated: list[EvaluatedCandidate] = []

    for i, candidate in enumerate(candidates.candidates):
        # 仮適用
        simulated_design = apply_patch_plan(
            design=design,
            patch_plan=candidate.plan,
            deck_thickness_required=context.deck_thickness_required,
        )
        simulated_input = judge_input_base.model_copy(update={"bridge_design": simulated_design})
        simulated_util, _ = judge_v1_lightweight(simulated_input)
        improvement = current_max_util - simulated_util.max_util

        evaluated.append(
            EvaluatedCandidate(
                candidate=candidate,
                simulated_max_util=simulated_util.max_util,
                simulated_utilization=simulated_util,
                improvement=improvement,
            )
        )

        logger.info(
            "  候補%d (%s): max_util=%.3f→%.3f (improvement=%.3f)",
            i + 1,
            candidate.approach_summary,
            current_max_util,
            simulated_util.max_util,
            improvement,
        )

    # 3. 最良案を選択（improvement最大 = max_util最小）
    best = max(evaluated, key=lambda e: e.improvement)
    logger.info(
        "PatchPlan 選択: 候補%d (%s) を採用, max_util=%.3f→%.3f",
        evaluated.index(best) + 1,
        best.candidate.approach_summary,
        current_max_util,
        best.simulated_max_util,
    )

    for action in best.candidate.plan.actions:
        logger.info("  - %s: delta=%.0fmm, path=%s", action.op, action.delta_mm, action.path)

    return best.candidate.plan, evaluated
