# AgenticGenBrim - CLAUDE.md

このファイルは Claude Code がプロジェクトを理解するためのコンテキストを提供します。

## プロジェクト概要

**鋼プレートガーダー橋 BrIM 生成エージェント**

鋼プレートガーダー橋（RC 床版）の断面モデルを RAG + OpenAI API で生成し、IFC まで出力するエージェント型 MVP。

## リポジトリ構成

```
AgenticGenBrim/
├── src/                              # ソースコード
│   ├── main.py                       # 統合CLI（Fire）
│   ├── bridge_agentic_generate/      # LLM橋梁設計生成
│   │   ├── designer/                 # 設計生成エージェント
│   │   ├── judge/                    # 設計評価（現状ダミー）
│   │   ├── rag/                      # RAG（検索拡張生成）
│   │   └── extractor/                # 設計制約抽出（計画中）
│   └── bridge_json_to_ifc/           # JSON→IFC変換
├── data/                             # データ（.gitignore）
│   ├── design_knowledge/             # 元PDF
│   ├── extracted_by_*/               # 抽出テキスト
│   ├── generated_simple_bridge_json/ # Designer出力
│   ├── generated_detailed_bridge_json/ # 詳細JSON
│   └── generated_ifc/                # IFC出力
├── rag_index/                        # RAGインデックス（.gitignore）
├── docs/                             # ドキュメント
├── backlog/                          # プロジェクト仕様
├── tasks/                            # タスクテンプレート
├── .claude/                          # Claude Code 設定
│   └── agents/                       # カスタムエージェント
└── Makefile                          # 開発コマンド
```

## 主要機能

1. **RAG**: 道路橋示方書等の PDF をテキスト化・埋め込みし、設計時に参照する条文チャンクを検索
2. **Designer**: 橋長 L・幅員 B を受け取り、RAG 文脈を踏まえた BridgeDesign（構造化 JSON）を生成
3. **Judge**: 道路橋示方書に基づき設計結果を評価（現状ダミー）
4. **Extractor**: RAG で得た条文を元に設計制約を構造化抽出（計画中）
5. **IFC Export**: BridgeDesign → 詳細 JSON → IFC に変換し BrIM 環境に渡す

## 技術スタック

- **言語**: Python 3.13
- **パッケージ管理**: uv
- **CLI**: fire
- **LLM**: OpenAI API (Responses API / Structured Output)
- **バリデーション**: Pydantic
- **IFC 出力**: ifcopenshell
- **フォーマット/Lint**: Ruff

詳細: `src/CLAUDE.md` 参照

## カスタムエージェント

| エージェント    | 用途                     |
| --------------- | ------------------------ |
| `designer-impl` | Designer/RAG 関連の実装  |
| `ifc-impl`      | IFC 変換関連の実装       |
| `quality-check` | コードレビュー・品質検証 |

詳細な規約は `.claude/agents/` 内の各ファイルを参照。

## 開発フロー

### コード変更時

```bash
make fmt          # フォーマット
make lint         # Lint（CI相当）
make fix          # Lint + 自動修正 + フォーマット
```

### 設計生成（Designer）

```bash
# Designer 単体実行
uv run python -m src.bridge_agentic_generate.main

# JSON生成のみ
uv run python -m src.main generate \
  --bridge_length_m 60 \
  --total_width_m 11 \
  --model_name gpt-5-mini

# 生成 → IFC まで一括
uv run python -m src.main run \
  --bridge_length_m 50 \
  --total_width_m 10 \
  --model_name gpt-5-mini \
  --ifc_output_path data/generated_ifc/sample.ifc
```

### RAG インデックス準備

```bash
# 1. PDF を data/design_knowledge/ に配置
# 2. テキスト抽出
uv run python -m src.bridge_agentic_generate.rag.extract_pdfs_with_pdfplumber

# 3. チャンク化・埋め込み生成
uv run python -m src.bridge_agentic_generate.rag.loader
```

### IFC 変換のみ

```bash
uv run python -m src.bridge_json_to_ifc.run_convert data/generated_simple_bridge_json/<file>.json
```

## タスクテンプレート

`tasks/template.md` にタスク依頼用のテンプレートがあります。

### 使い方

1. テンプレートをコピーしてタスクファイルを作成
   ```bash
   cp tasks/template.md tasks/[タスク名].md
   ```
2. 要件・対象ディレクトリ・受け入れ条件を記入
3. Claude Code に渡す
   ```bash
   claude "tasks/[タスク名].md を読んで実装して"
   ```

## コーディング規約

### 命名規則

- **変数・関数**: snake_case
- **クラス**: PascalCase
- **定数**: UPPER_SNAKE_CASE

### 型アノテーション

- すべての関数に型アノテーション必須
- Union 型は `X | Y` 形式（PEP 604）
- 組み込みジェネリクス使用（PEP 585）

### Pydantic

- 返り値に `dict` / `tuple` は使わず、Pydantic モデルで型を定義
- 文字列ハードコーディングは `StrEnum` や Pydantic モデルで管理
- `.value` は極力使わない

### ロギング

```python
from src.bridge_agentic_generate.logger_config import logger
logger.info("message")
```

- `print` 禁止

### その他

- CLI の引数管理には `fire` を使用
- マジックナンバーを避け、定数化
- ファイル/ディレクトリ操作は `pathlib.Path`
- Google スタイル Docstring
- `try: ... except: pass` 禁止
- 未使用コード・コメントアウトは削除

## 注意事項

- 環境変数は `.env` ファイルで管理（コミットしない）
- `data/` と `rag_index/` は `.gitignore` に含まれる
- LLM を使う処理のテストではモックを使用
- `git add/commit` は自動実行しない（コミットメッセージの提案のみ）

## ドキュメント

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - ディレクトリ構成・コンポーネント概要
- [docs/USAGE.md](docs/USAGE.md) - セットアップ・実行方法
- [docs/DEV_GUIDE.md](docs/DEV_GUIDE.md) - 開発メモ
- [docs/COMPONENT_DESIGNER.md](docs/COMPONENT_DESIGNER.md) - Designer 詳細
- [docs/COMPONENT_EXTRACTOR.md](docs/COMPONENT_EXTRACTOR.md) - Extractor 詳細
