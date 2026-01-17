from __future__ import annotations

from pathlib import Path

import pdfplumber

from src.bridge_agentic_generate.config import app_config
from src.bridge_agentic_generate.logger_config import logger
from src.bridge_agentic_generate.rag.embedding_config import FileNamesUsedForRag


def extract_text_from_pdf(pdf_path: Path) -> str:
    """1つのPDFから全文テキストを抽出する（pdfplumber 使用）。

    ページ区切りとして [Page N] を挿入する。
    """
    texts: list[str] = []

    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_index, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            texts.append(text)
            texts.append(f"\n\n[Page {page_index + 1}]\n\n")

    return "".join(texts)


def main(target_filename: str | None = None) -> None:
    pdf_root = app_config.data_dir
    txt_root = pdf_root / "extracted_by_pdfplumber"
    txt_root.mkdir(parents=True, exist_ok=True)

    # FileNamesUsedForRag に列挙されたファイルのみを対象にする。
    # さらに target_filename が指定された場合は、その1ファイルに絞る。
    target_filenames = {name.value for name in FileNamesUsedForRag}
    if target_filename is not None:
        if target_filename not in target_filenames:
            logger.warning(
                "[pdfplumber] target_filename %s is not in FileNamesUsedForRag; processing anyway",
                target_filename,
            )
        # 指定された1ファイルのみに絞る
        target_filenames = {target_filename}

    # data_dir/design_knowledge 以下を再帰的に探索し、対象ファイル名のPDFのみ抽出
    design_knowledge_root = pdf_root / "design_knowledge"
    for pdf_path in sorted(design_knowledge_root.rglob("*.pdf")):
        if pdf_path.name not in target_filenames:
            continue

        # data/design_knowledge 以下の相対パス構造を維持したまま txt を保存
        relative = pdf_path.relative_to(design_knowledge_root)
        txt_path = txt_root / relative
        txt_path = txt_path.with_suffix(".txt")
        txt_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info("[pdfplumber] Extracting text from %s -> %s", pdf_path, txt_path)
        text = extract_text_from_pdf(pdf_path)
        txt_path.write_text(text, encoding="utf-8")

    logger.info("[pdfplumber] PDF to text extraction completed.")


if __name__ == "__main__":
    # 実験として 1 ファイルだけを処理したい場合は、ここに名前を指定する
    # 例: target = "鋼橋設計の基本_第一章 概論.pdf"
    target = None
    main(target_filename=target)
