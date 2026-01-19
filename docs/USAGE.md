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

### Designer / Judge CLI

```bash
# Designer のみ（Judge なし）
uv run python -m src.bridge_agentic_generate.main run \
  --bridge_length_m 50 \
  --total_width_m 10

# Designer + Judge（1回照査のみ）
uv run python -m src.bridge_agentic_generate.main run \
  --bridge_length_m 50 \
  --total_width_m 10 \
  --judge

# Designer + Judge + 修正ループ（合格するまで繰り返し）
uv run python -m src.bridge_agentic_generate.main run_with_repair \
  --bridge_length_m 50 \
  --total_width_m 10 \
  --max_iterations 5

# バッチ実行（L=30,40,50,60,70m）
uv run python -m src.bridge_agentic_generate.main batch
```

出力:
- `data/generated_simple_bridge_json/design_L{L}_B{B}_{timestamp}.json`
- `data/generated_bridge_raglog_json/*_design_log.json`

### 生成 → IFC 一括実行

```bash
uv run python -m src.main run \
  --bridge_length_m 50 \
  --total_width_m 10 \
  --model_name gpt-5-mini \
  --ifc_output_path data/generated_ifc/sample.ifc
```

- Designer の出力を詳細 JSON に変換 (`data/generated_detailed_bridge_json/…_detailed.json`)。
- ifcopenshell を用いて IFC を出力。

### 既存 JSON を IFC 変換のみ

```bash
uv run python -m src.bridge_json_to_ifc.run_convert data/generated_simple_bridge_json/<file>.json
```
