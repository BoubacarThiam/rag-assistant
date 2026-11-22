import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Question = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]


class ChatRequest(BaseModel):
    message: Question
    conversation_id: uuid.UUID | None = Field(
        default=None, description="Absent : une nouvelle conversation est créée"
    )
    document_ids: list[uuid.UUID] | None = Field(
        default=None, description="Limiter la recherche à ces documents"
    )
    mode: Literal["documents", "general"] = Field(
        default="documents",
        description="documents : uniquement les documents, avec sources ; "
        "general : les documents d'abord, sinon les connaissances générales du modèle",
    )


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: Literal["user", "assistant"]
    content: str
    sources: list[dict[str, Any]] | None
    mode: Literal["documents", "general"] | None = None
    created_at: datetime


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    updated_at: datetime
