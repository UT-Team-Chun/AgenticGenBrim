# タスク: L荷重の簡易スクリーニングを p1/p2 ルールに合わせる

## 概要

現状の活荷重が「p1=12 を全スパン等分布」のように単純化されているため、道路橋示方書の p1/p2 ルール（載荷長 D、主載荷 5.5m、従載荷 1/2）に合わせた簡易モデルへ置換する。

## 要件

- [ ] p1/p2 の2成分を扱う（p1 は D=10m 部分載荷、p2 は全スパン）
- [ ] 幅方向は「主載荷 5.5m = 100%、残り = 1/2」を実効幅 $b_i^{eff}$ で反映
- [ ] 部分載荷は「等価な全スパン等分布」に換算して、現行の単純梁式（$L^2/8$, $L/2$）をそのまま使う
- [ ] 主桁ごとに個別の $b_i$ を計算する（端桁は張り出し + 半スパン、中間桁は両側の半スパン）
- [ ] **各主桁ごとに照査して、最も厳しい結果（最大 util）を採用**
- [ ] $L > 80$ m が来たら例外（NotApplicable）で止める
- [ ] 返り値は Pydantic モデルで型定義する（dict/tuple は使わない）

## 対象ディレクトリ

- [x] `src/bridge_agentic_generate/judge/` - 設計評価

## 対象ファイル

- `src/bridge_agentic_generate/judge/services.py` - `calc_live_load_effects()` の置換（L162-196）
- `src/bridge_agentic_generate/judge/models.py` - 新規 Pydantic モデル追加、`NotApplicableError` 追加、`LoadInput.p_live_equiv` 削除、`Diagnostics` に `live_load_result` 追加

## 適用範囲

- **対象**: 主桁（鋼I桁）、単純支持、支間 $L \leq 80$ m（B活荷重の p2=3.5 を使うため）
- **$L > 80$ m**: 例外（NotApplicable）で停止

## 計算仕様

### 定数（B活荷重）

| 項目 | 値 | 備考 |
|------|-----|------|
| 載荷長 | $D = \min(10, L)$ m | |
| 面圧（曲げ照査用） | $p_{1,M} = 10$ kN/m² | 道路橋示方書 |
| 面圧（せん断照査用） | $p_{1,V} = 12$ kN/m² | 道路橋示方書 |
| p2（支間80m以下） | $p_2 = 3.5$ kN/m² | | 道路橋示方書 |

### 幅方向: 主桁 i の受け持ち幅 $b_i$ と実効幅 $b_i^{eff}$

#### $b_i$ の計算（主桁ごとに異なる）

overhang を動的に算出:
$$
\text{overhang} = \frac{\text{total\_width} - (\text{num\_girders} - 1) \times \text{girder\_spacing}}{2}
$$

| 主桁位置 | $b_i$ の計算 |
|---------|-------------|
| 端桁 (G1, Gn) | $\text{overhang} + \frac{\text{girder\_spacing}}{2}$ |
| 中間桁 | $\text{girder\_spacing}$ |

#### $b_i^{eff}$ の計算

主載荷幅 5.5m（100%）+ 残り（1/2）を、最不利に主載荷をその桁に寄せられるとして:

$$
b_i^{eff} = 0.5 \cdot b_i + 0.5 \cdot \min(b_i, 5.5)
$$

線荷重への変換:
$$
w = p \cdot b_i^{eff}
$$

### 橋軸方向: p1（長さ D 部分載荷）を等価等分布へ換算

**等価係数（曲げ・せん断共通）**:
$$
\gamma(L, D) = \frac{D(2L - D)}{L^2}
$$

> **注意**: 曲げ/せん断の違いは $p_{1,M} = 10$ と $p_{1,V} = 12$ の違いで表現する。

### 等価面圧 → 等価線荷重

**曲げ照査用**:
$$
p_{eq,M} = p_2 + p_{1,M} \cdot \gamma(L, D)
$$
$$
w_M = p_{eq,M} \cdot b_i^{eff}
$$

**せん断照査用**:
$$
p_{eq,V} = p_2 + p_{1,V} \cdot \gamma(L, D)
$$
$$
w_V = p_{eq,V} \cdot b_i^{eff}
$$

### 単純梁の最大値（現行の形を維持）

**曲げ（中央）**:
$$
M_{live,i} = \frac{w_M \cdot L^2}{8}
$$

**せん断（支点）**:
$$
V_{live,i} = \frac{w_V \cdot L}{2}
$$

## 実装タスク

### 新規で作る関数・モデル

