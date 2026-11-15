"""Conversation storage behind a small interface (SQL in production, in-memory in tests)."""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import Conversation, Message, MessageRole

TITLE_MAX_LENGTH = 80


@dataclass(frozen=True)
class StoredMessage:
    id: uuid.UUID
    role: str
    content: str
    sources: list[dict[str, Any]] | None
    created_at: datetime


class ConversationStore(Protocol):
    async def create(self) -> uuid.UUID: ...

    async def exists(self, conversation_id: uuid.UUID) -> bool: ...

    async def messages(
        self, conversation_id: uuid.UUID, limit: int | None = None
    ) -> list[StoredMessage]:
        """Messages in chronological order; with `limit`, only the most recent ones."""
        ...

    async def save_exchange(
        self,
        conversation_id: uuid.UUID,
        question: str,
        answer: str,
        sources: list[dict[str, Any]],
        asked_at: datetime,
    ) -> uuid.UUID:
        """Store the user question and the assistant answer; returns the answer's id."""
        ...


def _title_from(question: str) -> str:
    title = " ".join(question.split())
    return title if len(title) <= TITLE_MAX_LENGTH else title[: TITLE_MAX_LENGTH - 1] + "…"


class SqlConversationStore:
    """Each method uses its own short session: nothing stays open while the LLM streams."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create(self) -> uuid.UUID:
        async with self._session_factory() as session:
            conversation = Conversation()
            session.add(conversation)
            await session.commit()
            return conversation.id

    async def exists(self, conversation_id: uuid.UUID) -> bool:
        async with self._session_factory() as session:
            return await session.get(Conversation, conversation_id) is not None

    async def messages(
        self, conversation_id: uuid.UUID, limit: int | None = None
    ) -> list[StoredMessage]:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        async with self._session_factory() as session:
            rows = list(await session.scalars(stmt))
        return [
            StoredMessage(m.id, m.role, m.content, m.sources, m.created_at) for m in reversed(rows)
        ]

    async def save_exchange(
        self,
        conversation_id: uuid.UUID,
        question: str,
        answer: str,
        sources: list[dict[str, Any]],
        asked_at: datetime,
    ) -> uuid.UUID:
        async with self._session_factory() as session:
            conversation = await session.get(Conversation, conversation_id)
            if conversation is None:
                raise LookupError(f"conversation {conversation_id} not found")
            if conversation.title is None:
                conversation.title = _title_from(question)
            # Explicit timestamps: both rows are inserted in one transaction, so the database
            # clock (now()) would give them the same time and their order would be ambiguous.
            answer_message = Message(
                conversation_id=conversation_id,
                role=MessageRole.ASSISTANT.value,
                content=answer,
                sources=sources,
                created_at=datetime.now(UTC),
            )
            session.add_all(
                [
                    Message(
                        conversation_id=conversation_id,
                        role=MessageRole.USER.value,
                        content=question,
                        created_at=asked_at,
                    ),
                    answer_message,
                ]
            )
            await session.commit()
            return answer_message.id


@dataclass
class InMemoryConversationStore:
    """For tests."""

    conversations: dict[uuid.UUID, list[StoredMessage]] = field(default_factory=dict)

    async def create(self) -> uuid.UUID:
        conversation_id = uuid.uuid4()
        self.conversations[conversation_id] = []
        return conversation_id

    async def exists(self, conversation_id: uuid.UUID) -> bool:
        return conversation_id in self.conversations

    async def messages(
        self, conversation_id: uuid.UUID, limit: int | None = None
    ) -> list[StoredMessage]:
        stored = self.conversations[conversation_id]
        return stored[-limit:] if limit else list(stored)

    async def save_exchange(
        self,
        conversation_id: uuid.UUID,
        question: str,
        answer: str,
        sources: list[dict[str, Any]],
        asked_at: datetime,
    ) -> uuid.UUID:
        answer_id = uuid.uuid4()
        self.conversations[conversation_id] += [
            StoredMessage(uuid.uuid4(), "user", question, None, asked_at),
            StoredMessage(answer_id, "assistant", answer, sources, datetime.now(UTC)),
        ]
        return answer_id
