import { MessageSquare, Trash2 } from "lucide-react";
import type { ConversationSummary } from "../types";

interface Props {
  conversations: ConversationSummary[];
  activeId: string | null;
  onOpen: (id: string) => void;
  onDelete: (id: string) => void;
}

function formatWhen(iso: string, now = new Date()): string {
  const date = new Date(iso);
  return date.toDateString() === now.toDateString()
    ? date.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })
    : date.toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
}

export function ConversationList({ conversations, activeId, onOpen, onDelete }: Props) {
  if (conversations.length === 0) {
    return <p className="px-2 text-sm text-muted">Vos conversations apparaîtront ici.</p>;
  }
  return (
    <ul className="flex flex-col gap-0.5">
      {conversations.map((conversation) => {
        const active = conversation.id === activeId;
        return (
          <li
            key={conversation.id}
            className={`group flex items-center gap-1 rounded-lg transition-colors duration-150 ${
              active ? "bg-primary-soft text-on-primary-soft" : "hover:bg-surface-2"
            }`}
          >
            <button
              type="button"
              onClick={() => onOpen(conversation.id)}
              aria-current={active ? "true" : undefined}
              title={conversation.title}
              className="flex min-h-10 min-w-0 flex-1 cursor-pointer items-center gap-2 px-2 text-left text-sm"
            >
              <MessageSquare className="size-3.5 shrink-0 opacity-70" aria-hidden />
              <span className="flex-1 truncate">{conversation.title}</span>
              <span className="shrink-0 text-xs opacity-70">{formatWhen(conversation.updated_at)}</span>
            </button>
            <button
              type="button"
              onClick={() => {
                if (window.confirm(`Supprimer la conversation « ${conversation.title} » ?`)) {
                  onDelete(conversation.id);
                }
              }}
              aria-label={`Supprimer la conversation ${conversation.title}`}
              className="cursor-pointer rounded-md p-1.5 text-muted transition-colors duration-150 hover:bg-danger-soft hover:text-danger md:opacity-0 md:group-hover:opacity-100 md:focus-visible:opacity-100"
            >
              <Trash2 className="size-4" aria-hidden />
            </button>
          </li>
        );
      })}
    </ul>
  );
}
