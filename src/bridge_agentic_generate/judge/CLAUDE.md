# judge/ - CLAUDE.md

## ゴール

BridgeDesign（床版・主桁・横桁）を入力として、
**活荷重（L荷重・p1/p2ルール）と死荷重を内部計算** し、主桁の

- 曲げ応力度 util
- せん断応力度 util（平均せん断）
- たわみ util（等価等分布換算）
- 床版厚 util（required/provided）
- 腹板幅厚比 util（web_thickness_min_required / web_thickness）
- 横桁配置チェック（panel_length × num_panels == L など）

を返す `JudgeReport` を実装する。
さらに `max_util` と `governing_check` を出し、`PatchPlan`（次に何を増やすか）まで返す。

---

## 1. 実装するインターフェース（Pydantic モデル）

### 1.1 入力：JudgeInput

```python
class SteelGrade(StrEnum):
    SM400 = "SM400"
    SM490 = "SM490"

def get_fy(grade: SteelGrade, thickness_mm: float) -> float:
    """鋼種と板厚から降伏点を返す。

    SM400:
        ≤16mm: 245 N/mm²
        16-40mm: 235 N/mm²
        >40mm: 215 N/mm²

    SM490:
        ≤16mm: 325 N/mm²
        16-40mm: 315 N/mm²
        >40mm: 295 N/mm²
    """

class JudgeParams(BaseModel):
    alpha_bend: float = 0.6
    alpha_shear: float = 0.6

class MaterialsSteel(BaseModel):
    E: float = 2.0e5       # N/mm²
    grade: SteelGrade = SteelGrade.SM490  # 鋼種（デフォルト: SM490）
    unit_weight: float = 78.5e-6  # N/mm³（78.5 kN/m³ = 78.5e-6 N/mm³）

class MaterialsConcrete(BaseModel):
    unit_weight: float = 25.0e-6  # N/mm³（25 kN/m³ = 25e-6 N/mm³）

class JudgeInput(BaseModel):
    bridge_design: BridgeDesign  # 既存スキーマを参照
    materials_steel: MaterialsSteel = Field(default_factory=MaterialsSteel)
    materials_concrete: MaterialsConcrete = Field(default_factory=MaterialsConcrete)
    judge_params: JudgeParams = Field(default_factory=JudgeParams)
```

> **注:** BridgeDesign は既存の構造化スキーマを使う（dimensions/sections/components が入ってるやつ）。
>
> **鋼種と降伏点:** 部材ごとの板厚に応じて降伏点(fy)を動的に決定する。SM490をデフォルトとし、板厚別の降伏点テーブルに基づいて計算する。
>
> **活荷重:** 外部入力（LoadInput）は廃止され、L荷重（p1/p2ルール）に基づいて内部計算される。

> alpha_bend, alpha_shear は v1の簡略パラメータであり、許容応力度法で用いられる鋼材降伏点に対する安全率（概ね 1.6〜1.7）を、σ_allow = α*fy の形に置き換えたものとする。
v1では安全率 1.7 を想定し、1/1.7 ≈ 0.59 を丸めて α = 0.60 をデフォルトとする。

### 1.2 活荷重の内部計算（L荷重・p1/p2ルール）

道路橋示方書のB活荷重に基づくL荷重計算を内部で自動実行する。

#### L荷重の定数

| 定数 | 値 | 説明 |
|------|-----|------|
| `P1_M_KN_M2` | 10.0 kN/m² | 曲げ照査用 p1 面圧 |
| `P1_V_KN_M2` | 12.0 kN/m² | せん断照査用 p1 面圧 |
| `P2_KN_M2` | 3.5 kN/m² | p2 面圧（支間80m以下） |
| `MAIN_LOADING_WIDTH_M` | 5.5 m | 主載荷幅 |
| `MAX_LOADING_LENGTH_M` | 10.0 m | 載荷長上限 |
| `MAX_APPLICABLE_SPAN_M` | 80.0 m | 適用限界支間長 |

