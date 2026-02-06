# Evaluation Policy

This document defines the evaluation policy for the Steel Plate Girder Bridge BrIM Generation Agent.
The purpose is to establish quantitative evaluation metrics for the paper and to clarify the limitations of the system.

---

## 1. Purpose of Evaluation

1. **Quantify System Performance**: Objectively demonstrate the effectiveness of design generation and repair loops
2. **Assess RAG Contribution**: Quantify the effect of knowledge retrieval by comparing with and without RAG
3. **Clarify Limitations**: Clearly define the scope the system can and cannot handle

---

## 2. Evaluation Metrics

### 2.1 Design Quality Metrics

| Metric | Definition | Calculation Method |
|--------|------------|-------------------|
| **First-Pass Rate** | Percentage of cases that passed all verification items on the first generation | Count of `iterations[0].report.pass_fail == True` / total count |
| **Convergence Rate** | Percentage of cases that reached a pass within the maximum number of iterations | Count of `converged == True` / total count |
| **Avg. Iterations** | Average number of iterations to reach a pass | Mean of `len(iterations)` for converged cases only |
| **Final Pass Rate** | Final pass rate after the repair loop | Count of `final_report.pass_fail == True` / total count |

### 2.2 Per-Check Metrics

Measure the pass rate for each verification item on the initial design.

| Verification Item | Pass Condition |
|-------------------|----------------|
| Bending (bend) | `util_bend <= 1.0` |
| Shear (shear) | `util_shear <= 1.0` |
| Deflection (deflection) | `util_deflection <= 1.0` |
| Deck slab thickness (deck) | `util_deck <= 1.0` |
| Web slenderness ratio (web_slenderness) | `util_web_slenderness <= 1.0` |
| Cross beam layout (crossbeam_layout) | `crossbeam_layout_ok == True` |

**Purpose**: Identify which verification items are difficult for the LLM.

### 2.3 RAG Contribution Metrics

Generate the same cases with and without RAG, and compare the following.

| Comparison Metric | Description |
|-------------------|-------------|
| **Difference in First-Pass Rate** | With RAG vs without RAG |
| **Difference in Avg. Iterations** | With RAG vs without RAG |
| **Difference in First max_util** | Comparison of maximum util values in the initial design |
| **Difference in Convergence Rate** | With RAG vs without RAG |

**Hypothesis**: With RAG, the first-pass rate is higher and the number of repair iterations is lower.

---

## 3. Evaluation Cases

### 3.1 List of Evaluation Cases

A total of 32 cases are selected from combinations of bridge length L=20-70m and total width B=8-24m.
Case definitions are managed in `DEFAULT_EVALUATION_CASES` in `src/evaluation/main.py`.

| L (m) | B (m) combinations |
|-------|---------------------|
| 20 | 8, 10 |
| 25 | 8, 10, 12 |
| 30 | 8, 10, 12 |
| 35 | 8, 10, 16 |
| 40 | 8, 10, 20 |
| 45 | 8, 10, 20 |
| 50 | 10, 16, 24 |
| 55 | 10, 16, 24 |
| 60 | 10, 16, 24 |
| 65 | 12, 16, 24 |
| 70 | 12, 16, 24 |

**Notes**:
- Span <= 80m is the applicable range for L-loading (system constraint)
- Short bridges (L<=35m) include narrow widths (B=8-12m), long bridges (L>=50m) include wide widths (B=16-24m)

### 3.2 Number of Trials

| Condition | Number of Trials | Reason |
|-----------|-----------------|--------|
| Each case x RAG condition | 3 | To account for variability in LLM generation |

**Total number of runs**: 32 cases x 2 conditions x 3 trials = 192 runs

### 3.3 Model Used

| Item | Value |
|------|-------|
| LLM Model | GPT-5.1 (`gpt-5-1`) |

**Note**: The same model is used for both the Designer (design generation) and Judge (PatchPlan generation).

### 3.4 Maximum Number of Repair Iterations

| Parameter | Value |
|-----------|-------|
| max_iterations | 5 |

---

## 4. Evaluation Procedure

### 4.1 Execution Flow

```
1. Define evaluation case (L, B) combinations
2. For each case:
   a. Run N generation and repair loop iterations with RAG enabled
   b. Run N generation and repair loop iterations with RAG disabled
   c. Record the results of each trial
3. Aggregate results and calculate metrics
4. Output report
```

### 4.2 Generation Without RAG

Toggle RAG on/off using the `use_rag` parameter of `generate_design_with_rag_log` (already implemented).

```python
def generate_design_with_rag_log(
    inputs: DesignerInput,
    top_k: int = TOP_K,
    model_name: LlmModel = LlmModel.GPT_5_MINI,
    use_rag: bool = True,
) -> DesignResult:
    """When use_rag=False, skip RAG retrieval and generate with an empty context."""
```

