# 評価方針

本ドキュメントでは、鋼プレートガーダー橋 BrIM 生成エージェントの評価方針を定義する。
論文用の定量的評価指標と、システムの限界を明確にすることを目的とする。

---

## 1. 評価の目的

1. **システム性能の定量化**: 設計生成・修正ループの有効性を客観的に示す
2. **RAG の貢献度評価**: RAG あり/なしの比較により、知識検索の効果を定量化する
3. **限界の明示**: システムが対応できる範囲と対応できない範囲を明確にする

---

## 2. 評価指標

### 2.1 設計生成品質（Design Quality Metrics）

| 指標 | 定義 | 計算方法 |
|------|------|----------|
| **初回合格率 (First-Pass Rate)** | 初回生成で全照査項目をパスした割合 | `iterations[0].report.pass_fail == True` の件数 / 全件数 |
| **修正収束率 (Convergence Rate)** | 最大反復回数以内に合格に到達した割合 | `converged == True` の件数 / 全件数 |
| **平均修正回数 (Avg. Iterations)** | 合格に至るまでの平均反復回数 | 収束ケースのみ `len(iterations)` の平均 |
| **最終合格率 (Final Pass Rate)** | 修正ループ後の最終合格率 | `final_report.pass_fail == True` の件数 / 全件数 |

### 2.2 照査項目別評価（Per-Check Metrics）

各照査項目について、初回設計での合格率を測定する。

| 照査項目 | 合格条件 |
|----------|----------|
| 曲げ (bend) | `util_bend ≤ 1.0` |
| せん断 (shear) | `util_shear ≤ 1.0` |
| たわみ (deflection) | `util_deflection ≤ 1.0` |
| 床版厚 (deck) | `util_deck ≤ 1.0` |
| 腹板幅厚比 (web_slenderness) | `util_web_slenderness ≤ 1.0` |
| 横桁配置 (crossbeam_layout) | `crossbeam_layout_ok == True` |

**目的**: どの照査項目が LLM にとって難しいかを特定する。

### 2.3 RAG 貢献度評価（RAG Contribution Metrics）

RAG あり/なしの条件で同一ケースを生成し、以下を比較する。

| 比較指標 | 説明 |
|----------|------|
| **初回合格率の差** | RAG あり vs なし |
| **平均修正回数の差** | RAG あり vs なし |
| **初回 max_util の差** | 初回設計の最大 util 値の比較 |
| **収束率の差** | RAG あり vs なし |

**仮説**: RAG ありの方が初回合格率が高く、修正回数が少ない。

---

## 3. 評価ケース

### 3.1 評価ケース一覧

橋長 L=20〜70m、幅員 B=8〜24m の組み合わせ（32 ケース）を選定する。
ケース定義は `src/evaluation/main.py` の `DEFAULT_EVALUATION_CASES` で管理。

| L (m) | B (m) の組み合わせ |
|-------|---------------------|
| 20 | 8, 10 |
| 25 | 8, 10, 12 |
| 30 | 8, 10, 12 |
| 35 | 8, 10, 16 |
| 40 | 8, 10, 20 |
| 45 | 8, 10, 20 |
| 50 | 10, 16, 24 |
| 55 | 10, 16, 24 |
| 60 | 10, 16, 24 |
| 65 | 12, 16, 24 |
| 70 | 12, 16, 24 |

**備考**:
- 支間 80m 以下が L 荷重の適用範囲（システム制約）
- 短橋（L≤35m）では狭幅員（B=8〜12m）、長橋（L≥50m）では広幅員（B=16〜24m）を含む

### 3.2 試行回数

| 条件 | 試行回数 | 理由 |
|------|----------|------|
| 各ケース × RAG条件 | 3回 | LLM 生成のばらつきを考慮 |

**合計実行数**: 32ケース × 2条件 × 3回 = 192回

### 3.3 使用モデル

| 項目 | 値 |
|------|-----|
| LLM モデル | GPT-5.1 (`gpt-5-1`) |

**備考**: Designer（設計生成）と Judge（PatchPlan生成）の両方で同一モデルを使用する。

### 3.4 最大修正回数

| パラメータ | 値 |
|------------|-----|
| max_iterations | 5 |

---

## 4. 評価手順

### 4.1 実行フロー

```
1. 評価ケース（L, B）の組み合わせを定義
2. 各ケースについて:
   a. RAG あり で N 回生成・修正ループ実行
   b. RAG なし で N 回生成・修正ループ実行
   c. 各試行の結果を記録
3. 結果を集計し、指標を算出
4. レポートを出力
```

### 4.2 RAG なし生成

`generate_design_with_rag_log` の `use_rag` パラメータで RAG の有無を切り替える（実装済み）。

