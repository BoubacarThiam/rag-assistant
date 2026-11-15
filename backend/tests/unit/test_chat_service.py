"""The RAG orchestration with a scripted LLM, an in-memory store and a fake retriever."""

import uuid
from collections.abc import Sequence
from typing import Any

from app.services.chat import ChatEvent, chat_stream
from app.services.conversations import InMemoryConversationStore
from app.services.llm import FakeLLMProvider, LLMError
from app.services.llm.prompts import REFUSAL_SENTENCE, SYSTEM_PROMPT
from app.services.retrieval import SearchHit
from tests.helpers import HITS


class FakeRetriever:
    def __init__(self, hits: list[SearchHit] | None = None, error: Exception | None = None) -> None:
        self.hits = HITS if hits is None else hits
        self.error = error
        self.calls: list[tuple[str, Sequence[uuid.UUID] | None]] = []

    async def __call__(
        self, query: str, document_ids: Sequence[uuid.UUID] | None
    ) -> list[SearchHit]:
        self.calls.append((query, document_ids))
        if self.error:
            raise self.error
        return self.hits


async def run(
    question: str,
    *,
    store: InMemoryConversationStore,
    llm: FakeLLMProvider,
    retriever: FakeRetriever | None = None,
    conversation_id: uuid.UUID | None = None,
    history_messages: int = 6,
    document_ids: list[uuid.UUID] | None = None,
) -> list[ChatEvent]:
    return [
        event
        async for event in chat_stream(
            store=store,
            retrieve=retriever or FakeRetriever(),
            llm=llm,
            question=question,
            conversation_id=conversation_id,
            document_ids=document_ids,
            history_messages=history_messages,
        )
    ]


def data(events: list[ChatEvent], name: str) -> dict[str, Any]:
    (event,) = [e for e in events if e.event == name]
    return event.data


async def test_events_arrive_in_order_with_streamed_text() -> None:
    store = InMemoryConversationStore()
    llm = FakeLLMProvider(chunks=["Vous avez ", "25 jours ", "de congés [1]."])

    events = await run("Combien de congés ?", store=store, llm=llm)

    assert [e.event for e in events] == ["meta", "token", "token", "token", "sources", "done"]
    assert "".join(e.data["text"] for e in events if e.event == "token") == (
        "Vous avez 25 jours de congés [1]."
    )
    assert uuid.UUID(data(events, "meta")["conversation_id"]) in store.conversations


async def test_sources_contain_only_cited_passages() -> None:
    llm = FakeLLMProvider(chunks=["Congés : 25 jours [1]. Mutuelle : 60 % [3]."])

    events = await run("Résumé ?", store=InMemoryConversationStore(), llm=llm)

    sources = data(events, "sources")["sources"]
    assert [s["index"] for s in sources] == [1, 3]
    assert sources[0] == {
        "index": 1,
        "chunk_id": str(HITS[0].chunk_id),
        "document_id": str(HITS[0].document_id),
        "document_name": "guide.pdf",
        "page_start": 3,
        "page_end": 3,
        "excerpt": HITS[0].content,
        "score": 0.8,
    }


async def test_llm_receives_system_prompt_passages_and_question() -> None:
    llm = FakeLLMProvider()

    await run("Combien de congés ?", store=InMemoryConversationStore(), llm=llm)

    (call,) = llm.calls
    assert call.system == SYSTEM_PROMPT
    assert [m.role for m in call.messages] == ["user"]
    assert HITS[0].content in call.messages[0].content
    assert call.messages[0].content.endswith("Question : Combien de congés ?")


