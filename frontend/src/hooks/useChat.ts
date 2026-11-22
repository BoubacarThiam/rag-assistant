import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, getMessages, streamChat } from "../lib/api";
import type { ChatEvent, ChatMessage, ChatMode, StoredMessage } from "../types";

const STORAGE_KEY = "conversation_id";
const MODE_KEY = "chat_mode";
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

function readStoredMode(): ChatMode {
  try {
    return localStorage.getItem(MODE_KEY) === "general" ? "general" : "documents";
  } catch {
    return "documents";
  }
}

function toChatMessages(history: StoredMessage[]): ChatMessage[] {
  return history.map((m) => ({
    id: m.id,
    role: m.role,
    content: m.content,
    sources: m.sources ?? [],
    ...(m.role === "assistant" && { mode: m.mode ?? "documents" }),
    status: "done",
  }));
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [mode, setModeState] = useState<ChatMode>(readStoredMode);
  const [isStreaming, setIsStreaming] = useState(false);
  const conversationId = useRef<string | null>(null);
  // Same value as the ref, as state: the sidebar highlights the open conversation.
  const [activeId, setActiveId] = useState<string | null>(null);
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
        setActiveId(stored);
        setMessages(toChatMessages(history));
      })
      .catch(() => storeConversation(null)); // deleted or unreachable: start fresh
    return () => {
      cancelled = true;
    };
  }, []);

  const setMode = useCallback((next: ChatMode) => {
    setModeState(next);
    try {
      localStorage.setItem(MODE_KEY, next);
    } catch {
      // ignore: the choice just won't survive a reload
    }
  }, []);

  const send = useCallback(async (question: string, documentIds: string[], mode: ChatMode) => {
    const text = question.trim();
    if (!text || abort.current) return;

    const answerId = nextId();
    const patchAnswer = (patch: (message: ChatMessage) => ChatMessage) =>
      setMessages((current) => current.map((m) => (m.id === answerId ? patch(m) : m)));

    setMessages((current) => [
      ...current,
      { id: nextId(), role: "user", content: text, sources: [], status: "done" },
      { id: answerId, role: "assistant", content: "", sources: [], mode, status: "streaming" },
    ]);
    setIsStreaming(true);
    const controller = new AbortController();
    abort.current = controller;

    const onEvent = ({ event, data }: ChatEvent) => {
      switch (event) {
        case "meta":
          conversationId.current = data.conversation_id;
          setActiveId(data.conversation_id);
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
          mode,
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
          setActiveId(null);
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

  /** Ask again the question of a failed answer: the failed pair is replaced by a new one.
   * (A failed answer is never stored by the server, so nothing is duplicated there.) */
  const retry = useCallback(
    (answerId: string, documentIds: string[], mode: ChatMode) => {
      if (abort.current) return;
      const index = messages.findIndex((m) => m.id === answerId);
      const question = messages[index - 1];
      if (index < 1 || question?.role !== "user") return;
      setMessages((current) => current.filter((m) => m.id !== answerId && m.id !== question.id));
      void send(question.content, documentIds, mode);
    },
    [messages, send],
  );

  const reset = useCallback(() => {
    abort.current?.abort();
    conversationId.current = null;
    setActiveId(null);
    storeConversation(null);
    setMessages([]);
  }, []);

  /** Show a past conversation; the next questions continue it. */
  const open = useCallback(async (id: string): Promise<boolean> => {
    abort.current?.abort();
    let history: StoredMessage[];
    try {
      history = await getMessages(id);
    } catch {
      return false;
    }
    conversationId.current = id;
    setActiveId(id);
    storeConversation(id);
    setMessages(toChatMessages(history));
    return true;
  }, []);

  return {
    messages,
    isStreaming,
    mode,
    setMode,
    send,
    stop,
    retry,
    reset,
    open,
    conversationId: activeId,
  };
}