#### 計算フロー

```python
# 1. 載荷長 D
D_m = min(10.0, L_m)

# 2. 等価係数 γ（部分載荷→等価全スパン分布の換算係数）
gamma = D_m * (2 * L_m - D_m) / L_m²

# 3. 等価面圧
p_eq_M = P2 + P1_M * gamma  # 曲げ用
p_eq_V = P2 + P1_V * gamma  # せん断用

# 4. 張り出し幅
overhang = (total_width - (num_girders - 1) * girder_spacing) / 2

# 5. 各主桁の受け持ち幅 b_i
#    端桁: overhang + girder_spacing / 2
#    中間桁: girder_spacing

# 6. 実効幅 b_eff（主載荷5.5mを最不利に配置）
b_eff = 0.5 * b_i + 0.5 * min(b_i, 5.5)

# 7. 等価線荷重
w_M = p_eq_M * b_eff  # [kN/m]
w_V = p_eq_V * b_eff  # [kN/m]

# 8. 断面力（単純桁）
M_live = w_M * L² / 8  # [kN·m] → [N·mm]
V_live = w_V * L / 2   # [kN] → [N]

# 9. 全主桁で最大値を採用（曲げ・せん断で別々に選定）
M_live_max = max(各主桁の M_live)
V_live_max = max(各主桁の V_live)
```

#### L荷重計算結果モデル

```python
class GirderLiveLoadResult(BaseModel):
    """1本の主桁の活荷重計算結果。"""
    girder_index: int    # 主桁インデックス（0始まり）
    b_i_m: float         # 受け持ち幅 [m]
    b_eff_m: float       # 実効幅 [m]
    w_M: float           # 曲げ用等価線荷重 [kN/m]
    w_V: float           # せん断用等価線荷重 [kN/m]
    M_live: float        # 活荷重最大曲げモーメント [N·mm]
    V_live: float        # 活荷重最大せん断力 [N]

class LiveLoadEffectsResult(BaseModel):
    """全主桁の活荷重計算結果。"""
    # 共通パラメータ
    L_m: float           # 支間長 [m]
    D_m: float           # 載荷長 [m]
    p2: float            # p2 面圧 [kN/m²]
    p1_M: float          # 曲げ用 p1 [kN/m²]
    p1_V: float          # せん断用 p1 [kN/m²]
    gamma: float         # 等価係数
    p_eq_M: float        # 曲げ用等価面圧 [kN/m²]
    p_eq_V: float        # せん断用等価面圧 [kN/m²]
    overhang_m: float    # 張り出し幅 [m]
    # 主桁ごとの結果
    girder_results: list[GirderLiveLoadResult]
    # 最厳しい結果（曲げ・せん断別々）
    critical_girder_index_M: int
    critical_girder_index_V: int
    M_live_max: float    # 最大曲げモーメント [N·mm]
    V_live_max: float    # 最大せん断力 [N]
```

### 1.3 出力：JudgeReport + PatchPlan

