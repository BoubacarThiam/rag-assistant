import { Check, Copy } from "lucide-react";
import { useEffect, useState } from "react";

const FEEDBACK_MS = 2000;

interface Props {
  /** The text to copy, or a function returning it (read at click time). */
  text: string | (() => string);
  label: string;
  className?: string;
}

/** Copies text to the clipboard and shows "Copié" for a moment. */
export function CopyButton({ text, label, className = "" }: Props) {
  const [state, setState] = useState<"idle" | "copied" | "failed">("idle");

  useEffect(() => {
    if (state === "idle") return;
    const timer = setTimeout(() => setState("idle"), FEEDBACK_MS);
    return () => clearTimeout(timer);
  }, [state]);

  async function copy() {
    try {
      await navigator.clipboard.writeText(typeof text === "function" ? text() : text);
      setState("copied");
    } catch {
      setState("failed"); // no clipboard access (old browser, page not in HTTPS)
    }
  }

  return (
    <button
      type="button"
      onClick={() => void copy()}
      aria-label={label}
      title={label}
      className={`inline-flex h-8 cursor-pointer items-center gap-1 rounded-md px-2 text-xs text-muted transition-colors duration-150 hover:bg-surface-2 hover:text-text ${className}`}
    >
      {state === "copied" ? (
        <Check className="size-3.5 text-primary" aria-hidden />
      ) : (
        <Copy className="size-3.5" aria-hidden />
      )}
      <span aria-live="polite">
        {state === "copied" ? "Copié" : state === "failed" ? "Échec de la copie" : "Copier"}
      </span>
    </button>
  );
}
