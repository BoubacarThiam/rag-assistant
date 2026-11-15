"""Runs every question through the real pipeline and collects per-question results."""

import asyncio
import logging
import time
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field

from app.services.chat import chat_stream
from app.services.conversations import InMemoryConversationStore
from app.services.llm.base import LLMProvider
from app.services.retrieval import SearchHit, SearchMode
from eval.backends import Backend
from eval.dataset import Question
from eval.judge import Judge, JudgeError, JudgeVerdict
from eval.metrics import AnswerChecks, RetrievalResult, check_answer, is_relevant, score_retrieval

logger = logging.getLogger(__name__)

PASS_THRESHOLD = 4  # minimum judge score (out of 5) on faithfulness and correctness


@dataclass
class CaseResult:
    question: Question
    hits: list[SearchHit] = field(default_factory=list)
    search_ms: float = 0.0
    retrieval: RetrievalResult | None = None  # None for unanswerable questions
    answer: str | None = None  # None when generation was not run
    checks: AnswerChecks | None = None
    verdict: JudgeVerdict | None = None
    # A failure of the plumbing (API error, judge error): reported apart, never scored as wrong.
    error: str | None = None

    @property
    def scored(self) -> bool:
        return self.error is None and self.checks is not None

    @property
    def passed(self) -> bool | None:
        """Overall verdict for one question; None if it could not be scored."""
        if not self.scored or self.checks is None:
            return None
        if not self.question.answerable:
            return self.checks.is_refusal
        if self.checks.is_refusal or not self.checks.cited or self.checks.invalid_citations:
            return False
        if self.verdict is None:
            return None
        return (
            self.verdict.faithfulness >= PASS_THRESHOLD
            and self.verdict.correctness >= PASS_THRESHOLD
        )

    def failure_reasons(self) -> list[str]:
        if self.error:
            return [f"erreur technique : {self.error}"]
        if self.checks is None or self.passed in (True, None):
            return []
        if not self.question.answerable:
            return ["a répondu au lieu de dire que l'information est absente"]
        reasons: list[str] = []
        if self.checks.is_refusal:
            reasons.append("refus à tort : l'information est dans les documents")
            return reasons
        if not self.checks.cited:
            reasons.append("aucune citation")
        if self.checks.invalid_citations:
            reasons.append(f"citations inexistantes : {list(self.checks.invalid_citations)}")
        if self.verdict and self.verdict.faithfulness < PASS_THRESHOLD:
            reasons.append(
                f"fidélité {self.verdict.faithfulness}/5 : {self.verdict.faithfulness_reason}"
            )
        if self.verdict and self.verdict.correctness < PASS_THRESHOLD:
            reasons.append(
                f"exactitude {self.verdict.correctness}/5 : {self.verdict.correctness_reason}"
            )
        return reasons


async def generate_answer(
    question: Question, hits: list[SearchHit], llm: LLMProvider
) -> tuple[str | None, str | None]:
    """Answer through the application's own chat orchestration. Returns (answer, error)."""

    async def retrieve(_query: str, _ids: Sequence[uuid.UUID] | None) -> list[SearchHit]:
        return hits  # the passages already retrieved (and scored) for this question

    parts: list[str] = []
    async for event in chat_stream(
        store=InMemoryConversationStore(),
        retrieve=retrieve,
        llm=llm,
        question=question.question,
        conversation_id=None,
        document_ids=None,
        history_messages=0,
    ):
        if event.event == "token":
            parts.append(event.data["text"])
        elif event.event == "error":
            return None, f"{event.data['code']}: {event.data['detail']}"
    return "".join(parts), None


async def evaluate_question(
    question: Question,
    *,
    backend: Backend,
    k: int,
    mode: SearchMode,
    llm: LLMProvider | None,
    judge: Judge | None,
) -> CaseResult:
    result = CaseResult(question)
    start = time.perf_counter()
    result.hits = await backend.search(question.question, k, mode)
    result.search_ms = (time.perf_counter() - start) * 1000
    if question.answerable:
        result.retrieval = score_retrieval(question, result.hits)
    if llm is None:
        return result  # retrieval-only run

    result.answer, result.error = await generate_answer(question, result.hits, llm)
    if result.answer is None:
        return result
    result.checks = check_answer(question, result.answer, result.hits)

    # The judge grades real answers to answerable questions. Refusals and answers to
    # unanswerable questions are decided by the mechanical checks alone.
    if judge and question.answerable and question.expected_answer and not result.checks.is_refusal:
        try:
            result.verdict = await judge.grade(
                question=question.question,
                expected_answer=question.expected_answer,
                passages=[hit.content for hit in result.hits],
                answer=result.answer,
            )
        except JudgeError as exc:
            result.error = str(exc)
    return result


async def run_all(
    questions: list[Question],
    *,
    backend: Backend,
    k: int,
    mode: SearchMode,
    llm: LLMProvider | None,
    judge: Judge | None,
    concurrency: int = 4,
) -> list[CaseResult]:
    semaphore = asyncio.Semaphore(concurrency)

    async def guarded(question: Question) -> CaseResult:
        async with semaphore:
            try:
                result = await evaluate_question(
                    question, backend=backend, k=k, mode=mode, llm=llm, judge=judge
                )
            except Exception as exc:  # one broken case must not lose the whole run
                logger.exception("Question %s failed", question.id)
                return CaseResult(question, error=f"{type(exc).__name__}: {exc}")
            logger.info("%s done", question.id)
            return result

    return list(await asyncio.gather(*(guarded(question) for question in questions)))


__all__ = ["PASS_THRESHOLD", "CaseResult", "evaluate_question", "is_relevant", "run_all"]
