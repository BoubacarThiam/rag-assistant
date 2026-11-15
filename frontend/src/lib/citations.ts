// Citations: the model writes "[1]" or "[1, 3]" in its answer. We turn each number into a
// Markdown link "[1](#cite-1)", which the Markdown renderer then displays as a clickable badge.

export const CITE_PREFIX = "#cite-";

// [1] or [1, 2], but not an existing Markdown link like [1](...)
const CITATION_RE = /\[(\d+(?:\s*,\s*\d+)*)\](?!\()/g;

export function linkifyCitations(text: string): string {
  return text.replace(CITATION_RE, (_match, numbers: string) =>
    numbers
      .split(",")
      .map((raw) => {
        const n = Number(raw.trim());
        return `[${n}](${CITE_PREFIX}${n})`;
      })
      .join(""),
  );
}

/** "#cite-3" -> 3, anything else -> null */
export function citationIndex(href: string | undefined): number | null {
  if (!href?.startsWith(CITE_PREFIX)) return null;
  const n = Number(href.slice(CITE_PREFIX.length));
  return Number.isInteger(n) && n > 0 ? n : null;
}
