"""Application settings, read from environment variables and the `.env` file."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
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
    # How long /health waits for the database. A remote database (Neon) can need several
    # seconds to open a connection, more when it wakes up or the network is slow.
    db_check_timeout_s: float = Field(default=10.0, gt=0)

    # --- LLM ---
    # "anthropic" = Claude (default) | "openai_compatible" = any API with the OpenAI chat format
    # (Groq, Gemini, Ollama...), configured with llm_base_url / llm_api_key / llm_model.
    llm_provider: Literal["anthropic", "openai_compatible"] = "anthropic"
    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_api_key: SecretStr | None = None
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
    # Prepend the document title to each chunk before embedding it (see ingestion/context.py).
    # On by default: measured gain in docs/EXPERIMENTS.md. Changing it requires re-importing
    # the documents, since embeddings are computed at import time.
    embed_document_title: bool = True

    # --- Retrieval / chat ---
    retrieval_top_k: int = Field(default=5, gt=0, le=50)
    # Default search mode; Phase 7 picks the best one based on the evaluation.
    retrieval_mode: Literal["vector", "fulltext", "hybrid"] = "vector"
    # Hybrid search: candidates fetched from each method before fusion, and RRF constant.
    hybrid_candidates: int = Field(default=20, gt=0, le=200)
    rrf_k: int = Field(default=60, gt=0)
    # Reranking: a cross-encoder re-orders the first `rerank_candidates` results.
    # Off by default: small measured gain for several seconds per query on CPU
    # (see docs/EXPERIMENTS.md).
    rerank_enabled: bool = False
    reranker_model: str = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
    rerank_candidates: int = Field(default=20, gt=0, le=200)
    chat_history_messages: int = Field(default=6, ge=0)

    # --- Single-container deployment (e.g. Hugging Face Spaces) ---
    # "/api" when this app also serves the frontend; empty = API at the root (docker compose).
    api_prefix: str = ""
    # Folder holding the frontend build (index.html); empty = API only.
    static_dir: str = ""
    # When set, every request except the health check needs this password (HTTP basic auth).
    demo_password: SecretStr | None = None

    @field_validator("database_url", "test_database_url", "eval_database_url")
    @classmethod
    def use_asyncpg_url(cls, url: str) -> str:
        """Accept the URL a hosting service gives (e.g. Neon) and adapt it to asyncpg.

        `postgresql://...?sslmode=require&channel_binding=require` becomes
        `postgresql+asyncpg://...?ssl=require`: asyncpg has its own name for the SSL option
        and does not know `channel_binding`.
        """
        if url.startswith(("postgresql://", "postgres://")):
            url = "postgresql+asyncpg://" + url.split("://", 1)[1]
        base, _, query = url.partition("?")
        if not query:
            return url
        params = []
        for param in query.split("&"):
            key, _, value = param.partition("=")
            if key == "channel_binding":
                continue
            params.append(f"ssl={value}" if key == "sslmode" else param)
        return f"{base}?{'&'.join(params)}" if params else base

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
