# USAGE

## Setup

Uses Python 3.13 + uv.

```bash
uv python install 3.13
uv venv .venv --python 3.13
. .venv/bin/activate  # Windows: .venv\Scripts\activate
uv sync

# Place your OpenAI API Key in .env
echo "OPENAI_API_KEY=sk-xxxxxxxx" > .env
```

## Preparing the RAG Index

1. Place the PDFs listed in `FileNamesUsedForRag` in `src/bridge_agentic_generate/rag/embedding_config.py` into the `data/design_knowledge/` directory.
   - 鋼橋設計の基本\_第一章 概論.pdf
   - 鋼橋設計の基本\_第四章 鋼橋の設計法.pdf
   - 鋼橋設計の基本\_第六章 床版.pdf
   - 鋼橋設計の基本\_第七章 プレートガーダー橋.pdf
   - 道路橋示方書\_鋼橋・鋼部材編.pdf

2. Extract text from PDFs (pdfplumber recommended).

   ```bash
   # Recommended
   uv run python -m src.bridge_agentic_generate.rag.extract_pdfs_with_pdfplumber

   # Alternatives
   uv run python -m src.bridge_agentic_generate.rag.extract_pdfs_with_pypdf
   uv run python -m src.bridge_agentic_generate.rag.extract_pdfs_with_pymupdf4llm
   ```

   Output is saved to `data/extracted_by_*/*.txt|.md`.

3. Chunking & embedding generation (defaults to using pdfplumber-extracted text).

   ```bash
   uv run python -m src.bridge_agentic_generate.rag.loader
   ```

   This generates `rag_index/pdfplumber/meta.jsonl` and `embeddings.npy`, which are used by `rag.search.search_text()`.

## Generation, Evaluation, and IFC Output

### Designer / Judge CLI

```bash
# Designer only (without Judge)
uv run python -m src.bridge_agentic_generate.main run \
  --bridge_length_m 50 \
  --total_width_m 10

# Designer + Judge (single verification only)
uv run python -m src.bridge_agentic_generate.main run \
  --bridge_length_m 50 \
  --total_width_m 10 \
  --judge

# Batch execution (L=30,40,50,60,70m)
uv run python -m src.bridge_agentic_generate.main batch
```

Output:

- `data/generated_simple_bridge_json/design_L{L}_B{B}_{timestamp}.json` - Designer output
- `data/generated_bridge_raglog_json/*_design_log.json` - RAG hit log
- `data/generated_judge_json/*_judge.json` - Judge output (verification results)

### Generation to IFC (All-in-One Execution)

```bash
# Designer -> Judge -> IFC all-in-one execution
uv run python -m src.main run \
  --bridge_length_m 50 \
  --total_width_m 10 \
  --model_name gpt-5-mini \
  --ifc_output_path data/generated_ifc/sample.ifc

# Designer -> Judge -> Repair loop -> IFC (all intermediate results saved)
uv run python -m src.main run_with_repair \
  --bridge_length_m 50 \
  --total_width_m 10 \
  --max_iterations 5
```

Output:

- `data/generated_simple_bridge_json/…` - Designer output (each iteration + final)
- `data/generated_judge_json/…` - Judge output (each iteration)
- `data/generated_bridge_raglog_json/…` - RAG hit log
- `data/generated_senkei_json/….senkei.json` - Senkei JSON (each iteration + final)
- `data/generated_report_md/…_report.md` - Repair loop report (Markdown)
- `data/generated_ifc/….ifc` - IFC file (each iteration + final)

### Convert Existing JSON to IFC Only

```bash
uv run python -m src.bridge_json_to_ifc.run_convert data/generated_simple_bridge_json/<file>.json
```

Output:

- `data/generated_senkei_json/<file>.senkei.json` - Senkei JSON
- `data/generated_ifc/<file>.ifc` - IFC file

## CLI Options Reference

### src.main (Integrated CLI)

#### run Command

| Option              | Type   | Default     | Description                                     |
| ------------------- | ------ | ----------- | ----------------------------------------------- |
| `bridge_length_m`   | float  | 40.0        | Bridge length [m]                               |
| `total_width_m`     | float  | 10.0        | Total width [m]                                 |
| `model_name`        | str    | gpt-5-mini  | LLM model to use                                |
| `top_k`             | int    | 5           | Number of results to retrieve in RAG search     |
| `judge_enabled`     | bool   | True        | Whether to run Judge                            |
| `senkei_json_path`  | str    | None        | Senkei JSON output path (auto-generated if omitted) |
| `ifc_output_path`   | str    | None        | IFC output path (auto-generated if omitted)     |

#### run_with_repair Command

| Option             | Type   | Default     | Description                                     |
| ------------------ | ------ | ----------- | ----------------------------------------------- |
| `bridge_length_m`  | float  | 20.0        | Bridge length [m]                               |
| `total_width_m`    | float  | 5.0         | Total width [m]                                 |
| `model_name`       | str    | gpt-5.1     | LLM model to use                                |
| `top_k`            | int    | 5           | Number of results to retrieve in RAG search     |
| `max_iterations`   | int    | 5           | Maximum iterations for the repair loop          |

### src.bridge_agentic_generate.main (Designer/Judge CLI)

#### run Command

| Option             | Type     | Default     | Description                                     |
| ------------------ | -------- | ----------- | ----------------------------------------------- |
| `bridge_length_m`  | float    | 50.0        | Bridge length [m]                               |
| `total_width_m`    | float    | 10.0        | Total width [m]                                 |
| `model_name`       | LlmModel | gpt-5-mini  | LLM model to use                                |
| `top_k`            | int      | 5           | Number of results to retrieve in RAG search     |
| `judge`            | bool     | False       | Whether to run Judge                            |

#### batch Command

| Option             | Type     | Default     | Description                                     |
| ------------------ | -------- | ----------- | ----------------------------------------------- |
| `model_name`       | LlmModel | gpt-5-mini  | LLM model to use                                |
| `total_width_m`    | float    | 10.0        | Total width [m] (shared across all cases)       |
| `top_k`            | int      | 5           | Number of results to retrieve in RAG search     |

**Note:** For execution with the repair loop (`run_with_repair`), use the integrated CLI at `src.main`.
