import pytest

from app.services.ingestion.extraction import PdfExtractionError, extract_pages
from tests.pdf_factory import make_pdf


def test_extracts_text_page_by_page_with_page_numbers() -> None:
    pages = extract_pages(make_pdf(["Première page, été.", "Deuxième page."]))

    assert [p.number for p in pages] == [1, 2]
    assert "Première page, été." in pages[0].text
    assert "Deuxième page." in pages[1].text


def test_corrupted_file_is_rejected() -> None:
    with pytest.raises(PdfExtractionError, match="illisible"):
        extract_pages(b"%PDF-1.7 this is not really a pdf")


def test_password_protected_pdf_is_rejected() -> None:
    with pytest.raises(PdfExtractionError, match="mot de passe"):
        extract_pages(make_pdf(["Secret."], password="1234"))
