"""Metrics computed without any LLM: retrieval quality and mechanical checks on answers.

Retrieval ("did we find the right passage?"), on answerable questions:
- hit rate@k: share of questions with at least one relevant passage in the top k.
- MRR (Mean Reciprocal Rank): average of 1/rank of the first relevant passage (1 if it is
  first, 0.5 if second, 0 if absent). Rewards putting the right passage at the top.
- evidence recall: share of the expected quotes found in the top k (matters for questions
  whose answer is spread over several passages).
"""

from dataclasses import dataclass
from statistics import mean

from app.services.llm.prompts import CITATION_RE, REFUSAL_SENTENCE, extract_citations
from app.services.retrieval import SearchHit
from eval.dataset import Question, contains_evidence, normalize

# Core of the refusal sentence, matched loosely (the model may add a detail after it).
REFUSAL_MARKER = normalize(REFUSAL_SENTENCE.rstrip("."))


@dataclass(frozen=True)
class RetrievalResult:
    first_rank: int | None  # 1-based rank of the first relevant passage, None if not retrieved
    relevant_ranks: tuple[int, ...]
    evidence_found: int
    evidence_total: int


def is_relevant(question: Question, hit: SearchHit) -> bool:
    return any(contains_evidence(hit.document_name, hit.content, e) for e in question.evidence)


def score_retrieval(question: Question, hits: list[SearchHit]) -> RetrievalResult:
    relevant = tuple(rank for rank, hit in enumerate(hits, start=1) if is_relevant(question, hit))
    found = sum(
        any(contains_evidence(hit.document_name, hit.content, evidence) for hit in hits)
        for evidence in question.evidence
    )
    return RetrievalResult(
        first_rank=relevant[0] if relevant else None,
        relevant_ranks=relevant,
        evidence_found=found,
        evidence_total=len(question.evidence),
    )


def aggregate_retrieval(results: list[RetrievalResult], k: int) -> dict[str, float | int]:
    if not results:
        return {"questions": 0}
    cutoffs = sorted({1, 3, k} & set(range(1, k + 1)))
    metrics: dict[str, float | int] = {"questions": len(results)}
    for cutoff in cutoffs:
        metrics[f"hit_rate@{cutoff}"] = mean(
            1.0 if r.first_rank is not None and r.first_rank <= cutoff else 0.0 for r in results
        )
    metrics["mrr"] = mean(1.0 / r.first_rank if r.first_rank else 0.0 for r in results)
    metrics["evidence_recall"] = mean(r.evidence_found / r.evidence_total for r in results)
    return metrics


@dataclass(frozen=True)
class AnswerChecks:
    is_refusal: bool  # says "not in your documents" and cites nothing
    cited: tuple[int, ...]  # valid passage numbers cited
    invalid_citations: tuple[int, ...]  # cited numbers that do not exist
    cites_evidence: bool  # at least one cited passage really contains the expected quote


def check_answer(question: Question, answer: str, hits: list[SearchHit]) -> AnswerChecks:
    cited = tuple(extract_citations(answer, len(hits)))
    all_numbers = {
        int(raw) for match in CITATION_RE.finditer(answer) for raw in match.group(1).split(",")
    }
    invalid = tuple(sorted(n for n in all_numbers if not 1 <= n <= len(hits)))
    return AnswerChecks(
        is_refusal=REFUSAL_MARKER in normalize(answer) and not cited,
        cited=cited,
        invalid_citations=invalid,
        cites_evidence=any(is_relevant(question, hits[number - 1]) for number in cited),
    )
