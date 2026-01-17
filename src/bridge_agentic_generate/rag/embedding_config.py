from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Sequence

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from src.bridge_agentic_generate.config import app_config

NUMERIC_STABILITY_EPSILON: float = 1e-8
EMBEDDING_DIMENSION: int = 1536
EMBEDDING_BATCH_SIZE: int = 32
TOP_K: int = 5


class FileNamesUsedForRag(StrEnum):
    """RAG で利用する PDF ファイル名。"""

    TEXT_1 = "鋼橋設計の基本_第一章 概論.pdf"
    TEXT_4 = "鋼橋設計の基本_第四章 鋼橋の設計法.pdf"
    TEXT_6 = "鋼橋設計の基本_第六章 床版.pdf"
    TEXT_7 = "鋼橋設計の基本_第七章 プレートガーダー橋.pdf"
    SPECIFICATION_STEEL = "道路橋示方書_鋼橋・鋼部材編.pdf"


class IndexFilenames(StrEnum):
    """インデックスファイル名。"""

    META_FILENAME = "meta.jsonl"
    EMBEDDINGS_FILENAME = "embeddings.npy"


class IndexChunk(BaseModel):
    """RAG インデックスの 1 チャンクを表すモデル。"""

    id: str = Field(..., description="チャンクの一意な ID。")
    source: str = Field(..., description="元となる PDF ファイル名。")
    section: str = Field(..., description="章名など（MVP では空でもよい）。")
    page: int = Field(..., description="元 PDF のページ番号 (0 始まり)。")
    text: str = Field(..., description="チャンク化されたテキスト本文。")


class SearchResult(BaseModel):
    """検索結果の 1 件を表すモデル。"""

    chunk: IndexChunk = Field(..., description="マッチしたチャンク。")
    score: float = Field(..., description="コサイン類似度スコア。")


class RagIndex(BaseModel):
    """検索用インデックス。

    - chunks: メタデータ
    - _embeddings: 検索用ベクトル (num_chunks, dim)
    """

    chunks: list[IndexChunk] = Field(..., description="チャンクメタデータ一覧")
    dim: int = Field(EMBEDDING_DIMENSION, description="埋め込み次元（固定）")

    # ランタイム専用の埋め込み行列（JSONには出さない）
    _embeddings: NDArray[np.float32] = PrivateAttr(
        default_factory=lambda: np.empty((0, EMBEDDING_DIMENSION), dtype=np.float32)
    )

    @classmethod
    def from_chunks_and_embeddings(
        cls,
        chunks: Sequence[IndexChunk],
        embeddings: NDArray[np.float32] | Sequence[Sequence[float]],
        dim: int = EMBEDDING_DIMENSION,
    ) -> RagIndex:
        """チャンクと埋め込みから RagIndex を生成する。

        Args:
            chunks: チャンクメタデータのシーケンス。
            embeddings: 埋め込み行列 (num_chunks, dim)。
            dim: 埋め込み次元。

        Returns:
            RagIndex: 正規化済み埋め込みを持つインデックス。

        Raises:
            ValueError: 形状が不正な場合。
        """
        arr = np.asarray(embeddings, dtype=np.float32)

        if arr.ndim != 2:
            raise ValueError(f"embeddings.ndim must be 2, got {arr.ndim}")
        if arr.shape[1] != dim:
            raise ValueError(f"embeddings.shape[1] must be {dim}, got {arr.shape[1]}")
        if arr.shape[0] != len(chunks):
            raise ValueError(f"num_embeddings ({arr.shape[0]}) must match num_chunks ({len(chunks)})")

        # 正規化しておくと検索時に内積=コサイン類似度になる
        norms = np.linalg.norm(arr, axis=1, keepdims=True) + NUMERIC_STABILITY_EPSILON
        arr = arr / norms

        obj = cls(chunks=list(chunks), dim=dim)
        obj._embeddings = arr
        return obj

    def search(
        self,
        query_embedding: NDArray[np.float32] | Sequence[float],
        top_k: int = TOP_K,
    ) -> list[SearchResult]:
        """クエリ埋め込みに対して上位 top_k のチャンクを返す（内積スコア）。

        Args:
            query_embedding: クエリの埋め込みベクトル (dim,).
            top_k: 返却する上位件数。

        Returns:
            list[SearchResult]: 検索結果のリスト。

        Raises:
            ValueError: クエリ埋め込みの形状が不正な場合。
        """
        if self._embeddings.size == 0:
            return []

        q = np.asarray(query_embedding, dtype=np.float32)
        if q.ndim != 1:
            raise ValueError(f"query_embedding.ndim must be 1, got {q.ndim}")
        if q.shape[0] != self.dim:
            raise ValueError(f"query_embedding length must be {self.dim}, got {q.shape[0]}")

        # クエリも正規化
        q = q / (np.linalg.norm(q) + NUMERIC_STABILITY_EPSILON)

        # (num_chunks, dim) · (dim,) -> (num_chunks,)
        scores = self._embeddings @ q

        top_k = min(top_k, scores.shape[0])
        if top_k <= 0:
            return []

        # 上位 top_k のインデックスを取得
        idx = np.argpartition(-scores, top_k - 1)[:top_k]
        idx = idx[np.argsort(-scores[idx])]

        return [SearchResult(chunk=self.chunks[i], score=float(scores[i])) for i in idx]


class EmbeddingModel(StrEnum):
    """埋め込みモデル名の定数。"""

    TEXT_EMBEDDING_3_SMALL = "text-embedding-3-small"


class EmbeddingConfig(BaseModel):
    """埋め込みに関する設定。"""

    model_config = ConfigDict(frozen=True)

    model: EmbeddingModel = EmbeddingModel.TEXT_EMBEDDING_3_SMALL
    dimensions: int = EMBEDDING_DIMENSION
    batch_size: int = EMBEDDING_BATCH_SIZE
    index_dir: Path


@lru_cache(maxsize=1)
def get_embedding_config() -> EmbeddingConfig:
    """Embedding 設定を返す。

    Returns:
        EmbeddingConfig: モデル名・次元数・バッチサイズ・インデックス保存先。
    """
    return EmbeddingConfig(index_dir=app_config.rag_index_dir_plumber)
