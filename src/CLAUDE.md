# src/ - CLAUDE.md

## 概要

鋼プレートガーダー橋BrIM生成エージェントのソースコード。
RAG + OpenAI API で橋梁設計JSONを生成し、IFCに変換する。

## 技術スタック

- **言語**: Python 3.13
- **パッケージ管理**: uv
- **CLI**: fire
- **LLM**: OpenAI API (Responses API / Structured Output)
- **バリデーション**: Pydantic
- **埋め込み**: sentence-transformers
- **PDF抽出**: pdfplumber / pypdf / pymupdf4llm
- **IFC出力**: ifcopenshell
- **フォーマット/Lint**: Ruff

## ディレクトリ構成

```
src/
├── main.py                         # 統合CLI（Designer→IFC）
├── bridge_agentic_generate/        # LLM橋梁設計生成
│   ├── main.py                     # Designer + Judge 実行
│   ├── config.py                   # パス定義
│   ├── llm_client.py               # Responses API ラッパー
│   ├── logger_config.py            # 共通ロガー
│   ├── designer/                   # 設計生成エージェント
│   │   ├── models.py               # BridgeDesign等のPydanticモデル
│   │   ├── prompts.py              # LLMプロンプト
│   │   └── services.py             # 生成ロジック
│   ├── judge/                      # 設計評価（現状ダミー）
│   │   ├── models.py               # 評価モデル
│   │   ├── prompts.py              # 評価プロンプト
│   │   └── services.py             # 評価ロジック
│   ├── rag/                        # RAG（検索拡張生成）
│   │   ├── embedding_config.py     # FileNamesUsedForRag定義
│   │   ├── loader.py               # チャンク化・埋め込み生成
│   │   ├── search.py               # ベクトル検索（search_text）
│   │   └── extract_pdfs_with_*.py  # PDF抽出スクリプト
│   └── extractor/                  # 設計制約抽出（計画中）
└── bridge_json_to_ifc/             # JSON→IFC変換
    ├── run_convert.py              # 変換CLI
    ├── convert_simple_to_detailed_json.py  # BridgeDesign→詳細JSON
    ├── convert_detailed_json_to_ifc.py     # 詳細JSON→IFC
    ├── models.py                   # 詳細JSONのPydanticモデル
    └── ifc_utils/                  # IFC生成ユーティリティ
        ├── DefIFC.py               # IFC要素定義
        └── DefMath.py              # 数学ユーティリティ
```

## 主要モジュール

### bridge_agentic_generate/

LLMを使った橋梁設計生成エージェント。

#### designer/
橋長L・幅員Bを受け取り、RAG文脈を踏まえたBridgeDesign（構造化JSON）を生成。

```python
# 使用例
from src.bridge_agentic_generate.designer.services import generate_design

result = generate_design(
    bridge_length_m=50,
    total_width_m=10,
    model_name="gpt-5-mini",
    top_k=5
)
```

#### rag/
道路橋示方書等のPDFをテキスト化・埋め込みし、設計時に参照する条文チャンクを検索。

```python
# 使用例
from src.bridge_agentic_generate.rag.search import search_text

results = search_text(query="主桁の最小板厚", top_k=5)
```

**対象PDF**（`embedding_config.py` の `FileNamesUsedForRag`）:
- 鋼橋設計の基本_第一章 概論.pdf
- 鋼橋設計の基本_第四章 鋼橋の設計法.pdf
- 鋼橋設計の基本_第六章 床版.pdf
- 鋼橋設計の基本_第七章 プレートガーダー橋.pdf
- 道路橋示方書_鋼橋・鋼部材編.pdf

#### judge/
道路橋示方書に基づき設計結果を評価する予定（現状はダミー実装）。

### bridge_json_to_ifc/

BridgeDesign JSONをIFCに変換するモジュール。

```python
# 使用例
from src.bridge_json_to_ifc.run_convert import convert_json_to_ifc

convert_json_to_ifc(
    input_path="data/generated_simple_bridge_json/design.json",
    output_path="data/generated_ifc/output.ifc"
)
```

## コマンド

```bash
# フォーマット
make fmt

# Lint + 自動修正 + フォーマット
make fix

# Lint のみ（CI相当）
make lint

# Designer 実行
uv run python -m src.bridge_agentic_generate.main

# 統合CLI（Designer→IFC）
uv run python -m src.main run \
  --bridge_length_m 50 \
  --total_width_m 10 \
  --model_name gpt-5-mini \
  --ifc_output_path data/generated_ifc/sample.ifc
```

## コーディング規約

詳細は `/.claude/agents/designer-impl.md` を参照。主要なルール：

### 命名規則
- **変数・関数**: snake_case
- **クラス**: PascalCase
- **定数**: UPPER_SNAKE_CASE

### 型アノテーション
- すべての関数に型アノテーション必須
- `Any` 型は避ける
- Union型は `X | Y` 形式（PEP 604）
- 組み込みジェネリクス使用（PEP 585）

### Docstring
- Google スタイル
- 日本語で記述

### Pydantic
- 返り値に `dict` / `tuple` は使わず、Pydantic モデルで型を定義
- 文字列ハードコーディングは `StrEnum` や Pydantic モデルで管理

### ロギング
```python
from src.bridge_agentic_generate.logger_config import logger
logger.info("message")
```
- `print` 禁止

### コード品質
- 未使用コード・コメントアウトは削除
- 後方互換性の残骸を残さない
- 1関数1責務
- `try: ... except: pass` 禁止

## 注意事項

- LLMを使う処理のテストでは必ずモックを使用
- 環境変数は `.env` で管理（コミットしない）
- CLI引数管理には `fire` を使用
- ファイル/ディレクトリ操作は `pathlib.Path`
