import { FileText, X } from "lucide-react";
import { useEffect, useRef } from "react";
import { formatPages } from "../lib/format";
import type { Source } from "../types";

interface Props {
  sources: Source[];
  activeIndex: number | null;
  onSelect: (index: number) => void;
  onClose: () => void;
}

export function SourcesPanel({ sources, activeIndex, onSelect, onClose }: Props) {
  const activeCard = useRef<HTMLLIElement>(null);

  useEffect(() => {
    activeCard.current?.scrollIntoView?.({ block: "nearest", behavior: "smooth" });
  }, [activeIndex]);

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">
          Sources ({sources.length})
        </h2>
        <button
          type="button"
          onClick={onClose}
          aria-label="Fermer le panneau des sources"
          className="cursor-pointer rounded-md p-2 text-muted transition-colors duration-150 hover:bg-surface-2 hover:text-text"
        >
          <X className="size-5" aria-hidden />
        </button>
      </div>

      {sources.length === 0 ? (
        <p className="p-4 text-sm text-muted">Cette réponse ne cite aucune source.</p>
      ) : (
        <ul className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto p-4">
          {sources.map((source) => {
            const active = source.index === activeIndex;
            return (
              <li
                key={source.index}
                ref={active ? activeCard : undefined}
                className={`rounded-xl border bg-surface transition-colors duration-200 ${
                  active ? "border-primary ring-2 ring-primary/25" : "border-border"
                }`}
              >
                <button
                  type="button"
                  onClick={() => onSelect(source.index)}
                  aria-current={active}
                  className="flex w-full cursor-pointer items-center gap-2 px-3 pt-3 text-left"
                >
                  <span className="inline-flex size-6 shrink-0 items-center justify-center rounded-md bg-primary-soft text-xs font-semibold text-on-primary-soft">
                    {source.index}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="flex items-center gap-1.5 text-sm font-medium">
                      <FileText className="size-3.5 shrink-0 text-muted" aria-hidden />
                      <span className="truncate" title={source.document_name}>
                        {source.document_name}
                      </span>
                    </span>
                    <span className="text-xs text-muted">{formatPages(source)}</span>
                  </span>
                </button>
                <blockquote className="m-3 max-h-56 overflow-y-auto border-l-2 border-primary/40 pl-3 text-sm leading-relaxed text-muted">
                  {source.excerpt}
                </blockquote>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
