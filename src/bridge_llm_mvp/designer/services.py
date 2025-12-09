from src.bridge_llm_mvp.designer.models import BridgeDesign, DesignerInput
from src.bridge_llm_mvp.designer.prompts import build_designer_prompt
from src.bridge_llm_mvp.llm_client import LlmModel, call_llm_with_structured_output, get_llm_client
from src.bridge_llm_mvp.logger_config import get_logger
from src.bridge_llm_mvp.rag.search import (
    SearchResult,
    search_text,
)

logger = get_logger(__name__)

# RAG 検索で使用するクエリ
DEFAULT_RAG_QUERY: str = "プレートガーダー 桁 床版 厚さ 桁高 腹板 フランジ"


def generate_design(inputs: DesignerInput, top_k: int, model_name: LlmModel) -> BridgeDesign:
    """RAG + LLM を使って鋼プレートガーダー橋の断面モデルを 1 ケース生成する。

    処理の流れ:
        1. RAG で教科書・示方書から関連チャンクを取得
        2. チャンクと設計条件からプロンプトを組み立て
        3. LLM に Structured Output で BridgeDesign を生成させる

    Args:
        inputs: 設計条件。橋長 L [m] と幅員 B [m] を含む。
        top_k: RAG 検索で取得するチャンク数。
        model_name: 使用する LLM モデル名。

    Returns:
        BridgeDesign: 主桁・横桁・床版の寸法を含む設計結果。
    """
    # 1. RAG で関連チャンク取得
    client = get_llm_client()
    search_results: list[SearchResult] = search_text(
        query=DEFAULT_RAG_QUERY,
        client=client,
        top_k=top_k,
    )
    chunks = [r.chunk for r in search_results]

    logger.info(
        "Designer: retrieved %d chunks for query='%s'",
        len(chunks),
        DEFAULT_RAG_QUERY,
    )

    # 2. プロンプト組み立て
    prompt = build_designer_prompt(inputs=inputs, chunks=chunks)

    # 3. LLM 呼び出し
    design: BridgeDesign = call_llm_with_structured_output(
        input=prompt,
        model=model_name,
        text_format=BridgeDesign,
    )

    logger.info(
        "Designer: generated design for L=%.1f, B=%.1f",
        inputs.bridge_length_m,
        inputs.total_width_m,
    )

    return design
