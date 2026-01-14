# judge/ - CLAUDE.md

## ゴール

BridgeDesign（床版・主桁・横桁）と活荷重断面力（M_live_max, V_live_max）を入力として、
**死荷重を内部推定（床版＋鋼桁のみ）** し、主桁の

- 曲げ応力度 util
- せん断応力度 util（平均せん断）
- たわみ util（等価等分布換算）
- 床版厚 util（required/provided）
- 横桁配置チェック（panel_length × num_panels == L など）

を返す `JudgeReport` を実装する。
さらに `max_util` と `governing_check` を出し、`PatchPlan`（次に何を増やすか）まで返す。

---

## 1. 実装するインターフェース（Pydantic モデル）

### 1.1 入力：JudgeInput

```python
class JudgeParams(BaseModel):
    alpha_bend: float = 0.6
    alpha_shear: float = 0.6
    deflection_ratio: float = 600.0

class MaterialsSteel(BaseModel):
    E: float           # N/mm²
    fy: float          # N/mm²
    unit_weight: float # kN/m³ (or N/mm³ どちらでも可。統一する)

class MaterialsConcrete(BaseModel):
    unit_weight: float # kN/m³

class LoadEffects(BaseModel):
    M_live_max: float  # N·mm
    V_live_max: float  # N

class DeckInfo(BaseModel):
    thickness: float                       # mm
    required_thickness: float | None = None # mm (Designer が計算済みなら入る)

class JudgeInput(BaseModel):
    bridge_design: BridgeDesign  # 既存スキーマを参照
    load_effects: LoadEffects
    materials_steel: MaterialsSteel
    materials_concrete: MaterialsConcrete
    judge_params: JudgeParams
    deck: DeckInfo
```

> **注:** BridgeDesign は既存の構造化スキーマを使う（dimensions/sections/components が入ってるやつ）。

### 1.2 出力：JudgeReport + PatchPlan

```python
class GoverningCheck(StrEnum):
    DECK = "deck"
    BEND = "bend"
    SHEAR = "shear"
    DEFLECTION = "deflection"
    CROSSBEAM_LAYOUT = "crossbeam_layout"

class Utilization(BaseModel):
    deck: float
    bend: float
    shear: float
    deflection: float
    max_util: float
    governing_check: GoverningCheck

class Diagnostics(BaseModel):
    b_tr: float
    w_dead: float
    M_dead: float
    V_dead: float
    M_total: float
    V_total: float
    I_steel: float
    y_top: float
    y_bottom: float
    sigma_top: float
    sigma_bottom: float
    tau_avg: float
    delta: float
    delta_allow: float
    sigma_allow: float
    tau_allow: float
    crossbeam_layout_ok: bool
    layout_violations: list[str] = []

class PatchPlan(BaseModel):
    actions: list[dict]  # path + op + delta で OK（後で厳密化）

class JudgeReport(BaseModel):
    pass_fail: bool
    utilization: Utilization
    diagnostics: Diagnostics
    patch_plan: PatchPlan
```

---

## 2. 計算仕様（必ずこの通りに）

### 2.1 単位系（最重要）

| 項目 | 単位 |
|------|------|
| E（ヤング率） | N/mm² |
| 断面寸法 | mm |
| 断面二次モーメント | mm⁴ |
| 応力度 | N/mm² |
| 長さ L | mm |
| M_* | N·mm |
| V_* | N |

`unit_weight`（kN/m³）は N/mm³ へ変換して使うか、全体を m 系にして最後に N·mm へ戻す。
→ 実装でバグりやすいので、どちらかに固定してドキュメント化すること。

**おすすめ:** `unit_weight_kN_m3` → `N/mm³` に変換

```
1 kN/m³ = 1000 N / (1e9 mm³) = 1e-6 N/mm³
```

### 2.2 受け持ち幅（v1 固定）

```
b_tr = total_width / num_girders（mm）

床版体積/長さ（1mm 長） = deck_thickness × b_tr（mm²）

w_deck (N/mm) = gamma_c (N/mm³) × deck_thickness (mm) × b_tr (mm)
```

### 2.3 鋼桁自重（断面積）

I 桁断面積（鋼のみ）：

```
A = A_web + A_tf + A_bf

A_web = web_height × web_thickness
A_tf  = top_flange_width × top_flange_thickness
A_bf  = bottom_flange_width × bottom_flange_thickness

w_steel (N/mm) = gamma_s (N/mm³) × A (mm²)
```

