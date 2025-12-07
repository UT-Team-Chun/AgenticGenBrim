from __future__ import annotations

import json
from typing import Sequence

import numpy as np
from openai import OpenAI
from pydantic import BaseModel, Field

from src.bridge_llm_mvp.config import get_app_config
from src.bridge_llm_mvp.llm_client import get_llm_client
from src.bridge_llm_mvp.logger_config import get_logger
from src.bridge_llm_mvp.rag.embedding_config import EmbeddingModel, IndexChunk, IndexFilenames, get_embedding_config

logger = get_logger(__name__)

NUMERIC_STABILITY_EPSILON: float = 1e-8


_CHUNKS: list[IndexChunk] | None = None
_EMBEDDINGS: np.ndarray | None = None


class RagIndex(BaseModel):
    """RAG インデックス全体を表すモデル。"""

    chunks: list[IndexChunk] = Field(..., description="チャンクメタデータの一覧。")
    embeddings: np.ndarray = Field(..., description="チャンクごとの埋め込み行列。")


def _load_index() -> RagIndex:
    """メタデータと embedding をメモリにロードする（キャッシュ付き）。

    Returns:
        RagIndex: チャンクと埋め込み行列。
    """
    global _CHUNKS, _EMBEDDINGS

    if _CHUNKS is not None and _EMBEDDINGS is not None:
        return RagIndex(chunks=_CHUNKS, embeddings=_EMBEDDINGS)

    app_config = get_app_config()
    embedding_config = get_embedding_config()
    index_dir = embedding_config.index_dir
    meta_path = index_dir / IndexFilenames.META_FILENAME
    embeddings_path = index_dir / IndexFilenames.EMBEDDINGS_FILENAME

    chunks: list[IndexChunk] = []
    with meta_path.open("r", encoding="utf-8") as file:
        for line in file:
            obj = json.loads(line)
            chunks.append(
                IndexChunk(
                    id=obj["id"],
                    source=obj["source"],
                    section=obj.get("section", ""),
                    page=obj["page"],
                    text=obj["text"],
                ),
            )

    embeddings = np.load(embeddings_path)
    logger.info("Loaded %d chunks from %s", len(chunks), app_config.rag_index_dir)
    logger.info("Loaded embeddings from %s, shape=%s", embeddings_path, embeddings.shape)

    _CHUNKS = chunks
    _EMBEDDINGS = embeddings

    return RagIndex(chunks=chunks, embeddings=embeddings)


def _embed_query(
    query: str,
    client: OpenAI,
    model: EmbeddingModel,
) -> np.ndarray:
    """クエリ1本を embedding ベクトルに変換する。

    Args:
        query: クエリ文字列。
        model: 使用する埋め込みモデル。

    Returns:
        np.ndarray: shape=(D,) のベクトル。
    """
    response = client.embeddings.create(model=model.value, input=query)
    vector = np.array(response.data[0].embedding, dtype=np.float32)
    return vector


def search_text(
    query: str,
    client: OpenAI,
    top_k: int,
) -> list[str]:
    """embedding に基づく類似度検索 (cosine similarity) を行う。

    Args:
        query: 検索クエリ文字列。
        top_k: 返却する上位件数。

    Returns:
        list[str]: 類似度の高いテキストチャンク。
    """
    rag_index = _load_index()
    embedding_config = get_embedding_config()
    query_vector = _embed_query(query, client=client, model=embedding_config.model)

    # 正規化してコサイン類似度を計算
    embeddings_norm = rag_index.embeddings / (
        np.linalg.norm(rag_index.embeddings, axis=1, keepdims=True) + NUMERIC_STABILITY_EPSILON
    )
    query_norm = query_vector / (np.linalg.norm(query_vector) + NUMERIC_STABILITY_EPSILON)

    similarities = embeddings_norm @ query_norm

    indices = np.argsort(-similarities)[:top_k]
    results: list[str] = []
    for index in indices:
        results.append(rag_index.chunks[int(index)].text)

    return results


def search_multiple(
    queries: Sequence[str],
    client: OpenAI,
    top_k: int,
) -> list[list[str]]:
    """複数クエリをまとめて検索する簡易ヘルパー。

    Args:
        queries: 検索クエリ列。
        top_k: 各クエリごとに返却する上位件数。

    Returns:
        list[list[str]]: 各クエリごとの検索結果リスト。
    """
    return [search_text(query, client=client, top_k=top_k) for query in queries]


if __name__ == "__main__":
    # 簡易テスト
    client = get_llm_client()
    test_queries = [
        "鋼橋の設計における主要な考慮事項は何ですか？",
        "橋梁の耐荷性能を評価する方法を教えてください。",
    ]
    results = search_multiple(test_queries, client=client, top_k=2)
    for i, query in enumerate(test_queries):
        print(f"=== Query {i + 1}: {query} ===")
        for j, text in enumerate(results[i]):
            print(f"[Result {j + 1}] {text[:200]}...")
            print("-" * 40)
