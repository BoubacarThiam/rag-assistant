"""Evaluate the RAG pipeline: python -m eval.run [--label baseline] [--retrieval-only] ...

1. Index the evaluation PDFs from scratch with the current settings (chunk size, model...).
2. For each question: retrieve passages, and unless --retrieval-only, generate an answer with
   the application's own chat code and have it graded.
3. Write a dated Markdown + JSON report in eval/reports/, to compare versions.

The generation part calls the Claude API (answers + judge): it costs money on every run.
"""

import argparse
import asyncio
import logging
import re
import subprocess
import sys
from datetime import datetime
from typing import Any

from app.core.config import Settings, get_settings
from app.services.embeddings import get_embedding_provider
from app.services.llm import AnthropicProvider, OpenAICompatibleProvider, get_llm_provider
from app.services.retrieval.reranker import CrossEncoderReranker
from eval import EVAL_DIR, PDF_DIR, REPORTS_DIR
from eval.backends import Backend, MemoryBackend, PgBackend, database_reachable
from eval.dataset import load_questions
from eval.judge import AnthropicJudge
from eval.report import build_report, save_report
from eval.runner import run_all


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Évalue le pipeline RAG.")
    parser.add_argument("--label", default="run", help="nom du rapport (ex. baseline, hybrid)")
    parser.add_argument("--k", type=int, help="nombre de passages (défaut : RETRIEVAL_TOP_K)")
    parser.add_argument(
        "--mode", choices=["vector", "fulltext", "hybrid"], help="défaut : RETRIEVAL_MODE"
    )
    parser.add_argument(
        "--backend",
        choices=["auto", "pg", "memory"],
        default="auto",
        help="pg = PostgreSQL/pgvector ; memory = sans base (mode vector seulement)",
    )
    parser.add_argument("--retrieval-only", action="store_true", help="ne pas appeler Claude")
    parser.add_argument("--chunk-size", type=int, help="défaut : CHUNK_SIZE_TOKENS")
    parser.add_argument("--chunk-overlap", type=int, help="défaut : CHUNK_OVERLAP_TOKENS")
    parser.add_argument(
        "--rerank",
        action=argparse.BooleanOptionalAction,
        help="activer/désactiver le reranking (défaut : RERANK_ENABLED)",
    )
    parser.add_argument(
        "--title-context",
        action=argparse.BooleanOptionalAction,
        help="ajouter le titre du document à chaque passage (EMBED_DOCUMENT_TITLE)",
    )
    parser.add_argument("--candidates", type=int, help="passages reclassés (RERANK_CANDIDATES)")
    parser.add_argument("--limit", type=int, help="n'évaluer que les N premières questions")
    parser.add_argument("--concurrency", type=int, default=4)
    return parser.parse_args(argv)


def git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=EVAL_DIR, timeout=5, check=True,
        )  # fmt: skip
        dirty = subprocess.run(
            ["git", "status", "--porcelain", "--", ".", "../backend"],
            capture_output=True, text=True, cwd=EVAL_DIR, timeout=5, check=True,
        )  # fmt: skip
        return out.stdout.strip() + (" (+ modifications locales)" if dirty.stdout.strip() else "")
    except (OSError, subprocess.SubprocessError):
        return "inconnu"


async def choose_backend(name: str, settings: Settings) -> Backend:
    embedder = get_embedding_provider()
    reranker = CrossEncoderReranker(settings.reranker_model) if settings.rerank_enabled else None
    if name == "auto":
        name = "pg" if await database_reachable(settings.eval_database_url) else "memory"
        if name == "memory":
            print("PostgreSQL injoignable : recherche en mémoire (cosinus exact, sans pgvector).")
    if name == "pg":
        return PgBackend(embedder, settings, reranker)
    return MemoryBackend(embedder, settings, reranker)


async def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    overrides = {
        "chunk_size_tokens": args.chunk_size,
        "chunk_overlap_tokens": args.chunk_overlap,
        "rerank_enabled": args.rerank,
        "rerank_candidates": args.candidates,
        "embed_document_title": args.title_context,
    }
    # Command-line options override .env for this run only (to compare configurations).
    settings = get_settings().model_copy(
        update={key: value for key, value in overrides.items() if value is not None}
    )
    k = args.k or settings.retrieval_top_k
    mode = args.mode or settings.retrieval_mode
    label = re.sub(r"[^\w-]+", "-", args.label).strip("-") or "run"

    questions = load_questions()[: args.limit]
    pdf_paths = sorted(PDF_DIR.glob("*.pdf"))
    if not pdf_paths:
        print("Aucun PDF dans eval/pdfs : lancez d'abord `python -m eval.build_pdfs`.")
        return 1

    backend = await choose_backend(args.backend, settings)
    llm = None if args.retrieval_only else get_llm_provider()
    api_key = settings.anthropic_api_key.get_secret_value() if settings.anthropic_api_key else None
    judge = None if args.retrieval_only else AnthropicJudge(settings.judge_model, api_key)

    try:
        print(f"Indexation de {len(pdf_paths)} PDF ({backend.name})...")
        chunks = await backend.setup(pdf_paths)
        print(f"{chunks} passages indexés. Évaluation de {len(questions)} questions...")
        results = await run_all(
            questions, backend=backend, k=k, mode=mode, llm=llm, judge=judge,
            concurrency=args.concurrency,
        )  # fmt: skip
    finally:
        await backend.close()

    now = datetime.now()
    config: dict[str, Any] = {
        "label": label,
        "date": now.strftime("%Y-%m-%d %H:%M"),
        "git_commit": git_commit(),
        "backend": backend.name,
        "mode": mode,
        "k": k,
        "chunk_size_tokens": settings.chunk_size_tokens,
        "chunk_overlap_tokens": settings.chunk_overlap_tokens,
        "chunks": chunks,
        "embed_document_title": settings.embed_document_title,
        "reranker": settings.reranker_model if settings.rerank_enabled else None,
        "rerank_candidates": settings.rerank_candidates if settings.rerank_enabled else None,
        "embedding_model": settings.embedding_model,
        "llm_model": settings.llm_model if llm else "non utilisé",
        "llm_effort": settings.llm_effort if llm else None,
        "judge_model": settings.judge_model if judge else "non utilisé",
        "questions": len(questions),
        "answerable": sum(q.answerable for q in questions),
        "unanswerable": sum(not q.answerable for q in questions),
    }
    usage: dict[str, Any] = {}
    if isinstance(llm, AnthropicProvider | OpenAICompatibleProvider):
        usage |= {"llm_input_tokens": llm.input_tokens, "llm_output_tokens": llm.output_tokens}
    if judge:
        usage |= {
            "judge_input_tokens": judge.input_tokens,
            "judge_output_tokens": judge.output_tokens,
        }

    report = build_report(results, config=config, k=k, usage=usage)
    markdown_path, json_path = save_report(report, REPORTS_DIR, now)

    retrieval, generation = report["retrieval"], report["generation"]
    hit_rate = retrieval[f"hit_rate@{k}"] * 100
    print(f"\nRecherche : hit rate@{k} = {hit_rate:.1f} %, MRR = {retrieval['mrr']:.3f}")
    if generation:
        rate = generation["pass_rate"]
        print(
            f"Génération : {generation['scored']} réponses notées, "
            f"{'n/a' if rate is None else f'{rate * 100:.1f} %'} réussies, "
            f"{generation['errors']} erreur(s) technique(s)"
        )
    print(f"Rapport : {markdown_path}\n          {json_path}")
    # A run where nothing could be scored is a failed run, not an empty success.
    return 1 if generation and generation["scored"] == 0 else 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(asyncio.run(main()))
