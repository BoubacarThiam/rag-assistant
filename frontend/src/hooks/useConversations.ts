import { useCallback, useEffect, useRef, useState } from "react";
import { deleteConversation, listConversations } from "../lib/api";
import type { ConversationSummary } from "../types";

/** The list of past conversations shown in the sidebar. */
export function useConversations() {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const refresh = useCallback(async () => {
    try {
      const list = await listConversations();
      if (mounted.current) setConversations(list);
    } catch {
      // The history is a convenience: the chat keeps working without it.
    }
  }, []);

  /** Returns false if the server refused or could not be reached. */
  const remove = useCallback(async (id: string): Promise<boolean> => {
    try {
      await deleteConversation(id);
    } catch {
      return false;
    }
    setConversations((current) => current.filter((c) => c.id !== id));
    return true;
  }, []);

  return { conversations, refresh, remove };
}
