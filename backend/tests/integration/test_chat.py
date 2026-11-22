"""End to end with a real database: upload a PDF, ask a question, get cited sources."""

import asyncio

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.main import app
from app.services.llm import FakeLLMProvider, get_llm_provider
from app.services.llm.prompts import REFUSAL_SENTENCE
from tests.helpers import parse_sse
from tests.pdf_factory import make_pdf

pytestmark = pytest.mark.integration

PAGES = [
    "Chaque salarié a droit à 25 jours de congés payés par an.",
    "Le télétravail est possible trois jours par semaine.",
]


@pytest.fixture
def llm() -> FakeLLMProvider:
    llm = FakeLLMProvider(chunks=["Vous avez 25 jours ", "de congés payés [1]."])
    app.dependency_overrides[get_llm_provider] = lambda: llm
    return llm


async def upload_and_wait(client: AsyncClient) -> str:
    response = await client.post(
        "/documents", files=[("files", ("guide.pdf", make_pdf(PAGES), "application/pdf"))]
    )
    document_id: str = response.json()[0]["id"]
    for _ in range(50):
        if (await client.get(f"/documents/{document_id}")).json()["status"] == "ready":
            return document_id
        await asyncio.sleep(0.1)
    raise AssertionError("ingestion did not finish")


async def test_question_answer_with_sources_and_persisted_history(
    client: AsyncClient, factory: async_sessionmaker[AsyncSession], llm: FakeLLMProvider
) -> None:
    document_id = await upload_and_wait(client)

    events = parse_sse((await client.post("/chat", json={"message": "congés payés ?"})).text)

    assert [name for name, _ in events] == ["meta", "token", "token", "sources", "done"]
    (source,) = events[3][1]["sources"]
    assert source["index"] == 1
    assert source["document_id"] == document_id
    assert source["document_name"] == "guide.pdf"
    assert "congés payés" in source["excerpt"]
    # The LLM was given the retrieved passage.
    assert "25 jours de congés payés" in llm.calls[0].messages[-1].content

    conversation_id = events[0][1]["conversation_id"]
    await client.post("/chat", json={"message": "Et ensuite ?", "conversation_id": conversation_id})

    messages = (await client.get(f"/conversations/{conversation_id}/messages")).json()
    assert [m["role"] for m in messages] == ["user", "assistant", "user", "assistant"]
    assert messages[1]["sources"][0]["document_name"] == "guide.pdf"
    assert messages[1]["id"] == events[4][1]["message_id"]
    # Second call: the first exchange was sent back as history.
    assert [m.role for m in llm.calls[1].messages] == ["user", "assistant", "user"]


async def test_without_documents_the_assistant_declines(
    client: AsyncClient, factory: async_sessionmaker[AsyncSession], llm: FakeLLMProvider
) -> None:
    events = parse_sse((await client.post("/chat", json={"message": "Bonjour ?"})).text)

    assert events[1] == ("token", {"text": REFUSAL_SENTENCE})
    assert llm.calls == []


async def test_conversation_list_and_delete(
    client: AsyncClient, factory: async_sessionmaker[AsyncSession], llm: FakeLLMProvider
) -> None:
    first = parse_sse((await client.post("/chat", json={"message": "Première question"})).text)
    second = parse_sse((await client.post("/chat", json={"message": "Seconde question"})).text)
    first_id = first[0][1]["conversation_id"]
    # Continuing the first conversation moves it back to the top.
    await client.post("/chat", json={"message": "Suite", "conversation_id": first_id})

    listed = (await client.get("/conversations")).json()
    assert [c["title"] for c in listed] == ["Première question", "Seconde question"]

    assert (await client.delete(f"/conversations/{first_id}")).status_code == 204
    listed = (await client.get("/conversations")).json()
    assert [c["id"] for c in listed] == [second[0][1]["conversation_id"]]
    # Its messages went with it (ON DELETE CASCADE).
    assert (await client.get(f"/conversations/{first_id}/messages")).status_code == 404