```python
def generate_design_with_rag_log(
    inputs: DesignerInput,
    top_k: int = TOP_K,
    model_name: LlmModel = LlmModel.GPT_5_MINI,
    use_rag: bool = True,
) -> DesignResult:
    """use_rag=False の場合、RAG 検索をスキップし空のコンテキストで生成する。"""
```

---

## 5. 出力形式

### 5.1 生データ（JSON）

各試行の詳細結果を JSON で保存する。

```json
{
  "case_id": "L50_B10_rag_true_trial_1",
  "bridge_length_m": 50,
  "total_width_m": 10,
  "use_rag": true,
  "trial": 1,
  "converged": true,
  "num_iterations": 2,
  "first_pass": false,
  "first_max_util": 1.23,
  "first_utilization": {
    "deck": 0.85,
    "bend": 1.23,
    "shear": 0.45,
    "deflection": 0.92,
    "web_slenderness": 0.78
  },
  "final_pass": true,
  "final_max_util": 0.95,
  "per_check_first_pass": {
    "deck": true,
    "bend": false,
    "shear": true,
    "deflection": true,
    "web_slenderness": true,
    "crossbeam_layout": true
  }
}
```

### 5.2 集計レポート（Markdown）

```markdown
## 評価結果サマリー

### 全体指標

| 条件 | 初回合格率 | 収束率 | 平均修正回数 | 最終合格率 |
|------|-----------|--------|--------------|------------|
| RAG あり | 32% (8/25) | 92% (23/25) | 2.1 | 92% |
| RAG なし | 12% (3/25) | 72% (18/25) | 3.4 | 72% |

### 照査項目別初回合格率

| 照査項目 | RAG あり | RAG なし | 差分 |
|----------|----------|----------|------|
| 曲げ | 76% | 56% | +20% |
| せん断 | 92% | 84% | +8% |
| たわみ | 48% | 28% | +20% |
| 床版厚 | 88% | 88% | 0% |
| 腹板幅厚比 | 80% | 64% | +16% |
| 横桁配置 | 96% | 92% | +4% |

### 橋長別の収束率

| 橋長 | RAG あり | RAG なし |
|------|----------|----------|
| 30m | 100% | 80% |
| 40m | 100% | 80% |
| 50m | 80% | 60% |
| 60m | 80% | 60% |
| 70m | 100% | 80% |
```

---

## 6. システムの限界

評価結果とは別に、システムの適用限界を明記する。

### 6.1 対応範囲

| 項目 | 範囲 |
|------|------|
| 橋梁形式 | 単純支持プレートガーダー橋（RC床版） |
| 支間長 | ≤ 80m（L荷重適用範囲） |
| 荷重条件 | B活荷重（L荷重・p1/p2ルール） |
| 設計段階 | 概略設計（断面寸法の決定） |

### 6.2 非対応項目

| 項目 | 理由 |
|------|------|
| 連続桁・ラーメン橋 | 単純桁の解析モデルのみ実装 |
| 支間 > 80m | L荷重の適用範囲外 |
| 詳細設計 | 溶接・ボルト接合・疲労照査等は未実装 |
| FEM解析 | 決定論的な簡易計算のみ |
| 特殊荷重 | 標準B活荷重のみ対応 |

---

## 7. 今後の拡張可能性

1. **専門家評価の追加**: 生成された設計の実務適用可能性を専門家が評価
2. **異なるLLMモデルの比較**: GPT-5.1 vs GPT-5-mini 等
3. **RAG精度の詳細評価**: Recall@k, MRR などの検索精度指標

---

## 8. 実装状況

### Phase 1: 評価基盤（完了）

- [x] 評価用モデル定義（`src/evaluation/models.py`）
- [x] 指標計算ロジック（`src/evaluation/metrics.py`）
- [x] RAG なし生成オプション追加（`use_rag` パラメータ）
- [x] バッチ評価 CLI（`src/evaluation/runner.py`）
- [x] グラフ出力（`src/evaluation/plot.py`）
- [x] 評価 CLI エントリーポイント（`src/evaluation/main.py`）

### Phase 2: 評価実行

- [ ] 全ケースの評価実行
- [ ] 結果の集計・レポート生成
- [ ] 論文用の図表作成

### 評価 CLI コマンド

```bash
# 全ケース実行（32ケース × RAG有無 × 3試行）
uv run python -m src.evaluation.main run

# 単一ケースのテスト実行
uv run python -m src.evaluation.main single_case \
  --bridge_length_m 50 --total_width_m 10

# RAG なしで単一ケース実行
uv run python -m src.evaluation.main single_case \
  --bridge_length_m 50 --total_width_m 10 --use_rag False

# 評価結果のグラフ生成
uv run python -m src.evaluation.main plot --data_dir data/evaluation_v5
```

---

## 参考資料

- [docs/COMPONENT_DESIGNER.md](COMPONENT_DESIGNER.md) - Designer 詳細
- [docs/COMPONENT_JUDGE.md](COMPONENT_JUDGE.md) - Judge 詳細
