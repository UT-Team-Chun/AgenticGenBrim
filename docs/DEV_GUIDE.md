# DEV_GUIDE

## 開発メモ

- CLI の引数管理には必ず fire を使用する。
- すべての関数に型アノテーションと Google スタイルの docstring を付与する。
- マジックナンバーを避け、定数化してから利用する。
- 文字列ハードコーディングは StrEnum や Pydantic モデルで管理する（`.value` は極力使わない）。
- 返り値に `dict` / `tuple` は使わず、Pydantic モデルで型を定義する。
- ファイル/ディレクトリ操作は `pathlib.Path` を使う。
- ログ出力は `from src.bridge_agentic_generate.logger_config import get_logger` を用い、`print` 禁止。
- `try: ... except: pass` のような例外の握りつぶしは禁止。
- フォーマット & Lint: `make fmt` / `make fix` / `make lint`（Ruff）。
