# AgenticGenBrim

鋼プレートガーダー橋（RC 床版）の断面モデルを RAG + OpenAI Responses API で生成し、IFC まで出力するエージェント型 MVP。

- RAG: 指定 PDF をテキスト化・埋め込みし、設計時に参照する条文チャンクを検索。
- Extractor (計画中): RAG で得た条文を元に設計制約を構造化抽出するエージェント。
- Designer: 橋長 L と幅員 B を受け取り、RAG 文脈を踏まえた BridgeDesign（構造化 JSON）を生成。
- Judge: 道路橋示方書に基づき設計結果を評価する予定（現状はダミー実装）。
- IFC Export: BridgeDesign → 詳細 JSON → IFC に変換して BrIM 環境に渡す。

## Quick Start

1. セットアップを実施（[docs/USAGE.md#セットアップ](docs/USAGE.md#セットアップ)）。
2. RAG インデックスを準備（[docs/USAGE.md#rag-インデックスの準備](docs/USAGE.md#rag-インデックスの準備)）。
3. サンプル橋の IFC を出力。

   ```bash
   uv run python -m src.main run \
     --bridge_length_m 50 \
     --total_width_m 10 \
     --model_name gpt-5-mini \
     --ifc_output_path data/generated_ifc/sample.ifc
   ```

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/USAGE.md](docs/USAGE.md)
- [docs/DEV_GUIDE.md](docs/DEV_GUIDE.md)
- [docs/COMPONENT_DESIGNER.md](docs/COMPONENT_DESIGNER.md)
- [docs/COMPONENT_EXTRACTOR.md](docs/COMPONENT_EXTRACTOR.md)
- [backlog/PROJECT_SPEC.md](backlog/PROJECT_SPEC.md)
