# DEV_GUIDE

## 開発コマンド

```bash
make fmt          # フォーマット（Ruff）
make lint         # Lint（CI相当）
make fix          # Lint + 自動修正 + フォーマット
```

## 命名規則

- **変数・関数**: snake_case
- **クラス**: PascalCase
- **定数**: UPPER_SNAKE_CASE

## 型アノテーション

- すべての関数に型アノテーション必須
- Union 型は `X | Y` 形式（PEP 604）
- 組み込みジェネリクス使用（PEP 585）
  - `list[str]` ○ / `List[str]` ×
  - `dict[str, int]` ○ / `Dict[str, int]` ×

```python
# Good
def process(items: list[str]) -> dict[str, int] | None:
    ...

# Bad
from typing import List, Dict, Optional
def process(items: List[str]) -> Optional[Dict[str, int]]:
    ...
```

## Pydantic

- 返り値に `dict` / `tuple` は使わず、Pydantic モデルで型を定義する
- 文字列ハードコーディングは `StrEnum` や Pydantic モデルで管理する
- `.value` は極力使わない（`StrEnum` を直接使う）

```python
# Good
class GoverningCheck(StrEnum):
    DECK = "deck"
    BEND = "bend"

def get_check() -> GoverningCheck:
    return GoverningCheck.DECK

# Bad
def get_check() -> str:
    return "deck"
```

## ロギング

```python
from src.bridge_agentic_generate.logger_config import logger

logger.info("処理開始")
logger.debug(f"パラメータ: {params}")
logger.error(f"エラー発生: {e}")
```

- `print` 禁止

## CLI

- CLI の引数管理には必ず `fire` を使用する

```python
import fire

class CLI:
    def run(self, bridge_length_m: float = 50.0) -> None:
        ...

if __name__ == "__main__":
    fire.Fire(CLI)
```

## ファイル操作

- ファイル/ディレクトリ操作は `pathlib.Path` を使う

```python
from pathlib import Path

output_dir = Path("data/generated_ifc")
output_dir.mkdir(parents=True, exist_ok=True)
output_path = output_dir / "sample.ifc"
```

## Docstring

- Google スタイル Docstring（日本語）

```python
def calculate_util(stress: float, allowable: float) -> float:
    """応力度比を計算する。

    Args:
        stress: 発生応力度 [N/mm²]
        allowable: 許容応力度 [N/mm²]

    Returns:
        応力度比（util）
    """
    return stress / allowable
```

## 禁止事項

- `try: ... except: pass` のような例外の握りつぶしは禁止
- 未使用コード・コメントアウトは削除する
- 後方互換性の残骸（未使用の `_vars`、re-export、`// removed` コメント等）を残さない
- マジックナンバーを避け、定数化してから利用する

```python
# Bad
if thickness < 160:
    ...

# Good
MIN_DECK_THICKNESS_MM = 160
if thickness < MIN_DECK_THICKNESS_MM:
    ...
```

## テスト

- LLM を使う処理のテストではモックを使用
- テストファイルは `tests/` ディレクトリに配置

## Git

- `git add/commit` は自動実行しない（コミットメッセージの提案のみ）
- `.env` ファイルはコミットしない
- `data/` と `rag_index/` は `.gitignore` に含まれる
