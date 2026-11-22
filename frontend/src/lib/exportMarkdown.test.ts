import { describe, expect, it } from "vitest";
import type { ChatMessage } from "../types";
import { conversationToMarkdown } from "./exportMarkdown";

describe("conversationToMarkdown", () => {
  it("writes questions, answers and their sources", () => {
    const messages: ChatMessage[] = [
      { id: "1", role: "user", content: "Combien de congés ?", sources: [], status: "done" },
      {
        id: "2",
        role: "assistant",
        content: "25 jours [1].",
        status: "done",
        sources: [
          {
            index: 1,
            chunk_id: "c",
            document_id: "d",
            document_name: "guide.pdf",
            page_start: 3,
            page_end: 4,
            excerpt: " 25 jours ouvrés. ",
            score: 0.8,
          },
        ],
      },
      { id: "3", role: "user", content: "Et après ?", sources: [], status: "done" },
      { id: "4", role: "assistant", content: "", sources: [], status: "error", error: "Coupé." },
    ];

    const markdown = conversationToMarkdown(messages, new Date(2026, 10, 22, 9, 5));

    expect(markdown).toContain("# Conversation — Assistant RAG");
    expect(markdown).toContain("22 novembre 2026");
    expect(markdown).toContain("## Question\n\nCombien de congés ?");
    expect(markdown).toContain("## Réponse\n\n25 jours [1].");
    expect(markdown).toContain("1. guide.pdf, pages 3–4 — « 25 jours ouvrés. »");
    expect(markdown).toContain("_(pas de réponse)_\n\n> Erreur : Coupé.");
  });
});
