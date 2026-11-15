"""Tests of the evaluation itself: a broken eval gives confident numbers that mean nothing."""

import json
import uuid
from collections.abc import AsyncIterator
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from eval import PDF_DIR
from eval.backends import MemoryBackend
from eval.build_pdfs import build_pdf
from eval.corpus import DOCUMENTS
from eval.dataset import Evidence, Question, contains_evidence, load_questions, normalize
from eval.judge import AnthropicJudge, FakeJudge, JudgeError, JudgeVerdict, build_judge_message
from eval.metrics import aggregate_retrieval, check_answer, score_retrieval
from eval.report import build_report, render_markdown, save_report
from eval.runner import run_all

from app.core.config import Settings
from app.services.embeddings import FakeEmbeddingProvider
from app.services.ingestion.pipeline import process_pdf
from app.services.llm import ChatMessage, LLMError
from app.services.llm.prompts import REFUSAL_SENTENCE
from app.services.retrieval import SearchHit

QUESTIONS = load_questions()
SETTINGS = Settings(_env_file=None)  # type: ignore[call-arg]


def hit(content: str, document: str = "guide-salarie-novalia.pdf") -> SearchHit:
    return SearchHit(uuid.uuid4(), uuid.uuid4(), document, content, 1, 1, 0, 0.5)


QUESTION = Question(
    id="q",
    type="factual",
    question="Combien de jours ?",
    expected_answer="27 jours.",
    evidence=(Evidence("guide-salarie-novalia.pdf", 2, "27 jours ouvrés"),),
)
UNANSWERABLE = Question("u", "unanswerable", "Quelle prime ?", None, ())
GOOD = hit("Chaque salarié bénéficie de 27 jours  ouvrés de congés.")
BAD = hit("Le télétravail est limité à deux jours.")
WRONG_DOC = hit("27 jours ouvrés", document="autre.pdf")


# --- Dataset ---------------------------------------------------------------------------------


def test_dataset_size_and_balance() -> None:
    assert 20 <= len(QUESTIONS) <= 30
    by_type = {t: sum(q.type == t for q in QUESTIONS) for t in {q.type for q in QUESTIONS}}
    assert by_type["unanswerable"] >= 5
    assert all(by_type[t] >= 3 for t in ("factual", "paraphrase", "keyword", "multi"))
    assert len({normalize(q.question) for q in QUESTIONS}) == len(QUESTIONS)


def test_every_quote_is_verbatim_on_exactly_the_stated_page() -> None:
    corpus = {document.filename: document for document in DOCUMENTS}
    for question in QUESTIONS:
        for evidence in question.evidence:
            pages = corpus[evidence.document].pages
            found_on = [
                n for n, text in enumerate(pages, 1) if normalize(evidence.quote) in normalize(text)
            ]
            assert found_on == [evidence.page], (
                f"{question.id}: {evidence.quote!r} found on {found_on}"
            )


