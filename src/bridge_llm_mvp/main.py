"""bridge-llm-mvp のメインエントリーポイント。"""

from __future__ import annotations

from typing import Sequence

# from fire import Fire
from src.bridge_llm_mvp.designer.models import DesignerInput
from src.bridge_llm_mvp.designer.services import generate_design
from src.bridge_llm_mvp.judge.models import JudgeInput
from src.bridge_llm_mvp.judge.services import judge_design
from src.bridge_llm_mvp.llm_client import LlmModel
from src.bridge_llm_mvp.logger_config import get_logger
from src.bridge_llm_mvp.rag.embedding_config import TOP_K

logger = get_logger(__name__)

DEFAULT_SPAN_LENGTHS_M: Sequence[float] = (30.0, 40.0, 50.0, 60.0, 70.0)
DEFAULT_TOTAL_WIDTH_M: float = 10.0


def run(
    model_name: LlmModel,
    span_lengths_m: Sequence[float] = DEFAULT_SPAN_LENGTHS_M,
    total_width_m: float = DEFAULT_TOTAL_WIDTH_M,
    top_k: int = TOP_K,
) -> None:
    """代表ケースの Designer→Judge を実行する。

    Args:
        model_name: 使用する LLM モデル名。
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
        design = generate_design(input_model, top_k=top_k, model_name=model_name)
        judge_input = JudgeInput(
            span_length_m=span_length_m,
            total_width_m=total_width_m,
            design=design,
        )
        result = judge_design(judge_input)
        logger.info("Judge result: %s", result.model_dump())


def main() -> None:
    """Fire 経由で `run` を公開するラッパー。"""
    # Fire(run)
    # テストとして1ケースで実行
    inputs = DesignerInput(span_length_m=50.0, total_width_m=10.0)
    design = generate_design(inputs, top_k=TOP_K, model_name=LlmModel.GPT_5_MINI)
    logger.info(design.model_dump_json(indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
