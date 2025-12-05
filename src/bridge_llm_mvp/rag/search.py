from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI()


@dataclass
class ChunkRecord:
    id: str
    source: str
    section: str
    page: int
    text: str


_INDEX_DIR = Path("rag_index")
_META_PATH = _INDEX_DIR / "meta.jsonl"
_EMB_PATH = _INDEX_DIR / "embeddings.npy"

_CHUNKS: list[ChunkRecord] | None = None
_EMBEDDINGS: np.ndarray | None = None


def _load_index() -> tuple[list[ChunkRecord], np.ndarray]:
    """メタデータと embedding をメモリにロードする（キャッシュ付き）。"""
    global _CHUNKS, _EMBEDDINGS

    if _CHUNKS is not None and _EMBEDDINGS is not None:
        return _CHUNKS, _EMBEDDINGS

    chunks: list[ChunkRecord] = []
    with _META_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            chunks.append(
                ChunkRecord(
                    id=obj["id"],
                    source=obj["source"],
                    section=obj.get("section", ""),
                    page=obj["page"],
                    text=obj["text"],
                ),
            )

    embeddings = np.load(_EMB_PATH)

    _CHUNKS = chunks
    _EMBEDDINGS = embeddings

    return chunks, embeddings


def _embed_query(query: str, model: str = "text-embedding-3-small") -> np.ndarray:
    """クエリ1本を embedding ベクトルに変換する。"""
    resp = client.embeddings.create(model=model, input=query)
    vec = np.array(resp.data[0].embedding, dtype="float32")
    return vec


def search_text(query: str, top_k: int = 5) -> list[str]:
    """embedding に基づく類似度検索 (cosine similarity) を行う。

    戻り値は「テキストチャンク」のリスト。
    """
    chunks, embeddings = _load_index()
    q_vec = _embed_query(query)

    # 正規化してコサイン類似度を計算
    emb_norm = embeddings / (np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-8)
    q_norm = q_vec / (np.linalg.norm(q_vec) + 1e-8)

    sims = emb_norm @ q_norm  # shape: (N,)

    top_idx = np.argsort(-sims)[:top_k]
    results: list[str] = []
    for i in top_idx:
        results.append(chunks[int(i)].text)

    return results


def search_multiple(queries: list[str], top_k: int = 5) -> list[list[str]]:
    """複数クエリをまとめて検索する簡易ヘルパー。"""
    return [search_text(q, top_k=top_k) for q in queries]
