"""bridge-llm-mvp のメインエントリーポイント。"""

from __future__ import annotations

from datetime import datetime
from typing import Sequence

# from fire import Fire
from src.bridge_agentic_generate.config import get_app_config
from src.bridge_agentic_generate.designer.models import DesignerInput
from src.bridge_agentic_generate.designer.services import generate_design
from src.bridge_agentic_generate.judge.models import JudgeInput
from src.bridge_agentic_generate.judge.services import judge_design
from src.bridge_agentic_generate.llm_client import LlmModel
from src.bridge_agentic_generate.logger_config import get_logger
from src.bridge_agentic_generate.rag.embedding_config import TOP_K

logger = get_logger(__name__)

DEFAULT_BRIDGE_LENGTHS_M: Sequence[float] = (30.0, 40.0, 50.0, 60.0, 70.0)
DEFAULT_TOTAL_WIDTH_M: float = 10.0


def run(
    model_name: LlmModel,
    bridge_lengths_m: Sequence[float] = DEFAULT_BRIDGE_LENGTHS_M,
    total_width_m: float = DEFAULT_TOTAL_WIDTH_M,
    top_k: int = TOP_K,
) -> None:
    """代表ケースの Designer→Judge を実行する。

    Args:
        model_name: 使用する LLM モデル名。
        bridge_lengths_m: 検討する橋長 L [m] の列。
        total_width_m: 全ケース共通の幅員 B [m]。

    Returns:
        None: 返り値は利用しない。
    """
    for bridge_length_m in bridge_lengths_m:
        input_model = DesignerInput(
            bridge_length_m=bridge_length_m,
            total_width_m=total_width_m,
        )
        logger.info("Span L=%.3f m, B=%.3f m で設計を開始", bridge_length_m, total_width_m)
        design = generate_design(input_model, top_k=top_k, model_name=model_name)
        judge_input = JudgeInput(
            bridge_length_m=bridge_length_m,
            total_width_m=total_width_m,
            design=design,
        )
        result = judge_design(judge_input)
        logger.info("Judge result: %s", result.model_dump())


def main() -> None:
    """Fire 経由で `run` を公開するラッパー。"""
    # Fire(run)
    # テストとして1ケースで実行
    app_config = get_app_config()
    inputs = DesignerInput(bridge_length_m=50.0, total_width_m=10.0)
    design = generate_design(inputs, top_k=TOP_K, model_name=LlmModel.GPT_5_MINI)

    # JSON ファイルとして保存
    output_dir = app_config.generated_bridge_json_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"design_L{inputs.bridge_length_m:.0f}_B{inputs.total_width_m:.0f}_{timestamp}.json"
    output_path.write_text(
        design.model_dump_json(indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("Saved design to %s", output_path)


if __name__ == "__main__":
    main()
