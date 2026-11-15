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
    # Separate database filled by `python -m eval.run` (created automatically).
    eval_database_url: str = "postgresql+asyncpg://rag:rag@localhost:5432/rag_eval"

    # --- LLM (Claude) ---
    anthropic_api_key: SecretStr | None = None
    llm_model: str = "claude-opus-5-5"
    judge_model: str = "claude-opus-5-5"
    # Upper bound for one answer (thinking + text). Generous: hitting it truncates the answer.
    llm_max_tokens: int = Field(default=64000, gt=0)
    # Thinking depth / token spend. Empty = let the model use its default
    # (required for older models that reject the parameter).
    llm_effort: Literal["", "low", "medium", "high", "xhigh", "max"] = "medium"
    # If a safety classifier declines a request, let the API retry it on a fallback model.
    # Turn off for models that do not support server-side fallbacks (e.g. Haiku).
    llm_refusal_fallback: bool = True

    # --- Embeddings ---
    embedding_model: str = "intfloat/multilingual-e5-base"
    embedding_batch_size: int = Field(default=32, gt=0)
    # "fake" = deterministic test provider, no model download (tests, quick demos).
    embedding_provider: Literal["e5", "fake"] = "e5"

    # --- Ingestion ---
    max_upload_mb: int = Field(default=20, gt=0)
    max_files_per_upload: int = Field(default=10, gt=0)
    chunk_size_tokens: int = Field(default=450, gt=0)
    chunk_overlap_tokens: int = Field(default=75, ge=0)

    # --- Retrieval / chat ---
    retrieval_top_k: int = Field(default=5, gt=0, le=50)
    # Default search mode; Phase 7 picks the best one based on the evaluation.
    retrieval_mode: Literal["vector", "fulltext", "hybrid"] = "vector"
    # Hybrid search: candidates fetched from each method before fusion, and RRF constant.
    hybrid_candidates: int = Field(default=20, gt=0, le=200)
    rrf_k: int = Field(default=60, gt=0)
    # Reranking: a cross-encoder re-orders the first `rerank_candidates` results.
    rerank_enabled: bool = False
    reranker_model: str = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
    rerank_candidates: int = Field(default=20, gt=0, le=200)
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
