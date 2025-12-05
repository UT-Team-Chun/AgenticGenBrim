from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader

load_dotenv()
client = OpenAI()


@dataclass
class TextChunk:
    """RAG 用の最小チャンク。"""

    id: str
    source: str  # PDF ファイル名
    section: str  # 章名など（MVPでは空でOK）
    page: int
    text: str


def extract_text_from_pdf(pdf_path: Path) -> list[str]:
    """PDF 1冊からページごとのテキストを抜き出す。"""
    reader = PdfReader(str(pdf_path))
    texts: list[str] = []

    for page in reader.pages:
        text = page.extract_text() or ""
        texts.append(text)

    return texts


def chunk_text(text: str, max_chars: int = 800) -> list[str]:
    """長いテキストを max_chars ごとにざっくり分割する。"""
    text = text.replace("\n", " ")
    chunks: list[str] = []
    start = 0

    while start < len(text):
        end = start + max_chars
        frag = text[start:end].strip()
        if frag:
            chunks.append(frag)
        start = end

    return chunks


def build_chunks(data_dir: Path) -> list[TextChunk]:
    """data/ 以下の PDF をすべて読んで TextChunk のリストを作る。"""
    chunks: list[TextChunk] = []

    for pdf_path in sorted(data_dir.glob("*.pdf")):
        pages = extract_text_from_pdf(pdf_path)
        for page_idx, page_text in enumerate(pages):
            for frag in chunk_text(page_text):
                chunks.append(
                    TextChunk(
                        id=str(uuid.uuid4()),
                        source=pdf_path.name,
                        section="",  # TODO: 余裕があればしおりから章名を取る
                        page=page_idx,
                        text=frag,
                    ),
                )

    return chunks


def embed_texts(texts: list[str], model: str = "text-embedding-3-small") -> np.ndarray:
    """テキストリストを embedding して 2D array にして返す。"""
    vectors: list[list[float]] = []

    for t in texts:
        resp = client.embeddings.create(model=model, input=t)
        vec = resp.data[0].embedding
        vectors.append(vec)

    return np.array(vectors, dtype="float32")


def build_corpus(
    data_dir: Path = Path("data"),
    index_dir: Path = Path("rag_index"),
) -> None:
    """PDF からチャンクを作り、embedding とメタデータを保存する。"""
    index_dir.mkdir(parents=True, exist_ok=True)
    meta_path = index_dir / "meta.jsonl"
    emb_path = index_dir / "embeddings.npy"

    chunks = build_chunks(data_dir)
    print(f"total chunks: {len(chunks)}")

    texts = [c.text for c in chunks]
    embeddings = embed_texts(texts)

    # メタデータ保存
    with meta_path.open("w", encoding="utf-8") as f:
        for c in chunks:
            json.dump(asdict(c), f, ensure_ascii=False)
            f.write("\n")

    # ベクトル保存
    np.save(emb_path, embeddings)

    print(f"saved meta to {meta_path}")
    print(f"saved embeddings to {emb_path}, shape={embeddings.shape}")


if __name__ == "__main__":
    build_corpus()
