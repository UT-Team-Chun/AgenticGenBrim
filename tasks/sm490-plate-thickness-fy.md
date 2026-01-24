# タスク: SM490対応 - 板厚別降伏点の実装

## 概要

鋼材をSM400からSM490に変更し、部材（ウェブ・上フランジ・下フランジ）ごとに板厚に応じた降伏点(fy)を適用する。

## 背景

SM490の降伏点は板厚によって異なる:
| 板厚範囲 | 降伏点 fy [N/mm²] |
|----------|-------------------|
| ≤ 16mm   | 325               |
| 16〜40mm | 315               |
| 40〜75mm | 295               |

現在のJudge計算では単一のfy（235 N/mm²、SM400相当）を使用しているが、これを部材ごとの板厚に応じて動的に決定するよう変更する。

## 要件

### 鋼種・降伏点の定義
- [ ] `SteelGrade` StrEnumを追加（SM400, SM490）
- [ ] `get_fy(grade: SteelGrade, thickness_mm: float) -> float` 関数を追加
- [ ] SM400の板厚別降伏点も定義（≤16mm: 245, 16-40mm: 235, 40-75mm: 215）

### MaterialsSteelモデルの変更
- [ ] `fy` フィールドを削除
- [ ] `grade: SteelGrade` フィールドを追加（デフォルト: SM490）

### Judge計算の修正
- [ ] 曲げ照査: 上フランジ板厚 → fy_top、下フランジ板厚 → fy_bottom を使用
- [ ] せん断照査: ウェブ板厚 → fy_web を使用
- [ ] 各部材の許容応力度を個別に計算

### Diagnosticsモデルの拡張
- [ ] `fy_top_flange`, `fy_bottom_flange`, `fy_web` フィールドを追加
- [ ] `sigma_allow_top`, `sigma_allow_bottom` フィールドを追加
- [ ] 既存の `sigma_allow` は後方互換のため残すか、削除するか検討

### IFC材料名の変更
- [ ] `DEFAULT_MATERIAL` を `"SM490A"` に変更
- [ ] Pydanticモデルのデフォルト材料名を `"SM490A"` に変更

## 対象ディレクトリ

- [x] `src/bridge_agentic_generate/judge/` - 設計評価
- [x] `src/bridge_json_to_ifc/` - IFC変換

## 対象ファイル

### judge/ (メイン変更)
- `src/bridge_agentic_generate/judge/models.py`
  - SteelGrade enum追加
  - get_fy関数追加
  - MaterialsSteel変更
  - Diagnostics拡張
- `src/bridge_agentic_generate/judge/services.py`
  - `_calculate_utilization_and_diagnostics` 関数の修正
  - 曲げ・せん断の許容応力度計算を部材別に変更
- `src/bridge_agentic_generate/judge/prompts.py`
  - LLMに渡す診断情報の更新（fy_top/bottom/web, sigma_allow_top/bottom）
- `src/bridge_agentic_generate/judge/CLAUDE.md`
  - 仕様書の更新

### bridge_json_to_ifc/ (材料名変更)
- `src/bridge_json_to_ifc/convert_simple_to_senkei_json.py`
  - `DEFAULT_MATERIAL = "SM490A"`
- `src/bridge_json_to_ifc/senkei_models.py`
  - `PanelMaterial.mat` デフォルト変更
  - `WebSpec.mat` デフォルト変更
  - `FlangeSpec.mat` デフォルト変更

### ifc_utils_new/ (オプション: フォールバック値)
- `src/bridge_json_to_ifc/ifc_utils_new/components/DefPanel.py`
- `src/bridge_json_to_ifc/ifc_utils_new/core/DefBridge.py`
- `src/bridge_json_to_ifc/ifc_utils_new/io/DefJson.py`

## 実装詳細

### 1. SteelGrade と get_fy 関数

```python
# judge/models.py に追加

class SteelGrade(StrEnum):
    SM400 = "SM400"
    SM490 = "SM490"


def get_fy(grade: SteelGrade, thickness_mm: float) -> float:
    """鋼種と板厚から降伏点を返す。

    Args:
        grade: 鋼種
        thickness_mm: 板厚 [mm]

    Returns:
        降伏点 [N/mm²]
    """
    if grade == SteelGrade.SM400:
        if thickness_mm <= 16:
            return 245.0
        elif thickness_mm <= 40:
            return 235.0
        else:
            return 215.0
    elif grade == SteelGrade.SM490:
        if thickness_mm <= 16:
            return 325.0
        elif thickness_mm <= 40:
            return 315.0
        else:
            return 295.0
    else:
        raise ValueError(f"未対応の鋼種: {grade}")
```

