# COMPONENT_JUDGE

BridgeDesign を入力として決定論的な照査計算を行い、不合格時は LLM で修正提案（PatchPlan）を生成する Judge の概要。

## 概要

Judge は以下の責務を担う：

1. **決定論的照査**: 曲げ・せん断・たわみ・床版厚・腹板幅厚比・横桁配置の util を計算
2. **合否判定**: すべての util ≤ 1.0 かつ横桁配置 OK なら合格
3. **修正提案**: 不合格時は LLM が PatchPlan（修正操作リスト）を生成

## 入力（JudgeInput）

```python
class JudgeInput(BaseModel):
    bridge_design: BridgeDesign
    load_input: LoadInput = LoadInput()           # p_live_equiv: 12.0 kN/m²
    materials_steel: MaterialsSteel = ...         # E=2.0e5, fy=235, unit_weight=78.5e-6
    materials_concrete: MaterialsConcrete = ...   # unit_weight=25.0e-6
    judge_params: JudgeParams = ...               # alpha_bend=0.6, alpha_shear=0.6, deflection_ratio=600
```

### JudgeParams（デフォルト値）

| パラメータ | デフォルト | 説明 |
|------------|------------|------|
| `alpha_bend` | 0.6 | 曲げ許容応力度係数。σ_allow = α × fy |
| `alpha_shear` | 0.6 | せん断許容応力度係数。τ_allow = α × (fy/√3) |
| `deflection_ratio` | 600.0 | たわみ制限比。δ_allow = L / ratio |

### 材料特性（デフォルト値）

| 材料 | E [N/mm²] | fy [N/mm²] | unit_weight [N/mm³] |
|------|-----------|------------|---------------------|
| 鋼 | 2.0×10⁵ | 235 | 78.5×10⁻⁶ |
| コンクリート | - | - | 25.0×10⁻⁶ |

## 出力（JudgeReport）

```python
class JudgeReport(BaseModel):
    pass_fail: bool           # 合否
    utilization: Utilization  # 各項目の util
    diagnostics: Diagnostics  # 中間計算値
    patch_plan: PatchPlan     # 修正提案（不合格時のみ）
```

### Utilization

| 項目 | 計算式 | 説明 |
|------|--------|------|
| `deck` | required / provided | 床版厚 util |
| `bend` | max(\|σ_top\|, \|σ_bottom\|) / σ_allow | 曲げ応力度 util |
| `shear` | \|τ_avg\| / τ_allow | せん断応力度 util |
| `deflection` | δ / δ_allow | たわみ util |
| `web_slenderness` | t_min_required / web_thickness | 腹板幅厚比 util |
| `max_util` | max(deck, bend, shear, deflection, web_slenderness) | 最大 util |
| `governing_check` | max_util の支配項目 | deck/bend/shear/deflection/web_slenderness/crossbeam_layout |

### Diagnostics（中間計算値）

| フィールド | 単位 | 説明 |
|------------|------|------|
| `b_tr` | mm | 受け持ち幅（= girder_spacing） |
| `w_dead` | N/mm | 死荷重線荷重 |
| `M_dead`, `V_dead` | N·mm, N | 死荷重断面力 |
| `M_live_max`, `V_live_max` | N·mm, N | 活荷重断面力 |
| `M_total`, `V_total` | N·mm, N | 合計断面力 |
| `ybar` | mm | 中立軸位置（下端基準） |
| `moment_of_inertia` | mm⁴ | 断面二次モーメント |
| `sigma_top`, `sigma_bottom` | N/mm² | 上下縁応力度 |
| `tau_avg` | N/mm² | 平均せん断応力度 |
| `delta`, `delta_allow` | mm | たわみ / 許容たわみ |
| `deck_thickness_required` | mm | 必要床版厚 |
| `web_thickness_min_required` | mm | 必要最小腹板厚 |
| `crossbeam_layout_ok` | bool | 横桁配置の整合性 |

## 照査計算の詳細

### 1. 活荷重断面力（内部計算）

```
受け持ち幅: b_tr_m = (total_width / 1000) / num_girders [m]
等価線荷重: w_live = p_live_equiv × b_tr_m [kN/m]
M_live_max = w_live × L² / 8 [kN·m] → [N·mm]
V_live_max = w_live × L / 2 [kN] → [N]
```

### 2. 死荷重断面力

```
w_deck = γ_c × deck_thickness × girder_spacing [N/mm]
w_steel = γ_s × A_girder [N/mm]
w_dead = w_deck + w_steel [N/mm]

M_dead = w_dead × L² / 8 [N·mm]
V_dead = w_dead × L / 2 [N]
```