```python
class GoverningCheck(StrEnum):
    DECK = "deck"
    BEND = "bend"
    SHEAR = "shear"
    DEFLECTION = "deflection"
    WEB_SLENDERNESS = "web_slenderness"
    CROSSBEAM_LAYOUT = "crossbeam_layout"

class Utilization(BaseModel):
    deck: float
    bend: float
    shear: float
    deflection: float
    web_slenderness: float
    max_util: float
    governing_check: GoverningCheck

class Diagnostics(BaseModel):
    b_tr: float                    # 受け持ち幅 [mm]
    w_dead: float                  # 死荷重線荷重 [N/mm]
    M_dead: float                  # 死荷重曲げモーメント [N·mm]
    V_dead: float                  # 死荷重せん断力 [N]
    M_live_max: float              # 活荷重最大曲げモーメント [N·mm]
    V_live_max: float              # 活荷重最大せん断力 [N]
    M_total: float                 # 合計曲げモーメント [N·mm]
    V_total: float                 # 合計せん断力 [N]
    ybar: float                    # 中立軸位置（下端基準）[mm]
    moment_of_inertia: float       # 断面二次モーメント [mm⁴]
    y_top: float                   # 上縁距離 [mm]
    y_bottom: float                # 下縁距離 [mm]
    sigma_top: float               # 上縁応力度 [N/mm²]
    sigma_bottom: float            # 下縁応力度 [N/mm²]
    tau_avg: float                 # 平均せん断応力度 [N/mm²]
    delta: float                   # たわみ [mm]
    delta_allow: float             # 許容たわみ [mm]
    fy_top_flange: float           # 上フランジ降伏点 [N/mm²]
    fy_bottom_flange: float        # 下フランジ降伏点 [N/mm²]
    fy_web: float                  # ウェブ降伏点 [N/mm²]
    sigma_allow_top: float         # 上縁許容曲げ応力度 [N/mm²]
    sigma_allow_bottom: float      # 下縁許容曲げ応力度 [N/mm²]
    tau_allow: float               # 許容せん断応力度 [N/mm²]
    deck_thickness_required: float # 必要床版厚 [mm]
    web_thickness_min_required: float  # 必要最小腹板厚 [mm]
    crossbeam_layout_ok: bool      # 横桁配置の整合性
    live_load_result: LiveLoadEffectsResult  # L荷重計算結果（詳細）

class PatchActionOp(StrEnum):
    INCREASE_WEB_HEIGHT = "increase_web_height"
    INCREASE_WEB_THICKNESS = "increase_web_thickness"
    INCREASE_TOP_FLANGE_THICKNESS = "increase_top_flange_thickness"
    INCREASE_BOTTOM_FLANGE_THICKNESS = "increase_bottom_flange_thickness"
    INCREASE_TOP_FLANGE_WIDTH = "increase_top_flange_width"
    INCREASE_BOTTOM_FLANGE_WIDTH = "increase_bottom_flange_width"
    SET_DECK_THICKNESS_TO_REQUIRED = "set_deck_thickness_to_required"
    FIX_CROSSBEAM_LAYOUT = "fix_crossbeam_layout"

class PatchAction(BaseModel):
    op: PatchActionOp
    path: str          # 例: "sections.girder_standard.web_height"
    delta_mm: float    # 変更量（mm）。set_deck_thickness_to_required等では0でも可
    reason: str        # 変更理由

class PatchPlan(BaseModel):
    actions: list[PatchAction] = Field(default_factory=list)

class JudgeReport(BaseModel):
    pass_fail: bool
    utilization: Utilization
    diagnostics: Diagnostics
    patch_plan: PatchPlan
    evaluated_candidates: list[EvaluatedCandidate] | None  # 評価済み候補リスト（不合格時のみ）
```

### 1.4 複数候補方式モデル

PatchPlan 生成は複数候補方式を採用している。

```python
class PatchPlanCandidate(BaseModel):
    """修正計画の候補1件。"""
    plan: PatchPlan
    approach_summary: str  # 例: "桁高増でたわみ改善狙い"

class PatchPlanCandidates(BaseModel):
    """修正計画の候補リスト（LLMが生成）。"""
    candidates: list[PatchPlanCandidate]  # 1〜5案

class EvaluatedCandidate(BaseModel):
    """評価済み候補。"""
    candidate: PatchPlanCandidate
    simulated_max_util: float      # シミュレーション後の max_util
    simulated_utilization: Utilization
    improvement: float             # 正なら改善
```

### 1.5 修正ループ結果モデル

