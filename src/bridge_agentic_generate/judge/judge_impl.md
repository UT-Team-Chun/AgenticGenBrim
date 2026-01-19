# Judge v1 実装計画

## 概要

BridgeDesign と活荷重条件（p_live_equiv）を入力として、道路橋示方書に基づく照査（util 計算）を行い、不合格の場合は LLM による修正提案（PatchPlan）を生成する Judge v1 を実装する。

---

## Phase 構成

| Phase | 内容 | 依存関係 |
|-------|------|----------|
| 1 | モデル定義（Pydantic） | なし |
| 2 | util 計算ロジック（決定論的） | Phase 1 |
| 3 | JudgeReport 生成 | Phase 2 |
| 4 | PatchPlan 生成（LLM 連携） | Phase 3 |
| 5 | Designer 連携ループ | Phase 4 |
| 6 | テスト | Phase 1-5 |

---

## Phase 1: モデル定義

### 対象ファイル
- `src/bridge_agentic_generate/judge/models.py`

### Task 1.1: 入力モデル定義

```python
class JudgeParams(BaseModel):
    alpha_bend: float = 0.6      # 曲げ許容応力度係数
    alpha_shear: float = 0.6     # せん断許容応力度係数
    deflection_ratio: float = 600.0  # たわみ制限 L/600

class MaterialsSteel(BaseModel):
    E: float           # N/mm² ヤング率
    fy: float          # N/mm² 降伏点
    unit_weight: float # N/mm³（78.5e-6 = 78.5 kN/m³）

class MaterialsConcrete(BaseModel):
    unit_weight: float # N/mm³（25e-6 = 25 kN/m³）

class LoadInput(BaseModel):
    p_live_equiv: float = 12.0  # kN/m² 等価活荷重（デフォルト12）

# 注意: v1 の活荷重モデルは簡略化
# 本来の L荷重は p1・p2、載荷幅（主車線5.5m等）、載荷長D、車線配置ルール込み。
# v1 ではこれを「等価面圧1本」に潰しているため、
# 「道示どおり厳密」ではなく「道示の代表値に基づく概略指標」として扱う。
```

### Task 1.2: 内部計算用モデル

```python
class LoadEffects(BaseModel):
    """Judge 内部で計算される活荷重断面力"""
    M_live_max: float  # N·mm
    V_live_max: float  # N
```

### Task 1.3: 出力モデル定義

```python
class GoverningCheck(StrEnum):
    DECK = "deck"
    BEND = "bend"
    SHEAR = "shear"
    DEFLECTION = "deflection"

class Utilization(BaseModel):
    deck: float
    bend: float
    shear: float
    deflection: float
    max_util: float
    governing_check: GoverningCheck

class Diagnostics(BaseModel):
    # 受け持ち幅・荷重
    b_tr: float         # mm 受け持ち幅
    w_dead: float       # N/mm 死荷重
    w_live: float       # N/mm 活荷重
    # 断面力
    M_dead: float       # N·mm
    V_dead: float       # N
    M_live_max: float   # N·mm
    V_live_max: float   # N
    M_total: float      # N·mm
    V_total: float      # N
    # 断面諸量
    ybar: float         # mm 中立軸位置
    I: float            # mm⁴ 断面二次モーメント
    y_top: float        # mm
    y_bottom: float     # mm
    # 応力・たわみ
    sigma_top: float    # N/mm²
    sigma_bottom: float # N/mm²
    sigma_allow: float  # N/mm²
    tau_avg: float      # N/mm²
    tau_allow: float    # N/mm²
    delta: float        # mm
    delta_allow: float  # mm
    # 床版
    deck_required: float  # mm 必要床版厚
    # 横桁
    crossbeam_layout_ok: bool

class JudgeReport(BaseModel):
    pass_fail: bool
    utilization: Utilization
    diagnostics: Diagnostics
    patch_plan: PatchPlan | None  # Phase 4 まで None
```

### Task 1.4: PatchPlan モデル

```python
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
    delta_mm: float    # 変更量（mm）
    reason: str        # 変更理由

class PatchPlan(BaseModel):
    actions: list[PatchAction]
```

### Task 1.5: JudgeInput 更新

