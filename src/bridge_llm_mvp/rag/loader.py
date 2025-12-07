from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Sequence

import numpy as np
from openai import OpenAI

from src.bridge_llm_mvp.config import get_app_config
from src.bridge_llm_mvp.llm_client import get_llm_client
from src.bridge_llm_mvp.logger_config import get_logger
from src.bridge_llm_mvp.rag.embedding_config import (
    EmbeddingModel,
    FileNamesUsedForRag,
    IndexChunk,
    IndexFilenames,
    get_embedding_config,
)

logger = get_logger(__name__)

DEFAULT_MAX_CHARS_PER_CHUNK: int = 800


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


def build_chunks(txt_root: Path) -> list[IndexChunk]:
    """TXT ディレクトリから TextChunk のリストを構築する。

    Args:
        txt_root: テキストファイルが格納されたルートディレクトリパス。

    Returns:
        list[IndexChunk]: 抽出されたチャンク一覧。
    """
    chunks: list[IndexChunk] = []

    # RAG で利用する PDF 名に対応する TXT のみを対象にする
    target_filenames = {name.value for name in FileNamesUsedForRag}

    for txt_path in sorted(txt_root.rglob("*.txt")):
        # 元の PDF 名に戻したときに FileNamesUsedForRag に含まれるかで判定
        pdf_like_name = txt_path.with_suffix(".pdf").name
        if pdf_like_name not in target_filenames:
            continue

        text = txt_path.read_text(encoding="utf-8")
        for fragment in chunk_text(text):
            chunks.append(
                IndexChunk(
                    id=str(uuid.uuid4()),
                    source=pdf_like_name,
                    section="",
                    page=0,
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
    total = len(texts)

    for i, text in enumerate(texts):
        if i % 100 == 0:
            logger.info("Embedding %d / %d", i, total)

        response = client.embeddings.create(model=model.value, input=text)
        vector = response.data[0].embedding
        vectors.append(vector)

    return np.array(vectors, dtype=np.float32)


def build_corpus() -> None:
    """PDF からチャンクを作り、embedding とメタデータを保存する。

    Args:
        target_filename: 対象とする PDF ファイル名（例: "foo.pdf"）。
            None の場合は data_dir 配下のすべての PDF を対象とする。
    """
    app_config = get_app_config()
    embedding_config = get_embedding_config()
    client = get_llm_client()
    index_dir = embedding_config.index_dir
    index_dir.mkdir(parents=True, exist_ok=True)
    meta_path = index_dir / IndexFilenames.META_FILENAME
    embeddings_path = index_dir / IndexFilenames.EMBEDDINGS_FILENAME

    # PDF からあらかじめ抽出しておいた TXT を使ってチャンクを構築する
    txt_root = app_config.data_dir / "extracted_by_pdfplumber"
    chunks = build_chunks(txt_root)
    logger.info("Total chunks: %d", len(chunks))

    texts = [chunk.text for chunk in chunks]
    embeddings = embed_texts(texts, client=client, model=embedding_config.model)

    with meta_path.open("w", encoding="utf-8") as file:
        for chunk in chunks:
            json.dump(chunk.model_dump(), file, ensure_ascii=False)
            file.write("\n")

    np.save(embeddings_path, embeddings)

    logger.info("Saved meta to %s", meta_path)
    logger.info("Saved embeddings to %s, shape=%s", embeddings_path, embeddings.shape)


if __name__ == "__main__":
    build_corpus()
