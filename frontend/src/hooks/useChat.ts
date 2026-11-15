import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, getMessages, streamChat } from "../lib/api";
import type { ChatEvent, ChatMessage } from "../types";

const STORAGE_KEY = "conversation_id";
const GENERIC_ERROR = "Une erreur inattendue est survenue. Réessayez.";

let localId = 0;
const nextId = () => `local-${++localId}`;

function readStoredConversation(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

function storeConversation(id: string | null) {
  try {
    if (id) localStorage.setItem(STORAGE_KEY, id);
    else localStorage.removeItem(STORAGE_KEY);
  } catch {
    // ignore: the conversation just won't survive a reload
  }
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const conversationId = useRef<string | null>(null);
  const abort = useRef<AbortController | null>(null);

  // Restore the previous conversation after a page reload.
  useEffect(() => {
    const stored = readStoredConversation();
    if (!stored) return;
    let cancelled = false;
    getMessages(stored)
      .then((history) => {
        if (cancelled) return;
        conversationId.current = stored;
        setMessages(
          history.map((m) => ({
            id: m.id,
            role: m.role,
            content: m.content,
            sources: m.sources ?? [],
            status: "done",
          })),
        );
      })
      .catch(() => storeConversation(null)); // deleted or unreachable: start fresh
    return () => {
      cancelled = true;
    };
  }, []);

  const send = useCallback(async (question: string, documentIds: string[]) => {
    const text = question.trim();
    if (!text || abort.current) return;

    const answerId = nextId();
    const patchAnswer = (patch: (message: ChatMessage) => ChatMessage) =>
      setMessages((current) => current.map((m) => (m.id === answerId ? patch(m) : m)));

    setMessages((current) => [
      ...current,
      { id: nextId(), role: "user", content: text, sources: [], status: "done" },
      { id: answerId, role: "assistant", content: "", sources: [], status: "streaming" },
    ]);
    setIsStreaming(true);
    const controller = new AbortController();
    abort.current = controller;

    const onEvent = ({ event, data }: ChatEvent) => {
      switch (event) {
        case "meta":
          conversationId.current = data.conversation_id;
          storeConversation(data.conversation_id);
          break;
        case "token":
          patchAnswer((m) => ({ ...m, content: m.content + data.text }));
          break;
        case "sources":
          patchAnswer((m) => ({ ...m, sources: data.sources }));
          break;
        case "done":
          patchAnswer((m) => ({ ...m, status: "done" }));
          break;
        case "error":
          patchAnswer((m) => ({ ...m, status: "error", error: data.detail }));
          break;
      }
    };

    try {
      await streamChat(
        {
          message: text,
          conversation_id: conversationId.current ?? undefined,
          document_ids: documentIds.length > 0 ? documentIds : undefined,
        },
        onEvent,
        controller.signal,
      );
      // Stream closed without "done" or "error" (connection cut): don't leave it spinning.
      patchAnswer((m) =>
        m.status === "streaming" ? { ...m, status: "error", error: "La réponse a été interrompue." } : m,
      );
    } catch (error) {
      if (controller.signal.aborted) {
        patchAnswer((m) => ({ ...m, status: "done" })); // stopped by the user: keep the partial text
      } else {
        // A stored conversation that no longer exists on the server: forget it.
        if (error instanceof ApiError && error.status === 404) {
          conversationId.current = null;
          storeConversation(null);
        }
        const detail = error instanceof ApiError ? error.message : GENERIC_ERROR;
        patchAnswer((m) => ({ ...m, status: "error", error: detail }));
      }
    } finally {
      abort.current = null;
      setIsStreaming(false);
    }
  }, []);

  const stop = useCallback(() => abort.current?.abort(), []);

  const reset = useCallback(() => {
    abort.current?.abort();
    conversationId.current = null;
    storeConversation(null);
    setMessages([]);
  }, []);

  return { messages, isStreaming, send, stop, reset };
}