```python
class JudgeInput(BaseModel):
    bridge_design: BridgeDesign
    load_input: LoadInput  # p_live_equiv を含む
    materials_steel: MaterialsSteel
    materials_concrete: MaterialsConcrete
    judge_params: JudgeParams = Field(default_factory=JudgeParams)
```

### Task 1.6: 旧モデル削除

以下を削除:
- `CheckStatus`, `OverallStatus`, `CheckItem`, `JudgeResult`（旧ダミー用）

---

## Phase 2: util 計算ロジック

### 対象ファイル
- `src/bridge_agentic_generate/judge/services.py`
- `src/bridge_agentic_generate/judge/calculators.py`（新規）

### Task 2.1: 活荷重計算

`p_live_equiv` → `M_live_max`, `V_live_max` を計算。

```python
def calc_load_effects(
    p_live_equiv_kN_m2: float,
    total_width_mm: float,
    num_girders: int,
    bridge_length_mm: float,
) -> LoadEffects:
    """p_live_equiv から主桁1本あたりの活荷重断面力を計算"""
    b_tr_m = (total_width_mm / 1000) / num_girders  # m
    w_live_kN_m = p_live_equiv_kN_m2 * b_tr_m       # kN/m
    L_m = bridge_length_mm / 1000                   # m

    M_live_max_kN_m = w_live_kN_m * L_m**2 / 8      # kN·m
    V_live_max_kN = w_live_kN_m * L_m / 2           # kN

    # 単位変換: kN·m → N·mm, kN → N
    return LoadEffects(
        M_live_max=M_live_max_kN_m * 1e6,  # N·mm
        V_live_max=V_live_max_kN * 1e3,    # N
    )
```

### Task 2.2: 死荷重計算

```python
def calc_dead_load(
    girder: GirderSection,
    deck_thickness_mm: float,
    b_tr_mm: float,
    gamma_steel: float,  # N/mm³
    gamma_concrete: float,  # N/mm³
) -> tuple[float, float]:
    """w_deck, w_steel を計算（N/mm）"""
    # 床版
    w_deck = gamma_concrete * deck_thickness_mm * b_tr_mm

    # 鋼桁断面積
    A_web = girder.web_height * girder.web_thickness
    A_tf = girder.top_flange_width * girder.top_flange_thickness
    A_bf = girder.bottom_flange_width * girder.bottom_flange_thickness
    A = A_web + A_tf + A_bf

    w_steel = gamma_steel * A

    return w_deck, w_steel
```

### Task 2.3: 断面諸量計算

```python
def calc_section_properties(girder: GirderSection) -> SectionProperties:
    """非対称I断面の中立軸・断面二次モーメントを計算"""
    # 全高
    H = girder.top_flange_thickness + girder.web_height + girder.bottom_flange_thickness

    # 各部の面積と図心位置（ボトムフランジ下端を原点）
    # ... 平行軸の定理で I を計算

    return SectionProperties(ybar=..., I=..., y_top=..., y_bottom=...)
```

### Task 2.4: 応力度チェック

```python
def calc_stress_util(
    M_total: float,  # N·mm
    I: float,        # mm⁴
    y_top: float,    # mm
    y_bottom: float, # mm
    fy: float,       # N/mm²
    alpha_bend: float,
) -> tuple[float, float, float, float]:
    """sigma_top, sigma_bottom, sigma_allow, util_bend を計算"""
    sigma_top = M_total * y_top / I
    sigma_bottom = M_total * y_bottom / I
    sigma_allow = alpha_bend * fy
    util_bend = max(abs(sigma_top), abs(sigma_bottom)) / sigma_allow
    return sigma_top, sigma_bottom, sigma_allow, util_bend
```

### Task 2.5: せん断チェック

```python
def calc_shear_util(
    V_total: float,     # N
    web_thickness: float,  # mm
    web_height: float,  # mm
    fy: float,          # N/mm²
    alpha_shear: float,
) -> tuple[float, float, float]:
    """tau_avg, tau_allow, util_shear を計算"""
    tau_avg = V_total / (web_thickness * web_height)
    tau_allow = alpha_shear * (fy / (3 ** 0.5))
    util_shear = abs(tau_avg) / tau_allow
    return tau_avg, tau_allow, util_shear
```

### Task 2.6: たわみチェック