```python
class RepairIteration(BaseModel):
    """修正ループの1イテレーション結果。"""
    iteration: int       # イテレーション番号（0から開始、0は初期設計）
    design: BridgeDesign # この時点の設計
    report: JudgeReport  # 照査結果

class RepairLoopResult(BaseModel):
    """修正ループの全体結果。"""
    converged: bool                     # 収束したかどうか（pass_fail=True に到達したか）
    iterations: list[RepairIteration]   # 各イテレーションの結果
    final_design: BridgeDesign          # 最終設計
    final_report: JudgeReport           # 最終照査結果
    rag_log: DesignerRagLog             # 初期設計生成時の RAG ログ
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

`unit_weight` は **N/mm³** で統一する。入力側で kN/m³ → N/mm³ に変換済みとする。

**変換式:**

```
1 kN/m³ = 1000 N / (1e9 mm³) = 1e-6 N/mm³
```

> **例:** 鋼 78.5 kN/m³ → 78.5e-6 N/mm³、コンクリート 25 kN/m³ → 25e-6 N/mm³

### 2.2 受け持ち幅（v1 固定）

```
girder_spacing = BridgeDesign.dimensions.girder_spacing (mm)
b_tr = girder_spacing（mm）

deck_thickness = BridgeDesign.components.deck.thickness（mm）

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
bridge_length = BridgeDesign.dimensions.bridge_length (mm)

w_dead = w_deck + w_steel（N/mm）
L = bridge_length（mm）

M_dead = w_dead × L² / 8（N·mm）
V_dead = w_dead × L / 2（N）
```

### 2.5 主桁断面諸量（鋼 I 断面：非対称 OK）

トップ・ウェブ・ボトムを矩形 3 つで合成して

- 中立軸 `ybar`
- `moment_of_inertia`（平行軸の定理）
- `y_top = (全高 - ybar)`
- `y_bottom = ybar`

```
全高：H = top_flange_thickness + web_height + bottom_flange_thickness
```
`web_height` は腹板高さ（フランジ間距離）。フランジ板厚を含まない。
簡略的に、合成桁としての床版の剛性寄与を無視する。

### 2.6 合計断面力

```
M_total = M_dead + M_live_max
V_total = V_dead + V_live_max
```
M_live_max, V_live_max は L荷重計算で自動的に算出される「最厳しい主桁の断面力」。

### 2.7 応力度

部材ごとの降伏点を計算：

```
fy_top = get_fy(steel.grade, girder.top_flange_thickness)
fy_bottom = get_fy(steel.grade, girder.bottom_flange_thickness)
fy_web = get_fy(steel.grade, girder.web_thickness)
```

曲げ応力度（上下フランジ別）：

```
sigma_top    = M_total × y_top / moment_of_inertia
sigma_bottom = M_total × y_bottom / moment_of_inertia

sigma_allow_top = alpha_bend × fy_top
sigma_allow_bottom = alpha_bend × fy_bottom

util_bend_top = |sigma_top| / sigma_allow_top
util_bend_bottom = |sigma_bottom| / sigma_allow_bottom
util_bend = max(util_bend_top, util_bend_bottom)
```

### 2.8 せん断（平均、ウェブの降伏点を使用）

```
tau_avg = V_total / (web_thickness × web_height)
```

せん断制限：

```
tau_allow  = alpha_shear × (fy_web / √3)
util_shear = |tau_avg| / tau_allow
```

### 2.9 たわみ（活荷重のみ・道路橋示方書準拠）

> **v1.1 変更:** 使用限界状態のたわみ照査は活荷重のみで評価する。
> 許容たわみは支間長に応じて 3 区分で計算する。

#### 計算式

```
# 活荷重による等価等分布荷重
w_eq_live = 8 × M_live_max / L²（N/mm）

# たわみ
delta = 5 × w_eq_live × L⁴ / (384 × E × I)（mm）

# 許容たわみ（L は m 単位で計算）
L_m = L / 1000

if L_m ≤ 10:
    delta_allow = L_m / 2000 × 1000（mm）
elif L_m ≤ 40:
    delta_allow = L_m² / 20000 × 1000（mm）
else:
    delta_allow = L_m / 500 × 1000（mm）