async def test_exchange_is_saved_and_sent_back_as_history() -> None:
    store = InMemoryConversationStore()
    llm = FakeLLMProvider(chunks=["Vous avez 25 jours [1]."])
    first = await run("Combien de congés ?", store=store, llm=llm)
    conversation_id = uuid.UUID(data(first, "meta")["conversation_id"])

    second = await run("Et le télétravail ?", store=store, llm=llm, conversation_id=conversation_id)

    assert data(second, "meta")["conversation_id"] == str(conversation_id)
    stored = store.conversations[conversation_id]
    assert [(m.role, m.content) for m in stored[:2]] == [
        ("user", "Combien de congés ?"),
        ("assistant", "Vous avez 25 jours [1]."),
    ]
    assert stored[1].sources and stored[1].sources[0]["index"] == 1
    assert data(second, "done")["message_id"] == str(stored[3].id)

    history = llm.calls[1].messages
    assert [m.role for m in history] == ["user", "assistant", "user"]
    assert history[0].content == "Combien de congés ?"  # raw question, without old passages
    assert history[1].content == "Vous avez 25 jours."  # old citation numbers removed
    assert "<passages>" in history[2].content


async def test_history_is_limited_to_the_last_messages() -> None:
    store = InMemoryConversationStore()
    llm = FakeLLMProvider()
    events = await run("Q1", store=store, llm=llm)
    conversation_id = uuid.UUID(data(events, "meta")["conversation_id"])
    for question in ("Q2", "Q3"):
        await run(question, store=store, llm=llm, conversation_id=conversation_id)

    await run("Q4", store=store, llm=llm, conversation_id=conversation_id, history_messages=2)

    messages = llm.calls[-1].messages
    assert [m.role for m in messages] == ["user", "assistant", "user"]
    assert messages[0].content == "Q3"


async def test_history_can_be_disabled() -> None:
    store = InMemoryConversationStore()
    llm = FakeLLMProvider()
    events = await run("Q1", store=store, llm=llm)
    conversation_id = uuid.UUID(data(events, "meta")["conversation_id"])

    await run("Q2", store=store, llm=llm, conversation_id=conversation_id, history_messages=0)

    assert len(llm.calls[-1].messages) == 1


async def test_without_passages_the_refusal_is_sent_without_calling_the_llm() -> None:
    store = InMemoryConversationStore()
    llm = FakeLLMProvider()

    events = await run("Question ?", store=store, llm=llm, retriever=FakeRetriever(hits=[]))

    assert llm.calls == []
    assert data(events, "token")["text"] == REFUSAL_SENTENCE
    assert data(events, "sources")["sources"] == []
    (messages,) = store.conversations.values()
    assert messages[1].content == REFUSAL_SENTENCE


async def test_refusal_from_the_llm_has_no_sources() -> None:
    llm = FakeLLMProvider(chunks=[REFUSAL_SENTENCE])
    events = await run("Capitale du Pérou ?", store=InMemoryConversationStore(), llm=llm)
    assert data(events, "sources")["sources"] == []


async def test_llm_error_ends_the_stream_with_an_error_event_and_saves_nothing() -> None:
    store = InMemoryConversationStore()
    llm = FakeLLMProvider(
        chunks=["Début"], error=LLMError("Service indisponible.", "llm_unavailable")
    )

    events = await run("Question ?", store=store, llm=llm)

    assert [e.event for e in events] == ["meta", "token", "error"]
    assert data(events, "error") == {"detail": "Service indisponible.", "code": "llm_unavailable"}
    assert list(store.conversations.values()) == [[]]


async def test_unexpected_error_is_hidden_from_the_client() -> None:
    retriever = FakeRetriever(error=RuntimeError("password=secret in connection string"))

    events = await run(
        "Question ?", store=InMemoryConversationStore(), llm=FakeLLMProvider(), retriever=retriever
    )

    error = data(events, "error")
    assert error["code"] == "internal_error"
    assert "secret" not in error["detail"]


async def test_document_filter_is_passed_to_the_retriever() -> None:
    retriever = FakeRetriever()
    doc_id = uuid.uuid4()

    await run(
        "Question ?",
        store=InMemoryConversationStore(),
        llm=FakeLLMProvider(),
        retriever=retriever,
        document_ids=[doc_id],
    )

    assert retriever.calls == [("Question ?", [doc_id])]
