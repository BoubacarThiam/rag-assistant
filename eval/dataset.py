"""Evaluation questions: loading, validation, and the rule that says whether a retrieved
passage is the right one."""

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from eval import DATASET_PATH

QuestionType = Literal["factual", "paraphrase", "keyword", "multi", "unanswerable"]
QUESTION_TYPES: tuple[QuestionType, ...] = (
    "factual",
    "paraphrase",
    "keyword",
    "multi",
    "unanswerable",
)


@dataclass(frozen=True)
class Evidence:
    """Where the answer is: a short verbatim quote, in a given document and page."""

    document: str
    page: int
    quote: str


@dataclass(frozen=True)
class Question:
    id: str
    type: QuestionType
    question: str
    expected_answer: str | None
    evidence: tuple[Evidence, ...]

    @property
    def answerable(self) -> bool:
        return self.type != "unanswerable"


def normalize(text: str) -> str:
    """Comparison form: same Unicode form, single spaces, lowercase."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text)).strip().lower()


def contains_evidence(document_name: str, passage: str, evidence: Evidence) -> bool:
    """A passage is relevant if it comes from the right document and contains the quote.

    Matching on the quote rather than on a chunk id keeps the ground truth valid when the
    chunk size or overlap changes (Phase 7), since chunk ids change but the text does not.
    """
    return document_name == evidence.document and normalize(evidence.quote) in normalize(passage)


def load_questions(path: Path = DATASET_PATH) -> list[Question]:
    questions: list[Question] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        raw = json.loads(line)
        question = Question(
            id=raw["id"],
            type=raw["type"],
            question=raw["question"],
            expected_answer=raw["expected_answer"],
            evidence=tuple(Evidence(**item) for item in raw["evidence"]),
        )
        problem = _validate(question)
        if problem:
            raise ValueError(f"{path.name} line {line_number} ({question.id}): {problem}")
        questions.append(question)

    ids = [q.id for q in questions]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate question ids")
    return questions


def _validate(question: Question) -> str | None:
    if question.type not in QUESTION_TYPES:
        return f"unknown type {question.type!r}"
    if question.answerable and not (question.expected_answer and question.evidence):
        return "an answerable question needs an expected answer and evidence"
    if not question.answerable and (question.expected_answer or question.evidence):
        return "an unanswerable question must have no expected answer and no evidence"
    return None
