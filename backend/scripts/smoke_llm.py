"""Manual check of the real Claude call (costs a few cents): python -m scripts.smoke_llm

Sends two fixed passages and two questions (one answerable, one not) and prints the streamed
answers, so you can see citations and the refusal sentence with your configured model.
"""

import asyncio
import uuid

from app.services.llm import ChatMessage, LLMError, get_llm_provider
from app.services.llm.prompts import SYSTEM_PROMPT, build_user_message, extract_citations
from app.services.retrieval import SearchHit

PASSAGES = [
    ("guide.pdf", 3, "Chaque salarié a droit à 25 jours ouvrés de congés payés par année civile."),
    ("charte.pdf", 7, "Le télétravail est autorisé jusqu'à trois jours par semaine."),
]
QUESTIONS = [
    "Combien de jours de congés ai-je, et puis-je télétravailler ?",
    "Quel est le salaire ?",
]


async def main() -> None:
    hits = [
        SearchHit(uuid.uuid4(), uuid.uuid4(), name, content, page, page, index, 0.8)
        for index, (name, page, content) in enumerate(PASSAGES)
    ]
    llm = get_llm_provider()
    for question in QUESTIONS:
        print(f"\nQ: {question}\nA: ", end="")
        parts: list[str] = []
        try:
            messages = [ChatMessage("user", build_user_message(question, hits))]
            async for text in llm.stream(SYSTEM_PROMPT, messages):
                parts.append(text)
                print(text, end="", flush=True)
        except LLMError as exc:
            print(f"\n[ERREUR {exc.code}] {exc.message}")
            return
        print(f"\n   -> passages cités : {extract_citations(''.join(parts), len(hits))}")


if __name__ == "__main__":
    asyncio.run(main())