```python
# models.py に追加

class NotApplicableError(Exception):
    """適用範囲外エラー（L > 80m など）。"""
    pass


class GirderLiveLoadResult(BaseModel):
    """1本の主桁の活荷重計算結果。"""
    girder_index: int = Field(..., description="主桁インデックス（0始まり）")
    b_i_m: float = Field(..., description="受け持ち幅 [m]")
    b_eff_m: float = Field(..., description="実効幅 [m]")
    w_M: float = Field(..., description="曲げ用等価線荷重 [kN/m]")
    w_V: float = Field(..., description="せん断用等価線荷重 [kN/m]")
    M_live: float = Field(..., description="活荷重最大曲げモーメント [N·mm]")
    V_live: float = Field(..., description="活荷重最大せん断力 [N]")


class LiveLoadEffectsResult(BaseModel):
    """全主桁の活荷重計算結果。"""
    # 共通パラメータ
    L_m: float = Field(..., description="支間長 [m]")
    D_m: float = Field(..., description="載荷長 [m]")
    p2: float = Field(..., description="p2 面圧 [kN/m²]")
    p1_M: float = Field(..., description="曲げ用 p1 面圧 [kN/m²]")
    p1_V: float = Field(..., description="せん断用 p1 面圧 [kN/m²]")
    gamma: float = Field(..., description="等価係数（曲げ・せん断共通）")
    p_eq_M: float = Field(..., description="曲げ用等価面圧 [kN/m²]")
    p_eq_V: float = Field(..., description="せん断用等価面圧 [kN/m²]")
    overhang_m: float = Field(..., description="張り出し幅 [m]")
    # 主桁ごとの結果
    girder_results: list[GirderLiveLoadResult] = Field(..., description="各主桁の計算結果")
    # 最厳しい結果（照査用）- 曲げとせん断で別々
    critical_girder_index_M: int = Field(..., description="曲げで最厳しい主桁のインデックス")
    critical_girder_index_V: int = Field(..., description="せん断で最厳しい主桁のインデックス")
    M_live_max: float = Field(..., description="最大活荷重曲げモーメント [N·mm]")
    V_live_max: float = Field(..., description="最大活荷重せん断力 [N]")


# Diagnostics に追加するフィールド
class Diagnostics(BaseModel):
    # ... 既存フィールド ...
    live_load_result: LiveLoadEffectsResult = Field(..., description="L荷重計算結果（詳細）")
```

```python
# services.py に追加

def calc_overhang(total_width_mm: float, num_girders: int, girder_spacing_mm: float) -> float:
    """張り出し幅を計算 [mm]。"""
    ...

def calc_tributary_width(girder_index: int, num_girders: int, overhang_mm: float, girder_spacing_mm: float) -> float:
    """主桁 i の受け持ち幅 b_i を計算 [mm]。

    Args:
        girder_index: 主桁インデックス（0始まり）
        num_girders: 主桁本数
        overhang_mm: 張り出し幅 [mm]
        girder_spacing_mm: 主桁間隔 [mm]

    Returns:
        受け持ち幅 [mm]
    """
    ...

def calc_beff(b_i_m: float) -> float:
    """実効幅を計算 [m]。"""
    ...

def calc_gamma(L_m: float, D_m: float) -> float:
    """等価係数を計算（曲げ・せん断共通）。"""
    ...

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
        ValueError: L <= 0 または b_i <= 0 の場合
    """
    ...
```

### 移行手順

1. `NotApplicableError`、`GirderLiveLoadResult`、`LiveLoadEffectsResult` を `models.py` に追加
2. `calc_l_live_load_effects` および補助関数を `services.py` に新規作成
3. 呼び出し元（`_calculate_utilization_and_diagnostics` 等）を新関数に切り替え
4. 動作確認（ユニットテスト + 回帰テスト）
5. **確認後、以下を削除:**
   - 旧関数 `calc_live_load_effects`
   - `LoadInput.p_live_equiv`（および呼び出し元の引数）

### 単位の注意

- JSON が mm 系なので、内部で **m に統一** してから計算すること
- $L$ [m]、$D$ [m]、$b_i$ [m]、5.5 [m]
- 出力は既存と同じ単位系（N·mm, N）

## 出力（JudgeReport / Diagnostics）に残す項目

| 分類 | 項目 |
|------|------|
| 共通 | L, D, p2, gamma, overhang |
| 曲げ用 | p1_M=10, p_eq_M |
| せん断用 | p1_V=12, p_eq_V |
| 主桁ごと | girder_index, b_i, b_eff, w_M, w_V, M_live, V_live |
| 最厳しい結果 | critical_girder_index_M, critical_girder_index_V, M_live_max, V_live_max |

## 受け入れ条件

### コード品質
- [ ] `make fmt` - フォーマットが適用済み
- [ ] `make lint` - Lintエラーなし
- [ ] 型アノテーションが付与されている
- [ ] Google スタイル Docstring が記述されている
- [ ] 返り値は Pydantic モデルで定義（dict/tuple は使わない）

### 機能

#### ユニットテスト（数式一致チェック）

**例1**: $L = 40$ m, $D = 10$ m
```
γ = 10 × (2×40 - 10) / 40² = 10 × 70 / 1600 = 0.4375
```

**例2**: $L = 30$ m, $D = 10$ m
```
γ = 10 × (2×30 - 10) / 30² = 10 × 50 / 900 = 0.5556
```

**b_eff のテスト**:
- $b_i = 2.5$ m → $b_{eff} = 0.5 \times 2.5 + 0.5 \times 2.5 = 2.5$ m（5.5未満ならそのまま）
- $b_i = 8.0$ m → $b_{eff} = 0.5 \times 8.0 + 0.5 \times 5.5 = 6.75$ m

#### 回帰テスト（スナップショット）

- **対象ファイル**: `data/generated_simple_bridge_json/design_L40_B10_20260123_214700_final.json`
- 変更前後で、死荷重側や断面性能の計算が変わっていないこと
- 変わるのは活荷重由来の `M_live`, `V_live` と、それに基づく `util` のみ

#### 例外系

- [ ] $L \leq 0$ → 例外
- [ ] $b_i \leq 0$ → 例外
- [ ] $L > 80$ → `NotApplicableError` で停止

### その他
- [ ] 未使用コード・コメントアウトがないこと
- [ ] マジックナンバーがないこと（定数として定義）
- [ ] 旧関数 `calc_live_load_effects` が削除されていること
- [ ] `LoadInput.p_live_equiv` が削除されていること

## 備考

- この変更は「L荷重の完全再現」ではなく、**スクリーニング用の簡易モデル**
- 等価係数 γ は曲げ・せん断共通で使用し、曲げ/せん断の違いは p1_M=10 / p1_V=12 で表現
- 幅方向は「主載荷を各桁に最不利に置ける」と仮定（桁ごとに安全側に寄せる）
