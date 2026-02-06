# ARCHITECTURE

## Directory Structure

```text
data/
  design_knowledge/               # Source PDF storage location
  extracted_by_pdfplumber/        # Text extracted with pdfplumber
  extracted_by_pypdf/             # Text extracted with pypdf
  extracted_by_pymupdf4llm/       # Text extracted with pymupdf4llm
  generated_simple_bridge_json/   # Designer output JSON (BridgeDesign)
  generated_bridge_raglog_json/   # RAG hit logs
  generated_judge_json/           # Judge output JSON (JudgeReport)
  generated_senkei_json/          # Senkei JSON for IFC conversion
  generated_report_md/            # Repair loop reports (Markdown)
  generated_ifc/                  # IFC output
rag_index/
  pdfplumber/{meta.jsonl,embeddings.npy}
  pymupdf/{meta.jsonl,embeddings.npy}
scripts/                          # Utility scripts
tests/                            # Tests
src/
  main.py                         # Integrated CLI for Designer to IFC (Fire)
  bridge_agentic_generate/
    main.py                       # Designer/Judge CLI (Fire)
    config.py                     # Path definitions (AppConfig)
    llm_client.py                 # Responses API / Structured Output wrapper
    logger_config.py              # Common logger
    designer/                     # Models, prompts, RAG-assisted generation
      models.py                   # Pydantic models (BridgeDesign, etc.)
      prompts.py                  # LLM prompt generation
      services.py                 # Generation logic
    judge/                        # Verification and repair suggestions (deterministic calculation + LLM)
      models.py                   # I/O models (JudgeReport, PatchPlan, etc.)
      prompts.py                  # PatchPlan generation prompts
      services.py                 # Verification calculations and repair application
      report.py                   # Repair loop report generation
    rag/                          # PDF extraction, chunking, embedding, search
      embedding_config.py         # Embedding configuration and index structure
      loader.py                   # Chunking and embedding generation
      search.py                   # Vector search
      extract_pdfs_with_*.py      # PDF extraction scripts (3 variants)
  bridge_json_to_ifc/
    run_convert.py                # Conversion CLI
    models.py                     # Detailed JSON schema (DetailedBridgeSpec)
    senkei_models.py              # Senkei JSON schema (SenkeiSpec)
    convert_simple_to_senkei_json.py    # BridgeDesign -> Senkei JSON
    convert_senkei_json_to_ifc.py       # Senkei JSON -> IFC
    ifc_utils/                    # Legacy IFC utilities
    ifc_utils_new/                # New IFC utilities (for Senkei)
      core/                       # DefBridge, DefIFC, DefMath, etc.
      components/                 # DefBracing, DefPanel, DefStiffener, etc.
      io/                         # DefExcel, DefJson, DefStrings
      utils/                      # DefBridgeUtils, logger
  evaluation/                     # Evaluation (metrics, plots)
    main.py                       # Evaluation CLI
    models.py                     # Evaluation models
    metrics.py                    # Metrics calculation
    plot.py                       # Graph rendering
    runner.py                     # Evaluation runner
```

## Component Overview

### RAG

Converts specified PDFs to text and generates embeddings, then searches for regulation text chunks to reference during design.

- **Target PDFs**: Fundamentals of Steel Bridge Design (Chapters 1, 4, 6, 7), Japan Road Bridge Specifications (JRA) -- Steel Bridge and Steel Member Edition
- **Embedding model**: text-embedding-3-small (OpenAI)
- **Multi-query search**: Parallel search across 5 aspects -- dimensions, main girder arrangement, main girder cross-section, deck slab, and cross beams

### Designer

Takes bridge length L and total width B as input and generates a BridgeDesign (structured JSON) informed by RAG context.

- **Input**: Bridge length L [m], total width B [m]
- **Output**: BridgeDesign (dimensions, sections, components)
- **LLM**: OpenAI Responses API + Structured Output

### Judge

Performs deterministic verification calculations (bending, shear, deflection, deck slab thickness, web slenderness ratio, cross beam arrangement) and generates a PatchPlan via LLM when the design fails.

- **Input**: JudgeInput (BridgeDesign + materials + parameters)
- **Live load**: Internally computed based on L-load (p1/p2 rules) (applicable for spans of 80 m or less)
- **Output**: JudgeReport (pass_fail, utilization, diagnostics, patch_plan, evaluated_candidates)
- **PatchPlan generation**: Multi-candidate approach (LLM generates 3 proposals, each is tentatively applied and evaluated, then the best proposal is selected)
- **Details**: See [COMPONENT_JUDGE.md](COMPONENT_JUDGE.md)

### Designer-Judge Loop

A repair loop (`run_with_repair_loop`) that applies a PatchPlan when verification fails, repeating until the design passes.

- **Max iterations**: Configurable (default: 5)
- **Output**: RepairLoopResult (converged, iterations, final_design, final_report)

### IFC Export

Converts BridgeDesign to Senkei JSON to IFC and delivers it to the BrIM environment.

- **Conversion pipeline**: BridgeDesign -> Senkei JSON -> IFC
- **Generated elements**: Deck slab (Brep), main girders (SweptSolid), cross beams (SweptSolid)
- **Library**: ifcopenshell

### Evaluation

Evaluates the convergence and design quality of the repair loop.

- **Metrics**: Convergence rate, number of iterations, final max_util, etc.
- **Plots**: Heatmaps, convergence graphs, etc.
- **Details**: See [EVALUATION.md](EVALUATION.md)

## Data Flow

```text
Input (bridge length L, total width B)
    |
    v
RAG search (multi-query across 5 aspects)
    |
    v
BridgeDesign generation via LLM
    |
    v
Judge (deterministic verification calculations)
    |
    v
Pass?
  +- Yes -> final_design
  +- No  -> PatchPlan generation via LLM
              |
              v
            Apply PatchPlan
              |
              v
            (repeat up to max iterations)
    |
    v
Save BridgeDesign JSON
    |
    v
Senkei JSON conversion -> IFC conversion
    |
    v
IFC file output
```
