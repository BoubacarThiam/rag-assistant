import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    size_bytes: int
    page_count: int | None
    chunk_count: int
    status: Literal["processing", "ready", "error"]
    error_message: str | None
    created_at: datetime
    updated_at: datetime
