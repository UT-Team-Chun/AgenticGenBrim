# src/bridge_llm_mvp/rag/debug_extract.py
from __future__ import annotations

from pathlib import Path

import fire
from pypdf import PdfReader


def debug_extract(pdf_path: Path, output_dir: Path | str = Path("data/extracted"), max_pages: int = 3) -> None:
    """PDF からテキストを抜き出して、最初の数ページ分を表示するデバッグ用スクリプト。

    全ページのテキストを指定した `output_dir` に保存する。

    Args:
        pdf_path: 抽出対象の PDF ファイルパス。
        output_dir: 出力ディレクトリ（Path または文字列）。デフォルトは `data/extracted`。
        max_pages: コンソールに表示するページ数（ファイル保存は全ページ）。
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    reader = PdfReader(str(pdf_path))
    num_pages = len(reader.pages)
    print(f"PDF: {pdf_path.name}")
    print(f"Total pages: {num_pages}")
    print("-" * 40)

    # 保存先ディレクトリ作成
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    output_file = out_dir / f"{pdf_path.stem}.txt"

    with output_file.open("w", encoding="utf-8") as f:
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""

            # ファイルに書き込み
            f.write(f"--- Page {i + 1} ---\n")
            f.write(text)
            f.write("\n\n")

            # コンソール表示（max_pages まで）
            if i < max_pages:
                print(f"--- Page {i + 1} ---")
                # 長すぎると読みにくいので先頭だけ表示
                print(text[:800])
                print("\n" + "=" * 40 + "\n")

    print(f"Full text saved to: {output_file}")


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


def main(input_path: Path | None = None, output_dir: Path | str = Path("data/extracted"), max_pages: int = 3) -> None:
    """実行用メイン。ファイルまたはディレクトリを受け取り処理する。

    Args:
        input_path: PDF ファイルまたは PDF を含むディレクトリ。None の場合は既定のフォルダを使用。
        output_dir: 出力ディレクトリパス。
        max_pages: コンソール表示する最大ページ数。
    """
    # デフォルトのフォルダ（従来の動作を維持）
    default_folder = Path("data/design_knowledge/鋼橋設計の基本")
    exclude_pdfs = ["鋼橋設計の基本.pdf", "道路橋示方書.pdf"]  # 全体 PDF は除外

    if input_path is None:
        pdf_paths = [p for p in default_folder.glob("*.pdf") if p.name not in exclude_pdfs]
    else:
        p = Path(input_path)
        if p.is_dir():
            pdf_paths = [pp for pp in p.glob("*.pdf") if pp.name not in exclude_pdfs]
        else:
            pdf_paths = [p]

    for pdf_path in pdf_paths:
        debug_extract(pdf_path, output_dir=output_dir, max_pages=max_pages)
        debug_extract_and_chunk(pdf_path, page_index=2)


if __name__ == "__main__":
    # example
    # uv run python debug_extract.py
    # --input_path data/design_knowledge/鋼橋設計の基本
    # --output_dir data/extracted_by_pypdf/鋼橋設計の基本
    fire.Fire(main)
