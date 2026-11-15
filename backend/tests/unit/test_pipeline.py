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


class RecordingEmbedder(FakeEmbeddingProvider):
    def __init__(self) -> None:
        super().__init__()
        self.texts: list[str] = []

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.texts.extend(texts)
        return super().embed_documents(texts)


def test_document_title_is_added_to_the_embedded_text_only() -> None:
    embedder = RecordingEmbedder()

    result = process_pdf(
        make_pdf([BODY]), embedder, 100, 20, 4, title_from="guide-salarie_acme.pdf"
    )

    assert all(text.startswith("Document : guide salarie acme\n") for text in embedder.texts)
    # What is stored and shown to the user stays the original text.
    assert not any("Document :" in chunk.text for chunk in result.chunks)
    assert [text.split("\n", 1)[1] for text in embedder.texts] == [c.text for c in result.chunks]


def test_no_title_by_default() -> None:
    embedder = RecordingEmbedder()
    process_pdf(make_pdf([BODY]), embedder, 100, 20, 4)
    assert not any("Document :" in text for text in embedder.texts)
