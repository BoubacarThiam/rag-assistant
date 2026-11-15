"""Text cleaning: raw PDF text is full of layout noise that hurts retrieval.

- Unicode normalization (ligatures "ﬁ" -> "fi", non-breaking spaces, soft hyphens)
- Repeated headers/footers and page numbers removed (they would pollute every chunk)
- Words hyphenated across lines rejoined ("infor-\\nmation" -> "information")
- Line breaks inside paragraphs replaced with spaces, whitespace collapsed
"""

import math
import re
import unicodedata
from collections import Counter

from app.services.ingestion.extraction import PageText

# Headers/footers are only searched among the first/last lines of each page.
EDGE_LINES = 3
# A line is a header/footer if it appears on at least this share of pages (and >= 3 pages).
REPEATED_LINE_RATIO = 0.5
MIN_PAGES_FOR_REPEATED = 3

PAGE_NUMBER_RE = re.compile(r"^\s*(page\s*)?\d{1,4}(\s*(/|sur|of)\s*\d{1,4})?\s*$", re.IGNORECASE)
# "infor-\nmation" -> "information" (next line starts in lowercase: a word cut in two)
HYPHEN_LOWER_RE = re.compile(r"(\w)-\n\s*(?=[a-zà-öø-ÿ])")
# "Jean-\nPierre" -> "Jean-Pierre" (next line starts in uppercase: a real compound word)
HYPHEN_UPPER_RE = re.compile(r"(\w)-\n\s*(?=[A-ZÀ-ÖØ-Þ])")
PARAGRAPH_BREAK_RE = re.compile(r"\n\s*\n")
SPACES_RE = re.compile(r"[ \t\f\v]+")
SOFT_HYPHEN = chr(0xAD)  # invisible hyphenation hint left by some PDF generators


def _line_key(line: str, page_number: int) -> str:
    """Comparison key: the page's own number is masked, so "ACME - p. 3" on page 3 and
    "ACME - p. 4" on page 4 match. Other numbers are kept: masking every digit would make
    body lines like "Total 2024: 12" and "Total 2025: 15" look like a repeated header."""
    return re.sub(rf"(?<!\d){page_number}(?!\d)", "#", line.strip().lower())


def _edge_indices(lines: list[str]) -> list[int]:
    non_empty = [i for i, line in enumerate(lines) if line.strip()]
    return sorted(set(non_empty[:EDGE_LINES] + non_empty[-EDGE_LINES:]))


def find_repeated_lines(pages_lines: list[list[str]], page_numbers: list[int]) -> set[str]:
    if len(pages_lines) < MIN_PAGES_FOR_REPEATED:
        return set()
    counter: Counter[str] = Counter()
    for lines, number in zip(pages_lines, page_numbers, strict=True):
        counter.update({_line_key(lines[i], number) for i in _edge_indices(lines)})
    threshold = max(MIN_PAGES_FOR_REPEATED, math.ceil(len(pages_lines) * REPEATED_LINE_RATIO))
    return {key for key, count in counter.items() if key and count >= threshold}


def normalize_unicode(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    return text.replace(SOFT_HYPHEN, "").replace("\r\n", "\n").replace("\r", "\n")


def clean_text(text: str) -> str:
    text = HYPHEN_LOWER_RE.sub(r"\1", text)
    text = HYPHEN_UPPER_RE.sub(r"\1-", text)
    paragraphs = [
        SPACES_RE.sub(" ", paragraph.replace("\n", " ")).strip()
        for paragraph in PARAGRAPH_BREAK_RE.split(text)
    ]
    return "\n\n".join(p for p in paragraphs if p)


def clean_pages(pages: list[PageText]) -> list[PageText]:
    pages_lines = [normalize_unicode(page.text).split("\n") for page in pages]
    repeated = find_repeated_lines(pages_lines, [page.number for page in pages])

    cleaned: list[PageText] = []
    for page, lines in zip(pages, pages_lines, strict=True):
        edges = set(_edge_indices(lines))
        kept = [
            line
            for i, line in enumerate(lines)
            if i not in edges
            or (_line_key(line, page.number) not in repeated and not PAGE_NUMBER_RE.match(line))
        ]
        cleaned.append(PageText(number=page.number, text=clean_text("\n".join(kept))))
    return cleaned