util_deflection = delta / delta_allow
```

### 2.10 床版厚 util
`BridgeDesign.components.deck.thickness` から床版厚を取得する。
道路橋示方書の式は `L_support` が **m単位** で入力される前提。内部の `girder_spacing` は **mm** なので変換が必要。

```
provided_mm = BridgeDesign.components.deck.thickness
L_support_m = girder_spacing_mm / 1000
required_mm = max(30 * L_support_m + 110, 160)
util_deck   = required_mm / provided_mm
```

### 2.11 腹板幅厚比照査

鋼種に応じた幅厚比制限から必要最小腹板厚を計算する。

```
# 必要最小腹板厚
SM490: t_min = web_height / 130
SM400: t_min = web_height / 152

# util
util_web_slenderness = t_min / web_thickness
```

### 2.12 横桁配置チェック（v1）

`panel_length` と `num_panels` は `BridgeDesign.dimensions` から取得する：
- `panel_length = dimensions.panel_length`（mm）
- `num_panels = dimensions.num_panels`

```
crossbeam_layout_ok = (abs(panel_length × num_panels - bridge_length) <= tol)
```

- `tol = 1.0` (mm)
- 追加で `panel_length <= 20000` もチェック
- NG なら `governing_check = "crossbeam_layout"` として `pass_fail = False`

---

## 3. PatchPlan（修正提案ロジック）

### 3.1 方針（v1の重要設計）

- 照査（util計算・合否判定）は**決定論的**に行う（同じ入力なら同じ結果）
- 修正案（どのパラメータをどれだけ動かすか）の選択は **LLM** に行わせる
- ただし LLM の自由度を暴れさせないため、許される修正操作を限定し、操作の範囲（刻み）も固定する

**優先順位**（固定）：

1. **安全**: すべての util ≤ 1.0
2. **施工性**: 急激な変更を避ける（変更量と変更箇所を最小化）
3. **鋼重最小**: 同等なら軽い案

### 3.2 AllowedActions（v1で許可する修正操作）

LLMが提案できる操作は以下のみ。

#### 主桁（girder_standard）

| 操作名 | 許容値 |
|--------|--------|
| `increase_web_height` | Δh ∈ {+100, +200, +300, +500} mm |
| `increase_web_thickness` | Δtw ∈ {+2, +4, +6} mm |
| `increase_top_flange_thickness` | Δtt ∈ {+2, +4, +6} mm |
| `increase_bottom_flange_thickness` | Δtb ∈ {+2, +4, +6} mm |
| `increase_top_flange_width` | Δbt ∈ {+50, +100} mm |
| `increase_bottom_flange_width` | Δbb ∈ {+50, +100} mm |

#### 床版（deck）

| 操作名 | 説明 |
|--------|------|
| `set_deck_thickness_to_required` | thickness := required_thickness（Judgeが計算した値） |

#### 横桁配置（dimensions）

| 操作名 | 説明 |
|--------|------|
| `fix_crossbeam_layout` | num_panels := round(L / panel_length) または panel_length := L / num_panels |

- v1では どちらか一方に固定する（推奨：num_panels を変更して整合させる）
- `panel_length <= 20000 mm` を満たす方向のみ許可

### 3.3 RepairContext（LLMへ渡す入力）

Judgeは util 計算後、LLMに渡すための RepairContext を組み立てる。

**含める情報**：

| フィールド | 内容 |
|------------|------|
| `utilization` | deck/bend/shear/deflection/web_slenderness の util |
| `crossbeam_layout_ok` | 横桁配置の整合性（bool） |
| `governing_check` | max_util の支配項目 |
| `diagnostics` | 主要中間量（M_total, V_total, moment_of_inertia, y_top/y_bottom, sigma_top/bottom, tau_avg, delta, web_thickness_min_required 等） |
| `current_design` | 対象パラメータ（web_height, web_thickness, flange_width/thickness, deck_thickness, panel_length, num_panels） |
| `allowed_actions` | 3.2の操作一式（操作名＋可能なΔ） |
| `deck_thickness_required` | 必要床版厚 [mm] |
| `priorities` | 安全>施工性>鋼重（固定文言） |

### 3.4 複数候補方式（v1.1）

PatchPlan 生成は複数候補方式を採用：

1. **LLM が3案を生成**: 異なるアプローチ（桁高重視、フランジ厚重視など）
2. **各案を仮適用・評価**: `apply_patch_plan` → `judge_v1_lightweight` で max_util をシミュレーション
3. **最良案を選択**: improvement（= 現在の max_util - シミュレーション後の max_util）が最大の案を採用

#### LLMへのシステムプロンプト（抜粋）

```
あなたは鋼プレートガーダー橋の設計を、照査結果に基づいて修正する担当です。
目的は「全util ≤ 1.0（できれば0.98以下）に最短で入れる」ことです。

