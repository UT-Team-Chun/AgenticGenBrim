# COMPONENT_DESIGNER

Overview of the Designer, which takes bridge length L and total width B as inputs and generates a BridgeDesign (structured JSON) based on RAG context.

## Input Parameters

Defined by the `DesignerInput` class in `src/bridge_agentic_generate/designer/models.py`.

- **bridge_length_m** (`float`): Bridge length $L$ [m].
- **total_width_m** (`float`): Total width $B$ [m].

## Output JSON Schema (BridgeDesign)

Structured data defined by the `BridgeDesign` class in `src/bridge_agentic_generate/designer/models.py`.
The main components are as follows.

### 1. Dimensions (Overall Dimensions)

- `bridge_length`: Bridge length [mm]
- `total_width`: Total width [mm]
- `num_girders`: Number of main girders
- `girder_spacing`: Main girder spacing [mm]
- `panel_length`: Panel length [mm]
- `num_panels` (optional): If not explicitly specified, automatically calculated as `bridge_length / panel_length`

### 2. Sections (Member Cross-Sections)

- **girder_standard** (Main girder standard I-shaped cross-section)
  - `web_height`, `web_thickness`: Web height and thickness [mm]
  - `top_flange_width`, `top_flange_thickness`: Top flange width and thickness [mm]
  - `bottom_flange_width`, `bottom_flange_thickness`: Bottom flange width and thickness [mm]
- **crossbeam_standard** (Cross beam standard I-shaped cross-section)
  - `total_height`: Girder height [mm]
  - `web_thickness`: Web thickness [mm]
  - `flange_width`, `flange_thickness`: Flange width and thickness [mm]

### 3. Components

- **deck** (Deck slab)
  - `thickness`: Deck slab thickness [mm]

## RAG Context Used (Multi-Query Search)

During design generation, the Designer performs multi-query RAG searches across the following 5 perspectives, retrieving relevant regulation clauses and design knowledge to include in the prompt.

### Search Queries (5 Perspectives)

1. **Dimensions-related (dimensions)**
   - Query: `"鋼プレートガーダー橋 橋長{L}m 幅員{B}m 桁配置 主桁本数 桁間隔 パネル長"`

2. **Main girder layout (girder_layout)**
   - Query: `"並列I桁 主桁間隔 幅員と主桁本数の関係 標準断面 主桁本数"`

3. **Main girder cross-section (girder_section)**
   - Query: `"プレートガーダー橋 橋長{L}m 主桁断面 桁高 腹板厚さ フランジ幅 フランジ厚さ 経済的桁高 h/L"`

4. **RC deck slab (deck)**
   - Query: `"RC床版合成桁 床版厚さ 最小床版厚 床版厚と支間の比"`

5. **Cross beam (crossbeam)**
   - Query: `"横桁 対傾構 横構 設計"`

### Use of Search Results

- **Reference sources**: Text chunks extracted from PDFs under `data/design_knowledge/` (Japan Road Bridge Specifications (JRA), Fundamentals of Steel Bridge Design, etc.).
- **top_k**: Retrieves the top 5 results per query (up to 25 chunks total).
- **Prompt integration**: Chunks matched by the search are presented to the LLM as reference materials.
- **RAG log**: Search results (rank, score, source, page, text) are recorded as `DesignerRagLog` and saved to `data/generated_bridge_raglog_json/`.

## LLM Output Schema (DesignerOutput)

Defined by the `DesignerOutput` class in `src/bridge_agentic_generate/designer/models.py`.
The LLM returns not only the BridgeDesign but also the design rationale and applied rules in a structured format.

- **reasoning** (`str`): Reasoning and judgment basis for the entire design process (e.g., why certain dimensions were chosen)
- **rules** (`list[DesignRule]`): List of design rules applied in this design
- **dependency_rules** (`list[DependencyRule]`): Dependency rules between members (used for cascading updates during the repair loop)
- **bridge_design** (`BridgeDesign`): The generated cross-section design

### DesignRule

A single design rule extracted from the RAG context.

- `rule_id`: Rule ID (e.g., "R1")
- `category`: Category (`dimensions` / `girder_section` / `deck` / `crossbeam_section` / `other`)
- `summary`: Japanese-language summary
- `condition_expression`: Condition expression (e.g., `"web_height ≒ L/20〜L/25"`)
- `formula_latex`: LaTeX-style formula (optional)
- `applies_to_fields`: List of BridgeDesign field names affected
- `source_hit_ranks`: RAG hit rank numbers used as basis (empty if no basis)

### DependencyRule

Dependencies between members (e.g., cross beam height = main girder height x coefficient). Used for automatic cascading updates after PatchPlan application.

- `rule_id`: Rule ID (e.g., "D1")
- `target_field`: Target to update (e.g., `"crossbeam.total_height"`)
- `source_field`: Source reference (e.g., `"girder.web_height"`)
- `factor`: Coefficient (e.g., `0.8`)
- `source_hit_ranks`: RAG hit rank numbers used as basis

## Generation Flow

```text
DesignerInput (bridge length L, total width B)
    ↓
Multi-query RAG search (5 perspectives)
    ↓
Prompt construction (RAG context + design instructions)
    ↓
LLM call (Structured Output → DesignerOutput)
    ↓
Decompose DesignerOutput:
  - bridge_design → BridgeDesign
  - reasoning, rules, dependency_rules → Recorded in DesignerRagLog
    ↓
DesignResult (design + rag_log + rules + dependency_rules)
    ↓
Save JSON + Save RAG log
```

## Typical Use Cases

1. **Automatic preliminary design generation**
   - By simply specifying bridge length and total width, the system automatically generates an initial proposal with reasonable cross-section dimensions (girder height, plate thickness, etc.) based on specifications and textbooks.

2. **Verifying design rationale**
   - Since the generated results include RAG logs (`DesignerRagLog`), users can verify which regulation clauses (source file name, page number) served as the basis for determining each dimension.

3. **Integration with BIM/CIM models**
   - The output JSON is converted to an IFC file through the `bridge_json_to_ifc` module and can be visualized and utilized as a 3D model.

4. **Integration with Judge**
   - The generated BridgeDesign is verified by the Judge component, and when it fails verification, it is corrected based on the PatchPlan.

## Related Files

- `src/bridge_agentic_generate/designer/models.py`: Pydantic model definitions (BridgeDesign, DesignerOutput, DesignRule, DependencyRule, etc.)
- `src/bridge_agentic_generate/designer/services.py`: Generation logic (`generate_design_with_rag_log()`)
- `src/bridge_agentic_generate/designer/prompts.py`: Prompt construction (`build_designer_prompt()`)
- `src/bridge_agentic_generate/rag/search.py`: RAG search (`search_text()`)
