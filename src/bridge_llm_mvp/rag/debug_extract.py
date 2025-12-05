# src/bridge_llm_mvp/rag/debug_extract.py
from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader


def debug_extract(pdf_path: Path, max_pages: int = 3) -> None:
    """PDF からテキストを抜き出して、最初の数ページ分を表示するデバッグ用スクリプト。"""
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    reader = PdfReader(str(pdf_path))
    num_pages = len(reader.pages)
    print(f"PDF: {pdf_path.name}")
    print(f"Total pages: {num_pages}")
    print("-" * 40)

    for i in range(min(num_pages, max_pages)):
        page = reader.pages[i]
        text = page.extract_text() or ""
        print(f"--- Page {i + 1} ---")
        # 長すぎると読みにくいので先頭だけ表示
        print(text[:800])
        print("\n" + "=" * 40 + "\n")


def chunk_text(text: str, max_chars: int = 400) -> list[str]:
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


def debug_extract_and_chunk(pdf_path: Path, page_index: int = 0) -> None:
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    reader = PdfReader(str(pdf_path))
    page = reader.pages[page_index]
    text = page.extract_text() or ""

    print("=== Raw text (first 400 chars) ===")
    print(text[:400])
    print("\n=== Chunked ===")

    chunks = chunk_text(text, max_chars=400)
    for i, c in enumerate(chunks):
        print(f"[chunk {i}] {c[:200]}...")
        print("-" * 40)


def main() -> None:
    # ここを自分の PDF 名に合わせて変える
    pdf_path = Path("data/design_knowledge/鋼橋設計の基本/鋼橋設計の基本_第七章 プレートガーダー橋.pdf")
    debug_extract(pdf_path, max_pages=3)
    debug_extract_and_chunk(pdf_path, page_index=2)


if __name__ == "__main__":
    main()
