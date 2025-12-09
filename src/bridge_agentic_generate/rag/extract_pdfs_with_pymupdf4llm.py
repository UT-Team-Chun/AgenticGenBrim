from __future__ import annotations

from pathlib import Path

import pymupdf4llm

from src.bridge_agentic_generate.config import get_app_config
from src.bridge_agentic_generate.logger_config import get_logger
from src.bridge_agentic_generate.rag.embedding_config import FileNamesUsedForRag

logger = get_logger(__name__)


def extract_text_from_pdf(pdf_path: Path) -> str:
    """1つのPDFから全文テキストを抽出する（pymupdf4llm 使用）。

    Markdownとして出力されるが、RAG用途ではプレーンテキストとして扱う。
    force_text_order=True でレイアウト解析を改善する。
    """
    md_text: str = pymupdf4llm.to_markdown(
        str(pdf_path),
        write_images=True,
        # レイアウト解析の改善オプション
        force_text_order=True,  # テキストの読み順を強制的に補正
        use_legacy=False,  # 新しいレイアウト解析エンジンを使用
    )
    return md_text


def main(target_filename: str | None = None) -> None:
    app_config = get_app_config()

    pdf_root = app_config.data_dir
    txt_root = pdf_root / "extracted_by_pymupdf4llm"
    txt_root.mkdir(parents=True, exist_ok=True)

    # FileNamesUsedForRag に列挙されたファイルのみを対象にする。
    # さらに target_filename が指定された場合は、その1ファイルに絞る。
    target_filenames = {name.value for name in FileNamesUsedForRag}
    if target_filename is not None:
        if target_filename not in target_filenames:
            logger.warning(
                "[pymupdf4llm] target_filename %s is not in FileNamesUsedForRag; processing anyway",
                target_filename,
            )
        # 指定された1ファイルのみに絞る
        target_filenames = {target_filename}

    # data_dir/design_knowledge 以下を再帰的に探索し、対象ファイル名のPDFのみ抽出
    design_knowledge_root = pdf_root / "design_knowledge"
    for pdf_path in sorted(design_knowledge_root.rglob("*.pdf")):
        if pdf_path.name not in target_filenames:
            continue

        # data/design_knowledge 以下の相対パス構造を維持したまま md を保存
        relative = pdf_path.relative_to(design_knowledge_root)
        md_path = txt_root / relative
        md_path = md_path.with_suffix(".md")
        md_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info("[pymupdf4llm] Extracting text from %s -> %s", pdf_path, md_path)
        md_text = extract_text_from_pdf(pdf_path)
        md_path.write_text(md_text, encoding="utf-8")

    logger.info("[pymupdf4llm] PDF to text extraction completed.")


if __name__ == "__main__":
    # 実験として 1 ファイルだけを処理したい場合は、ここに名前を指定する
    # 例: target = "鋼橋設計の基本_第一章 概論.pdf"
    target = None
    main(target_filename=target)