---

## 5. Output Format

### 5.1 Raw Data (JSON)

Save detailed results of each trial as JSON.

```json
{
  "case_id": "L50_B10_rag_true_trial_1",
  "bridge_length_m": 50,
  "total_width_m": 10,
  "use_rag": true,
  "trial": 1,
  "converged": true,
  "num_iterations": 2,
  "first_pass": false,
  "first_max_util": 1.23,
  "first_utilization": {
    "deck": 0.85,
    "bend": 1.23,
    "shear": 0.45,
    "deflection": 0.92,
    "web_slenderness": 0.78
  },
  "final_pass": true,
  "final_max_util": 0.95,
  "per_check_first_pass": {
    "deck": true,
    "bend": false,
    "shear": true,
    "deflection": true,
    "web_slenderness": true,
    "crossbeam_layout": true
  }
}
```

### 5.2 Aggregated Report (Markdown)

```markdown
## Evaluation Results Summary

### Overall Metrics

| Condition | First-Pass Rate | Convergence Rate | Avg. Iterations | Final Pass Rate |
|-----------|----------------|-----------------|-----------------|-----------------|
| With RAG | 32% (8/25) | 92% (23/25) | 2.1 | 92% |
| Without RAG | 12% (3/25) | 72% (18/25) | 3.4 | 72% |

### First-Pass Rate by Verification Item

| Verification Item | With RAG | Without RAG | Difference |
|-------------------|----------|-------------|------------|
| Bending | 76% | 56% | +20% |
| Shear | 92% | 84% | +8% |
| Deflection | 48% | 28% | +20% |
| Deck slab thickness | 88% | 88% | 0% |
| Web slenderness ratio | 80% | 64% | +16% |
| Cross beam layout | 96% | 92% | +4% |

### Convergence Rate by Bridge Length

| Bridge Length | With RAG | Without RAG |
|--------------|----------|-------------|
| 30m | 100% | 80% |
| 40m | 100% | 80% |
| 50m | 80% | 60% |
| 60m | 80% | 60% |
| 70m | 100% | 80% |
```

---

## 6. System Limitations

Separately from the evaluation results, the applicable limitations of the system are documented here.

### 6.1 Supported Scope

| Item | Scope |
|------|-------|
| Bridge type | Simply supported plate girder bridge (RC deck slab) |
| Span length | <= 80m (applicable range for L-loading) |
| Load conditions | B live load (L-loading / p1/p2 rules) |
| Design stage | Preliminary design (determination of cross-sectional dimensions) |

### 6.2 Unsupported Items

| Item | Reason |
|------|--------|
| Continuous girder / Rigid frame bridge | Only simple girder analysis model is implemented |
| Span > 80m | Outside the applicable range of L-loading |
| Detailed design | Welding, bolted connections, fatigue verification, etc. are not implemented |
| FEM analysis | Only deterministic simplified calculations |
| Special loads | Only standard B live load is supported |

---

## 7. Future Extension Possibilities

1. **Adding Expert Evaluation**: Experts evaluate the practical applicability of generated designs
2. **Comparison of Different LLM Models**: GPT-5.1 vs GPT-5-mini, etc.
3. **Detailed RAG Accuracy Evaluation**: Retrieval accuracy metrics such as Recall@k, MRR

---

## 8. Implementation Status

### Phase 1: Evaluation Infrastructure (Completed)

- [x] Evaluation model definitions (`src/evaluation/models.py`)
- [x] Metric calculation logic (`src/evaluation/metrics.py`)
- [x] Added generation option without RAG (`use_rag` parameter)
- [x] Batch evaluation CLI (`src/evaluation/runner.py`)
- [x] Graph output (`src/evaluation/plot.py`)
- [x] Evaluation CLI entry point (`src/evaluation/main.py`)

### Phase 2: Evaluation Execution

- [ ] Run evaluation for all cases
- [ ] Aggregate results and generate reports
- [ ] Create figures and tables for the paper

### Evaluation CLI Commands

```bash
# Run all cases (32 cases x with/without RAG x 3 trials)
uv run python -m src.evaluation.main run

# Test run for a single case
uv run python -m src.evaluation.main single_case \
  --bridge_length_m 50 --total_width_m 10

# Run a single case without RAG
uv run python -m src.evaluation.main single_case \
  --bridge_length_m 50 --total_width_m 10 --use_rag False

# Generate graphs from evaluation results
uv run python -m src.evaluation.main plot --data_dir data/evaluation_v5
```

---

## References

- [docs/COMPONENT_DESIGNER.md](COMPONENT_DESIGNER.md) - Designer Details
- [docs/COMPONENT_JUDGE.md](COMPONENT_JUDGE.md) - Judge Details
