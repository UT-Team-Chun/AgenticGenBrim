from __future__ import annotations

import json
from typing import Sequence

import numpy as np
from openai import OpenAI

from src.bridge_llm_mvp.llm_client import get_llm_client
from src.bridge_llm_mvp.logger_config import get_logger
from src.bridge_llm_mvp.rag.embedding_config import (
    EmbeddingModel,
    IndexChunk,
    IndexFilenames,
    RagIndex,
    SearchResult,
    get_embedding_config,
)

logger = get_logger(__name__)


_RAG_INDEX: RagIndex | None = None


def _load_index() -> RagIndex:
    """メタデータと embedding をメモリにロードする（キャッシュ付き）。

    Returns:
        RagIndex: チャンクと埋め込み行列。
    """
    global _RAG_INDEX

    if _RAG_INDEX is not None:
        return _RAG_INDEX

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
    logger.info("Loaded %d chunks from %s", len(chunks), index_dir)
    logger.info("Loaded embeddings from %s, shape=%s", embeddings_path, embeddings.shape)

    _RAG_INDEX = RagIndex.from_chunks_and_embeddings(
        chunks=chunks,
        embeddings=embeddings,
        dim=embedding_config.dimensions,
    )

    return _RAG_INDEX


def _embed_query(
    query: str,
    client: OpenAI,
    model: EmbeddingModel,
) -> np.ndarray:
    """クエリ1本を embedding ベクトルに変換する。

    Args:
        query: クエリ文字列。
        client: OpenAI クライアント。
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
) -> list[SearchResult]:
    """embedding に基づく類似度検索 (cosine similarity) を行う。

    Args:
        query: 検索クエリ文字列。
        client: OpenAI クライアント。
        top_k: 返却する上位件数。

    Returns:
        list[SearchResult]: 検索結果のリスト。
    """
    rag_index = _load_index()
    embedding_config = get_embedding_config()
    query_vector = _embed_query(query, client=client, model=embedding_config.model)

    return rag_index.search(query_embedding=query_vector, top_k=top_k)


def search_multiple(
    queries: Sequence[str],
    client: OpenAI,
    top_k: int,
) -> list[list[SearchResult]]:
    """複数クエリをまとめて検索する簡易ヘルパー。

    Args:
        queries: 検索クエリ列。
        client: OpenAI クライアント。
        top_k: 各クエリごとに返却する上位件数。

    Returns:
        list[list[SearchResult]]: 各クエリごとの検索結果リスト。
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
        print(f"Query: {query}")
        for result in results[i]:
            print(f"- Score: {result.score:.4f}, Source: {result.chunk.source}, Page: {result.chunk.page}")
            print(f"  Text: {result.chunk.text[:100]}...")
        print()
