"""POST /chat over HTTP: SSE format, validation, history endpoint (no database, fake LLM)."""

import uuid
from collections.abc import Sequence

import pytest
from httpx import AsyncClient

from app.api.deps import get_conversation_store, get_retriever
from app.main import app
from app.services.conversations import InMemoryConversationStore
from app.services.llm import FakeLLMProvider, get_llm_provider
from app.services.retrieval import SearchHit
from tests.helpers import HITS, parse_sse


@pytest.fixture
def store() -> InMemoryConversationStore:
    store = InMemoryConversationStore()
    llm = FakeLLMProvider(chunks=["Vous avez 25 jours ", "de congés payés [1]."])

    async def retrieve(query: str, document_ids: Sequence[uuid.UUID] | None) -> list[SearchHit]:
        return HITS

    app.dependency_overrides[get_conversation_store] = lambda: store
    app.dependency_overrides[get_retriever] = lambda: retrieve
    app.dependency_overrides[get_llm_provider] = lambda: llm
    return store


async def test_chat_streams_server_sent_events(
    client: AsyncClient, store: InMemoryConversationStore
) -> None:
    response = await client.post("/chat", json={"message": "Combien de congés ?"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-cache"
    events = parse_sse(response.text)
    assert [name for name, _ in events] == ["meta", "token", "token", "sources", "done"]
    assert events[1][1] == {"text": "Vous avez 25 jours "}
    (source,) = events[3][1]["sources"]
    assert source["document_name"] == "guide.pdf"
    assert source["page_start"] == 3
    # Accents are sent as-is, not as é escapes.
    assert "congés payés" in response.text


async def test_chat_continues_an_existing_conversation(
    client: AsyncClient, store: InMemoryConversationStore
) -> None:
    first = parse_sse((await client.post("/chat", json={"message": "Q1"})).text)
    conversation_id = first[0][1]["conversation_id"]

    await client.post("/chat", json={"message": "Q2", "conversation_id": conversation_id})

    response = await client.get(f"/conversations/{conversation_id}/messages")
    assert response.status_code == 200
    messages = response.json()
    assert [(m["role"], m["content"]) for m in messages] == [
        ("user", "Q1"),
        ("assistant", "Vous avez 25 jours de congés payés [1]."),
        ("user", "Q2"),
        ("assistant", "Vous avez 25 jours de congés payés [1]."),
    ]
    assert messages[0]["sources"] is None
    assert messages[1]["sources"][0]["index"] == 1


async def test_unknown_conversation_is_a_plain_404(
    client: AsyncClient, store: InMemoryConversationStore
) -> None:
    unknown = str(uuid.uuid4())

    response = await client.post("/chat", json={"message": "Q", "conversation_id": unknown})

    assert response.status_code == 404
    assert response.json() == {"detail": "Conversation introuvable.", "code": "not_found"}
    assert (await client.get(f"/conversations/{unknown}/messages")).status_code == 404


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"message": ""},
        {"message": "   "},
        {"message": "x" * 4001},
        {"message": "Q", "conversation_id": "abc"},
    ],
)
async def test_invalid_requests_are_rejected(
    client: AsyncClient, store: InMemoryConversationStore, payload: dict[str, str]
) -> None:
    assert (await client.post("/chat", json=payload)).status_code == 422
    assert store.conversations == {}
