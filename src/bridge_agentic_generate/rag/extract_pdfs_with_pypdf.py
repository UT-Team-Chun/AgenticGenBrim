from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

from src.bridge_agentic_generate.config import get_app_config
from src.bridge_agentic_generate.logger_config import get_logger
from src.bridge_agentic_generate.rag.embedding_config import FileNamesUsedForRag

logger = get_logger(__name__)


def extract_text_from_pdf(pdf_path: Path) -> str:
    """1つのPDFから全文テキストを抽出する。

    ページ区切りとして改行を挿入するだけの素朴な実装。
    """
    reader = PdfReader(str(pdf_path))
    texts: list[str] = []

    for page_index, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        texts.append(text)
        # ページ区切りとして空行を入れておく
        texts.append(f"\n\n[Page {page_index + 1}]\n\n")

    return "".join(texts)


def main() -> None:
    app_config = get_app_config()

    pdf_root = app_config.data_dir
    txt_root = pdf_root / "extracted_by_pypdf"
    txt_root.mkdir(parents=True, exist_ok=True)

    target_filenames = {name.value for name in FileNamesUsedForRag}

    # data_dir/design_knowledge 以下を再帰的に探索し、対象ファイル名のPDFのみ抽出
    for pdf_path in sorted(pdf_root.joinpath("design_knowledge").rglob("*.pdf")):
        if pdf_path.name not in target_filenames:
            continue

        # data/design_knowledge 以下の相対パス構造を維持したまま txt を保存
        relative = pdf_path.relative_to(pdf_root.joinpath("design_knowledge"))
        txt_path = txt_root / relative
        txt_path = txt_path.with_suffix(".txt")
        txt_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info("Extracting text from %s -> %s", pdf_path, txt_path)
        text = extract_text_from_pdf(pdf_path)
        txt_path.write_text(text, encoding="utf-8")

    logger.info("PDF to text extraction completed.")


if __name__ == "__main__":
    main()
