import pytest
from pydantic import ValidationError

from app.core.config import Settings


def make_settings(**overrides: object) -> Settings:
    # _env_file=None: the test must not depend on a developer's local .env
    return Settings(_env_file=None, **overrides)  # type: ignore[call-arg]


def test_defaults_are_sane() -> None:
    settings = make_settings()
    assert settings.llm_model == "claude-opus-5-5"
    assert settings.embedding_model == "intfloat/multilingual-e5-base"
    assert settings.chunk_overlap_tokens < settings.chunk_size_tokens
    assert settings.anthropic_api_key is None


def test_cors_origins_are_split_and_trimmed() -> None:
    settings = make_settings(cors_origins=" http://a.test , http://b.test,, ")
    assert settings.cors_origin_list == ["http://a.test", "http://b.test"]


def test_max_upload_bytes() -> None:
    assert make_settings(max_upload_mb=2).max_upload_bytes == 2 * 1024 * 1024


def test_reads_environment_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_MODEL", "claude-sonnet-5-5")
    monkeypatch.setenv("RETRIEVAL_TOP_K", "8")
    settings = make_settings()
    assert settings.llm_model == "claude-sonnet-5-5"
    assert settings.retrieval_top_k == 8


def test_api_key_is_never_printed() -> None:
    settings = make_settings(anthropic_api_key="sk-ant-secret")
    assert "sk-ant-secret" not in repr(settings)


def test_invalid_values_are_rejected() -> None:
    with pytest.raises(ValidationError):
        make_settings(retrieval_top_k=0)
