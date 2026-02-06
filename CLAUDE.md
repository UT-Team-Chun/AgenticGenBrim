# AgenticGenBrim - CLAUDE.md

This file provides context for Claude Code to understand the project.

## Project Overview

**Steel Plate Girder Bridge BrIM Generation Agent**

An agent-based MVP that generates cross-section models of Steel Plate Girder Bridges (RC Deck Slab) using RAG + OpenAI API and outputs them as IFC.

## Repository Structure

```
AgenticGenBrim/
├── src/                              # Source code
│   ├── main.py                       # Unified CLI (Fire)
│   ├── bridge_agentic_generate/      # LLM bridge design generation
│   │   ├── main.py                   # Designer/Judge CLI
│   │   ├── designer/                 # Design generation agent
│   │   ├── judge/                    # Verification & fix proposals (deterministic calculation + LLM)
│   │   └── rag/                      # RAG (Retrieval-Augmented Generation)
│   ├── bridge_json_to_ifc/           # JSON to IFC conversion
│   └── evaluation/                   # Evaluation (metrics, plots)
├── scripts/                          # Utility scripts
├── tests/                            # Tests
├── data/                             # Data (.gitignore)
│   ├── design_knowledge/             # Source PDFs
│   ├── extracted_by_*/               # Extracted text
│   ├── generated_simple_bridge_json/ # Designer output
│   ├── generated_bridge_raglog_json/ # RAG hit logs
│   ├── generated_judge_json/         # Judge output
│   ├── generated_senkei_json/        # Senkei JSON (intermediate format for IFC conversion)
│   ├── generated_report_md/          # Repair loop reports
│   └── generated_ifc/               # IFC output
├── rag_index/                        # RAG index (.gitignore)
├── docs/                             # Documentation
├── tasks/                            # Task templates
├── .claude/                          # Claude Code settings
│   ├── commands/                     # Custom commands
│   └── agents/                       # Custom agents
└── Makefile                          # Development commands
```

## Key Features

1. **RAG**: Converts PDFs such as Japan Road Bridge Specifications (JRA) to text, generates embeddings, and searches for relevant specification chunks during design
2. **Designer**: Receives bridge length L and total width B, and generates a BridgeDesign (structured JSON) based on RAG context
3. **Judge**: Performs deterministic verification calculations (bending, shear, deflection, deck slab thickness, web slenderness ratio, cross beam placement) and generates a PatchPlan via LLM when verification fails
4. **Designer-Judge Loop**: A repair loop that applies PatchPlan on failure and repeats until all verifications pass
5. **IFC Export**: Converts BridgeDesign to Senkei JSON to IFC and passes it to the BrIM environment

## Tech Stack

- **Language**: Python 3.13
- **Package management**: uv
- **CLI**: fire
- **LLM**: OpenAI API (Responses API / Structured Output)
- **Validation**: Pydantic
- **IFC output**: ifcopenshell
- **Formatting/Lint**: Ruff

Details: See `src/CLAUDE.md`

## Custom commands

### /impl [task description]

A command that performs feature implementation and automatically runs a review.

```bash
# Usage example
/impl RAG検索の精度を改善
```

**Execution steps:**
1. Implements using the `designer-impl` or `ifc-impl` agent depending on the task
2. Validates with `make fmt && make lint`
3. Reviews with the `quality-check` agent
4. Repeats fixes if issues are found

## Custom agents

| Agent           | Purpose                              |
| --------------- | ------------------------------------ |
| `designer-impl` | Designer/RAG related implementation  |
| `ifc-impl`      | IFC conversion related implementation |
| `quality-check` | Code review and quality verification |

See the individual files in `.claude/agents/` for detailed conventions.

## Development workflow

### When changing code

```bash
make fmt          # Format
make lint         # Lint (CI equivalent)
make fix          # Lint + auto-fix + format
```

### Design generation (Designer / Judge)

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

# Generation through IFC in one step
uv run python -m src.main run \
  --bridge_length_m 50 \
  --total_width_m 10 \
  --model_name gpt-5-mini \
  --ifc_output_path data/generated_ifc/sample.ifc

# With repair loop (repeat until pass, then IFC)
uv run python -m src.main run_with_repair \
  --bridge_length_m 50 \
  --total_width_m 10 \
  --max_iterations 5
```

### RAG Index Preparation

```bash
# 1. Place PDFs in data/design_knowledge/
# 2. Extract text
uv run python -m src.bridge_agentic_generate.rag.extract_pdfs_with_pdfplumber

# 3. Chunk and generate embeddings
uv run python -m src.bridge_agentic_generate.rag.loader
```

### IFC Conversion Only

```bash
uv run python -m src.bridge_json_to_ifc.run_convert data/generated_simple_bridge_json/<file>.json
```

## Task templates

There is a task request template at `tasks/template.md`.

### How to use

1. Copy the template to create a task file
   ```bash
   cp tasks/template.md tasks/[task-name].md
   ```
2. Fill in the requirements, target directories, and acceptance criteria
3. Pass it to Claude Code
   ```bash
   claude "tasks/[task-name].md を読んで実装して"
   ```

## Coding conventions

### Naming conventions

- **Variables and functions**: snake_case
- **Classes**: PascalCase
- **Constants**: UPPER_SNAKE_CASE

### Type annotations

- Type annotations are required for all functions
- Use `X | Y` format for Union types (PEP 604)
- Use built-in generics (PEP 585)

### Pydantic

- Do not use `dict` / `tuple` as return types; define types with Pydantic models
- Manage hardcoded strings with `StrEnum` or Pydantic models
- Avoid using `.value` whenever possible

### Logging

```python
from src.bridge_agentic_generate.logger_config import logger
logger.info("message")
```

- `print` is prohibited

### Other

- Use `fire` for CLI argument management
- Avoid magic numbers; use constants instead
- Use `pathlib.Path` for file/directory operations
- Google-style Docstrings
- `try: ... except: pass` is prohibited
- Remove unused code and commented-out code

## Notes

- Environment variables are managed via `.env` files (do not commit)
- `data/` and `rag_index/` are included in `.gitignore`
- Use mocks for tests that involve LLM calls
- Do not automatically run `git add/commit` (only suggest commit messages)

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - Directory structure and component overview
- [docs/USAGE.md](docs/USAGE.md) - Setup and usage instructions
- [docs/DEV_GUIDE.md](docs/DEV_GUIDE.md) - Development notes
- [docs/COMPONENT_DESIGNER.md](docs/COMPONENT_DESIGNER.md) - Designer details
- [docs/COMPONENT_JUDGE.md](docs/COMPONENT_JUDGE.md) - Judge details
- [docs/EVALUATION.md](docs/EVALUATION.md) - Evaluation methods
- [docs/json_spec.md](docs/json_spec.md) - Senkei JSON specification
