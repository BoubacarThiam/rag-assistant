"""RAG orchestration: question -> retrieval -> prompt -> streamed answer -> cited sources.

`chat_stream` yields events that the API layer serializes as Server-Sent Events:

    meta     {"conversation_id": ...}          once, first
    token    {"text": "..."}                    many, as the answer is generated
    sources  {"sources": [...]}                 once, the passages actually cited
    done     {"message_id": ...}                once, last
    error    {"detail": "...", "code": "..."}   instead of sources/done if something fails
"""

import logging
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.services.conversations import ConversationStore, StoredMessage
from app.services.llm.base import ChatMessage, LLMError, LLMProvider
from app.services.llm.prompts import (
    REFUSAL_SENTENCE,
    SYSTEM_PROMPT,
    build_user_message,
    extract_citations,
    strip_citations,
)
from app.services.retrieval.types import SearchHit

logger = logging.getLogger(__name__)

# (question, document_ids) -> passages. Hides the database and the embedding model.
Retriever = Callable[[str, Sequence[uuid.UUID] | None], Awaitable[list[SearchHit]]]

UNEXPECTED_ERROR = "Une erreur inattendue est survenue. Réessayez."


@dataclass(frozen=True)
class ChatEvent:
    event: str
    data: dict[str, Any]


def build_history(stored: list[StoredMessage]) -> list[ChatMessage]:
    """Past messages for the LLM: citations removed, and starting with a user turn."""
    history = [
        ChatMessage(
            role="assistant" if m.role == "assistant" else "user",
            content=strip_citations(m.content) if m.role == "assistant" else m.content,
        )
        for m in stored
    ]
    while history and history[0].role != "user":
        history.pop(0)  # the window may have cut an exchange in half
    return history


def build_sources(answer: str, hits: list[SearchHit]) -> list[dict[str, Any]]:
    """Only the passages the answer actually cites, keeping their [n] number."""
    return [
        {
            "index": number,
            "chunk_id": str(hits[number - 1].chunk_id),
            "document_id": str(hits[number - 1].document_id),
            "document_name": hits[number - 1].document_name,
            "page_start": hits[number - 1].page_start,
            "page_end": hits[number - 1].page_end,
            "excerpt": hits[number - 1].content,
            "score": round(hits[number - 1].score, 4),
        }
        for number in extract_citations(answer, len(hits))
    ]


async def chat_stream(
    *,
    store: ConversationStore,
    retrieve: Retriever,
    llm: LLMProvider,
    question: str,
    conversation_id: uuid.UUID | None,
    document_ids: Sequence[uuid.UUID] | None,
    history_messages: int,
) -> AsyncIterator[ChatEvent]:
    asked_at = datetime.now(UTC)
    try:
        if conversation_id is None:
            conversation_id = await store.create()
        yield ChatEvent("meta", {"conversation_id": str(conversation_id)})

        hits = await retrieve(question, document_ids)
        parts: list[str] = []
        if not hits:
            # Nothing to ground an answer on (no document imported yet): no need to call the LLM.
            parts.append(REFUSAL_SENTENCE)
            yield ChatEvent("token", {"text": REFUSAL_SENTENCE})
        else:
            stored = await store.messages(conversation_id, limit=history_messages or None)
            history = build_history(stored) if history_messages else []
            messages = [*history, ChatMessage("user", build_user_message(question, hits))]
            async for text in llm.stream(SYSTEM_PROMPT, messages):
                parts.append(text)
                yield ChatEvent("token", {"text": text})

        answer = "".join(parts)
        sources = build_sources(answer, hits)
        message_id = await store.save_exchange(conversation_id, question, answer, sources, asked_at)
        logger.info(
            "Chat answered: conversation=%s passages=%d cited=%d chars=%d",
            conversation_id,
            len(hits),
            len(sources),
            len(answer),
        )
        yield ChatEvent("sources", {"sources": sources})
        yield ChatEvent("done", {"message_id": str(message_id)})
    except LLMError as exc:
        logger.warning("Chat failed (%s): %s", exc.code, exc.message)
        yield ChatEvent("error", {"detail": exc.message, "code": exc.code})
    except Exception:
        logger.exception("Chat failed unexpectedly")
        yield ChatEvent("error", {"detail": UNEXPECTED_ERROR, "code": "internal_error"})
