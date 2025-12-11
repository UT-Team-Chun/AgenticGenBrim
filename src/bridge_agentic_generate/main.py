"""bridge-llm-mvp のメインエントリーポイント。"""

from __future__ import annotations

from datetime import datetime
from typing import Sequence

# from fire import Fire
from src.bridge_agentic_generate.config import get_app_config
from src.bridge_agentic_generate.designer.models import DesignerInput
from src.bridge_agentic_generate.designer.services import generate_design_with_rag_log
from src.bridge_agentic_generate.judge.models import JudgeInput
from src.bridge_agentic_generate.judge.services import judge_design
from src.bridge_agentic_generate.llm_client import LlmModel
from src.bridge_agentic_generate.logger_config import get_logger
from src.bridge_agentic_generate.rag.embedding_config import TOP_K

logger = get_logger(__name__)

DEFAULT_BRIDGE_LENGTHS_M: Sequence[float] = (30.0, 40.0, 50.0, 60.0, 70.0)
DEFAULT_TOTAL_WIDTH_M: float = 10.0


def run_batch(
    model_name: LlmModel,
    bridge_lengths_m: Sequence[float] = DEFAULT_BRIDGE_LENGTHS_M,
    total_width_m: float = DEFAULT_TOTAL_WIDTH_M,
    top_k: int = TOP_K,
) -> None:
    """代表ケースの Designer→Judge を run_single_case 経由で実行する。

    Args:
        model_name: 使用する LLM モデル名。
        bridge_lengths_m: 実行する橋長のリスト [m]。
        total_width_m: 橋幅員 B [m]（全ケース共通）。
        top_k: RAG で取得するチャンク数。
    """
    for bridge_length_m in bridge_lengths_m:
        run_single_case(
            bridge_length_m=bridge_length_m,
            total_width_m=total_width_m,
            model_name=model_name,
            top_k=top_k,
            judge_enabled=True,
        )


def run_single_case(
    bridge_length_m: float,
    total_width_m: float,
    model_name: LlmModel = LlmModel.GPT_5_MINI,
    top_k: int = TOP_K,
    judge_enabled: bool = False,
) -> None:
    """単一ケースの Designer→(任意で Judge) を実行し、結果を保存する。

    Args:
        bridge_length_m: 橋長 L [m]。
        total_width_m: 幅員 B [m]。
        model_name: 使用する LLM モデル名。
        top_k: RAG で取得するチャンク数。
        judge_enabled: True の場合、Judge も実行する。
    """
    app_config = get_app_config()
    simple_json_dir = app_config.generated_simple_bridge_json_dir
    simple_json_dir.mkdir(parents=True, exist_ok=True)
    raglog_json_dir = app_config.generated_bridge_raglog_json_dir
    raglog_json_dir.mkdir(parents=True, exist_ok=True)
    inputs = DesignerInput(bridge_length_m=bridge_length_m, total_width_m=total_width_m)
    design, rag_log = generate_design_with_rag_log(inputs=inputs, top_k=top_k, model_name=model_name)

    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    base_name = f"design_L{int(inputs.bridge_length_m)}_B{int(inputs.total_width_m * 10):02d}_{timestamp}"

    design_path = simple_json_dir / f"{base_name}.json"
    raglog_path = raglog_json_dir / f"{base_name}_raglog.json"

    design_path.write_text(design.model_dump_json(indent=2, ensure_ascii=False), encoding="utf-8")
    raglog_path.write_text(rag_log.model_dump_json(indent=2, ensure_ascii=False), encoding="utf-8")

    logger.info("Saved design to %s", design_path)
    logger.info("Saved RAG log to %s", raglog_path)

    if judge_enabled:
        judge_input = JudgeInput(
            bridge_length_m=bridge_length_m,
            total_width_m=total_width_m,
            design=design,
        )
        result = judge_design(judge_input)
        logger.info("Judge result: %s", result.model_dump())


def main() -> None:
    """CLI エントリーポイント。"""
    run_single_case(
        bridge_length_m=50.0, total_width_m=10.0, model_name=LlmModel.GPT_5_MINI, top_k=TOP_K, judge_enabled=True
    )


if __name__ == "__main__":
    main()
