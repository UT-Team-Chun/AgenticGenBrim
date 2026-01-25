# タスク: 死荷重の桁別計算

## 概要

死荷重を活荷重と同様に「桁ごと」に計算し、合計断面力・util も桁別に算出して governing 桁を特定する。

## 背景

現状の実装では死荷重が「中間桁を代表値として1つ」で計算されている。
活荷重は既に桁別に計算されているが、合計時に「死荷重（代表）+ 活荷重（最大）」としており、支配桁の説明がしづらい。

**変更後:**
- 死荷重も桁ごとに計算（床版自重は `b_i` を使用）
- 合計断面力 `M_total_i`, `V_total_i` を桁ごとに計算
- util も桁ごとに計算し、最大の桁を governing として特定

## 要件

### 1. 死荷重の桁別計算

- [ ] 床版自重に「桁ごとのトリビュタリ幅 `b_i`」を使用
  ```python
  # b_i は活荷重で既に計算済み（端桁: overhang + spacing/2, 中間桁: spacing）
  w_deck_i = gamma_concrete * deck_thickness * b_i
  w_dead_i = w_deck_i + w_steel  # w_steel は全桁共通（断面同一）
  ```
- [ ] `b_eff`（実効幅）は死荷重では使わない（主載荷/従載荷の話は活荷重のみ）
- [ ] 断面力も桁ごとに計算
  ```python
  M_dead_i = w_dead_i * L**2 / 8
  V_dead_i = w_dead_i * L / 2
  ```

### 2. 合計断面力の桁別計算

- [ ] 同じ桁どうしで足す
  ```python
  M_total_i = M_dead_i + M_live_i
  V_total_i = V_dead_i + V_live_i
  ```

### 3. util の桁別計算と governing 桁の特定

- [ ] 曲げ照査
  ```python
  sigma_top_i = M_total_i * y_top / I
  sigma_bottom_i = M_total_i * y_bottom / I
  util_bend_i = max(|sigma_top_i|, |sigma_bottom_i|) / sigma_allow
  util_bend_governing = max(util_bend_i for all i)
  governing_girder_index_bend = argmax(util_bend_i)
  ```
- [ ] せん断照査
  ```python
  tau_avg_i = V_total_i / (web_thickness * web_height)
  util_shear_i = |tau_avg_i| / tau_allow
  util_shear_governing = max(util_shear_i for all i)
  governing_girder_index_shear = argmax(util_shear_i)
  ```
- [ ] たわみ照査は現状維持（活荷重のみ、桁別対応不要）

### 4. データモデルの拡張

- [ ] `GirderLoadResult` モデルを新設（死荷重・活荷重を統合）
  ```python
  class GirderLoadResult(BaseModel):
      """1本の主桁の荷重計算結果（死荷重・活荷重統合）。"""
      girder_index: int           # 主桁インデックス（0始まり）
      b_i_m: float                # 受け持ち幅 [m]

      # 死荷重
      w_dead: float               # 死荷重線荷重 [N/mm]
      M_dead: float               # 死荷重曲げモーメント [N·mm]
      V_dead: float               # 死荷重せん断力 [N]

      # 活荷重（既存の GirderLiveLoadResult から移行）
      b_eff_m: float              # 実効幅 [m]（活荷重用）
      w_M: float                  # 曲げ用等価線荷重 [kN/m]
      w_V: float                  # せん断用等価線荷重 [kN/m]
      M_live: float               # 活荷重曲げモーメント [N·mm]
      V_live: float               # 活荷重せん断力 [N]

      # 合計
      M_total: float              # 合計曲げモーメント [N·mm]
      V_total: float              # 合計せん断力 [N]
  ```
- [ ] `Diagnostics` に governing 桁情報を追加
  ```python
  governing_girder_index_bend: int    # 曲げで最厳しい桁
  governing_girder_index_shear: int   # せん断で最厳しい桁
  girder_results: list[GirderLoadResult]  # 全桁の詳細結果
  ```
- [ ] 既存の `GirderLiveLoadResult` と `LiveLoadEffectsResult` を廃止または統合

### 5. 出力・レポートへの反映

- [ ] 照査結果に「どの桁が支配的か」を出力
  ```
  曲げ照査: G2 が支配 (util = 0.85)
  せん断照査: G1 が支配 (util = 0.72)
  ```
- [ ] `Diagnostics` に桁ごとの詳細を含める（ただし `util_bend_i` 等は不要）

### 6. PatchPlan への反映

- [ ] `RepairContext` に「どの桁が NG か」の情報を含める
- [ ] LLM プロンプトで桁情報を活用できるようにする

## 対象ディレクトリ

- [x] `src/bridge_agentic_generate/judge/` - 設計評価

## 対象ファイル

- `src/bridge_agentic_generate/judge/models.py` - モデル定義
- `src/bridge_agentic_generate/judge/services.py` - 計算ロジック
- `src/bridge_agentic_generate/judge/prompts.py` - LLM プロンプト
- `src/bridge_agentic_generate/judge/report.py` - レポート出力
- `tests/judge/test_services.py` - テスト

## 受け入れ条件

### コード品質
- [ ] `make fmt` - フォーマットが適用済み
- [ ] `make lint` - Lintエラーなし
- [ ] 型アノテーションが付与されている
- [ ] Google スタイル Docstring が記述されている

### 機能
- [ ] 死荷重が桁ごとに計算されること
- [ ] 合計断面力 `M_total_i`, `V_total_i` が桁ごとに計算されること
- [ ] `util_bend`, `util_shear` が governing 桁の値であること
- [ ] governing 桁のインデックスが `Diagnostics` に含まれること
- [ ] レポートに governing 桁が表示されること
- [ ] PatchPlan 生成時に桁情報が LLM に渡ること
- [ ] テストが追加されていること（LLM呼び出しはモック）

### その他
- [ ] 未使用コード・コメントアウトがないこと
- [ ] マジックナンバーがないこと
- [ ] 既存のテストが通ること

## 技術的な補足

### 計算フローの変更点

**Before:**
```
calc_l_live_load_effects() → M_live_max, V_live_max
calc_dead_load() → w_dead（1つ）
calc_dead_load_effects() → M_dead, V_dead（1つ）
M_total = M_dead + M_live_max
V_total = V_dead + V_live_max
```

**After:**
```
calc_girder_load_effects() → List[GirderLoadResult]
  ├─ 各桁 i について:
  │   ├─ w_dead_i = gamma_c * deck_thickness * b_i + w_steel
  │   ├─ M_dead_i = w_dead_i * L² / 8
  │   ├─ V_dead_i = w_dead_i * L / 2
  │   ├─ M_live_i, V_live_i（既存の活荷重計算）
  │   ├─ M_total_i = M_dead_i + M_live_i
  │   └─ V_total_i = V_dead_i + V_live_i
  └─ governing 桁を特定
```

### 単位系（変更なし）

| 項目 | 単位 |
|------|------|
| b_i | mm（内部）/ m（モデル出力） |
| w_dead_i | N/mm |
| M_dead_i, M_total_i | N·mm |
| V_dead_i, V_total_i | N |

### 注意点

- `w_steel` は全桁共通（断面同一の前提）
- たわみ照査は活荷重のみのため、桁別対応は不要
- 曲げとせん断で governing 桁が異なる可能性がある
