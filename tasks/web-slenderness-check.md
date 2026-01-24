# タスク: 腹板幅厚比照査 (WEB_SLENDERNESS) の追加

## 概要

プレートガーダーの最小腹板厚照査を Judge に追加する。鋼種に応じて SM490 は b/130、SM400 は b/152 の基準を適用する。

## 要件

- [ ] `GoverningCheck.WEB_SLENDERNESS` を追加
- [ ] 鋼種別の最小腹板厚計算関数 `get_min_web_thickness()` を追加
- [ ] `_calculate_utilization_and_diagnostics()` に照査ロジックを追加
- [ ] `Diagnostics` に `web_thickness_min_required` フィールドを追加
- [ ] 修正提案プロンプトに `WEB_SLENDERNESS` 対応を追加
- [ ] 照査 NG 時は腹板厚を増やす修正提案を生成

## 仕様詳細

### 最小腹板厚の計算式

| 鋼種   | 最小腹板厚 t_min        |
| ------ | ----------------------- |
| SM490  | `web_height / 130`      |
| SM400  | `web_height / 152`      |

- `web_height`: フランジ間距離 [mm]（`GirderSection.web_height`）
- 出典: 社内基準（RAG 登録なし）

### util 計算式

```
util_web_slenderness = t_min_required / web_thickness
```

- `util > 1.0` で NG（実際の腹板厚が必要値より薄い）

### 修正方針

- 照査 NG 時は `web_thickness` を `ceil(t_min_required)` 以上に増加させる

## 対象ディレクトリ

- [x] `src/bridge_agentic_generate/judge/` - 設計評価

## 対象ファイル

- `src/bridge_agentic_generate/judge/models.py` - `GoverningCheck`, `Diagnostics` の変更
- `src/bridge_agentic_generate/judge/services.py` - 照査ロジックの追加
- `src/bridge_agentic_generate/judge/prompts.py` - 修正提案プロンプトの更新

## 受け入れ条件

### コード品質

- [ ] `make fmt` - フォーマットが適用済み
- [ ] `make lint` - Lint エラーなし
- [ ] 型アノテーションが付与されている
- [ ] Google スタイル Docstring が記述されている

### 機能

- [ ] 既存の照査パターンと整合性が取れていること
- [ ] SM490 / SM400 両方の鋼種で正しく計算されること
- [ ] テストが追加されていること（LLM 呼び出しはモック）

### その他

- [ ] 未使用コード・コメントアウトがないこと
- [ ] マジックナンバーがないこと（130, 152 は定数化）

## 実装ガイド

### 1. models.py の変更

```python
class GoverningCheck(StrEnum):
    # 既存
    BEND = "BEND"
    SHEAR = "SHEAR"
    DEFLECTION = "DEFLECTION"
    DECK = "DECK"
    CROSSBEAM_LAYOUT = "CROSSBEAM_LAYOUT"
    # 追加
    WEB_SLENDERNESS = "WEB_SLENDERNESS"

class Diagnostics(BaseModel):
    # 既存フィールド...
    # 追加
    web_thickness_min_required: float | None = None  # 必要最小腹板厚 [mm]
```

### 2. services.py の変更

```python
def get_min_web_thickness(grade: SteelGrade, web_height: float) -> float:
    """鋼種とフランジ間距離から最小腹板厚を返す。

    Args:
        grade: 鋼種
        web_height: フランジ間距離 [mm]

    Returns:
        最小腹板厚 [mm]
    """
    if grade == SteelGrade.SM490:
        return web_height / 130
    elif grade == SteelGrade.SM400:
        return web_height / 152
    else:
        return web_height / 130  # デフォルト
```

### 3. 既存パターンとの整合性

| 項目       | 既存パターン               | 今回の実装                              |
| ---------- | -------------------------- | --------------------------------------- |
| util 計算  | `必要値 / 実際値`          | `t_min / web_thickness`                 |
| 鋼種依存   | `get_fy(grade, thickness)` | `get_min_web_thickness(grade, height)`  |
| 決定論的   | LLM 呼び出しなし           | 同様                                    |

## 備考

- `get_fy()` 関数（板厚別降伏点）と同様のパターンで実装
- 将来的に他の鋼種（SN400 等）を追加する場合は `get_min_web_thickness()` を拡張