3案を提示し、それぞれ異なるアプローチを取ってください。

## 判断の方針
- 診断値（sigma_top, sigma_bottom, tau_avg, delta, I 等）に基づいて判断する
- 曲げが支配なら、sigma_top と sigma_bottom の大きい側を見て、効く変更を選ぶ
- たわみが支配なら、I（断面二次モーメント）を増やす方向を優先する
- せん断が支配なら、web_thickness を優先する
- 腹板幅厚比（web_slenderness）が支配なら、web_thickness を ceil(web_thickness_min_required) 以上に増やす

## 変更量の目安
- util が大きく超えているとき（> 1.50）: 大きめの刻み
- util が少し超えているとき（1.10 < util ≤ 1.50）: 中程度の刻み
- util がギリギリのとき（util ≤ 1.10）: 最小刻み
```

**PatchPlanCandidates のフォーマット**：

```json
{
  "candidates": [
    {
      "plan": {
        "actions": [
          {
            "op": "increase_web_height",
            "path": "sections.girder_standard.web_height",
            "delta_mm": 200,
            "reason": "たわみが支配的。桁高増でI増加を狙う。"
          }
        ]
      },
      "approach_summary": "桁高重視でたわみ改善"
    },
    {
      "plan": {
        "actions": [
          {
            "op": "increase_bottom_flange_thickness",
            "path": "sections.girder_standard.bottom_flange_thickness",
            "delta_mm": 4,
            "reason": "下縁応力が大きい。フランジ厚増で改善。"
          }
        ]
      },
      "approach_summary": "フランジ厚重視で曲げ改善"
    },
    ...
  ]
}
```

### 3.5 ループ内の責務分担（重要）

| 担当 | ステップ | 内容 |
|------|----------|------|
| **Judge**（決定論） | 1 | util計算・合否判定・governing_check決定 |
| | 2 | RepairContext作成 |
| **LLM**（判断） | 3 | RepairContextを見て PatchPlanCandidates（3案）を生成 |
| **Judge**（評価） | 4 | 各案を仮適用・評価し、最良案を選択 |
| **Designer**（適用） | 5 | 選択された PatchPlan を BridgeDesign に反映 |
| **Judge**（再照査） | 6 | 更新案を再度評価し、収束 or 次のPatchPlan生成 |

> **注:** JudgeがBridgeDesignを直接書き換えない。修正の適用はDesigner側の責務とする（ログと責務が明確になるため）。

### 3.6 フォールバック（LLMが変な提案をした場合）

| ケース | 対処 |
|--------|------|
| LLMが許可されていない操作を出した場合 | Judgeは無効として差し戻し（allowed_actionsの範囲内に再提案を要求） |
| `pass_fail = False` かつ actions が空の場合 | **エラーとして処理を中断**（`ValueError` を送出し、呼び出し元で対処させる） |
| `pass_fail = True` かつ actions が空の場合 | **正常終了**（修正不要のため空で問題なし） |

---

## 4. 主要関数

### 4.1 judge_v1

```python
def judge_v1(judge_input: JudgeInput, model: LlmModel) -> JudgeReport:
    """Judge v1 メイン関数。

    決定論的に util を計算し、合否判定・PatchPlan 生成を行う。

    Args:
        judge_input: Judge 入力
        model: PatchPlan 生成に使用する LLM モデル

    Returns:
        JudgeReport
    """
