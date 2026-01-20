# AgenticGenBrim

鋼プレートガーダー橋（RC 床版）の断面モデルを RAG + OpenAI API で生成し、IFC まで出力するエージェント型システム。

## 概要

橋長と幅員の 2 パラメータを入力するだけで、道路橋示方書等の設計知識を参照しながら断面設計を自動生成し、照査・修正を経て IFC ファイルを出力します。

```
入力（橋長 L, 幅員 B）
    ↓
RAG 検索（設計知識から関連条文を取得）
    ↓
Designer（LLM で BridgeDesign 生成）
    ↓
Judge（決定論的照査 + 不合格時は修正提案）
    ↓
修正ループ（合格まで繰り返し）
    ↓
IFC 出力（BIM/CIM 連携）
```

## 主要機能

| コンポーネント | 説明 |
|----------------|------|
| **RAG** | 道路橋示方書・鋼橋設計の基本等の PDF をテキスト化・埋め込みし、設計時に参照する条文チャンクを検索 |
| **Designer** | 橋長 L と幅員 B を受け取り、RAG 文脈を踏まえた BridgeDesign（構造化 JSON）を生成 |
| **Judge** | 決定論的な照査計算（曲げ・せん断・たわみ・床版厚・横桁配置）を行い、不合格時は LLM で PatchPlan を生成 |
| **修正ループ** | 不合格時に PatchPlan を適用し、合格するまで Designer-Judge を繰り返す |
| **IFC Export** | BridgeDesign → Senkei JSON → IFC に変換して BIM/CIM 環境に渡す |
| **Extractor** | RAG で得た条文から設計制約を構造化抽出（計画中） |

## 技術スタック

- **言語**: Python 3.13
- **パッケージ管理**: uv
- **CLI**: fire
- **LLM**: OpenAI API（Responses API / Structured Output）
- **バリデーション**: Pydantic
- **IFC 出力**: ifcopenshell
- **埋め込み**: OpenAI text-embedding-3-small
- **フォーマット/Lint**: Ruff

## リポジトリ構成

```
AgenticGenBrim/
├── src/
│   ├── main.py                       # 統合CLI（Designer → Judge → IFC）
│   └── bridge_agentic_generate/
│       ├── main.py                   # Designer/Judge CLI
│       ├── designer/                 # 設計生成（models, prompts, services）
│       ├── judge/                    # 照査・修正提案（決定論計算 + LLM）
│       ├── rag/                      # RAG（PDF抽出, チャンク化, 検索）
│       └── extractor/                # 設計制約抽出（計画中）
│   └── bridge_json_to_ifc/           # JSON → IFC 変換
├── data/                             # データ（.gitignore）
│   ├── design_knowledge/             # 元 PDF
│   ├── generated_simple_bridge_json/ # Designer 出力
│   ├── generated_judge_json/         # Judge 出力
│   ├── generated_senkei_json/        # Senkei JSON（IFC 変換用）
│   └── generated_ifc/                # IFC 出力
├── rag_index/                        # RAG インデックス（.gitignore）
├── docs/                             # ドキュメント
└── Makefile                          # 開発コマンド
```

## Quick Start

### 1. セットアップ

```bash
uv python install 3.13
uv venv .venv --python 3.13
. .venv/bin/activate
uv sync

# OpenAI API Key を設定
echo "OPENAI_API_KEY=sk-xxxxxxxx" > .env
```

### 2. RAG インデックスの準備

```bash
# PDF を data/design_knowledge/ に配置後
uv run python -m src.bridge_agentic_generate.rag.extract_pdfs_with_pdfplumber
uv run python -m src.bridge_agentic_generate.rag.loader
```

### 3. 設計生成 → IFC 出力

```bash
# Designer → Judge → IFC まで一括実行
uv run python -m src.main run \
  --bridge_length_m 50 \
  --total_width_m 10 \
  --ifc_output_path data/generated_ifc/sample.ifc

# 修正ループ付き（合格するまで繰り返し）
uv run python -m src.main run_with_repair \
  --bridge_length_m 50 \
  --total_width_m 10 \
  --max_iterations 5
```

## 主要コマンド

### Designer / Judge

```bash
# Designer のみ
uv run python -m src.bridge_agentic_generate.main run \
  --bridge_length_m 50 --total_width_m 10

# Designer + Judge（1回照査）
uv run python -m src.bridge_agentic_generate.main run \
  --bridge_length_m 50 --total_width_m 10 --judge

# Designer + Judge + 修正ループ
uv run python -m src.bridge_agentic_generate.main run_with_repair \
  --bridge_length_m 50 --total_width_m 10 --max_iterations 5
```

### IFC 変換のみ

```bash
uv run python -m src.bridge_json_to_ifc.run_convert \
  data/generated_simple_bridge_json/<file>.json
```

### 開発

```bash
make fmt   # フォーマット
make lint  # Lint
make fix   # Lint + 自動修正 + フォーマット
```

## 出力スキーマ

### BridgeDesign（Designer 出力）

```
BridgeDesign
├── dimensions
│   ├── bridge_length [mm]
│   ├── total_width [mm]
│   ├── num_girders
│   ├── girder_spacing [mm]
│   └── panel_length [mm]
├── sections
│   ├── girder_standard（I形: web_height, web_thickness, flange等）
│   └── crossbeam_standard（I形）
└── components
    └── deck.thickness [mm]
```

### JudgeReport（Judge 出力）

```
JudgeReport
├── pass_fail: bool
├── utilization（deck, bend, shear, deflection, max_util, governing_check）
├── diagnostics（中間計算値）
└── patch_plan（修正提案: actions）
```

詳細は [docs/COMPONENT_JUDGE.md](docs/COMPONENT_JUDGE.md) を参照。

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - ディレクトリ構成・コンポーネント概要
- [docs/USAGE.md](docs/USAGE.md) - セットアップ・実行方法
- [docs/DEV_GUIDE.md](docs/DEV_GUIDE.md) - 開発規約
- [docs/COMPONENT_DESIGNER.md](docs/COMPONENT_DESIGNER.md) - Designer 詳細
- [docs/COMPONENT_JUDGE.md](docs/COMPONENT_JUDGE.md) - Judge 詳細
- [docs/COMPONENT_EXTRACTOR.md](docs/COMPONENT_EXTRACTOR.md) - Extractor 詳細（計画中）
- [docs/json_spec.md](docs/json_spec.md) - Senkei JSON 仕様
