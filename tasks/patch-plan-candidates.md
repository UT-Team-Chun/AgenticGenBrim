# PatchPlan生成の改善: 方針ベースプロンプト + 複数候補方式

## 背景・課題

現在のシステムプロンプト（`prompts.py:31-42`）が特定の定石にLLMを誘導している：
- 「util_bend > 1.0: ... 最後に increase_web_height」→ 曲げだけ残っててもwebに寄る癖（自重増で収束が鈍る）
- 「util_deck > 1.0: set_deck_thickness_to_required を必ず入れる」→ 丸め誤差（1.00〜1.02）でも入れがち → 3手の枠を無駄にしやすい

**目的**: LLMの「考える力」を活かしつつ、数値評価で安定性を担保する

---

## 変更内容

### 1. システムプロンプトの変更

**ファイル**: `src/bridge_agentic_generate/judge/prompts.py`
**対象**: `build_repair_system_prompt()` (行13-52)

**削除**: 行31-42の「各utilと修正方針（優先順位付き）」

**新しいプロンプト**:
```python
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
各案の reason には「何を支配と見て、どれくらい下げる狙いか」を短く書く。
"""
```

**ポイント**:
- 「こうしろ」を削除し、「評価基準と観察点」だけを渡す
- 3案を要求することを明示
- deckの1.00問題を明示的に注意喚起

---

### 2. 新しいモデルの追加

**ファイル**: `src/bridge_agentic_generate/judge/models.py`

```python
class PatchPlanCandidate(BaseModel):
    """修正計画の候補1件。"""
    plan: PatchPlan = Field(..., description="修正計画")
    approach_summary: str = Field(..., description="アプローチの概要（例: フランジ厚重視）")


class PatchPlanCandidates(BaseModel):
    """修正計画の候補リスト（LLMが生成）。"""
    candidates: list[PatchPlanCandidate] = Field(
        default_factory=list,
        min_length=1,
        max_length=5,
    )


class EvaluatedCandidate(BaseModel):
    """評価済み候補。"""
    candidate: PatchPlanCandidate
    simulated_max_util: float
    simulated_utilization: Utilization
    improvement: float  # 正なら改善
```

---

### 3. 軽量Judge関数の追加

**ファイル**: `src/bridge_agentic_generate/judge/services.py`

**リファクタ**: `judge_v1`の計算ロジック（行278-422）を抽出

```python
def _calculate_utilization_and_diagnostics(
    judge_input: JudgeInput,
) -> tuple[Utilization, Diagnostics, bool]:
    """util と diagnostics を計算する（LLM呼び出しなし）。"""
    # 既存の judge_v1 から行278-422を移動
    # pass_fail = (max_util <= 1.0) and crossbeam_layout_ok
    return utilization, diagnostics, pass_fail


def judge_v1_lightweight(judge_input: JudgeInput) -> tuple[Utilization, Diagnostics]:
    """軽量版Judge（LLM呼び出しなし）。PatchPlanの仮適用評価用。"""
    utilization, diagnostics, _ = _calculate_utilization_and_diagnostics(judge_input)
    return utilization, diagnostics
```

**judge_v1 の修正**:
```python
def judge_v1(judge_input: JudgeInput, model: LlmModel) -> JudgeReport:
    utilization, diagnostics, pass_fail = _calculate_utilization_and_diagnostics(judge_input)

    if pass_fail:
        patch_plan = PatchPlan(actions=[])
    else:
        repair_context = _build_repair_context(...)
        patch_plan = generate_patch_plan(
            context=repair_context,
            model=model,
            design=judge_input.bridge_design,
            judge_input_base=judge_input,
        )
    # ...
```

---

### 4. generate_patch_plan の変更

**ファイル**: `src/bridge_agentic_generate/judge/prompts.py`

**シグネチャ変更**:
```python
def generate_patch_plan(
    context: RepairContext,
    model: LlmModel,
    design: BridgeDesign,          # 追加
    judge_input_base: JudgeInput,  # 追加
) -> PatchPlan:
```

**処理フロー**:
1. LLMに `PatchPlanCandidates`（3案）を生成させる
2. 各案を `apply_patch_plan` → `judge_v1_lightweight` で評価
3. `max_util` が最も低い案を採用
4. 全案が悪化する場合は、悪化幅が最小の案を採用

```python
def generate_patch_plan(...) -> PatchPlan:
    # 1. LLMに3案を生成させる
    candidates = call_llm_with_structured_output(
        input=full_prompt,
        model=model,
        text_format=PatchPlanCandidates,
    )

    # 2. 各案を評価
    current_max_util = context.utilization.max_util
    evaluated = []

    for candidate in candidates.candidates:
        simulated_design = apply_patch_plan(
            design=design,
            patch_plan=candidate.plan,
            deck_thickness_required=context.deck_thickness_required,
        )
        simulated_input = judge_input_base.model_copy(
            update={"bridge_design": simulated_design}
        )
        simulated_util, _ = judge_v1_lightweight(simulated_input)
        improvement = current_max_util - simulated_util.max_util

        evaluated.append(EvaluatedCandidate(
            candidate=candidate,
            simulated_max_util=simulated_util.max_util,
            simulated_utilization=simulated_util,
            improvement=improvement,
        ))

    # 3. 最良案を選択（improvement最大 = max_util最小）
    best = max(evaluated, key=lambda e: e.improvement)
    return best.candidate.plan
```

---

## 変更ファイル一覧

| ファイル | 変更内容 |
|---------|---------|
| `src/bridge_agentic_generate/judge/models.py` | `PatchPlanCandidate`, `PatchPlanCandidates`, `EvaluatedCandidate` 追加 |
| `src/bridge_agentic_generate/judge/prompts.py` | `build_repair_system_prompt` 書き換え、`generate_patch_plan` シグネチャ変更・ロジック変更 |
| `src/bridge_agentic_generate/judge/services.py` | `_calculate_utilization_and_diagnostics` 抽出、`judge_v1_lightweight` 追加、`judge_v1` リファクタ |
| `tests/judge/test_services.py` | `judge_v1_lightweight` のテスト追加 |

---

## 実装順序

1. **Phase 1: モデル追加** - `models.py` に3つのクラスを追加
2. **Phase 2: 計算ロジック抽出** - `_calculate_utilization_and_diagnostics` + `judge_v1_lightweight`
3. **Phase 3: システムプロンプト変更** - `build_repair_system_prompt` 書き換え
4. **Phase 4: 複数候補ロジック** - `generate_patch_plan` の変更
5. **Phase 5: テスト・検証** - ユニットテスト + 手動テスト

---

## 検証方法

```bash
# 1. Lint/フォーマット
make fix

# 2. 既存テスト（モック使用）
uv run pytest tests/judge/ -v

# 3. 手動テスト（実際のLLM呼び出し）
uv run python -m src.bridge_agentic_generate.main run_with_repair \
  --bridge_length_m 50 \
  --total_width_m 10 \
  --max_iterations 5

# 期待する挙動:
# - ログに「候補1 (...): max_util=X→Y (improvement=Z)」が3行出る
# - 最良案が選択されたログが出る
# - 収束するまでのイテレーション数が減るか同等
```

---

## 注意点

- **Breaking change**: `generate_patch_plan` のシグネチャが変わるため、呼び出し元（`judge_v1`）の修正が必須
- **パフォーマンス**: 1回の提案で3回の軽量評価が必要だが、LLM呼び出しは1回のままなのでほぼ影響なし
- **後方互換性なし**: 単一候補方式は完全に置き換え（要件通り）
