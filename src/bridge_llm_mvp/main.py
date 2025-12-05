# src/bridge_llm_mvp/main.py
from __future__ import annotations

from bridge_llm_mvp.designer.models import DesignerInput
from bridge_llm_mvp.designer.services import generate_design
from bridge_llm_mvp.judge.models import JudgeInput
from bridge_llm_mvp.judge.services import judge_design

TEST_CASES: list[DesignerInput] = [
    DesignerInput(span_length_m=30.0, total_width_m=8.0),
    DesignerInput(span_length_m=40.0, total_width_m=9.0),
    DesignerInput(span_length_m=50.0, total_width_m=10.0),
    DesignerInput(span_length_m=60.0, total_width_m=11.0),
    DesignerInput(span_length_m=70.0, total_width_m=12.0),
]


def main() -> None:
    for case in TEST_CASES:
        print(f"=== Case L={case.span_length_m} m, B={case.total_width_m} m ===")
        design = generate_design(case)
        judge_input = JudgeInput(
            span_length_m=case.span_length_m,
            total_width_m=case.total_width_m,
            design=design,
        )
        result = judge_design(judge_input)
        print(result.model_dump())


if __name__ == "__main__":
    main()
