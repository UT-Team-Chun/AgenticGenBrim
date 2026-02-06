# COMPONENT_JUDGE

Overview of the Judge, which performs deterministic verification calculations on a BridgeDesign input and generates repair proposals (PatchPlan) via LLM when the design fails.

## Overview

The Judge is responsible for the following:

1. **Deterministic verification**: Compute utilization ratios for bending, shear, deflection, deck slab thickness, web slenderness ratio, and cross beam layout
2. **Pass/fail determination**: Pass if all utilization ratios are ≤ 1.0 and the cross beam layout is OK
3. **Repair proposal**: When the design fails, the LLM generates a PatchPlan (list of repair operations) using the multiple-candidate approach

## Input (JudgeInput)

```python
class JudgeInput(BaseModel):
    bridge_design: BridgeDesign
    materials_steel: MaterialsSteel = ...         # E=2.0e5, grade=SM490, unit_weight=78.5e-6
    materials_concrete: MaterialsConcrete = ...   # unit_weight=25.0e-6
    judge_params: JudgeParams = ...               # alpha_bend=0.6, alpha_shear=0.6
```

> **Note**: Live load is not provided as external input via `LoadInput`; instead, it is computed internally based on L-load (p1/p2 rule).

### JudgeParams (Default Values)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `alpha_bend` | 0.6 | Bending allowable stress coefficient. σ_allow = α × fy |
| `alpha_shear` | 0.6 | Shear allowable stress coefficient. τ_allow = α × (fy/√3) |

### Material Properties (Default Values)

| Material | E [N/mm²] | grade | unit_weight [N/mm³] |
|----------|-----------|-------|---------------------|
| Steel | 2.0×10⁵ | SM490 | 78.5×10⁻⁶ |
| Concrete | - | - | 25.0×10⁻⁶ |

**Yield point fy**: Dynamically computed by `get_fy()` based on steel grade and plate thickness.

| Steel grade | Plate thickness ≤16mm | 16-40mm | >40mm |
|-------------|-----------------------|---------|-------|
| SM400 | 245 | 235 | 215 |
| SM490 | 325 | 315 | 295 |

## Output (JudgeReport)

```python
class JudgeReport(BaseModel):
    pass_fail: bool                        # Pass/fail
    utilization: Utilization               # Utilization ratios for each check
    diagnostics: Diagnostics               # Intermediate calculation values
    patch_plan: PatchPlan                  # Repair proposal (only when failed)
    evaluated_candidates: list | None      # List of evaluated candidates (only when failed)
```

### Utilization

| Item | Formula | Description |
|------|---------|-------------|
| `deck` | required / provided | Deck slab thickness util |
| `bend` | max(\|σ_top\|/σ_allow_top, \|σ_bottom\|/σ_allow_bottom) | Bending stress util |
| `shear` | \|τ_avg\| / τ_allow | Shear stress util |
| `deflection` | δ / δ_allow | Deflection util |
| `web_slenderness` | t_min_required / web_thickness | Web slenderness ratio util |
| `max_util` | max(deck, bend, shear, deflection, web_slenderness) | Maximum util |
| `governing_check` | Governing item for max_util | deck/bend/shear/deflection/web_slenderness/crossbeam_layout |

### Diagnostics (Intermediate Calculation Values)

| Field | Unit | Description |
|-------|------|-------------|
| `M_total`, `V_total` | N·mm, N | Total sectional forces for the governing girder |
| `ybar` | mm | Neutral axis position (measured from the bottom) |
| `moment_of_inertia` | mm⁴ | Moment of inertia |
| `y_top`, `y_bottom` | mm | Distance to top edge / distance to bottom edge |
| `sigma_top`, `sigma_bottom` | N/mm² | Top and bottom edge stresses for the governing girder |
| `tau_avg` | N/mm² | Average shear stress for the governing girder |
| `delta`, `delta_allow` | mm | Deflection / allowable deflection |
| `fy_top_flange`, `fy_bottom_flange`, `fy_web` | N/mm² | Yield point for each component |
| `sigma_allow_top`, `sigma_allow_bottom` | N/mm² | Allowable bending stress at top and bottom edges |
| `tau_allow` | N/mm² | Allowable shear stress |
| `deck_thickness_required` | mm | Required deck slab thickness |
| `web_thickness_min_required` | mm | Required minimum web thickness |
| `crossbeam_layout_ok` | bool | Cross beam layout consistency |
| `load_effects` | LoadEffectsResult | Detailed load calculation results |
| `governing_girder_index_bend` | int | Index of the girder with the most critical bending |
| `governing_girder_index_shear` | int | Index of the girder with the most critical shear |

