from dataclasses import replace

from app.services.llm.prompts import (
    REFUSAL_SENTENCE,
    SYSTEM_PROMPT,
    build_user_message,
    extract_citations,
    format_pages,
    strip_citations,
)
from tests.helpers import HITS


def test_system_prompt_states_the_key_rules() -> None:
    assert REFUSAL_SENTENCE in SYSTEM_PROMPT
    assert "[1]" in SYSTEM_PROMPT
    assert "seule source" in SYSTEM_PROMPT


def test_user_message_numbers_passages_and_ends_with_the_question() -> None:
    message = build_user_message("Combien de congés ?", HITS)

    assert '<passage numero="1" document="guide.pdf" page="3">' in message
    assert '<passage numero="2" document="charte.pdf" page="7">' in message
    assert HITS[2].content in message
    assert message.endswith("Question : Combien de congés ?")
    assert message.index('numero="1"') < message.index('numero="2"') < message.index("Question")


def test_format_pages() -> None:
    assert format_pages(HITS[0]) == "3"
    assert format_pages(replace(HITS[0], page_end=5)) == "3-5"


def test_extract_citations_in_order_of_first_appearance() -> None:
    answer = "25 jours [2]. Télétravail possible [1][3]. Encore les congés [2]."
    assert extract_citations(answer, passage_count=3) == [2, 1, 3]


def test_extract_citations_accepts_grouped_form() -> None:
    assert extract_citations("Voir [1, 3].", passage_count=3) == [1, 3]


def test_extract_citations_ignores_invalid_numbers() -> None:
    # [0] and [7] do not exist; "[note]" and "2024" are not citations.
    answer = "Selon [0] et [7], en 2024 [note], c'est vrai [2]."
    assert extract_citations(answer, passage_count=3) == [2]


def test_extract_citations_of_a_refusal_is_empty() -> None:
    assert extract_citations(REFUSAL_SENTENCE, passage_count=3) == []


def test_strip_citations() -> None:
    assert strip_citations("25 jours [2]. Télétravail [1][3] possible [1, 2].") == (
        "25 jours. Télétravail possible."
    )
