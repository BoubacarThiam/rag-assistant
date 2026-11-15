"""Application settings, read from environment variables and the `.env` file."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Application ---
    app_name: str = "Assistant RAG"
    environment: Literal["dev", "test", "prod"] = "dev"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    # Comma-separated list, e.g. "http://localhost:5173,http://127.0.0.1:5173"
    cors_origins: str = "http://localhost:5173"

    # --- Database ---
    database_url: str = "postgresql+asyncpg://rag:rag@localhost:5432/rag"
    test_database_url: str = "postgresql+asyncpg://rag:rag@localhost:5432/rag_test"

    # --- LLM (Claude) ---
    anthropic_api_key: SecretStr | None = None
    llm_model: str = "claude-opus-5-5"
    judge_model: str = "claude-opus-5-5"

    # --- Embeddings ---
    embedding_model: str = "intfloat/multilingual-e5-base"

    # --- Ingestion ---
    max_upload_mb: int = Field(default=20, gt=0)
    chunk_size_tokens: int = Field(default=450, gt=0)
    chunk_overlap_tokens: int = Field(default=75, ge=0)

    # --- Retrieval / chat ---
    retrieval_top_k: int = Field(default=5, gt=0, le=50)
    chat_history_messages: int = Field(default=6, ge=0)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
