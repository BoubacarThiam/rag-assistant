"""Chunking: split cleaned pages into passages of ~N tokens, with overlap, never cutting a sentence.

Why chunks? A whole document as one vector would blur its meaning, and the LLM only needs the
relevant passages. Why overlap? An idea that straddles two chunks stays complete in at least one.

Algorithm (greedy):
1. Split each page into sentences ("units"), each tagged with its page and token count.
   A sentence longer than the chunk size (rare: tables, lists without punctuation) is split on
   word boundaries, otherwise the embedding model would silently truncate it.
2. Add units to the current chunk until the next one would exceed the size.
3. Emit the chunk; start the next one with the last sentences of the previous one, up to
   `overlap` tokens.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass

from app.services.ingestion.extraction import PageText

TokenCounter = Callable[[str], int]

# A sentence ends with . ! ? or … , followed by whitespace and an uppercase letter / digit / quote.
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?…])[\"»”)\]]*\s+(?=[\"«“(\[]?[A-ZÀ-ÖØ-Þ0-9])")
# Abbreviations that end with a dot without ending the sentence ("M. Dupont", "p. 12").
ABBREVIATIONS = {
    "m", "mm", "mme", "mmes", "mlle", "dr", "pr", "me", "st", "ste", "p", "pp", "ex", "cf", "art",
    "al", "vol", "fig", "chap", "env", "n", "no", "mr", "mrs", "ms", "vs", "etc", "av", "bd",
}  # fmt: skip
LAST_WORD_RE = re.compile(r"(\w+)\.$")


@dataclass(frozen=True)
class ChunkDraft:
    position: int
    text: str
    page_start: int
    page_end: int
    token_count: int


@dataclass(frozen=True)
class _Unit:
    text: str
    page: int
    tokens: int


def _ends_with_abbreviation(sentence: str) -> bool:
    match = LAST_WORD_RE.search(sentence)
    if not match:
        return False
    word = match.group(1)
    is_initial = len(word) == 1 and word.isupper()  # "J. Martin"
    return is_initial or word.lower() in ABBREVIATIONS


def split_sentences(text: str) -> list[str]:
    sentences: list[str] = []
    for paragraph in text.split("\n\n"):
        pending = ""
        for part in SENTENCE_SPLIT_RE.split(paragraph):
            part = part.strip()
            if not part:
                continue
            pending = f"{pending} {part}" if pending else part
            if not _ends_with_abbreviation(pending):
                sentences.append(pending)
                pending = ""
        if pending:
            sentences.append(pending)
    return sentences


def _split_long_sentence(
    sentence: str, page: int, max_tokens: int, count: TokenCounter
) -> list[_Unit]:
    units: list[_Unit] = []
    current: list[str] = []
    for word in sentence.split():
        candidate = " ".join([*current, word])
        if current and count(candidate) > max_tokens:
            text = " ".join(current)
            units.append(_Unit(text, page, count(text)))
            current = [word]
        else:
            current.append(word)
    if current:
        text = " ".join(current)
        units.append(_Unit(text, page, count(text)))
    return units


def _to_units(pages: list[PageText], max_tokens: int, count: TokenCounter) -> list[_Unit]:
    units: list[_Unit] = []
    for page in pages:
        for sentence in split_sentences(page.text):
            tokens = count(sentence)
            if tokens > max_tokens:
                units.extend(_split_long_sentence(sentence, page.number, max_tokens, count))
            else:
                units.append(_Unit(sentence, page.number, tokens))
    return units


def _overlap_tail(units: list[_Unit], overlap_tokens: int) -> list[_Unit]:
    """Last sentences of a chunk, up to `overlap_tokens` (never the whole chunk)."""
    tail: list[_Unit] = []
    total = 0
    for unit in reversed(units[1:]):
        if total + unit.tokens > overlap_tokens:
            break
        tail.insert(0, unit)
        total += unit.tokens
    return tail


def _make_chunk(position: int, units: list[_Unit]) -> ChunkDraft:
    return ChunkDraft(
        position=position,
        text=" ".join(unit.text for unit in units),
        page_start=min(unit.page for unit in units),
        page_end=max(unit.page for unit in units),
        token_count=sum(unit.tokens for unit in units),
    )


def chunk_pages(
    pages: list[PageText], count_tokens: TokenCounter, chunk_size: int, overlap: int
) -> list[ChunkDraft]:
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks: list[ChunkDraft] = []
    current: list[_Unit] = []
    current_tokens = 0

    for unit in _to_units(pages, chunk_size, count_tokens):
        if current and current_tokens + unit.tokens > chunk_size:
            chunks.append(_make_chunk(len(chunks), current))
            current = _overlap_tail(current, overlap)
            current_tokens = sum(u.tokens for u in current)
            # The overlap must leave room for the new sentence.
            while current and current_tokens + unit.tokens > chunk_size:
                current_tokens -= current.pop(0).tokens
        current.append(unit)
        current_tokens += unit.tokens

    if current:
        chunks.append(_make_chunk(len(chunks), current))
    return chunks
