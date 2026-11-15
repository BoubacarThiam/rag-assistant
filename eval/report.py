"""Turns per-question results into aggregate metrics, a JSON file and a Markdown report."""

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any

from eval.dataset import QUESTION_TYPES
from eval.metrics import aggregate_retrieval
from eval.runner import PASS_THRESHOLD, CaseResult, is_relevant


def _rate(flags: list[bool]) -> float | None:
    return mean(1.0 if flag else 0.0 for flag in flags) if flags else None


def aggregate_generation(results: list[CaseResult]) -> dict[str, Any]:
    scored = [r for r in results if r.scored and r.checks is not None]
    answerable = [r for r in scored if r.question.answerable]
    unanswerable = [r for r in scored if not r.question.answerable]
    judged = [r.verdict for r in answerable if r.verdict is not None]
    verdicts = [r.passed for r in scored if r.passed is not None]
    return {
        "scored": len(scored),
        "errors": sum(1 for r in results if r.error),
        "pass_rate": _rate(verdicts),
        "faithfulness": mean(v.faithfulness for v in judged) if judged else None,
        "relevance": mean(v.relevance for v in judged) if judged else None,
        "correctness": mean(v.correctness for v in judged) if judged else None,
        "judged": len(judged),
        # Among answerable questions:
        "citation_rate": _rate([bool(r.checks and r.checks.cited) for r in answerable]),
        "cites_evidence_rate": _rate(
            [bool(r.checks and r.checks.cites_evidence) for r in answerable]
        ),
        "false_refusal_rate": _rate([bool(r.checks and r.checks.is_refusal) for r in answerable]),
        # Among unanswerable questions:
        "correct_refusal_rate": _rate(
            [bool(r.checks and r.checks.is_refusal) for r in unanswerable]
        ),
    }


def aggregate_by_type(results: list[CaseResult], k: int) -> dict[str, dict[str, Any]]:
    by_type: dict[str, dict[str, Any]] = {}
    for question_type in QUESTION_TYPES:
        subset = [r for r in results if r.question.type == question_type]
        if not subset:
            continue
        retrieval = aggregate_retrieval([r.retrieval for r in subset if r.retrieval], k)
        verdicts = [r.passed for r in subset if r.passed is not None]
        by_type[question_type] = {
            "questions": len(subset),
            f"hit_rate@{k}": retrieval.get(f"hit_rate@{k}"),
            "mrr": retrieval.get("mrr"),
            "pass_rate": _rate(verdicts),
        }
    return by_type


def case_to_dict(result: CaseResult) -> dict[str, Any]:
    question = result.question
    return {
        "id": question.id,
        "type": question.type,
        "question": question.question,
        "expected_answer": question.expected_answer,
        "retrieved": [
            {
                "rank": rank,
                "document": hit.document_name,
                "pages": [hit.page_start, hit.page_end],
                "score": round(hit.score, 4),
                "relevant": is_relevant(question, hit),
                "content": hit.content,
            }
            for rank, hit in enumerate(result.hits, start=1)
        ],
        "retrieval": asdict(result.retrieval) if result.retrieval else None,
        "answer": result.answer,
        "checks": asdict(result.checks) if result.checks else None,
        "judge": result.verdict.model_dump() if result.verdict else None,
        "passed": result.passed,
        "failure_reasons": result.failure_reasons(),
        "error": result.error,
    }


def build_report(
    results: list[CaseResult], *, config: dict[str, Any], k: int, usage: dict[str, Any]
) -> dict[str, Any]:
    retrieval = aggregate_retrieval([r.retrieval for r in results if r.retrieval], k)
    generation_ran = any(r.answer is not None or r.error for r in results)
    return {
        "config": config,
        "retrieval": retrieval,
        "generation": aggregate_generation(results) if generation_ran else None,
        "by_type": aggregate_by_type(results, k),
        "usage": usage,
        "cases": [case_to_dict(r) for r in results],
    }


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.1f} %"


def _score(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2f} / 5"


