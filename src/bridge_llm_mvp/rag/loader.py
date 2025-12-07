from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Sequence

import numpy as np
from openai import OpenAI
from pypdf import PdfReader

from src.bridge_llm_mvp.config import get_app_config
from src.bridge_llm_mvp.llm_client import get_llm_client
from src.bridge_llm_mvp.logger_config import get_logger
from src.bridge_llm_mvp.rag.embedding_config import EmbeddingModel, IndexChunk, IndexFilenames, get_embedding_config

logger = get_logger(__name__)

DEFAULT_MAX_CHARS_PER_CHUNK: int = 800


def extract_text_from_pdf(pdf_path: Path) -> list[str]:
    """PDF 1冊からページごとのテキストを抜き出す。

    Args:
        pdf_path: 対象となる PDF ファイルパス。

    Returns:
        list[str]: ページごとのテキスト一覧。
    """
    reader = PdfReader(str(pdf_path))
    texts: list[str] = []

    for page in reader.pages:
        text = page.extract_text() or ""
        texts.append(text)

    return texts


def chunk_text(
    text: str,
    max_chars: int = DEFAULT_MAX_CHARS_PER_CHUNK,
) -> list[str]:
    """長いテキストを max_chars ごとにざっくり分割する。

    Args:
        text: 分割対象のテキスト。
        max_chars: 1 チャンクあたりの最大文字数。

    Returns:
        list[str]: 分割後のテキストチャンク一覧。
    """
    text = text.replace("\n", " ")
    chunks: list[str] = []
    start = 0

    while start < len(text):
        end = start + max_chars
        fragment = text[start:end].strip()
        if fragment:
            chunks.append(fragment)
        start = end

    return chunks


def build_chunks(data_dir: Path) -> list[IndexChunk]:
    """PDF ディレクトリから TextChunk のリストを構築する。

    Args:
        data_dir: PDF が格納されたディレクトリパス。

    Returns:
        list[IndexChunk]: 抽出されたチャンク一覧。
    """
    chunks: list[IndexChunk] = []

    for pdf_path in sorted(data_dir.glob("*.pdf")):
        pages = extract_text_from_pdf(pdf_path)
        for page_index, page_text in enumerate(pages):
            for fragment in chunk_text(page_text):
                chunks.append(
                    IndexChunk(
                        id=str(uuid.uuid4()),
                        source=pdf_path.name,
                        section="",
                        page=page_index,
                        text=fragment,
                    ),
                )

    return chunks


def embed_texts(
    texts: Sequence[str],
    client: OpenAI,
    model: EmbeddingModel,
) -> np.ndarray:
    """テキストリストを embedding して 2D array にして返す。

    Args:
        texts: 埋め込み対象のテキスト列。
        client: OpenAI クライアント。
        model: 使用する埋め込みモデル。

    Returns:
        np.ndarray: shape=(N, D) の埋め込み行列。
    """
    vectors: list[list[float]] = []

    for text in texts:
        response = client.embeddings.create(model=model.value, input=text)
        vector = response.data[0].embedding
        vectors.append(vector)

    return np.array(vectors, dtype=np.float32)


def build_corpus() -> None:
    """PDF からチャンクを作り、embedding とメタデータを保存する。"""
    app_config = get_app_config()
    embedding_config = get_embedding_config()
    client = get_llm_client()
    index_dir = embedding_config.index_dir
    index_dir.mkdir(parents=True, exist_ok=True)
    meta_path = index_dir / IndexFilenames.META_FILENAME
    embeddings_path = index_dir / IndexFilenames.EMBEDDINGS_FILENAME

    chunks = build_chunks(app_config.data_dir)
    logger.info("Total chunks: %d", len(chunks))

    texts = [chunk.text for chunk in chunks]
    embeddings = embed_texts(texts, client=client, model=embedding_config.model)

    with meta_path.open("w", encoding="utf-8") as file:
        for chunk in chunks:
            json.dump(asdict(chunk), file, ensure_ascii=False)
            file.write("\n")

    np.save(embeddings_path, embeddings)

    logger.info("Saved meta to %s", meta_path)
    logger.info("Saved embeddings to %s, shape=%s", embeddings_path, embeddings.shape)


if __name__ == "__main__":
    build_corpus()
