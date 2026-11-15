"""Importing this package registers every model on `Base.metadata` (used by Alembic)."""

from app.models.base import Base
from app.models.conversation import Conversation, Message, MessageRole
from app.models.document import EMBEDDING_DIM, Chunk, Document, DocumentStatus

__all__ = [
    "EMBEDDING_DIM",
    "Base",
    "Chunk",
    "Conversation",
    "Document",
    "DocumentStatus",
    "Message",
    "MessageRole",
]