## Verification Calculation Details

### 1. Live Load Sectional Forces (L-load / p1/p2 Rule)

L-load calculation based on the B live load from the Specifications for Highway Bridges is automatically performed internally.

#### L-load Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `P1_M_KN_M2` | 10.0 kN/m² | p1 surface pressure for bending verification |
| `P1_V_KN_M2` | 12.0 kN/m² | p1 surface pressure for shear verification |
| `P2_KN_M2` | 3.5 kN/m² | p2 surface pressure (span ≤ 80m) |
| `MAIN_LOADING_WIDTH_M` | 5.5 m | Main loading width |
| `MAX_LOADING_LENGTH_M` | 10.0 m | Maximum loading length |
| `MAX_APPLICABLE_SPAN_M` | 80.0 m | Maximum applicable span length |

#### Calculation Flow

```python
# 1. Loading length D
D_m = min(10.0, L_m)

# 2. Equivalence coefficient γ (conversion factor from partial loading to equivalent full-span distribution)
gamma = D_m * (2 * L_m - D_m) / L_m²

# 3. Equivalent surface pressure
p_eq_M = P2 + P1_M * gamma  # For bending
p_eq_V = P2 + P1_V * gamma  # For shear

# 4. Overhang width
overhang = (total_width - (num_girders - 1) * girder_spacing) / 2

# 5. Tributary width b_i for each girder
#    End girder: overhang + girder_spacing / 2
#    Interior girder: girder_spacing

# 6. Effective width b_eff (most unfavorable placement of 5.5m main loading width)
b_eff = 0.5 * b_i + 0.5 * min(b_i, 5.5)

# 7. Equivalent line load
w_M = p_eq_M * b_eff  # [kN/m]
w_V = p_eq_V * b_eff  # [kN/m]

# 8. Sectional forces (simply supported beam)
M_live = w_M * L² / 8  # [kN·m] → [N·mm]
V_live = w_V * L / 2   # [kN] → [N]

# 9. Use maximum across all girders (selected separately for bending and shear)
M_live_max = max(M_live for each girder)
V_live_max = max(V_live for each girder)
```

#### LoadEffectsResult

Detailed results of load calculations (dead load and live load combined) are stored in `Diagnostics.load_effects`.

```python
class GirderLoadResult(BaseModel):
    """Load calculation results for a single girder (dead load and live load combined)."""
    girder_index: int       # Girder index (0-based)
    b_i_m: float            # Tributary width [m]
    # Dead load
    w_dead: float           # Dead load line load [N/mm]
    M_dead: float           # Dead load bending moment [N·mm]
    V_dead: float           # Dead load shear force [N]
    # Live load
    b_eff_m: float          # Effective width [m] (for live load)
    w_M: float              # Equivalent line load for bending [kN/m]
    w_V: float              # Equivalent line load for shear [kN/m]
    M_live: float           # Live load bending moment [N·mm]
    V_live: float           # Live load shear force [N]
    # Total
    M_total: float          # Total bending moment [N·mm]
    V_total: float          # Total shear force [N]

class LoadEffectsResult(BaseModel):
    """Load calculation results for all girders (dead load and live load combined)."""
    L_m: float              # Span length [m]
    D_m: float              # Loading length [m]
    p2: float               # p2 surface pressure [kN/m²]
    p1_M: float             # p1 for bending [kN/m²]
    p1_V: float             # p1 for shear [kN/m²]
    gamma: float            # Equivalence coefficient
    p_eq_M: float           # Equivalent surface pressure for bending [kN/m²]
    p_eq_V: float           # Equivalent surface pressure for shear [kN/m²]
    overhang_m: float       # Overhang width [m]
    girder_results: list[GirderLoadResult]  # Results for each girder
    governing_girder_index_bend: int    # Girder with most critical bending
    governing_girder_index_shear: int   # Girder with most critical shear
    M_total_max: float      # Maximum total bending moment [N·mm]
    V_total_max: float      # Maximum total shear force [N]
```

