# src/ - CLAUDE.md

## Overview

Source code for the Steel Plate Girder Bridge BrIM generation agent.
Generates bridge design JSON using RAG + OpenAI API and converts it to IFC.

## Tech Stack

- **Language**: Python 3.13
- **Package Management**: uv
- **CLI**: fire
- **LLM**: OpenAI API (Responses API / Structured Output)
- **Validation**: Pydantic
- **Embedding**: text-embedding-3-small (OpenAI)
- **PDF Extraction**: pdfplumber / pypdf / pymupdf4llm
- **IFC Output**: ifcopenshell
- **Formatting/Lint**: Ruff

## Directory Structure

```
src/
├── main.py                         # Unified CLI (Designer→IFC)
├── bridge_agentic_generate/        # LLM bridge design generation
│   ├── main.py                     # Designer/Judge CLI (Fire)
│   ├── config.py                   # Path definitions
│   ├── llm_client.py               # Responses API wrapper
│   ├── logger_config.py            # Common logger
│   ├── designer/                   # Design generation agent
│   │   ├── models.py               # Pydantic models such as BridgeDesign
│   │   ├── prompts.py              # LLM prompts
│   │   └── services.py             # Generation logic
│   ├── judge/                      # Verification & repair suggestions
│   │   ├── models.py               # JudgeInput/JudgeReport/PatchPlan etc.
│   │   ├── prompts.py              # PatchPlan generation prompts
│   │   ├── services.py             # Verification calculations & apply_patch_plan
│   │   └── report.py               # Repair loop report generation
│   ├── rag/                        # RAG (Retrieval-Augmented Generation)
│   │   ├── embedding_config.py     # FileNamesUsedForRag definition
│   │   ├── loader.py               # Chunking & embedding generation
│   │   ├── search.py               # Vector search (search_text)
│   │   └── extract_pdfs_with_*.py  # PDF extraction scripts
└── bridge_json_to_ifc/             # JSON→IFC conversion
    ├── run_convert.py              # Conversion CLI
    ├── models.py                   # Pydantic models for detailed JSON (DetailedBridgeSpec)
    ├── senkei_models.py            # Pydantic models for Senkei JSON (SenkeiSpec)
    ├── convert_simple_to_detailed_json.py  # BridgeDesign→Detailed JSON (legacy)
    ├── convert_simple_to_senkei_json.py    # BridgeDesign→Senkei JSON (recommended)
    ├── convert_detailed_json_to_ifc.py     # Detailed JSON→IFC (legacy)
    ├── convert_senkei_json_to_ifc.py       # Senkei JSON→IFC (recommended)
    ├── ifc_utils/                  # Legacy IFC generation utilities
    │   ├── DefIFC.py               # IFC element definitions
    │   └── DefMath.py              # Math utilities
    └── ifc_utils_new/              # New IFC generation utilities (for Senkei)
        ├── core/                   # DefBridge, DefIFC, DefMath etc.
        ├── components/             # DefBracing, DefPanel, DefStiffener etc.
        ├── io/                     # DefExcel, DefJson, DefStrings
        └── utils/                  # DefBridgeUtils, logger
```

## Main Modules

### bridge_agentic_generate/

LLM-based bridge design generation agent.

#### designer/
Takes bridge length L and total width B as input, and generates a BridgeDesign (structured JSON) informed by RAG context.

```python
# Usage example
from src.bridge_agentic_generate.designer.services import generate_design

result = generate_design(
    bridge_length_m=50,
    total_width_m=10,
    model_name="gpt-5-mini",
    top_k=5
)
```

#### rag/
Extracts text from PDFs such as Japan Road Bridge Specifications (JRA), generates embeddings, and searches for regulation text chunks referenced during design.

```python
# Usage example
from src.bridge_agentic_generate.rag.search import search_text

results = search_text(query="主桁の最小板厚", top_k=5)
```

**Target PDFs** (defined in `FileNamesUsedForRag` in `embedding_config.py`):
- Fundamentals of Steel Bridge Design, Chapter 1: Introduction
- Fundamentals of Steel Bridge Design, Chapter 4: Steel Bridge Design Methods
- Fundamentals of Steel Bridge Design, Chapter 6: Deck Slab
- Fundamentals of Steel Bridge Design, Chapter 7: Plate Girder Bridge
- Japan Road Bridge Specifications: Steel Bridge and Steel Member Edition

#### judge/
Performs deterministic verification calculations (bending, shear, deflection, deck slab thickness, web slenderness ratio, cross beam arrangement), and generates a PatchPlan via LLM when verification fails.
Live loads are computed internally based on L-loading (p1/p2 rule) (applicable for spans up to 80m).

```python
# Usage example
from src.bridge_agentic_generate.judge.services import judge_v1, apply_patch_plan
from src.bridge_agentic_generate.judge.models import JudgeInput
from src.bridge_agentic_generate.llm_client import LlmModel

judge_input = JudgeInput(bridge_design=design)
report = judge_v1(judge_input, model=LlmModel.GPT_5_MINI)

if not report.pass_fail:
    # Apply PatchPlan and re-verify
    new_design = apply_patch_plan(
        design=design,
        patch_plan=report.patch_plan,
        deck_thickness_required=report.diagnostics.deck_thickness_required,
    )
```

**Verification Items:**
- Bending stress utilization (sigma / sigma_allow)
- Shear stress utilization (tau / tau_allow)
- Deflection utilization (delta / delta_allow)
- Deck slab thickness utilization (required / provided)
- Web slenderness ratio utilization (web_thickness_min_required / web_thickness)
- Cross beam arrangement check (panel_length * num_panels == bridge_length)

**PatchPlan Generation:**
- Multiple candidate approach: LLM generates 3 proposals, each is tentatively applied and evaluated, and the best one is selected

### bridge_json_to_ifc/

Module for converting BridgeDesign JSON to IFC.

```python
# Usage example
from src.bridge_json_to_ifc.run_convert import convert

# BridgeDesign JSON → Senkei JSON → IFC
convert(
    design_json_path="data/generated_simple_bridge_json/design.json",
    senkei_json_path="data/generated_senkei_json/design.senkei.json",
    ifc_path="data/generated_ifc/design.ifc",
)
```

## Commands

See [docs/USAGE.md](../docs/USAGE.md) for full CLI reference and [docs/DEV_GUIDE.md](../docs/DEV_GUIDE.md) for development commands (`make fmt`, `make lint`, `make fix`).

## Coding Conventions

See [docs/DEV_GUIDE.md](../docs/DEV_GUIDE.md) for the full coding conventions (naming, types, Pydantic, logging, prohibited practices, etc.).
