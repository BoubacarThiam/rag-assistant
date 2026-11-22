"""Chat routes: streamed answer (Server-Sent Events) and conversation history."""

import json
import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Query, Response, status
from fastapi.responses import StreamingResponse

from app.api.deps import ConversationStoreDep, LLMDep, RetrieverDep, SettingsDep
from app.core.errors import NotFoundError
from app.schemas.chat import ChatRequest, ConversationOut, MessageOut
from app.services.chat import ChatEvent, chat_stream
from app.services.conversations import ConversationSummary, StoredMessage

router = APIRouter(tags=["chat"])


def format_sse(event: ChatEvent) -> str:
    """One Server-Sent Event: an `event:` line, a `data:` line (JSON), then a blank line."""
    return f"event: {event.event}\ndata: {json.dumps(event.data, ensure_ascii=False)}\n\n"


@router.post(
    "/chat",
    response_class=StreamingResponse,
    responses={200: {"content": {"text/event-stream": {}}, "description": "Flux SSE"}},
)
async def chat(
    request: ChatRequest,
    store: ConversationStoreDep,
    retrieve: RetrieverDep,
    llm: LLMDep,
    settings: SettingsDep,
) -> StreamingResponse:
    # Checked before the stream starts, so the client gets a real 404 instead of an SSE error.
    if request.conversation_id and not await store.exists(request.conversation_id):
        raise NotFoundError("Conversation introuvable.")

    async def body() -> AsyncIterator[str]:
        async for event in chat_stream(
            store=store,
            retrieve=retrieve,
            llm=llm,
            question=request.message,
            conversation_id=request.conversation_id,
            document_ids=request.document_ids,
            history_messages=settings.chat_history_messages,
            mode=request.mode,
        ):
            yield format_sse(event)

    return StreamingResponse(
        body(),
        media_type="text/event-stream",
        # Proxies must not buffer or cache the stream, or tokens would arrive all at once.
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(
    store: ConversationStoreDep, limit: int = Query(default=50, ge=1, le=200)
) -> list[ConversationSummary]:
    return await store.recent(limit)


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(conversation_id: uuid.UUID, store: ConversationStoreDep) -> Response:
    if not await store.delete(conversation_id):
        raise NotFoundError("Conversation introuvable.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
async def list_messages(
    conversation_id: uuid.UUID, store: ConversationStoreDep
) -> list[StoredMessage]:
    if not await store.exists(conversation_id):
        raise NotFoundError("Conversation introuvable.")
    return await store.messages(conversation_id)
