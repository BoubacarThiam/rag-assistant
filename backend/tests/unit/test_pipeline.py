"""End-to-end processing of a PDF without database (fake embeddings)."""

import math

import pytest

from app.models import EMBEDDING_DIM
from app.services.embeddings import FakeEmbeddingProvider
from app.services.ingestion.extraction import PdfExtractionError
from app.services.ingestion.pipeline import process_pdf
from tests.pdf_factory import make_pdf

BODY = " ".join(
    f"Le chapitre {i} explique la politique de congés et le télétravail." for i in range(1, 25)
)


def test_process_pdf_produces_chunks_with_embeddings() -> None:
    pdf = make_pdf([BODY, BODY, BODY], header="Manuel interne ACME", numbered=True)

    result = process_pdf(pdf, FakeEmbeddingProvider(), chunk_size=100, overlap=20, batch_size=4)

    assert result.page_count == 3
    assert len(result.chunks) == len(result.embeddings) > 1
    assert all(len(v) == EMBEDDING_DIM for v in result.embeddings)
    assert all(math.isclose(math.sqrt(sum(x * x for x in v)), 1.0) for v in result.embeddings)
    # Headers were cleaned before chunking.
    assert not any("Manuel interne ACME" in c.text for c in result.chunks)
    assert result.chunks[-1].page_end == 3


def test_pdf_without_text_is_rejected() -> None:
    with pytest.raises(PdfExtractionError, match="Aucun texte"):
        process_pdf(make_pdf(["", ""]), FakeEmbeddingProvider(), 100, 20, 4)
