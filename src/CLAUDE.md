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
- **埋め込み**: text-embedding-3-small（OpenAI）
- **PDF抽出**: pdfplumber / pypdf / pymupdf4llm
- **IFC出力**: ifcopenshell
- **フォーマット/Lint**: Ruff

## ディレクトリ構成

```
src/
├── main.py                         # 統合CLI（Designer→IFC）
├── bridge_agentic_generate/        # LLM橋梁設計生成
│   ├── main.py                     # Designer/Judge CLI（Fire）
│   ├── config.py                   # パス定義
│   ├── llm_client.py               # Responses API ラッパー
│   ├── logger_config.py            # 共通ロガー
│   ├── designer/                   # 設計生成エージェント
│   │   ├── models.py               # BridgeDesign等のPydanticモデル
│   │   ├── prompts.py              # LLMプロンプト
│   │   └── services.py             # 生成ロジック
│   ├── judge/                      # 照査・修正提案
│   │   ├── models.py               # JudgeInput/JudgeReport/PatchPlan等
│   │   ├── prompts.py              # PatchPlan生成プロンプト
│   │   ├── services.py             # 照査計算・apply_patch_plan
│   │   └── report.py               # 修正ループレポート生成
│   ├── rag/                        # RAG（検索拡張生成）
│   │   ├── embedding_config.py     # FileNamesUsedForRag定義
│   │   ├── loader.py               # チャンク化・埋め込み生成
│   │   ├── search.py               # ベクトル検索（search_text）
│   │   └── extract_pdfs_with_*.py  # PDF抽出スクリプト
└── bridge_json_to_ifc/             # JSON→IFC変換
    ├── run_convert.py              # 変換CLI
    ├── models.py                   # 詳細JSONのPydanticモデル（DetailedBridgeSpec）
    ├── senkei_models.py            # Senkei JSONのPydanticモデル（SenkeiSpec）
    ├── convert_simple_to_detailed_json.py  # BridgeDesign→詳細JSON（旧方式）
    ├── convert_simple_to_senkei_json.py    # BridgeDesign→Senkei JSON（推奨）
    ├── convert_detailed_json_to_ifc.py     # 詳細JSON→IFC（旧方式）
    ├── convert_senkei_json_to_ifc.py       # Senkei JSON→IFC（推奨）
    ├── ifc_utils/                  # 旧IFC生成ユーティリティ
    │   ├── DefIFC.py               # IFC要素定義
    │   └── DefMath.py              # 数学ユーティリティ
    └── ifc_utils_new/              # 新IFC生成ユーティリティ（Senkei用）
        ├── core/                   # DefBridge, DefIFC, DefMath等
        ├── components/             # DefBracing, DefPanel, DefStiffener等
        ├── io/                     # DefExcel, DefJson, DefStrings
        └── utils/                  # DefBridgeUtils, logger
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
決定論的な照査計算（曲げ・せん断・たわみ・床版厚・腹板幅厚比・横桁配置）を行い、不合格時は LLM で PatchPlan を生成。
活荷重は L荷重（p1/p2ルール）に基づいて内部計算される（支間80m以下が適用範囲）。

```python
# 使用例
from src.bridge_agentic_generate.judge.services import judge_v1, apply_patch_plan
from src.bridge_agentic_generate.judge.models import JudgeInput
from src.bridge_agentic_generate.llm_client import LlmModel

judge_input = JudgeInput(bridge_design=design)
report = judge_v1(judge_input, model=LlmModel.GPT_5_MINI)

if not report.pass_fail:
    # PatchPlan を適用して再照査
    new_design = apply_patch_plan(
        design=design,
        patch_plan=report.patch_plan,
        deck_thickness_required=report.diagnostics.deck_thickness_required,
    )
```

**照査項目:**
- 曲げ応力度 util（sigma / sigma_allow）
- せん断応力度 util（tau / tau_allow）
- たわみ util（delta / delta_allow）
- 床版厚 util（required / provided）
- 腹板幅厚比 util（web_thickness_min_required / web_thickness）
- 横桁配置チェック（panel_length * num_panels == bridge_length）

**PatchPlan 生成:**
- 複数候補方式: LLM が3案を生成し、各案を仮適用・評価して最良案を選択

### bridge_json_to_ifc/

BridgeDesign JSONをIFCに変換するモジュール。

```python
# 使用例
from src.bridge_json_to_ifc.run_convert import convert

# BridgeDesign JSON → Senkei JSON → IFC
convert(
    design_json_path="data/generated_simple_bridge_json/design.json",
    senkei_json_path="data/generated_senkei_json/design.senkei.json",
    ifc_path="data/generated_ifc/design.ifc",
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

# Designer のみ（Judge なし）
uv run python -m src.bridge_agentic_generate.main run \
  --bridge_length_m 50 \
  --total_width_m 10

# Designer + Judge（1回照査のみ）
uv run python -m src.bridge_agentic_generate.main run \
  --bridge_length_m 50 \
  --total_width_m 10 \
  --judge

# バッチ実行（L=30,40,50,60,70m）
uv run python -m src.bridge_agentic_generate.main batch

# 統合CLI（Designer→Judge→IFC）
uv run python -m src.main run \
  --bridge_length_m 50 \
  --total_width_m 10 \
  --model_name gpt-5-mini \
  --ifc_output_path data/generated_ifc/sample.ifc

# 統合CLI（Designer→Judge→修正ループ→IFC）
uv run python -m src.main run_with_repair \
  --bridge_length_m 50 \
  --total_width_m 10 \
  --max_iterations 5
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
