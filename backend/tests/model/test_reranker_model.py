"""Checks with the REAL reranker (downloads ~470 MB the first time).

Skipped by default; run with: RUN_MODEL_TESTS=1 uv run pytest tests/model
"""

import os

import pytest

from app.core.config import get_settings
from app.services.retrieval.reranker import CrossEncoderReranker

pytestmark = [
    pytest.mark.model,
    pytest.mark.skipif(os.getenv("RUN_MODEL_TESTS") != "1", reason="set RUN_MODEL_TESTS=1"),
]


def test_cross_encoder_ranks_the_answer_first_in_french() -> None:
    reranker = CrossEncoderReranker(get_settings().reranker_model)
    passages = [
        "La cantine de l'entreprise ouvre à midi.",
        "Chaque salarié bénéficie de 25 jours de congés payés annuels.",
        "Le thermostat doit être fixé à 1,50 m du sol.",
    ]

    scores = reranker.score("Combien de jours de vacances ai-je par an ?", passages)

    assert len(scores) == 3
    assert all(0.0 <= score <= 1.0 for score in scores)
    assert scores[1] == max(scores)