```python
def calc_deflection_util(
    M_total: float,    # N·mm
    L: float,          # mm
    E: float,          # N/mm²
    I: float,          # mm⁴
    deflection_ratio: float,
) -> tuple[float, float, float]:
    """delta, delta_allow, util_defl を計算"""
    w_eq = 8 * M_total / L**2
    delta = 5 * w_eq * L**4 / (384 * E * I)
    delta_allow = L / deflection_ratio
    util_defl = delta / delta_allow
    return delta, delta_allow, util_defl
```

### Task 2.7: 床版厚チェック

```python
def calc_deck_util(
    provided_mm: float,
    girder_spacing_mm: float,
) -> tuple[float, float]:
    """required_mm, util_deck を計算"""
    L_support_m = girder_spacing_mm / 1000
    required_mm = max(30 * L_support_m + 110, 160)
    util_deck = required_mm / provided_mm
    return required_mm, util_deck
```

### Task 2.8: 横桁配置チェック

```python
def check_crossbeam_layout(
    panel_length: float,
    num_panels: int,
    bridge_length: float,
    tol: float = 1.0,
) -> bool:
    """横桁配置の整合性をチェック"""
    return (
        abs(panel_length * num_panels - bridge_length) <= tol
        and panel_length <= 20000
    )
```

---

## Phase 3: JudgeReport 生成

### 対象ファイル
- `src/bridge_agentic_generate/judge/services.py`

### Task 3.1: judge_design 関数

```python
def judge_design(judge_input: JudgeInput) -> JudgeReport:
    """メイン照査関数"""
    design = judge_input.bridge_design
    # 1. 活荷重計算
    # 2. 死荷重計算
    # 3. 断面諸量計算
    # 4. 各 util 計算
    # 5. Diagnostics 組み立て
    # 6. Utilization 組み立て（max_util, governing_check 決定）
    # 7. pass_fail 判定（all util <= 1.0 and crossbeam_layout_ok）
    # 8. JudgeReport 返却
```

### Task 3.2: governing_check 決定ロジック

```python
def determine_governing(utilization: Utilization) -> GoverningCheck:
    """最大 util の項目を特定"""
    utils = {
        GoverningCheck.DECK: utilization.deck,
        GoverningCheck.BEND: utilization.bend,
        GoverningCheck.SHEAR: utilization.shear,
        GoverningCheck.DEFLECTION: utilization.deflection,
    }
    return max(utils, key=utils.get)
```

---

## Phase 4: PatchPlan 生成（LLM 連携）

### 対象ファイル
- `src/bridge_agentic_generate/judge/prompts.py`
- `src/bridge_agentic_generate/judge/services.py`
- `src/bridge_agentic_generate/judge/models.py`（RepairContext 追加）

### Task 4.1: RepairContext モデル

```python
class AllowedAction(BaseModel):
    op: PatchActionOp
    allowed_deltas: list[float]  # 許容される変更量

class RepairContext(BaseModel):
    utilization: Utilization
    crossbeam_layout_ok: bool
    governing_check: GoverningCheck
    diagnostics: Diagnostics
    current_design: dict  # 対象パラメータの現在値
    allowed_actions: list[AllowedAction]
    priorities: str = "安全 > 施工性 > 鋼重"
```

### Task 4.2: プロンプト定義

`prompts.py` に以下を追加:

```python
REPAIR_SYSTEM_PROMPT = """あなたは橋梁設計の修正を提案するエキスパートです。

以下の優先順位で修正案を提案してください:
1. 安全: すべての util ≤ 1.0
2. 施工性: 急激な変更を避ける（変更量と変更箇所を最小化）
3. 鋼重最小: 同等なら軽い案

制約:
- 許可された操作（allowed_actions）のみ使用可能
- 最大3手まで
- 急激な変更を避ける（最初は小さい変更量を優先）
"""

REPAIR_USER_PROMPT_TEMPLATE = """
以下の照査結果に対して、修正案（PatchPlan）を提案してください。

## 照査結果
{repair_context_json}

## 出力形式
PatchPlan（JSON）のみ返してください。
"""
```

### Task 4.3: PatchPlan 生成関数

```python
def generate_patch_plan(
    repair_context: RepairContext,
    model_name: str = "gpt-4o-mini",
) -> PatchPlan:
    """LLM に RepairContext を渡し、PatchPlan を取得"""
    # llm_client.py の call_llm を使用
    # Structured Output で PatchPlan を取得
```

