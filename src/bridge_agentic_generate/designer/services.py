from src.bridge_agentic_generate.designer.models import (
    BridgeDesign,
    DesignerInput,
    DesignerOutput,
    DesignerRagLog,
    DesignResult,
    RagHit,
)
from src.bridge_agentic_generate.designer.prompts import DESIGNER_PROMPT
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
        DesignResult: 設計結果とRAGログ + （あれば）使用ルール一覧
    """
    client = get_llm_client()

    # 1) マルチクエリRAG
    rag_results_dimensions = search_text(
        query=(
            f"橋長 {inputs.bridge_length_m} m, 幅員 {inputs.total_width_m} m の "
            "鋼プレートガーダー橋の桁配置・主桁本数・桁間隔・パネル長に関する "
            "条文・図・表を探してください。"
        ),
        client=client,
        top_k=top_k,
    )

    rag_results_girder = search_text(
        query=(
            f"橋長 {inputs.bridge_length_m} m のプレートガーダー橋の "
            "主桁断面（桁高・腹板厚さ・フランジ幅・フランジ厚さ）の決め方、 "
            "経済的桁高の目安、h/L の経験式に関する記述を探してください。"
        ),
        client=client,
        top_k=top_k,
    )

    rag_results_deck = search_text(
        query=(
            "RC床版合成桁における床版厚さの決め方、"
            "最小床版厚、床版厚と支間の比の規定、代表的な床版厚の例に関する "
            "条文・図・表を探してください。"
        ),
        client=client,
        top_k=top_k,
    )

    # 2) プロンプト用コンテキスト組み立て
    def _join_chunks(results: list[SearchResult], start_index: int = 1) -> str:
        parts: list[str] = []
        for i, res in enumerate(results, start=start_index):
            c = res.chunk
            parts.append(f"--- Reference {i} ---\n[source={c.source}, page={c.page}]\n{c.text}\n")
        return "\n".join(parts)

    dimensions_context = _join_chunks(rag_results_dimensions, start_index=1)
    girder_context = _join_chunks(
        rag_results_girder,
        start_index=1 + len(rag_results_dimensions),
    )
    deck_context = _join_chunks(
        rag_results_deck,
        start_index=1 + len(rag_results_dimensions) + len(rag_results_girder),
    )

    # 3) 全ヒットをまとめて RAGログを作る（rank を通し番号にする）
    all_results: list[SearchResult] = rag_results_dimensions + rag_results_girder + rag_results_deck
    rag_query = "multi: dimensions/girder/deck"
    rag_log = _build_rag_log(
        query=rag_query,
        top_k=len(all_results),
        results=all_results,
    )

    # 4) プロンプト組み立て
    prompt = DESIGNER_PROMPT.format(
        bridge_length_m=inputs.bridge_length_m,
        total_width_m=inputs.total_width_m,
        dimensions_context=dimensions_context,
        girder_section_context=girder_context,
        deck_context=deck_context,
        other_context="",  # 余力あればここも埋める
    )

    # 5) LLM呼び出し
    designer_output: DesignerOutput = call_llm_with_structured_output(
        input=prompt,
        model=model_name,
        text_format=DesignerOutput,
    )

    # 6) ログに reasoning と rules を追加
    rag_log.reasoning = designer_output.reasoning
    rag_log.rules = designer_output.rules

    # 7) DesignResult に bridge_design + rules を詰めて返す
    return DesignResult(
        design=designer_output.bridge_design,
        rag_log=rag_log,
        rules=designer_output.rules,
    )
