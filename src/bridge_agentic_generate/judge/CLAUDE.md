# judge/ - CLAUDE.md

## ゴール

BridgeDesign（床版・主桁・横桁）と活荷重断面力（M_live_max, V_live_max）を入力として、
**死荷重を内部推定（床版＋鋼桁のみ）** し、主桁の

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

class LoadInput(BaseModel):
    p_live_equiv: float = 12.0  # kN/m² 等価活荷重（デフォルト12、感度解析で6〜12を振る）

class JudgeInput(BaseModel):
    bridge_design: BridgeDesign  # 既存スキーマを参照
    load_input: LoadInput = Field(default_factory=LoadInput)
    materials_steel: MaterialsSteel = Field(default_factory=MaterialsSteel)
    materials_concrete: MaterialsConcrete = Field(default_factory=MaterialsConcrete)
    judge_params: JudgeParams = Field(default_factory=JudgeParams)
```

> **注:** BridgeDesign は既存の構造化スキーマを使う（dimensions/sections/components が入ってるやつ）。
>
> **鋼種と降伏点:** 部材ごとの板厚に応じて降伏点(fy)を動的に決定する。SM490をデフォルトとし、板厚別の降伏点テーブルに基づいて計算する。

### 1.2 活荷重の内部計算

ユーザーは `p_live_equiv`（kN/m²）を入力し、Judge が BridgeDesign の寸法から主桁1本あたりの `M_live_max`, `V_live_max` を内部生成する。

```python
# 受け持ち幅
b_tr_m = (total_width_mm / 1000) / num_girders  # m

# 等価線荷重
w_live_kN_m = p_live_equiv * b_tr_m  # kN/m

# 橋長
L_m = bridge_length_mm / 1000  # m

# 単純桁の最大断面力
M_live_max_kN_m = w_live_kN_m * L_m**2 / 8  # kN·m
V_live_max_kN = w_live_kN_m * L_m / 2       # kN

# 単位変換: kN·m → N·mm, kN → N
M_live_max = M_live_max_kN_m * 1e6  # N·mm
V_live_max = V_live_max_kN * 1e3    # N
```

**p_live_equiv のデフォルト値:**
- デフォルト: 12 kN/m²（せん断側の方が大きいので保守的）
- 感度解析: 6〜12 kN/m² を振る

> **注意: v1 の活荷重モデルは簡略化**
>
> 本来の L荷重は p1・p2（等分布荷重と集中荷重）、載荷幅（主車線 5.5m 等）、載荷長 D、車線配置ルール込みで複雑な載荷条件を持つ。
> v1 ではこれを「等価面圧 1 本（p_live_equiv）」に潰しているため、**「道示どおり厳密」ではなく「道示の代表値に基づく概略指標」** として扱う。
> 詳細設計段階では別途厳密な活荷重計算が必要。

> alpha_bend, alpha_shear は v1の簡略パラメータであり、許容応力度法で用いられる鋼材降伏点に対する安全率（概ね 1.6〜1.7）を、σ_allow = α*fy の形に置き換えたものとする。
v1では安全率 1.7 を想定し、1/1.7 ≈ 0.59 を丸めて α = 0.60 をデフォルトとする。

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
```

### 1.4 修正ループ結果モデル

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
M_live_max, V_live_max は「代表主桁（1本）に生じる最大断面力（活荷重分）」を入力する（橋全体系ではない）。

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

### 2.11 横桁配置チェック（v1）

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

**含める情報**（最低限）：

| フィールド | 内容 |
|------------|------|
| `utilization` | deck/bend/shear/deflection の util|
| `crossbeam_layout_ok` | 横桁配置の整合性（bool） |
| `governing_check` | max_util の支配項目 |
| `diagnostics` | 主要中間量（M_total, V_total, moment_of_inertia, y_top/y_bottom, sigma_top/bottom, tau_avg, delta 等） |
| `current_design` | 対象パラメータ（web_height, web_thickness, flange_width/thickness, deck_thickness, panel_length, num_panels） |
| `allowed_actions` | 3.2の操作一式（操作名＋可能なΔ） |
| `deck_thickness_required` | 必要床版厚 [mm] |
| `priorities` | 安全>施工性>鋼重（固定文言で良い） |

### 3.4 LLMの出力（PatchPlan）

LLMは RepairContext を入力として、以下の制約を満たす PatchPlan を返す：

- actions は**最大3手**まで
- 急激な変更を避ける（例：最初は +100mm を優先し、必要なら次ループで追加）
- 支配 util を確実に下げる意図が説明されている
- 許可された操作以外は禁止

**PatchPlan のフォーマット**（v1）：

```json
{
  "actions": [
    {
      "op": "increase_web_height",
      "path": "sections.girder_standard.web_height",
      "delta_mm": 100,
      "reason": "util_deflection が支配的。桁高増はたわみと曲げの両方を改善しやすい。急激変更回避のため+100mmから開始。"
    }
  ]
}
```

### 3.5 ループ内の責務分担（重要）

| 担当 | ステップ | 内容 |
|------|----------|------|
| **Judge**（決定論） | 1 | util計算・合否判定・governing_check決定 |
| | 2 | RepairContext作成 |
| **LLM**（判断） | 3 | RepairContextを見て PatchPlan（actions）を選ぶ |
| **Designer**（適用） | 4 | PatchPlan を BridgeDesign に反映（スキーマに沿って更新） |
| **Judge**（再照査） | 5 | 更新案を再度評価し、収束 or 次のPatchPlan生成 |

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
def judge_v1(judge_input: JudgeInput, model: LlmModel = LlmModel.GPT_5_MINI) -> JudgeReport:
    """Judge v1 メイン関数。

    決定論的に util を計算し、合否判定・PatchPlan 生成を行う。

    Args:
        judge_input: Judge 入力
        model: PatchPlan 生成に使用する LLM モデル

    Returns:
        JudgeReport
    """
```

### 4.2 apply_patch_plan

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

---

## 5. テスト（必須）

### 5.1 単体テスト：断面計算

- 非対称 I 断面で `ybar`, `moment_of_inertia` が妥当か（手計算値と比較）

### 5.2 単体テスト：死荷重

- 既知の寸法で `w_dead`, `M_dead`, `V_dead` が式通りか

### 5.3 統合テスト：既存設計値で 1 回回す

この JSON（既にこのチャットで出たやつ）を fixture として流し、以下を確認する：

- `report` が出る
- `util` が数値で埋まる
- `governing_check` が決まる

---

## 6. 完了条件（Definition of Done）

- [x] `judge_v1(input: JudgeInput, model: LlmModel) -> JudgeReport` が実装されている
- [x] 単体テストが通る
- [x] fixture（既存設計値）で report が生成できる
- [x] 主要中間量（`w_dead`, `M_dead`, `moment_of_inertia`, `sigma`, `delta`）が `diagnostics` に出て説明可能

---

## 7. 注意点（落とし穴）

- 単位の統一（kN/m³ → N/mm³ 変換）でバグりやすい
- `M_live_max`, `V_live_max` は正の最大値（gt=0）を入力する前提（符号は扱わない）
