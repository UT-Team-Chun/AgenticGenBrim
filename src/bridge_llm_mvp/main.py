"""bridge-llm-mvp のメインエントリーポイント。"""

from __future__ import annotations

from typing import Sequence

from fire import Fire

from src.bridge_llm_mvp.designer.models import DesignerInput
from src.bridge_llm_mvp.designer.services import generate_design
from src.bridge_llm_mvp.judge.models import JudgeInput
from src.bridge_llm_mvp.judge.services import judge_design
from src.bridge_llm_mvp.logger_config import get_logger

logger = get_logger(__name__)

DEFAULT_SPAN_LENGTHS_M: Sequence[float] = (30.0, 40.0, 50.0, 60.0, 70.0)
DEFAULT_TOTAL_WIDTH_M: float = 10.0


def run(
    span_lengths_m: Sequence[float] = DEFAULT_SPAN_LENGTHS_M,
    total_width_m: float = DEFAULT_TOTAL_WIDTH_M,
) -> None:
    """代表ケースの Designer→Judge を実行する。

    Args:
        span_lengths_m: 検討する支間長 L [m] の列。
        total_width_m: 全ケース共通の全幅 B [m]。

    Returns:
        None: 返り値は利用しない。
    """
    for span_length_m in span_lengths_m:
        input_model = DesignerInput(
            span_length_m=span_length_m,
            total_width_m=total_width_m,
        )
        logger.info("Span L=%.3f m, B=%.3f m で設計を開始", span_length_m, total_width_m)
        design = generate_design(input_model)
        judge_input = JudgeInput(
            span_length_m=span_length_m,
            total_width_m=total_width_m,
            design=design,
        )
        result = judge_design(judge_input)
        logger.info("Judge result: %s", result.model_dump())


def main() -> None:
    """Fire 経由で `run` を公開するラッパー。"""
    Fire(run)


if __name__ == "__main__":
    main()
