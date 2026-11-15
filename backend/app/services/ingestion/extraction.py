"""PDF text extraction, page by page (PyMuPDF)."""

from dataclasses import dataclass
from typing import Any

import pymupdf


@dataclass(frozen=True)
class PageText:
    number: int  # 1-based, as displayed in a PDF reader
    text: str


class PdfExtractionError(Exception):
    """The PDF cannot be used. The message is shown to the user (in French)."""


def extract_pages(data: bytes) -> list[PageText]:
    try:
        # PyMuPDF's type hints are incomplete: treat its objects as Any at this boundary.
        document: Any = pymupdf.open(stream=data, filetype="pdf")  # type: ignore[no-untyped-call]
    except Exception as exc:  # PyMuPDF raises several error types for broken files
        raise PdfExtractionError("Le fichier PDF est illisible ou corrompu.") from exc

    with document:
        if document.needs_pass:
            raise PdfExtractionError("Le PDF est protégé par un mot de passe.")
        if document.page_count == 0:
            raise PdfExtractionError("Le PDF ne contient aucune page.")
        # sort=True: reading order (top-left to bottom-right) rather than internal PDF order.
        return [
            PageText(number=index + 1, text=page.get_text("text", sort=True))
            for index, page in enumerate(document)
        ]