### 3. 断面諸量（非対称 I 断面）

```
全高: H = top_flange_thickness + web_height + bottom_flange_thickness
中立軸: ybar = Σ(A_i × y_i) / Σ(A_i)
断面二次モーメント: I = Σ(I_i + A_i × (ybar - y_i)²)
```

### 4. 応力度

```
σ_top = M_total × y_top / I
σ_bottom = M_total × y_bottom / I
σ_allow = α_bend × fy
util_bend = max(|σ_top|, |σ_bottom|) / σ_allow
```

### 5. せん断（平均せん断応力度）

```
τ_avg = V_total / (web_thickness × web_height)
τ_allow = α_shear × (fy / √3)
util_shear = |τ_avg| / τ_allow
```

### 6. たわみ（等価等分布換算）

```
w_eq = 8 × M_total / L²
δ = 5 × w_eq × L⁴ / (384 × E × I)
δ_allow = L / deflection_ratio
util_deflection = δ / δ_allow
```

### 7. 床版厚

```
L_support_m = girder_spacing / 1000 [m]
required = max(30 × L_support_m + 110, 160) [mm]
util_deck = required / provided
```

### 8. 横桁配置チェック

```
layout_ok = |panel_length × num_panels - bridge_length| ≤ 1.0mm
          AND panel_length ≤ 20000mm
```

### 9. 腹板幅厚比

鋼種に応じた幅厚比制限から必要最小腹板厚を計算し、現在の腹板厚と比較する。

```
# 必要最小腹板厚
SM490: t_min = web_height / 130
SM400: t_min = web_height / 152

# util
util_web_slenderness = t_min / web_thickness
```

## 修正提案（PatchPlan）

不合格時、LLM が `RepairContext` を基に修正操作を提案する。

### 許可される操作（AllowedActions）

| 操作 | 対象 | 許容値 |
|------|------|--------|
| `increase_web_height` | girder.web_height | +100, +200, +300 mm |
| `increase_web_thickness` | girder.web_thickness | +2, +4 mm |
| `increase_top_flange_thickness` | girder.top_flange_thickness | +2, +4, +6 mm |
| `increase_bottom_flange_thickness` | girder.bottom_flange_thickness | +2, +4, +6 mm |
| `increase_top_flange_width` | girder.top_flange_width | +50, +100 mm |
| `increase_bottom_flange_width` | girder.bottom_flange_width | +50, +100 mm |
| `set_deck_thickness_to_required` | deck.thickness | = required |
| `fix_crossbeam_layout` | dims.num_panels | = round(L / panel_length) |

### PatchPlan の制約

- actions は最大 3 手まで
- 急激な変更を避ける（最初は小さい変更から）
- 許可された操作以外は禁止

### PatchAction の例

```json
{
  "op": "increase_web_height",
  "path": "sections.girder_standard.web_height",
  "delta_mm": 100,
  "reason": "util_deflection が支配的。桁高増でたわみと曲げを改善。"
}
```

## 修正ループ

不合格時に PatchPlan を適用し、合格するまで繰り返す。

```
BridgeDesign
    ↓
Judge（照査）
    ↓
合格？ → Yes → 終了
    ↓ No
LLM（PatchPlan 生成）
    ↓
apply_patch_plan（適用）
    ↓
（最大イテレーションまで繰り返し）
```

### RepairLoopResult

```python
class RepairLoopResult(BaseModel):
    converged: bool                     # 収束したか
    iterations: list[RepairIteration]   # 各イテレーションの結果
    final_design: BridgeDesign          # 最終設計
    final_report: JudgeReport           # 最終照査結果
    rag_log: DesignerRagLog             # 初期設計の RAG ログ
```

## 関連ファイル

- `src/bridge_agentic_generate/judge/models.py`: Pydantic モデル定義
- `src/bridge_agentic_generate/judge/services.py`: 照査計算・PatchPlan 適用
- `src/bridge_agentic_generate/judge/prompts.py`: PatchPlan 生成プロンプト
- `src/bridge_agentic_generate/judge/report.py`: 修正ループレポート生成（Markdown）
- `src/bridge_agentic_generate/judge/CLAUDE.md`: 詳細仕様書

## 注意事項

- **単位系**: すべて mm, N, N/mm², N·mm で統一
- **活荷重モデル**: v1 は等価面圧で簡略化（道示の厳密な載荷条件ではない）
- **たわみ util**: 概略設計のスクリーニング指標（厳密なたわみ照査ではない）
- **決定論的照査**: 同じ入力なら常に同じ結果（テスト容易）
