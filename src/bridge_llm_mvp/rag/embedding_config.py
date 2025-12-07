from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from bridge_llm_mvp.config import get_app_config


class IndexFilenames(StrEnum):
    META_FILENAME = "meta.jsonl"
    EMBEDDINGS_FILENAME = "embeddings.npy"


class IndexChunk(BaseModel):
    """RAG インデックスの 1 チャンクを表すモデル。"""

    id: str = Field(..., description="チャンクの一意な ID。")
    source: str = Field(..., description="元となる PDF ファイル名。")
    section: str = Field(..., description="章名など（MVP では空でもよい）。")
    page: int = Field(..., description="元 PDF のページ番号 (0 始まり)。")
    text: str = Field(..., description="チャンク化されたテキスト本文。")


class EmbeddingModel(StrEnum):
    """埋め込みモデル名の定数。"""

    TEXT_EMBEDDING_3_SMALL = "text-embedding-3-small"


class EmbeddingConfig(BaseModel):
    """埋め込みに関する設定。"""

    model_config = ConfigDict(frozen=True)

    model: EmbeddingModel = EmbeddingModel.TEXT_EMBEDDING_3_SMALL
    dimensions: int = 1536
    batch_size: int = 32
    index_dir: Path


@lru_cache(maxsize=1)
def get_embedding_config() -> EmbeddingConfig:
    """Embedding 設定を返す。

    Returns:
        EmbeddingConfig: モデル名・次元数・バッチサイズ・インデックス保存先。
    """
    app_config = get_app_config()
    return EmbeddingConfig(index_dir=app_config.rag_index_dir)