@pytest.mark.parametrize("chunk_size", [450, 120])
def test_every_quote_survives_pdf_extraction_cleaning_and_chunking(chunk_size: int) -> None:
    """The PDFs on disk are up to date and no quote is cut by a chunk boundary."""
    chunks_by_document = {}
    for document in DOCUMENTS:
        data = (PDF_DIR / document.filename).read_bytes()
        result = process_pdf(data, FakeEmbeddingProvider(), chunk_size, chunk_size // 6, 32)
        assert result.page_count == len(document.pages)
        assert not any(document.header in chunk.text for chunk in result.chunks)
        chunks_by_document[document.filename] = result.chunks

    for question in QUESTIONS:
        for evidence in question.evidence:
            matching = [
                chunk
                for chunk in chunks_by_document[evidence.document]
                if contains_evidence(evidence.document, chunk.text, evidence)
            ]
            assert matching, f"{question.id}: quote not found in any chunk"
            assert all(c.page_start <= evidence.page <= c.page_end for c in matching)


def test_pdf_generation_is_reproducible() -> None:
    assert build_pdf(DOCUMENTS[0]) == build_pdf(DOCUMENTS[0])


def test_invalid_dataset_rows_are_rejected(tmp_path: Path) -> None:
    row = {"id": "x", "type": "factual", "question": "Q ?", "expected_answer": None, "evidence": []}
    path = tmp_path / "bad.jsonl"
    path.write_text(json.dumps(row), encoding="utf-8")
    with pytest.raises(ValueError, match="needs an expected answer"):
        load_questions(path)


# --- Retrieval metrics -----------------------------------------------------------------------


def test_relevance_needs_the_right_document_and_ignores_spacing_and_case() -> None:
    assert score_retrieval(QUESTION, [BAD, GOOD]).first_rank == 2
    assert score_retrieval(QUESTION, [WRONG_DOC, BAD]).first_rank is None


def test_retrieval_aggregates() -> None:
    results = [
        score_retrieval(QUESTION, [GOOD, BAD]),  # rank 1
        score_retrieval(QUESTION, [BAD, BAD, GOOD]),  # rank 3
        score_retrieval(QUESTION, [BAD, BAD]),  # miss
    ]
    metrics = aggregate_retrieval(results, k=5)
    assert metrics["hit_rate@1"] == pytest.approx(1 / 3)
    assert metrics["hit_rate@3"] == pytest.approx(2 / 3)
    assert metrics["hit_rate@5"] == pytest.approx(2 / 3)
    assert metrics["mrr"] == pytest.approx((1 + 1 / 3 + 0) / 3)


def test_evidence_recall_counts_each_expected_quote() -> None:
    multi = Question(
        "m", "multi", "Q ?", "A.",
        (Evidence("a.pdf", 1, "premier fait"), Evidence("a.pdf", 2, "second fait")),
    )  # fmt: skip
    result = score_retrieval(multi, [hit("Voici le premier fait.", "a.pdf"), BAD])
    assert (result.evidence_found, result.evidence_total) == (1, 2)


# --- Answer checks ---------------------------------------------------------------------------


def test_good_answer_checks() -> None:
    checks = check_answer(QUESTION, "Vous avez 27 jours [1].", [GOOD, BAD])
    assert (checks.is_refusal, checks.cited, checks.invalid_citations, checks.cites_evidence) == (
        False, (1,), (), True,
    )  # fmt: skip


def test_citing_the_wrong_passage_or_a_missing_one_is_detected() -> None:
    checks = check_answer(QUESTION, "Vous avez 27 jours [2][7].", [GOOD, BAD])
    assert checks.cited == (2,)
    assert checks.invalid_citations == (7,)
    assert checks.cites_evidence is False


def test_refusal_detection() -> None:
    assert check_answer(UNANSWERABLE, REFUSAL_SENTENCE, [BAD]).is_refusal
    assert check_answer(
        UNANSWERABLE, "je ne trouve pas  cette information dans tes documents", [BAD]
    ).is_refusal
    # A partial answer that cites a source is not a refusal.
    partial = f"Le télétravail est limité [1]. Pour la prime : {REFUSAL_SENTENCE}"
    assert not check_answer(UNANSWERABLE, partial, [BAD]).is_refusal
    assert not check_answer(UNANSWERABLE, "", [BAD]).is_refusal


# --- Whole run: oracle, null baselines, plumbing errors --------------------------------------


class ScriptedLLM:
    """Answers each question with a function of the question text."""

    def __init__(self, reply: Any) -> None:
        self.reply = reply

    async def stream(self, system: str, messages: list[ChatMessage]) -> AsyncIterator[str]:
        question = messages[-1].content.rsplit("Question : ", 1)[1]
        answer = self.reply(question)
        if isinstance(answer, Exception):
            raise answer
        yield answer


@pytest.fixture
async def backend() -> MemoryBackend:
    backend = MemoryBackend(FakeEmbeddingProvider(), SETTINGS)
    assert await backend.setup(sorted(PDF_DIR.glob("*.pdf"))) > 5
    return backend


async def run(backend: MemoryBackend, reply: Any, judge_score: int = 5) -> dict[str, Any]:
    results = await run_all(
        QUESTIONS, backend=backend, k=5, mode="vector",
        llm=ScriptedLLM(reply), judge=FakeJudge(judge_score),  # type: ignore[arg-type]
    )  # fmt: skip
    config = {
        "label": "test", "date": "2026-01-01 00:00", "git_commit": "abc", "backend": backend.name,
        "mode": "vector", "k": 5, "chunk_size_tokens": 450, "chunk_overlap_tokens": 75, "chunks": 1,
        "embedding_model": "fake", "llm_model": "fake", "judge_model": "fake",
        "questions": len(QUESTIONS), "answerable": 23, "unanswerable": 5,
    }  # fmt: skip
    return build_report(results, config=config, k=5, usage={})


def oracle(question: str) -> str:
    expected = {q.question: q for q in QUESTIONS}[question]
    return f"{expected.expected_answer} [1]" if expected.answerable else REFUSAL_SENTENCE


async def test_oracle_answers_pass(backend: MemoryBackend) -> None:
    report = await run(backend, oracle)
    assert report["generation"]["pass_rate"] == 1.0
    assert report["generation"]["correct_refusal_rate"] == 1.0
    assert report["generation"]["false_refusal_rate"] == 0.0
    assert report["generation"]["judged"] == 23  # refusals are not sent to the judge


async def test_empty_answers_fail(backend: MemoryBackend) -> None:
    report = await run(backend, lambda _: "")
    assert report["generation"]["pass_rate"] == 0.0


async def test_always_refusing_only_passes_unanswerable_questions(backend: MemoryBackend) -> None:
    report = await run(backend, lambda _: REFUSAL_SENTENCE)
    assert report["generation"]["pass_rate"] == pytest.approx(5 / 28)
    assert report["generation"]["false_refusal_rate"] == 1.0
    assert report["by_type"]["unanswerable"]["pass_rate"] == 1.0


async def test_answers_without_citation_or_judged_unfaithful_fail(backend: MemoryBackend) -> None:
    no_citation = await run(backend, lambda q: oracle(q).replace(" [1]", ""))
    assert no_citation["by_type"]["factual"]["pass_rate"] == 0.0
    low_score = await run(backend, oracle, judge_score=2)
    assert low_score["by_type"]["factual"]["pass_rate"] == 0.0
    assert low_score["by_type"]["unanswerable"]["pass_rate"] == 1.0


async def test_technical_errors_are_reported_apart_not_scored_as_wrong(
    backend: MemoryBackend,
) -> None:
    report = await run(backend, lambda _: LLMError("Service indisponible.", "llm_unavailable"))
    generation = report["generation"]
    assert (generation["scored"], generation["errors"], generation["pass_rate"]) == (0, 28, None)
    assert "llm_unavailable" in report["cases"][0]["error"]


async def test_retrieval_only_run_and_report_files(backend: MemoryBackend, tmp_path: Path) -> None:
    results = await run_all(QUESTIONS, backend=backend, k=5, mode="vector", llm=None, judge=None)
    config = {
        "label": "recherche", "date": "2026-01-01 00:00", "git_commit": "abc",
        "backend": backend.name, "mode": "vector", "k": 5, "chunk_size_tokens": 450,
        "chunk_overlap_tokens": 75, "chunks": 1, "embedding_model": "fake",
        "llm_model": "non utilisé", "judge_model": "non utilisé",
        "questions": 28, "answerable": 23, "unanswerable": 5,
    }  # fmt: skip
    report = build_report(results, config=config, k=5, usage={})

    assert report["generation"] is None
    assert report["retrieval"]["questions"] == 23
    assert 0.0 <= report["retrieval"]["mrr"] <= report["retrieval"]["hit_rate@5"] <= 1.0

    markdown_path, json_path = save_report(report, tmp_path, datetime(2026, 1, 2, 3, 4))
    assert markdown_path.name == "2026-01-02_0304_recherche.md"
    assert json.loads(json_path.read_text(encoding="utf-8"))["config"]["label"] == "recherche"
    text = markdown_path.read_text(encoding="utf-8")
    assert "Hit rate@5" in text and "Non évaluée" in text


async def test_markdown_report_lists_failures(backend: MemoryBackend) -> None:
    markdown = render_markdown(await run(backend, lambda _: REFUSAL_SENTENCE))
    assert "refus à tort" in markdown
    assert "| fact-01 |" in markdown


# --- Judge -----------------------------------------------------------------------------------


def test_judge_message_contains_everything_needed() -> None:
    message = build_judge_message("Q ?", "Référence.", ["P1", "P2"], "Réponse [1].")
    for part in (
        "Q ?",
        "Référence.",
        '<passage numero="2">\nP2',
        "<reponse>\nRéponse [1].\n</reponse>",
    ):
        assert part in message


async def test_anthropic_judge_parses_verdict_and_counts_tokens() -> None:
    verdict = JudgeVerdict(
        faithfulness_reason="ok", faithfulness=5, relevance_reason="ok", relevance=4,
        correctness_reason="ok", correctness=3,
    )  # fmt: skip
    calls: list[dict[str, Any]] = []

    async def parse(**request: Any) -> Any:
        calls.append(request)
        return SimpleNamespace(
            parsed_output=verdict, stop_reason="end_turn",
            usage=SimpleNamespace(input_tokens=100, output_tokens=20),
        )  # fmt: skip

    judge = AnthropicJudge("claude-opus-5-5", api_key="test")
    judge._client = SimpleNamespace(messages=SimpleNamespace(parse=parse))  # type: ignore[assignment]

    result = await judge.grade(
        question="Q ?", expected_answer="R.", passages=["P"], answer="A [1]."
    )

    assert result == verdict
    assert (judge.input_tokens, judge.output_tokens) == (100, 20)
    assert calls[0]["model"] == "claude-opus-5-5"
    assert calls[0]["output_format"] is JudgeVerdict


async def test_anthropic_judge_without_verdict_raises() -> None:
    async def parse(**_: Any) -> Any:
        return SimpleNamespace(
            parsed_output=None, stop_reason="refusal",
            usage=SimpleNamespace(input_tokens=1, output_tokens=0),
        )  # fmt: skip

    judge = AnthropicJudge("claude-opus-5-5", api_key="test")
    judge._client = SimpleNamespace(messages=SimpleNamespace(parse=parse))  # type: ignore[assignment]

    with pytest.raises(JudgeError):
        await judge.grade(question="Q", expected_answer="R", passages=[], answer="A")