def _num(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def render_markdown(report: dict[str, Any]) -> str:
    config, retrieval, generation = report["config"], report["retrieval"], report["generation"]
    k = config["k"]
    lines = [
        f"# Rapport d'évaluation : {config['label']}",
        "",
        f"- Date : {config['date']}",
        f"- Version du code : `{config['git_commit']}`",
        f"- Moteur de recherche : {config['backend']} (mode `{config['mode']}`, k = {k})",
        f"- Découpage : {config['chunk_size_tokens']} tokens, chevauchement "
        f"{config['chunk_overlap_tokens']} ; {config['chunks']} passages indexés",
        f"- Embeddings : `{config['embedding_model']}`",
        f"- Modèle de réponse : `{config['llm_model']}` ; juge : `{config['judge_model']}`",
        f"- Questions : {config['questions']} ({config['answerable']} avec réponse, "
        f"{config['unanswerable']} sans réponse dans les documents)",
        "",
        "## Recherche (retrieval)",
        "",
        f"Sur les {retrieval.get('questions', 0)} questions ayant une réponse dans les documents.",
        "",
        "| Mesure | Valeur |",
        "|---|---|",
    ]
    for cutoff in sorted({1, 3, k}):
        if f"hit_rate@{cutoff}" in retrieval:
            lines.append(f"| Hit rate@{cutoff} | {_pct(retrieval[f'hit_rate@{cutoff}'])} |")
    lines += [
        f"| MRR | {_num(retrieval.get('mrr'))} |",
        f"| Rappel des preuves | {_pct(retrieval.get('evidence_recall'))} |",
        "",
    ]

    lines += ["## Génération", ""]
    if generation is None:
        lines += ["Non évaluée dans ce rapport (recherche seule).", ""]
    else:
        lines += [
            f"{generation['scored']} réponses notées, {generation['errors']} erreur(s) "
            "technique(s) exclue(s) des moyennes. Une question est « réussie » si la réponse cite "
            "ses sources "
            f"et obtient au moins {PASS_THRESHOLD}/5 en fidélité et en exactitude, ou si elle "
            "refuse correctement quand l'information est absente.",
            "",
            "| Mesure | Valeur |",
            "|---|---|",
            f"| Questions réussies | {_pct(generation['pass_rate'])} |",
            f"| Fidélité (juge) | {_score(generation['faithfulness'])} |",
            f"| Pertinence (juge) | {_score(generation['relevance'])} |",
            f"| Exactitude (juge) | {_score(generation['correctness'])} |",
            f"| Réponses avec citation | {_pct(generation['citation_rate'])} |",
            f"| Citation pointant le bon passage | {_pct(generation['cites_evidence_rate'])} |",
            f"| Refus à tort | {_pct(generation['false_refusal_rate'])} |",
            "| Refus corrects (questions sans réponse) "
            f"| {_pct(generation['correct_refusal_rate'])} |",
            "",
        ]

    lines += [
        "## Par type de question",
        "",
        f"| Type | Questions | Hit rate@{k} | MRR | Réussies |",
        "|---|---|---|---|---|",
    ]
    for question_type, row in report["by_type"].items():
        lines.append(
            f"| {question_type} | {row['questions']} | {_pct(row[f'hit_rate@{k}'])} "
            f"| {_num(row['mrr'])} | {_pct(row['pass_rate'])} |"
        )

    lines += [
        "",
        "## Détail par question",
        "",
        "| Id | Rang du bon passage | Citations | Fidélité | Pertinence | Exactitude | Résultat |",
        "|---|---|---|---|---|---|---|",
    ]
    for case in report["cases"]:
        rank = case["retrieval"]["first_rank"] if case["retrieval"] else None
        rank_text = "—" if case["retrieval"] is None else (str(rank) if rank else "absent")
        cited = case["checks"]["cited"] if case["checks"] else None
        judge = case["judge"] or {}
        outcome = {True: "réussie", False: "échec", None: "—"}[case["passed"]]
        if case["error"]:
            outcome = "erreur"
        lines.append(
            f"| {case['id']} | {rank_text} | {'—' if cited is None else (cited or 'aucune')} "
            f"| {judge.get('faithfulness', '—')} | {judge.get('relevance', '—')} "
            f"| {judge.get('correctness', '—')} | {outcome} |"
        )

    problems = [c for c in report["cases"] if c["failure_reasons"]]
    missed = [c for c in report["cases"] if c["retrieval"] and not c["retrieval"]["first_rank"]]
    if missed:
        lines += ["", "## Bon passage non retrouvé", ""]
        for case in missed:
            top = case["retrieved"][0] if case["retrieved"] else None
            lines.append(
                f"- **{case['id']}** : « {case['question']} » "
                + (f"(premier résultat : {top['document']}, page {top['pages'][0]})" if top else "")
            )
    if problems:
        lines += ["", "## Échecs et erreurs", ""]
        for case in problems:
            lines.append(f"### {case['id']} : {case['question']}")
            lines.append("")
            if case["answer"]:
                lines.append(f"> {case['answer'].strip().replace(chr(10), chr(10) + '> ')}")
                lines.append("")
            lines += [f"- {reason}" for reason in case["failure_reasons"]]
            lines.append("")

    noise = 100 / max(config["questions"], 1)
    lines += [
        "",
        "## Comment lire ces chiffres",
        "",
        f"Avec {config['questions']} questions, une seule question pèse environ {noise:.1f} points "
        "de pourcentage. Un écart plus petit que cela entre deux rapports ne prouve rien : "
        "relancez l'évaluation ou regardez le détail des questions qui ont changé.",
        "",
    ]
    usage = report["usage"]
    if usage:
        lines += [
            f"Tokens consommés : réponses {usage.get('llm_input_tokens', 0)} en entrée / "
            f"{usage.get('llm_output_tokens', 0)} en sortie ; juge "
            f"{usage.get('judge_input_tokens', 0)} / {usage.get('judge_output_tokens', 0)}.",
            "",
        ]
    return "\n".join(lines)


def save_report(report: dict[str, Any], directory: Path, now: datetime) -> tuple[Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    stem = f"{now:%Y-%m-%d_%H%M}_{report['config']['label']}"
    json_path = directory / f"{stem}.json"
    markdown_path = directory / f"{stem}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    return markdown_path, json_path