### Task 4.4: PatchPlan バリデーション

```python
def validate_patch_plan(
    patch_plan: PatchPlan,
    allowed_actions: list[AllowedAction],
) -> bool:
    """PatchPlan が許可された操作のみを含むかチェック"""
```

---

## Phase 5: Designer 連携ループ

### 対象ファイル
- `src/bridge_agentic_generate/main.py`
- `src/bridge_agentic_generate/judge/services.py`（apply_patch 関数）

### Task 5.1: apply_patch_plan 関数

```python
def apply_patch_plan(
    design: BridgeDesign,
    patch_plan: PatchPlan,
) -> BridgeDesign:
    """PatchPlan を BridgeDesign に適用"""
    # path を解析し、対応するフィールドを更新
    # set_deck_thickness_to_required の場合は diagnostics.deck_required を使用
```

### Task 5.2: ループ実装（main.py）

```python
def run_with_repair_loop(
    bridge_length_m: float,
    total_width_m: float,
    model_name: str,
    max_iterations: int = 5,
) -> tuple[BridgeDesign, JudgeReport]:
    """Designer → Judge → (必要なら修正) のループ"""
    design = generate_design(...)

    for _ in range(max_iterations):
        report = judge_design(...)
        if report.pass_fail:
            return design, report

        if not report.patch_plan or not report.patch_plan.actions:
            raise ValueError("不合格だが修正案がない")

        design = apply_patch_plan(design, report.patch_plan)

    raise RuntimeError(f"{max_iterations}回の修正で収束せず")
```

---

## Phase 6: テスト

### 対象ファイル
- `tests/bridge_agentic_generate/judge/test_calculators.py`（新規）
- `tests/bridge_agentic_generate/judge/test_services.py`（新規）

### Task 6.1: 断面計算の単体テスト

```python
def test_section_properties_symmetric():
    """対称I断面で ybar, I が正しいか"""

def test_section_properties_asymmetric():
    """非対称I断面で手計算値と一致するか"""
```

### Task 6.2: 死荷重計算の単体テスト

```python
def test_dead_load():
    """既知の寸法で w_dead, M_dead, V_dead が式通りか"""
```

### Task 6.3: 統合テスト（fixture）

```python
def test_judge_design_with_fixture():
    """既存設計値で report が生成できるか"""
    # data/generated_simple_bridge_json/ から fixture を読み込み
    # report.utilization に数値が入ることを確認
    # report.diagnostics に中間量が入ることを確認
```

### Task 6.4: LLM 連携テスト（モック）

```python
def test_generate_patch_plan_with_mock():
    """LLM 呼び出しをモックして PatchPlan が生成されるか"""
```

---

## 完了条件（Definition of Done）

- [ ] Phase 1: models.py が v1 仕様に更新されている
- [ ] Phase 2: 全 util 計算関数が実装されている
- [ ] Phase 3: `judge_design(input) -> JudgeReport` が動作する
- [ ] Phase 4: LLM による PatchPlan 生成が動作する
- [ ] Phase 5: Designer-Judge ループが動作する
- [ ] Phase 6: 単体・統合テストが通る
- [ ] `make fmt && make lint` がエラーなし

---

## 注意事項

### 単位系（最重要）

| 項目 | 単位 |
|------|------|
| E（ヤング率） | N/mm² |
| 断面寸法 | mm |
| I（断面二次モーメント） | mm⁴ |
| 応力度 | N/mm² |
| 橋長 L | mm（BridgeDesign内）|
| M_* | N·mm |
| V_* | N |
| unit_weight | N/mm³ |
| p_live_equiv | kN/m²（入力）|

### 単位変換

```python
# kN/m³ → N/mm³
78.5 kN/m³ = 78.5e-6 N/mm³

# kN/m² → N/mm²
12 kN/m² = 0.012 N/mm²

# kN·m → N·mm
1 kN·m = 1e6 N·mm

# kN → N
1 kN = 1e3 N
```

### フォールバック

| ケース | 対処 |
|--------|------|
| LLM が許可されていない操作を出した | 差し戻し（再提案要求） |
| pass_fail=False かつ actions 空 | ValueError 送出 |
| pass_fail=True かつ actions 空 | 正常終了（修正不要） |