※溶接・リブ等は無視（v1）

### 2.4 死荷重断面力（単純桁・等分布）

```
w_dead = w_deck + w_steel（N/mm）
L = bridge_length（mm）

M_dead = w_dead × L² / 8（N·mm）
V_dead = w_dead × L / 2（N）
```

### 2.5 主桁断面諸量（鋼 I 断面：非対称 OK）

トップ・ウェブ・ボトムを矩形 3 つで合成して

- 中立軸 `ybar`
- `I`（平行軸の定理）
- `y_top = (全高 - ybar)`
- `y_bottom = ybar`

```
全高：H = top_flange_thickness + web_height + bottom_flange_thickness
```

### 2.6 合計断面力

```
M_total = M_dead + M_live_max
V_total = V_dead + V_live_max
```

### 2.7 応力度

```
sigma_top    = M_total × y_top / I
sigma_bottom = M_total × y_bottom / I
```

応力度制限（B 案）：

```
sigma_allow = alpha_bend × fy
util_bend   = max(|sigma_top|, |sigma_bottom|) / sigma_allow
```

### 2.8 せん断（平均）

```
tau_avg = V_total / (web_thickness × web_height)
```

せん断制限：

```
tau_allow  = alpha_shear × (fy / √3)
util_shear = |tau_avg| / tau_allow
```

### 2.9 たわみ（M から等価等分布に換算）

```
w_eq        = 8 × M_total / L²（N/mm）
delta       = 5 × w_eq × L⁴ / (384 × E × I)（mm）
delta_allow = L / deflection_ratio（mm）
util_defl   = delta / delta_allow
```

### 2.10 床版厚 util

- `required_thickness` が入力にあるならそれを使う
- ない場合は v1 では `util_deck = 0` とせず、**1.0 扱い（=未評価）** にするか、例外にする

> **おすすめ:** `required_thickness is None` なら `util_deck = 1.0` で `layout_violations` に「required_thickness missing」を入れる（ループが止まらない）

```
util_deck = required / provided
```

### 2.11 横桁配置チェック（v1）

```
crossbeam_layout_ok = (abs(panel_length × num_panels - bridge_length) <= tol)
```

- `tol` は 1mm 程度
- 追加で `panel_length <= 20000` もチェック
- NG なら `governing_check = "crossbeam_layout"` として `pass_fail = False`

---

## 3. PatchPlan（修正提案ロジック）

`governing_check` に応じた修正：

| governing_check | 修正内容 |
|-----------------|----------|
| `deflection` | `sections.girder_standard.web_height += 100` |
| `bend` | `top_flange_thickness += 2`（or bottom 優先でも良いが固定化） |
| `shear` | `web_thickness += 2` |
| `deck` | `deck.thickness += 10` |
| `crossbeam_layout` | `dimensions.num_panels` を `round(L/panel_length)` に合わせる or `panel_length = L/num_panels` に修正（どちらか固定） |

Patch は「path」「delta」「reason」を dict で入れる：

```json
{
  "path": "sections.girder_standard.web_height",
  "delta_mm": 100,
  "reason": "util_deflection governs"
}
```

---

## 4. テスト（必須）

### 4.1 単体テスト：断面計算

- 非対称 I 断面で `ybar`, `I` が妥当か（手計算値と比較）

### 4.2 単体テスト：死荷重

- 既知の寸法で `w_dead`, `M_dead`, `V_dead` が式通りか

### 4.3 統合テスト：既存設計値で 1 回回す

この JSON（既にこのチャットで出たやつ）を fixture として流し、以下を確認する：

- `report` が出る
- `util` が数値で埋まる
- `governing_check` が決まる

---

## 5. 完了条件（Definition of Done）

- [ ] `judge_v1(input: JudgeInput) -> JudgeReport` が実装されている
- [ ] 単体テストが通る
- [ ] fixture（既存設計値）で report が生成できる
- [ ] 主要中間量（`w_dead`, `M_dead`, `I`, `sigma`, `delta`）が `diagnostics` に出て説明可能

---

## 6. 注意点（落とし穴）

- 単位の統一（kN/m³ → N/mm³ 変換）でバグりやすい
- `M_live_max` の符号（正負）は一旦 `abs()` で util を計算してよい（v1 は最大値入力前提）
- `deck required_thickness` が未入力の時の扱いは固定する（止めない）
