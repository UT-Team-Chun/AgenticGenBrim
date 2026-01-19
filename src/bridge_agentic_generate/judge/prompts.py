"""Judge 用プロンプト定義と LLM 連携。

仕様: judge_impl.md に基づく PatchPlan 生成。
"""

from __future__ import annotations

from src.bridge_agentic_generate.judge.models import PatchPlan, RepairContext
from src.bridge_agentic_generate.llm_client import LlmModel, call_llm_with_structured_output
from src.bridge_agentic_generate.logger_config import logger


def build_repair_system_prompt() -> str:
    """PatchPlan 生成用のシステムプロンプトを構築する。

    Returns:
        システムプロンプト文字列
    """
    return """あなたは鋼プレートガーダー橋の構造設計を最適化するエンジニアです。

与えられた照査結果（util）と現在の設計値を分析し、
合格（全util ≤ 1.0）となるための修正案（PatchPlan）を提案してください。

## 修正の優先順位（厳守）
1. **安全**: すべての util ≤ 1.0 を達成する
2. **施工性**: 急激な変更を避ける（最小限の変更量を優先）
3. **鋼重最小**: 同等の効果なら軽量化に寄与する案を選ぶ

## 制約条件
- 修正アクション（actions）は**最大3件**まで
- 許可された操作（allowed_actions）と変更量（allowed_deltas）のみ使用可能
- 急激な変更を避ける（例: 最初は +100mm を優先し、必要なら次ループで追加）

## 各util項目と効果的な修正
- **util_deck > 1.0**: `set_deck_thickness_to_required` で床版厚を必要値に設定
- **util_bend > 1.0**:
  - `increase_web_height`: 断面二次モーメント増加（曲げ・たわみ両方に効果大）
  - `increase_bottom_flange_thickness/width`: 引張側フランジ増強
- **util_shear > 1.0**:
  - `increase_web_thickness`: せん断抵抗面積増加
  - `increase_web_height`: せん断抵抗面積増加
- **util_deflection > 1.0**:
  - `increase_web_height`: 断面二次モーメント増加（最も効果的）
  - フランジ増強: 断面二次モーメント増加
- **crossbeam_layout_ok = false**: `fix_crossbeam_layout` で横桁配置を修正

## 出力フォーマット
PatchPlan を JSON で返してください。各 action には:
- `op`: 操作種別（allowed_actions から選択）
- `path`: 対象フィールドパス
- `delta_mm`: 変更量（allowed_deltas から選択）
- `reason`: 変更理由（どの util を改善するか、なぜその変更量か）

支配的な util（governing_check）を優先的に改善してください。"""


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
