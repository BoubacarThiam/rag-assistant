from app.services.ingestion.cleaning import clean_pages, clean_text, normalize_unicode
from app.services.ingestion.extraction import PageText


def page(number: int, text: str) -> PageText:
    return PageText(number=number, text=text)


def test_rejoins_words_hyphenated_across_lines() -> None:
    assert (
        clean_text("Le système d'infor-\nmation est prêt.") == "Le système d'information est prêt."
    )


def test_keeps_hyphen_of_compound_proper_nouns() -> None:
    assert (
        clean_text("Rencontre avec Jean-\nPierre demain.") == "Rencontre avec Jean-Pierre demain."
    )


def test_joins_lines_inside_paragraph_and_keeps_paragraphs() -> None:
    text = "Première ligne\ndu paragraphe.\n\n  Second   paragraphe. "
    assert clean_text(text) == "Première ligne du paragraphe.\n\nSecond paragraphe."


def test_unicode_normalization() -> None:
    ligature_fi, nbsp, soft_hyphen = chr(0xFB01), chr(0xA0), chr(0xAD)
    raw = f"{ligature_fi}chier{nbsp}prêt, ma{soft_hyphen}nuel"
    assert normalize_unicode(raw) == "fichier prêt, manuel"


TOPICS = ["Les congés payés.", "Le télétravail.", "La mutuelle.", "Les horaires."]


def test_removes_repeated_headers_and_page_numbers() -> None:
    pages = [
        page(n, f"ACME — Rapport annuel 2025\n{topic}\n{n}")
        for n, topic in enumerate(TOPICS, start=1)
    ]

    cleaned = clean_pages(pages)

    assert [p.text for p in cleaned] == TOPICS
    assert [p.number for p in cleaned] == [1, 2, 3, 4]


def test_removes_headers_containing_the_page_number() -> None:
    pages = [page(n, f"Guide ACME — p. {n}\n{topic}") for n, topic in enumerate(TOPICS, start=1)]
    assert [p.text for p in clean_pages(pages)] == TOPICS


def test_lines_differing_only_by_other_numbers_are_kept() -> None:
    # Regression: masking every digit made these look like a repeated header.
    lines = [f"Total {2020 + n} : {n * 7} jours." for n in range(1, 5)]
    pages = [page(n, line) for n, line in enumerate(lines, start=1)]
    assert [p.text for p in clean_pages(pages)] == lines


def test_page_numbers_like_page_x_of_y_are_removed() -> None:
    pages = [page(n, f"{TOPICS[n]}\nPage {n} / 3") for n in range(1, 4)]
    assert [p.text for p in clean_pages(pages)] == TOPICS[1:4]


def test_short_documents_keep_their_lines() -> None:
    # With fewer than 3 pages, a repeated line cannot be told apart from real content.
    pages = [page(1, "Titre\nA."), page(2, "Titre\nB.")]
    assert [p.text for p in clean_pages(pages)] == ["Titre A.", "Titre B."]


def test_numbers_inside_the_body_are_kept() -> None:
    body = "Introduction.\nLigne 2.\nLigne 3.\n2024\nLigne 5.\nLigne 6.\nConclusion."
    assert "2024" in clean_pages([page(1, body)])[0].text
