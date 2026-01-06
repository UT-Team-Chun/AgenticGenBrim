# /impl

**ultrathink**
指定されたタスクに対して、適切なサブエージェントを選択して以下の順で実装してください。
2 のレビューで問題点があれば、1 に戻って修正を行います。すべてのレビューをクリアするまで、1 と 2 を繰り返します。

## エージェント思考モード

引数: $ARGUMENTS

もし引数に `--ultrathink` が含まれている場合は、各エージェントを呼び出す際に「ultrathinkモードで実行してください」と明示的に指示してください。
含まれていない場合は、通常モードで実行してください。

1. タスク要件に従い、機能実装を行う

- タスク内容に応じて適切なエージェントを選択する
  - Designer/RAG 関連: `designer-impl` エージェント
  - IFC 変換関連: `ifc-impl` エージェント
- プロジェクト内容を詳細に理解したうえで、要件に基づいて実装する
- `make fmt` でフォーマットを適用する
- `make lint` で Lint エラーがないことを確認する

2. 実装内容が要件に沿っているか確認する

- 必ず `quality-check` エージェントを使用して確認する
- 実装要件に抜け漏れがないか、バグやセキュリティリスクなど潜在的な問題がないか、徹底的にレビューする

## 技術スタック

- Python 3.13 / uv
- OpenAI API (Responses API / Structured Output)
- Pydantic / StrEnum
- ifcopenshell (IFC出力)
- sentence-transformers (埋め込み)
- pdfplumber / pypdf / pymupdf4llm (PDF抽出)
- fire (CLI)
- Ruff (Lint/Format)
