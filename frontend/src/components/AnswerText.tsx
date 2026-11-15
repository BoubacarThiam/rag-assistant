import { memo, useMemo } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import { citationIndex, linkifyCitations } from "../lib/citations";
import type { Source } from "../types";

interface Props {
  text: string;
  sources: Source[];
  onCitationClick: (index: number) => void;
}

/** The assistant's answer: Markdown, with each [n] rendered as a badge that opens its source. */
export const AnswerText = memo(function AnswerText({ text, sources, onCitationClick }: Props) {
  const markdown = useMemo(() => linkifyCitations(text), [text]);

  const components = useMemo<Components>(() => {
    const known = new Map(sources.map((source) => [source.index, source]));
    return {
      a({ href, children }) {
        const index = citationIndex(href);
        if (index === null) {
          return (
            <a href={href} target="_blank" rel="noreferrer" className="text-primary underline">
              {children}
            </a>
          );
        }
        const source = known.get(index);
        const badge =
          "mx-0.5 inline-flex h-5 min-w-5 items-center justify-center rounded-md px-1 align-text-top text-xs font-semibold";
        // Sources arrive at the end of the stream: until then the number is shown but inert.
        if (!source) {
          return <span className={`${badge} bg-surface-2 text-muted`}>{index}</span>;
        }
        return (
          <button
            type="button"
            onClick={() => onCitationClick(index)}
            title={`${source.document_name} — page ${source.page_start}`}
            aria-label={`Voir la source ${index} : ${source.document_name}, page ${source.page_start}`}
            className={`${badge} cursor-pointer bg-primary-soft text-on-primary-soft transition-colors duration-150 hover:bg-primary hover:text-on-primary`}
          >
            {index}
          </button>
        );
      },
    };
  }, [sources, onCitationClick]);

  return (
    <div className="answer leading-relaxed">
      <ReactMarkdown components={components}>{markdown}</ReactMarkdown>
    </div>
  );
});
