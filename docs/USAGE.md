# USAGE

## セットアップ

Python 3.13 + uv を利用。

```bash
uv python install 3.13
uv venv .venv --python 3.13
. .venv/bin/activate  # Windows は .venv\Scripts\activate
uv sync

# OpenAI API Key を .env に置く
echo "OPENAI_API_KEY=sk-xxxxxxxx" > .env
```

## RAG インデックスの準備

1. `src/bridge_agentic_generate/rag/embedding_config.py` の `FileNamesUsedForRag` にある PDF を `data/design_knowledge/` に配置。
   - 鋼橋設計の基本\_第一章 概論.pdf
   - 鋼橋設計の基本\_第四章 鋼橋の設計法.pdf
   - 鋼橋設計の基本\_第六章 床版.pdf
   - 鋼橋設計の基本\_第七章 プレートガーダー橋.pdf
   - 道路橋示方書\_鋼橋・鋼部材編.pdf
2. PDF → テキスト抽出（pdfplumber 推奨）。

   ```bash
   # 推奨
   uv run python -m src.bridge_agentic_generate.rag.extract_pdfs_with_pdfplumber

   # 代替
   uv run python -m src.bridge_agentic_generate.rag.extract_pdfs_with_pypdf
   uv run python -m src.bridge_agentic_generate.rag.extract_pdfs_with_pymupdf4llm
   ```

   出力は `data/extracted_by_*/*.txt|.md`。

3. チャンク化 & 埋め込み生成（デフォルトは pdfplumber の抽出物を使用）。

   ```bash
   uv run python -m src.bridge_agentic_generate.rag.loader
   ```

   `rag_index/pdfplumber/meta.jsonl` と `embeddings.npy` が生成され、`rag.search.search_text()` が利用する。

## 生成・評価・IFC 出力

- Designer 単体（既定: L=50m, B=10m, GPT-5-mini, top_k=5）。

  ```bash
  uv run python -m src.bridge_agentic_generate.main
  ```

  出力: `data/generated_simple_bridge_json/design_L{L}_B{B*10:02d}_{timestamp}.json` と
  `data/generated_bridge_raglog_json/*_raglog.json`。

- JSON 生成だけ行う CLI（Fire）。戻り値は生成ファイルパス。

  ```bash
  uv run python -m src.main generate \
    --bridge_length_m 60 \
    --total_width_m 11 \
    --model_name gpt-5-mini \
    --top_k 5 \
    --judge_enabled false
  ```

- 生成 → IFC まで一括実行。

  ```bash
  uv run python -m src.main run \
    --bridge_length_m 50 \
    --total_width_m 10 \
    --model_name gpt-5-mini \
    --ifc_output_path data/generated_ifc/sample.ifc
  ```

  - Designer の出力を詳細 JSON に変換 (`data/generated_detailed_bridge_json/…_detailed.json`)。
  - ifcopenshell を用いて IFC を出力。

- 既存の BridgeDesign JSON を IFC 変換だけ行う。

  ```bash
  uv run python -m src.bridge_json_to_ifc.run_convert data/generated_simple_bridge_json/<file>.json
  ```
