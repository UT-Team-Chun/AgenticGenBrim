# AgenticGenBrim

An agent-based system that generates cross-section models of Steel Plate Girder Bridges (RC Deck Slab) using RAG + OpenAI API and outputs IFC files.

## Overview

By simply inputting two parameters — bridge length and total width — the system automatically generates a cross-section design while referencing design knowledge from the Japan Road Bridge Specifications (JRA) and other sources, then outputs an IFC file after verification and repair.

```
Input (bridge length L, total width B)
    ↓
RAG Search (retrieve relevant clauses from design knowledge)
    ↓
Designer (generate BridgeDesign via LLM)
    ↓
Judge (deterministic verification + repair suggestions on failure)
    ↓
Repair Loop (repeat until pass)
    ↓
IFC Output (BIM/CIM integration)
```

## Key Features

| Component | Description |
|----------------|------|
| **RAG** | Extracts text and generates embeddings from PDFs such as the Japan Road Bridge Specifications (JRA) and Fundamentals of Steel Bridge Design, then searches for relevant clause chunks during design |
| **Designer** | Takes bridge length L and total width B as input, and generates a BridgeDesign (structured JSON) informed by RAG context |
| **Judge** | Performs deterministic verification calculations (bending, shear, deflection, deck slab thickness, web slenderness ratio, cross beam arrangement), and generates a PatchPlan via LLM when verification fails |
| **Repair Loop** | Applies the PatchPlan on failure and repeats the Designer-Judge cycle until pass |
| **IFC Export** | Converts BridgeDesign → Senkei JSON → IFC and passes it to the BIM/CIM environment |

## Tech Stack

- **Language**: Python 3.13
- **Package Management**: uv
- **CLI**: fire
- **LLM**: OpenAI API (Responses API / Structured Output)
- **Validation**: Pydantic
- **IFC Output**: ifcopenshell
- **Embeddings**: OpenAI text-embedding-3-small
- **Formatting/Lint**: Ruff

## Repository Structure

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full directory tree with file-level details.

## Quick Start

### 1. Setup

```bash
uv python install 3.13
uv venv .venv --python 3.13
. .venv/bin/activate
uv sync
# Place your OpenAI API Key in .env
echo "OPENAI_API_KEY=sk-xxxxxxxx" > .env
```


### 2. Prepare RAG Index

```bash
# After placing PDFs in data/design_knowledge/
uv run python -m src.bridge_agentic_generate.rag.extract_pdfs_with_pdfplumber
uv run python -m src.bridge_agentic_generate.rag.loader
```

### 3. Design Generation → IFC Output

```bash
# Run Designer → Judge → IFC all at once
uv run python -m src.main run \
  --bridge_length_m 50 \
  --total_width_m 10 \
  --ifc_output_path data/generated_ifc/sample.ifc

# With repair loop (repeat until pass)
uv run python -m src.main run_with_repair \
  --bridge_length_m 50 \
  --total_width_m 10 \
  --max_iterations 5
```

## Commands

For the full CLI reference (Designer, Judge, IFC, batch execution, options), see [docs/USAGE.md](docs/USAGE.md).

For development commands (`make fmt`, `make lint`, `make fix`), see [docs/DEV_GUIDE.md](docs/DEV_GUIDE.md).

## Developing with Claude Code

This project provides custom commands, agents, and task templates for use with Claude Code.

### Custom Commands

```bash
# /impl: Run implementation → fmt/lint → review all at once
/impl RAG検索の精度を改善
```

`/impl` automatically selects the appropriate agent based on the task content, and repeats the cycle of implementation → `make fmt && make lint` → `quality-check` review.

### Custom Agents

| Agent | Purpose | Target Directory |
|---|---|---|
| `designer-impl` | Designer/RAG/Judge implementation | `src/bridge_agentic_generate/` |
| `ifc-impl` | IFC conversion implementation | `src/bridge_json_to_ifc/` |
| `quality-check` | Code review & quality verification | Entire project |

### Task Templates

For routine task requests, you can use `tasks/template.md`.

```bash
# 1. Copy the template
cp tasks/template.md tasks/my-task.md

# 2. Fill in requirements, target directories, and acceptance criteria

# 3. Pass it to Claude Code
claude "tasks/my-task.md を読んで実装して"
```

### Configuration Files

| File | Contents |
|---|---|
| `CLAUDE.md` | Project overview, conventions, command reference |
| `src/CLAUDE.md` | Source code details, module descriptions |
| `.claude/commands/impl.md` | `/impl` command definition |
| `.claude/agents/*.md` | Custom agent definitions |

### How to Add Custom Commands and Agents

**Custom Commands** (slash commands invoked with `/xxx`):

```bash
# Create a Markdown file in .claude/commands/
# The filename becomes the command name (e.g., review.md → /review)
cat > .claude/commands/review.md << 'EOF'
# /review

指定されたファイルをレビューしてください。

引数: $ARGUMENTS
EOF
```

- Use `$ARGUMENTS` to receive command arguments
- Execute in Claude Code like `/review src/main.py`

**Custom Agents** (specialized AI invoked as sub-agents):

```bash
# Create a Markdown file in .claude/agents/
cat > .claude/agents/my-agent.md << 'EOF'
---
name: my-agent
description: このエージェントの説明（Task ツールの選択時に参照される）
model: opus
color: green
---

エージェントへの指示をここに記述。
対象ディレクトリ、コーディング規約、責務などを定義する。
EOF
```

- Specify `name`, `description`, `model`, and `color` in the YAML front matter
- `description` is referenced by the Task tool when selecting an agent
- Invoke from other commands or agents with instructions like "use the my-agent agent"

## Output Schemas

### BridgeDesign (Designer Output)

```
BridgeDesign
├── dimensions
│   ├── bridge_length [mm]
│   ├── total_width [mm]
│   ├── num_girders
│   ├── girder_spacing [mm]
│   ├── panel_length [mm]
│   └── num_panels
├── sections
│   ├── girder_standard (I-shape: web_height, web_thickness,
│   │     top/bottom_flange_width, top/bottom_flange_thickness)
│   └── crossbeam_standard (I-shape: total_height, web_thickness,
│         flange_width, flange_thickness)
└── components
    └── deck.thickness [mm]
```

### JudgeReport (Judge Output)

```
JudgeReport
├── pass_fail: bool
├── utilization (deck, bend, shear, deflection, web_slenderness, max_util, governing_check)
├── diagnostics (intermediate calculation values)
├── patch_plan (repair suggestions: actions)
└── evaluated_candidates (list of evaluated candidates, only on failure)
```

See [docs/COMPONENT_JUDGE.md](docs/COMPONENT_JUDGE.md) for details.

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - Directory structure & component overview
- [docs/USAGE.md](docs/USAGE.md) - Setup & usage instructions
- [docs/DEV_GUIDE.md](docs/DEV_GUIDE.md) - Development conventions
- [docs/COMPONENT_DESIGNER.md](docs/COMPONENT_DESIGNER.md) - Designer details
- [docs/COMPONENT_JUDGE.md](docs/COMPONENT_JUDGE.md) - Judge details
- [docs/EVALUATION.md](docs/EVALUATION.md) - Evaluation methodology
- [docs/json_spec.md](docs/json_spec.md) - Senkei JSON specification
