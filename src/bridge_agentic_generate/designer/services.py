from src.bridge_agentic_generate.designer.models import (
    BridgeDesign,
    DesignerInput,
    DesignerRagLog,
    DesignResult,
    RagHit,
)
from src.bridge_agentic_generate.designer.prompts import build_designer_prompt
from src.bridge_agentic_generate.llm_client import LlmModel, call_llm_with_structured_output, get_llm_client
from src.bridge_agentic_generate.logger_config import get_logger
from src.bridge_agentic_generate.rag.search import (
    SearchResult,
    search_text,
)

logger = get_logger(__name__)

# RAG 検索で使用するクエリ
DEFAULT_RAG_QUERY: str = "プレートガーダー 桁 床版 厚さ 桁高 腹板 フランジ"


def _build_rag_log(
    query: str,
    top_k: int,
    results: list[SearchResult],
) -> DesignerRagLog:
    """SearchResult のリストを DesignerRagLog に変換する。"""
    hits: list[RagHit] = []
    for idx, res in enumerate(results):
        hits.append(
            RagHit(
                rank=idx + 1,
                score=float(res.score),
                source=res.chunk.source,
                page=res.chunk.page,
                text=res.chunk.text,
            ),
        )
    return DesignerRagLog(query=query, top_k=top_k, hits=hits)


def generate_design(
    inputs: DesignerInput,
    top_k: int,
    model_name: LlmModel,
) -> BridgeDesign:
    """後方互換用: BridgeDesign だけ欲しいときはこちら。"""
    result = generate_design_with_rag_log(
        inputs=inputs,
        top_k=top_k,
        model_name=model_name,
    )
    return result.design


def generate_design_with_rag_log(
    inputs: DesignerInput,
    top_k: int,
    model_name: LlmModel,
) -> DesignResult:
    """RAG コンテキストのログも含めて設計を生成する。

    Args:
        inputs: 橋長・幅員などの入力パラメータ
        top_k: RAG で取得するチャンク数
        model_name: 使用する LLM モデル

    Returns:
        DesignResult: 設計結果とRAGログ
    """
    client = get_llm_client()

    # 1) RAG クエリ生成（今既にやっているものをそのまま使う）
    rag_query = (
        f"橋長 {inputs.bridge_length_m} m, 幅員 {inputs.total_width_m} m の"
        "鋼プレートガーダー橋の断面設計に関係する条文・式を探してください。"
    )
    rag_results = search_text(query=rag_query, client=client, top_k=top_k)

    # 2) プロンプト組み立て（RAG 結果の text を渡す）
    context_chunks = [res.chunk for res in rag_results]
    prompt = build_designer_prompt(inputs=inputs, chunks=context_chunks)

    # 3) LLM 本体呼び出し（既存の Structured Output ラッパー）
    design: BridgeDesign = call_llm_with_structured_output(
        input=prompt,
        model=model_name,
        text_format=BridgeDesign,
    )

    # 4) RAG ログ構築
    rag_log = _build_rag_log(query=rag_query, top_k=top_k, results=rag_results)

    return DesignResult(design=design, rag_log=rag_log)
