"""Generate the evaluation PDFs from eval/corpus.py: python -m eval.build_pdfs

Each page gets a repeated header and a page number, like a real document, so the evaluation
also exercises text cleaning.
"""

from typing import Any

import pymupdf

from eval import PDF_DIR
from eval.corpus import DOCUMENTS, CorpusDocument

PAGE_WIDTH, PAGE_HEIGHT = 595, 842  # A4, in points
MARGIN = 60


def build_pdf(document: CorpusDocument) -> bytes:
    # PyMuPDF's type hints are incomplete: treat its objects as Any.
    pdf: Any = pymupdf.open()  # type: ignore[no-untyped-call]
    for number, text in enumerate(document.pages, start=1):
        page = pdf.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
        page.insert_text((MARGIN, 40), document.header, fontsize=9, color=(0.4, 0.4, 0.4))
        body: Any = pymupdf.Rect(  # type: ignore[no-untyped-call]
            MARGIN, 70, PAGE_WIDTH - MARGIN, PAGE_HEIGHT - 70
        )
        overflow = page.insert_textbox(body, text, fontsize=11, lineheight=1.5)
        if overflow < 0:
            raise ValueError(f"{document.filename} page {number}: text does not fit on the page")
        page.insert_text((PAGE_WIDTH / 2 - 4, PAGE_HEIGHT - 35), str(number), fontsize=9)
    # No timestamps or random ids: the same corpus always gives byte-identical files.
    pdf.set_metadata({"title": document.header, "creationDate": "", "modDate": ""})
    data: bytes = pdf.tobytes(deflate=True, no_new_id=True)
    return data


def main() -> None:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    for document in DOCUMENTS:
        path = PDF_DIR / document.filename
        path.write_bytes(build_pdf(document))
        print(f"{path.name}: {len(document.pages)} pages, {path.stat().st_size // 1024} Ko")


if __name__ == "__main__":
    main()