### 2. Dead Load Sectional Forces (Per-girder Calculation)

Dead load is calculated individually for each girder based on its tributary width.

```
# Tributary width b_i [m] for each girder
#   End girder: overhang + girder_spacing / 2
#   Interior girder: girder_spacing

# Dead load line load (per girder)
w_deck = γ_c × deck_thickness × b_i [N/mm]
w_steel = γ_s × A_girder [N/mm]
w_dead = w_deck + w_steel [N/mm]

# Dead load sectional forces (per girder)
M_dead = w_dead × L² / 8 [N·mm]
V_dead = w_dead × L / 2 [N]

# Total sectional forces (per girder)
M_total = M_dead + M_live [N·mm]
V_total = V_dead + V_live [N]
```

The governing girder may differ between bending and shear (`governing_girder_index_bend/shear`).

### 3. Section Properties (Asymmetric I-section)

```
Total height: H = top_flange_thickness + web_height + bottom_flange_thickness
Neutral axis: ybar = Σ(A_i × y_i) / Σ(A_i)
Moment of inertia: I = Σ(I_i + A_i × (ybar - y_i)²)
```

### 4. Stress

When the top and bottom flanges have different plate thicknesses, the allowable stress is calculated from each flange's respective yield point.

```
σ_top = M_total × y_top / I
σ_bottom = M_total × y_bottom / I

# Allowable stress for each flange
σ_allow_top = α_bend × fy_top
σ_allow_bottom = α_bend × fy_bottom

# Compute util separately for top and bottom, and take the larger value
util_bend_top = |σ_top| / σ_allow_top
util_bend_bottom = |σ_bottom| / σ_allow_bottom
util_bend = max(util_bend_top, util_bend_bottom)
```

### 5. Shear (Average Shear Stress)

The web yield point is used.

```
τ_avg = V_total / (web_thickness × web_height)
τ_allow = α_shear × (fy_web / √3)
util_shear = |τ_avg| / τ_allow
```

### 6. Deflection (Live Load Only / Per Specifications for Highway Bridges)

Deflection verification for the serviceability limit state is evaluated using live load only. The allowable deflection is calculated in 3 tiers based on span length.

```
# Equivalent uniformly distributed load from live load
w_eq_live = 8 × M_live_max / L²

# Deflection
δ = 5 × w_eq_live × L⁴ / (384 × E × I)

# Allowable deflection (L_m in meters)
L_m = L / 1000

if L_m ≤ 10:
    δ_allow = L_m / 2000 × 1000 [mm]
elif L_m ≤ 40:
    δ_allow = L_m² / 20000 × 1000 [mm]
else:
    δ_allow = L_m / 500 × 1000 [mm]

util_deflection = δ / δ_allow
```

### 7. Deck Slab Thickness

```
L_support_m = girder_spacing / 1000 [m]
required = max(30 × L_support_m + 110, 160) [mm]
util_deck = required / provided
```

### 8. Cross Beam Layout Check

```
layout_ok = |panel_length × num_panels - bridge_length| ≤ 1.0mm
          AND panel_length ≤ 20000mm
```

### 9. Web Slenderness Ratio

The required minimum web thickness is calculated from the slenderness ratio limit based on steel grade, and compared against the current web thickness.

```
# Required minimum web thickness
SM490: t_min = web_height / 130
SM400: t_min = web_height / 152

# util
util_web_slenderness = t_min / web_thickness
```

## Repair Proposal (PatchPlan)

When the design fails, the LLM proposes repair operations based on the `RepairContext`.

### Multiple-Candidate Approach (v1.1)

PatchPlan generation uses the multiple-candidate approach:

