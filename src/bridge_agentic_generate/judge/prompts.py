"""Judge 用プロンプト定義と LLM 連携。

仕様: judge_impl.md に基づく PatchPlan 生成。
"""

from __future__ import annotations

from src.bridge_agentic_generate.judge.models import PatchPlan, RepairContext
from src.bridge_agentic_generate.llm_client import LlmModel, call_llm_with_structured_output
from src.bridge_agentic_generate.logger_config import logger


def build_repair_system_prompt() -> str:
    return """あなたは鋼プレートガーダー橋の設計を、照査結果に基づいて修正する担当です。
目的は「全util ≤ 1.0（できれば0.98以下）に最短で入れる」ことです。

## 最重要ルール（ブレ防止）
- 曲げ(util_bend)は、sigma_top と sigma_bottom のうち「大きい側」を支配側とみなす。
- 支配側が上（sigma_topが大）なら上フランジ、下（sigma_bottomが大）なら下フランジを優先する。
- util_deflection がすでに十分OK（例: ≤0.90）なら、曲げ対策で web_height を上げるのは最後の手段にする。
  （web_heightは効くが、自重も増えて M_total が増え、収束が遅くなりやすい）

## 目標の取り方
- 合格ラインは util ≤ 1.0 だが、ギリギリ落ちを避けるため「狙い」は 0.98 以下にする。
- utilが大きく超えているときは刻みを大きく、1.10未満なら最小刻みを使う。
  例:
  - util > 1.50: 大きめ（web +300 / flange_thk +6 / flange_w +100）
  - 1.10 < util ≤ 1.50: 中くらい（web +200 / flange_thk +4 / flange_w +50）
  - util ≤ 1.10: 小さめ（web +100 / flange_thk +2）

## 各utilと修正方針（優先順位付き）
- util_deck > 1.0: set_deck_thickness_to_required を必ず入れる（原則1手でOK）
- util_shear > 1.0:
  1) increase_web_thickness（+2→+4）
  2) それでもNGなら increase_web_height（+100→+200）
- util_deflection > 1.0:
  1) increase_web_height（+300→+200→+100の順でもよい）
  2) 次にフランジ厚（上下どちらでもOK）
- util_bend > 1.0:
  1) 支配側フランジ厚（+6→+4→+2 の順でもよい）
  2) 次に支配側フランジ幅（+100→+50）
  3) 最後に increase_web_height

## 制約
- actions は最大3件
- allowed_actions と allowed_deltas 以外は使わない
- 同じ目的の手を重複させない（例: web+100 と web+200 を同時に入れない）

## 出力
PatchPlan(JSON)のみを返す。各 action には op/path/delta_mm/reason を入れる。
reason には「どのutilをどれだけ下げる狙いか」を短く書く。
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
- sigma_top: {diag.sigma_top:.2f} N/mm² (allow: {diag.sigma_allow:.2f})
- sigma_bottom: {diag.sigma_bottom:.2f} N/mm² (allow: {diag.sigma_allow:.2f})
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


def generate_patch_plan(context: RepairContext, model: LlmModel) -> PatchPlan:
    """LLM を使用して PatchPlan を生成する。

    Args:
        context: RepairContext
        model: 使用する LLM モデル

    Returns:
        PatchPlan

    Raises:
        ValueError: LLM が有効な出力を返さなかった場合
    """
    system_prompt = build_repair_system_prompt()
    user_prompt = build_repair_user_prompt(context)

    full_prompt = f"{system_prompt}\n\n---\n\n{user_prompt}"

    logger.info("PatchPlan 生成: LLM 呼び出し開始 (model=%s)", model)
    logger.debug("RepairContext: governing=%s, max_util=%.3f", context.governing_check, context.utilization.max_util)

    patch_plan = call_llm_with_structured_output(
        input=full_prompt,
        model=model,
        text_format=PatchPlan,
    )

    logger.info("PatchPlan 生成完了: actions=%d件", len(patch_plan.actions))
    for action in patch_plan.actions:
        logger.info("  - %s: delta=%.0fmm, path=%s", action.op, action.delta_mm, action.path)

    return patch_plan
