from itertools import pairwise

import pytest

from app.services.ingestion.chunking import chunk_pages, split_sentences
from app.services.ingestion.extraction import PageText


def count_words(text: str) -> int:
    """Simple token counter for tests: 1 word = 1 token."""
    return len(text.split())


def sentence(i: int, words: int = 10) -> str:
    return f"Phrase{i} " + " ".join(["mot"] * (words - 2)) + " fin."


def test_split_sentences_basic() -> None:
    text = "Bonjour à tous. Comment allez-vous ? Très bien ! Parfait…"
    assert split_sentences(text) == [
        "Bonjour à tous.",
        "Comment allez-vous ?",
        "Très bien !",
        "Parfait…",
    ]


def test_split_sentences_ignores_abbreviations_and_initials() -> None:
    text = "M. Dupont cite la p. 12 de J. Martin. Ensuite il part."
    assert split_sentences(text) == ["M. Dupont cite la p. 12 de J. Martin.", "Ensuite il part."]


def test_split_sentences_does_not_split_decimals() -> None:
    assert split_sentences("Le taux est de 3.5 % cette année.") == [
        "Le taux est de 3.5 % cette année."
    ]


def test_split_sentences_respects_paragraphs() -> None:
    assert split_sentences("Titre sans point\n\nTexte.") == ["Titre sans point", "Texte."]


def test_chunks_respect_size_and_never_cut_sentences() -> None:
    sentences = [sentence(i) for i in range(30)]  # 30 sentences x 10 tokens
    pages = [PageText(1, " ".join(sentences))]

    chunks = chunk_pages(pages, count_words, chunk_size=50, overlap=10)

    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.token_count <= 50
        assert chunk.token_count == count_words(chunk.text)
        # Each chunk is made of whole sentences.
        assert all(s in sentences for s in split_sentences(chunk.text))


def test_consecutive_chunks_overlap() -> None:
    pages = [PageText(1, " ".join(sentence(i) for i in range(30)))]

    chunks = chunk_pages(pages, count_words, chunk_size=50, overlap=10)

    for previous, current in pairwise(chunks):
        last_sentence = split_sentences(previous.text)[-1]
        assert split_sentences(current.text)[0] == last_sentence


def test_no_overlap_when_disabled() -> None:
    pages = [PageText(1, " ".join(sentence(i) for i in range(10)))]
    chunks = chunk_pages(pages, count_words, chunk_size=30, overlap=0)
    assert sum(c.token_count for c in chunks) == 100


def test_chunks_track_pages_and_positions() -> None:
    pages = [PageText(n, " ".join(sentence(n * 10 + i) for i in range(4))) for n in (1, 2, 3)]

    chunks = chunk_pages(pages, count_words, chunk_size=50, overlap=0)

    assert [c.position for c in chunks] == list(range(len(chunks)))
    assert chunks[0].page_start == 1
    assert chunks[-1].page_end == 3
    # A chunk can straddle two pages: its range covers both.
    assert any(c.page_start < c.page_end for c in chunks)


def test_very_long_sentence_is_split_on_words() -> None:
    long_sentence = " ".join(f"mot{i}" for i in range(120)) + "."
    chunks = chunk_pages([PageText(1, long_sentence)], count_words, chunk_size=50, overlap=10)

    assert all(c.token_count <= 50 for c in chunks)
    # Nothing is lost.
    assert set(long_sentence.split()) <= {w for c in chunks for w in c.text.split()}


def test_empty_pages_give_no_chunks() -> None:
    assert chunk_pages([PageText(1, ""), PageText(2, "")], count_words, 50, 10) == []


def test_overlap_must_be_smaller_than_size() -> None:
    with pytest.raises(ValueError):
        chunk_pages([PageText(1, "Texte.")], count_words, chunk_size=10, overlap=10)