1. **LLM generates 3 proposals**: Different approaches (e.g., prioritizing girder height increase, prioritizing flange thickness, etc.)
2. **Each proposal is tentatively applied and evaluated**: `apply_patch_plan` → `judge_v1_lightweight` to simulate max_util
3. **Best proposal is selected**: The proposal with the greatest improvement (= current max_util - simulated max_util) is adopted

```python
class PatchPlanCandidate(BaseModel):
    plan: PatchPlan
    approach_summary: str  # e.g., "Targeting deflection improvement via girder height increase"

class EvaluatedCandidate(BaseModel):
    candidate: PatchPlanCandidate
    simulated_max_util: float      # max_util after simulation
    simulated_utilization: Utilization
    improvement: float             # Positive means improvement
```

### Allowed Actions (AllowedActions)

| Action | Target | Allowed values |
|--------|--------|----------------|
| `increase_web_height` | girder.web_height | +100, +200, +300, +500 mm |
| `increase_web_thickness` | girder.web_thickness | +2, +4, +6 mm |
| `increase_top_flange_thickness` | girder.top_flange_thickness | +2, +4, +6 mm |
| `increase_bottom_flange_thickness` | girder.bottom_flange_thickness | +2, +4, +6 mm |
| `increase_top_flange_width` | girder.top_flange_width | +50, +100 mm |
| `increase_bottom_flange_width` | girder.bottom_flange_width | +50, +100 mm |
| `increase_num_girders` | dims.num_girders | +1 |
| `set_deck_thickness_to_required` | deck.thickness | = required |
| `fix_crossbeam_layout` | dims.num_panels | = round(L / panel_length) |

> **`increase_num_girders`**: Increases the number of girders by +1 and recalculates girder_spacing while maintaining the overhang. If the new girder_spacing requires a greater deck slab thickness, deck.thickness is also updated accordingly.

### PatchPlan Constraints

- Maximum of 3 actions per plan
- Avoid drastic changes (start with small modifications first)
- Only the allowed actions listed above are permitted

### PatchAction Example

```json
{
  "op": "increase_web_height",
  "path": "sections.girder_standard.web_height",
  "delta_mm": 100,
  "reason": "util_deflection is governing. Girder height increase improves deflection and bending."
}
```

## Repair Loop

When the design fails, the PatchPlan is applied and the process repeats until it passes.

```
BridgeDesign
    ↓
Judge (verification)
    ↓
Pass? → Yes → End
    ↓ No
LLM (generate 3 PatchPlan candidates)
    ↓
Tentatively apply and evaluate (each candidate)
    ↓
Select and apply the best candidate (apply_patch_plan)
    ↓
Apply dependency rules (apply_dependency_rules)
  └ e.g., cross beam height = main girder height × factor
    ↓
(Repeat up to max iterations)
```

### RepairLoopResult

```python
class RepairLoopResult(BaseModel):
    converged: bool                     # Whether the loop converged
    iterations: list[RepairIteration]   # Results for each iteration
    final_design: BridgeDesign          # Final design
    final_report: JudgeReport           # Final verification report
    rag_log: DesignerRagLog             # RAG log from the initial design
```

## Related Files

- `src/bridge_agentic_generate/judge/models.py`: Pydantic model definitions
- `src/bridge_agentic_generate/judge/services.py`: Verification calculations, L-load calculations, PatchPlan application
- `src/bridge_agentic_generate/judge/prompts.py`: PatchPlan generation prompts (multiple-candidate approach)
- `src/bridge_agentic_generate/judge/report.py`: Repair loop report generation (Markdown)
- `src/bridge_agentic_generate/judge/CLAUDE.md`: Detailed specification document

## Notes

- **Unit system**: All values are in mm, N, N/mm², N·mm
- **Live load model**: Calculation per the Specifications for Highway Bridges based on L-load (p1/p2 rule). Applicable for spans of 80m or less.
- **Deflection util**: A screening indicator for preliminary design (not a rigorous deflection verification)
- **Deterministic verification**: Same input always produces the same result (easy to test)
- **Multiple-candidate approach**: LLM proposals are tentatively applied and evaluated, with the best candidate automatically selected
