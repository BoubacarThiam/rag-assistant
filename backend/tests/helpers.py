"""Small helpers shared by chat tests."""

import json
import uuid
from typing import Any

from app.services.retrieval import SearchHit


def parse_sse(body: str) -> list[tuple[str, dict[str, Any]]]:
    """Parse a Server-Sent Events body into (event, data) pairs."""
    events: list[tuple[str, dict[str, Any]]] = []
    for block in body.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.split("\n"))
        events.append((lines["event"], json.loads(lines["data"])))
    return events


def make_hit(content: str, document_name: str = "guide.pdf", page: int = 1) -> SearchHit:
    return SearchHit(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        document_name=document_name,
        content=content,
        page_start=page,
        page_end=page,
        position=page - 1,
        score=0.8,
    )


HITS = [
    make_hit("Chaque salarié a droit à 25 jours de congés payés.", page=3),
    make_hit("Le télétravail est possible trois jours par semaine.", "charte.pdf", page=7),
    make_hit("La mutuelle est prise en charge à 60 %.", page=12),
]