```

### 4.2 judge_v1_lightweight

```python
def judge_v1_lightweight(judge_input: JudgeInput) -> tuple[Utilization, Diagnostics]:
    """軽量版Judge（LLM呼び出しなし）。PatchPlanの仮適用評価用。

    Args:
        judge_input: Judge 入力

    Returns:
        (Utilization, Diagnostics) のタプル
    """
```

### 4.3 apply_patch_plan

```python
def apply_patch_plan(
    design: BridgeDesign,
    patch_plan: PatchPlan,
    deck_thickness_required: float | None = None,
) -> BridgeDesign:
    """PatchPlan を BridgeDesign に適用する。

    Args:
        design: 元の BridgeDesign
        patch_plan: 適用する PatchPlan
        deck_thickness_required: 必要床版厚 [mm]（SET_DECK_THICKNESS_TO_REQUIRED 用）

    Returns:
        修正後の新しい BridgeDesign
    """
```

### 4.4 calc_l_live_load_effects

```python
def calc_l_live_load_effects(
    bridge_length_mm: float,
    total_width_mm: float,
    num_girders: int,
    girder_spacing_mm: float,
) -> LiveLoadEffectsResult:
    """L荷重（p1/p2ルール）に基づく活荷重を計算し、最も厳しい結果を返す。

    全主桁をループして各桁の M_live, V_live を計算し、
    最大の断面力を持つ主桁を critical として選定する。

    Args:
        bridge_length_mm: 橋長 [mm]
        total_width_mm: 橋全幅 [mm]
        num_girders: 主桁本数
        girder_spacing_mm: 主桁間隔 [mm]

    Returns:
        LiveLoadEffectsResult: 全主桁の結果と最厳しい結果

    Raises:
        NotApplicableError: L > 80m の場合
    """
```

---

## 5. テスト（必須）

### 5.1 単体テスト：断面計算

- 非対称 I 断面で `ybar`, `moment_of_inertia` が妥当か（手計算値と比較）

### 5.2 単体テスト：死荷重

- 既知の寸法で `w_dead`, `M_dead`, `V_dead` が式通りか

### 5.3 単体テスト：L荷重計算

- 既知の寸法で `gamma`, `p_eq_M`, `p_eq_V`, `M_live_max`, `V_live_max` が式通りか
- 支間80m超で `NotApplicableError` が発生するか

### 5.4 統合テスト：既存設計値で 1 回回す

既存設計値を fixture として流し、以下を確認する：

- `report` が出る
- `util` が数値で埋まる
- `governing_check` が決まる
- `live_load_result` が `diagnostics` に含まれる

---

## 6. 完了条件（Definition of Done）

- [x] `judge_v1(input: JudgeInput, model: LlmModel) -> JudgeReport` が実装されている
- [x] L荷重計算（p1/p2ルール）が実装されている
- [x] 複数候補方式の PatchPlan 生成が実装されている
- [x] 単体テストが通る
- [x] fixture（既存設計値）で report が生成できる
- [x] 主要中間量（`w_dead`, `M_dead`, `moment_of_inertia`, `sigma`, `delta`, `live_load_result`）が `diagnostics` に出て説明可能

---

## 7. 注意点（落とし穴）

- 単位の統一（kN/m³ → N/mm³ 変換）でバグりやすい
- L荷重計算は支間80m以下が適用範囲。超えると `NotApplicableError` が発生する
- 曲げとせん断で異なる p1 を使用するため、最厳しい主桁が曲げとせん断で異なる場合がある
- `M_live_max`, `V_live_max` は正の最大値（gt=0）を入力する前提（符号は扱わない）
