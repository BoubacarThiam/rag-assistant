import { AlertCircle, ArrowUp, BookOpen, FileSearch, Square } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { pluralize } from "../lib/format";
import type { ChatMessage } from "../types";
import { AnswerText } from "./AnswerText";

interface Props {
  messages: ChatMessage[];
  isStreaming: boolean;
  hasReadyDocuments: boolean;
  onSend: (question: string) => void;
  onStop: () => void;
  onOpenSources: (messageId: string, index: number | null) => void;
}

const SUGGESTIONS = [
  "Résume les points clés de ce document.",
  "Quelles sont les dates importantes mentionnées ?",
  "Quelles obligations sont décrites ?",
];

function ThinkingIndicator() {
  return (
    <div role="status" className="flex items-center gap-2 text-sm text-muted">
      <span className="flex gap-1" aria-hidden>
        <span className="thinking-dot size-1.5 rounded-full bg-primary" />
        <span className="thinking-dot size-1.5 rounded-full bg-primary" />
        <span className="thinking-dot size-1.5 rounded-full bg-primary" />
      </span>
      Réflexion…
    </div>
  );
}

function MessageBubble({
  message,
  onOpenSources,
}: {
  message: ChatMessage;
  onOpenSources: Props["onOpenSources"];
}) {
  if (message.role === "user") {
    return (
      <div className="animate-in flex justify-end">
        <p className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-md bg-primary px-4 py-2.5 text-on-primary">
          {message.content}
        </p>
      </div>
    );
  }

  const waiting = message.status === "streaming" && message.content === "";
  return (
    <div className="animate-in flex justify-start">
      <div className="max-w-[92%] rounded-2xl rounded-bl-md border border-border bg-surface px-4 py-3 md:max-w-[85%]">
        {waiting ? (
          <ThinkingIndicator />
        ) : (
          <AnswerText
            text={message.content}
            sources={message.sources}
            onCitationClick={(index) => onOpenSources(message.id, index)}
          />
        )}

        {message.status === "error" && (
          <p
            role="alert"
            className="mt-2 flex items-start gap-2 rounded-lg bg-danger-soft px-3 py-2 text-sm text-danger"
          >
            <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden />
            {message.error}
          </p>
        )}

        {message.sources.length > 0 && (
          <button
            type="button"
            onClick={() => onOpenSources(message.id, null)}
            className="mt-3 inline-flex cursor-pointer items-center gap-1.5 rounded-lg border border-border px-2.5 py-1.5 text-xs font-medium text-muted transition-colors duration-150 hover:border-primary hover:text-primary"
          >
            <BookOpen className="size-3.5" aria-hidden />
            {pluralize(message.sources.length, "source")}
          </button>
        )}
      </div>
    </div>
  );
}

function EmptyState({
  hasReadyDocuments,
  onPick,
}: {
  hasReadyDocuments: boolean;
  onPick: (question: string) => void;
}) {
  return (
    <div className="mx-auto flex h-full max-w-md flex-col items-center justify-center gap-4 px-4 text-center">
      <span className="flex size-14 items-center justify-center rounded-2xl bg-primary-soft text-on-primary-soft">
        <FileSearch className="size-7" aria-hidden />
      </span>
      <h1 className="text-xl font-semibold">Interrogez vos documents</h1>
      <p className="text-sm text-muted">
        {hasReadyDocuments
          ? "Posez une question : la réponse s'appuie uniquement sur vos PDF, avec les sources citées."
          : "Importez un PDF dans la barre latérale, puis posez vos questions. Chaque réponse cite ses sources."}
      </p>
      {hasReadyDocuments && (
        <ul className="flex w-full flex-col gap-2">
          {SUGGESTIONS.map((suggestion) => (
            <li key={suggestion}>
              <button
                type="button"
                onClick={() => onPick(suggestion)}
                className="w-full cursor-pointer rounded-xl border border-border bg-surface px-4 py-2.5 text-left text-sm transition-colors duration-150 hover:border-primary"
              >
                {suggestion}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function Chat({
  messages,
  isStreaming,
  hasReadyDocuments,
  onSend,
  onStop,
  onOpenSources,
}: Props) {
  const [draft, setDraft] = useState("");
  const scroller = useRef<HTMLDivElement>(null);
  const stickToBottom = useRef(true);

  // Follow the stream, unless the user scrolled up to read something.
  useEffect(() => {
    const element = scroller.current;
    if (element && stickToBottom.current) element.scrollTop = element.scrollHeight;
  }, [messages]);

  function submit(event?: FormEvent) {
    event?.preventDefault();
    if (!draft.trim() || isStreaming) return;
    stickToBottom.current = true;
    onSend(draft);
    setDraft("");
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      submit();
    }
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div
        ref={scroller}
        onScroll={(event) => {
          const el = event.currentTarget;
          stickToBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
        }}
        className="min-h-0 flex-1 overflow-y-auto"
      >
        {messages.length === 0 ? (
          <EmptyState hasReadyDocuments={hasReadyDocuments} onPick={onSend} />
        ) : (
          <div className="mx-auto flex max-w-3xl flex-col gap-4 px-4 py-6" aria-live="polite">
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} onOpenSources={onOpenSources} />
            ))}
          </div>
        )}
      </div>

      <form onSubmit={submit} className="border-t border-border bg-bg px-4 py-3">
        <div className="mx-auto flex max-w-3xl items-end gap-2 rounded-2xl border border-border bg-surface p-2 transition-colors duration-150 focus-within:border-primary">
          <label htmlFor="question" className="sr-only">
            Votre question
          </label>
          <textarea
            id="question"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={onKeyDown}
            rows={1}
            placeholder="Posez une question sur vos documents…"
            className="max-h-40 min-h-11 flex-1 resize-none bg-transparent px-2 py-2.5 placeholder:text-muted focus:outline-none [field-sizing:content]"
          />
          {isStreaming ? (
            <button
              type="button"
              onClick={onStop}
              aria-label="Arrêter la réponse"
              className="flex size-11 shrink-0 cursor-pointer items-center justify-center rounded-xl bg-surface-2 text-text transition-colors duration-150 hover:bg-border"
            >
              <Square className="size-4 fill-current" aria-hidden />
            </button>
          ) : (
            <button
              type="submit"
              disabled={!draft.trim()}
              aria-label="Envoyer la question"
              className="flex size-11 shrink-0 cursor-pointer items-center justify-center rounded-xl bg-primary text-on-primary transition-colors duration-150 hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-40"
            >
              <ArrowUp className="size-5" aria-hidden />
            </button>
          )}
        </div>
        <p className="mx-auto mt-1.5 max-w-3xl text-center text-xs text-muted">
          Entrée pour envoyer · Maj + Entrée pour un retour à la ligne
        </p>
      </form>
    </div>
  );
}
