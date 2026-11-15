"""Compare evaluation reports side by side: python -m eval.compare A.json B.json [C.json ...]

The first report is the reference. Prints a Markdown table of the main metrics and, for each
other report, the questions whose result changed: aggregate numbers alone hide whether a gain
of one question is real or noise.
"""

import json
import sys
from pathlib import Path
from typing import Any

METRICS: list[tuple[str, str, str]] = [
    # (section, key, label)
    ("retrieval", "hit_rate@1", "Hit rate@1"),
    ("retrieval", "hit_rate@3", "Hit rate@3"),
    ("retrieval", "hit_rate@5", "Hit rate@5"),
    ("retrieval", "mrr", "MRR"),
    ("retrieval", "evidence_recall", "Rappel des preuves"),
    ("retrieval", "search_ms_median", "Recherche médiane (ms)"),
    ("generation", "pass_rate", "Questions réussies"),
    ("generation", "faithfulness", "Fidélité /5"),
    ("generation", "relevance", "Pertinence /5"),
    ("generation", "correctness", "Exactitude /5"),
    ("generation", "citation_rate", "Réponses avec citation"),
    ("generation", "false_refusal_rate", "Refus à tort"),
    ("generation", "correct_refusal_rate", "Refus corrects"),
]
PERCENT_KEYS = {"pass_rate", "citation_rate", "false_refusal_rate", "correct_refusal_rate",
                "evidence_recall"}  # fmt: skip


def _format(key: str, value: Any) -> str:
    if value is None:
        return "—"
    if key.startswith("hit_rate") or key in PERCENT_KEYS:
        return f"{value * 100:.1f} %"
    if key == "search_ms_median":
        return f"{value:.0f}"
    return f"{value:.3f}" if key == "mrr" else f"{value:.2f}"


def _describe(config: dict[str, Any]) -> str:
    parts = [f"{config['chunk_size_tokens']}/{config['chunk_overlap_tokens']} tokens",
             f"{config['chunks']} passages", config["mode"]]  # fmt: skip
    if config.get("reranker"):
        parts.append(f"rerank {config['rerank_candidates']}")
    return ", ".join(parts)


def _rank(case: dict[str, Any]) -> int | None:
    return case["retrieval"]["first_rank"] if case["retrieval"] else None


def compare(reports: list[dict[str, Any]]) -> str:
    labels = [r["config"]["label"] for r in reports]
    lines = [
        "| Mesure | " + " | ".join(labels) + " |",
        "|---|" + "---|" * len(reports),
        "| Configuration | " + " | ".join(_describe(r["config"]) for r in reports) + " |",
    ]
    for section, key, label in METRICS:
        values = [(r.get(section) or {}).get(key) for r in reports]
        if all(value is None for value in values):
            continue
        lines.append(f"| {label} | " + " | ".join(_format(key, v) for v in values) + " |")

    reference = {case["id"]: case for case in reports[0]["cases"]}
    for report in reports[1:]:
        changes: list[str] = []
        for case in report["cases"]:
            before = reference.get(case["id"])
            if before is None or before["retrieval"] is None:
                continue
            old, new = _rank(before), _rank(case)
            if old != new:
                better = new is not None and (old is None or new < old)
                changes.append(
                    f"- {case['id']} : rang {old or 'absent'} → {new or 'absent'} "
                    f"({'mieux' if better else 'moins bien'})"
                )
            if before["passed"] != case["passed"] and None not in (
                before["passed"],
                case["passed"],
            ):
                changes.append(
                    f"- {case['id']} : {'échec → réussie' if case['passed'] else 'réussie → échec'}"
                )
        lines += ["", f"**{report['config']['label']}** par rapport à **{labels[0]}** :", ""]
        lines += changes or ["- aucun changement par question"]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 1
    reports = [json.loads(Path(path).read_text(encoding="utf-8")) for path in argv]
    print(compare(reports))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
