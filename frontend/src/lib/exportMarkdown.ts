import type { ChatMessage } from "../types";
import { formatPages } from "./format";

/** The conversation as a Markdown document: questions, answers, and the sources they cite. */
export function conversationToMarkdown(messages: ChatMessage[], exportedAt = new Date()): string {
  const date = exportedAt.toLocaleString("fr-FR", { dateStyle: "long", timeStyle: "short" });
  const parts = [`# Conversation — Assistant RAG\n\n_Exportée le ${date}_`];
  for (const message of messages) {
    if (message.role === "user") {
      parts.push(`## Question\n\n${message.content}`);
      continue;
    }
    let answer = `## Réponse\n\n${message.content || "_(pas de réponse)_"}`;
    if (message.status === "error" && message.error) answer += `\n\n> Erreur : ${message.error}`;
    if (message.sources.length > 0) {
      const sources = message.sources.map(
        (s) => `${s.index}. ${s.document_name}, ${formatPages(s)} — « ${s.excerpt.trim()} »`,
      );
      answer += `\n\n**Sources**\n\n${sources.join("\n")}`;
    }
    parts.push(answer);
  }
  return `${parts.join("\n\n")}\n`;
}

/** Make the browser save `text` as a file. */
export function downloadText(filename: string, text: string): void {
  const url = URL.createObjectURL(new Blob([text], { type: "text/markdown;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