### 2. MaterialsSteel の変更

```python
# judge/models.py

class MaterialsSteel(BaseModel):
    """鋼材の材料特性。"""

    E: float = Field(default=2.0e5, description="ヤング率 [N/mm²]")
    grade: SteelGrade = Field(default=SteelGrade.SM490, description="鋼種")
    unit_weight: float = Field(
        default=78.5e-6,
        description="単位体積重量 [N/mm³]（78.5 kN/m³ = 78.5e-6 N/mm³）",
    )
    # fy は削除（板厚から動的に計算）
```

### 3. Judge計算の修正 (services.py)

```python
# _calculate_utilization_and_diagnostics 関数内

# 部材ごとの降伏点を計算
fy_top = get_fy(steel.grade, girder.top_flange_thickness)
fy_bottom = get_fy(steel.grade, girder.bottom_flange_thickness)
fy_web = get_fy(steel.grade, girder.web_thickness)

# 曲げ照査（上下別）
sigma_allow_top = params.alpha_bend * fy_top
sigma_allow_bottom = params.alpha_bend * fy_bottom

util_bend_top = abs(sigma_top) / sigma_allow_top
util_bend_bottom = abs(sigma_bottom) / sigma_allow_bottom
util_bend = max(util_bend_top, util_bend_bottom)

# せん断照査
tau_allow = params.alpha_shear * (fy_web / math.sqrt(3))
util_shear = abs(tau_avg) / tau_allow
```

### 4. Diagnostics の拡張

```python
# judge/models.py

class Diagnostics(BaseModel):
    # ... 既存フィールド ...

    # 新規追加
    fy_top_flange: float = Field(..., description="上フランジ降伏点 [N/mm²]")
    fy_bottom_flange: float = Field(..., description="下フランジ降伏点 [N/mm²]")
    fy_web: float = Field(..., description="ウェブ降伏点 [N/mm²]")
    sigma_allow_top: float = Field(..., description="上縁許容曲げ応力度 [N/mm²]")
    sigma_allow_bottom: float = Field(..., description="下縁許容曲げ応力度 [N/mm²]")

    # sigma_allow, tau_allow は残す（後方互換 or 削除検討）
```

## 受け入れ条件

### コード品質
- [ ] `make fmt` - フォーマットが適用済み
- [ ] `make lint` - Lintエラーなし
- [ ] 型アノテーションが付与されている
- [ ] Google スタイル Docstring が記述されている

### 機能
- [ ] 要件がすべて満たされていること
- [ ] SM490、板厚30mmの場合に fy=315 が適用されることを確認
- [ ] SM490、板厚12mmの場合に fy=325 が適用されることを確認
- [ ] 曲げ照査で上下フランジ別の許容応力度が使用されること
- [ ] せん断照査でウェブの許容応力度が使用されること
- [ ] テストが追加されていること（LLM呼び出しはモック）

### その他
- [ ] 未使用コード・コメントアウトがないこと
- [ ] マジックナンバーがないこと（板厚閾値・降伏点は定数化を検討）

## 備考

### 板厚閾値と降伏点の定数化

板厚と降伏点のマッピングをハードコーディングではなく、定数や設定として管理することを検討:

```python
SM490_FY_TABLE = [
    (16.0, 325.0),   # thickness <= 16mm
    (40.0, 315.0),   # 16mm < thickness <= 40mm
    (75.0, 295.0),   # 40mm < thickness <= 75mm
]
```

### 後方互換性

- `MaterialsSteel.fy` を使っている既存コードがある場合は、マイグレーション期間を設けるか、`@property` で代替値を返すことを検討
- 既存のテストが `fy=235.0` を期待している場合は修正が必要

### 将来の拡張

- SM520, SM570 などの高強度鋼への対応も同様のパターンで追加可能
- 設計JSONに鋼種を含めることで、部材ごとに異なる鋼種を指定できるようにする拡張も可能
