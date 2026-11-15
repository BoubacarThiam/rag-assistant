import type { Source } from "../types";

export function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} o`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} Ko`;
  return `${(bytes / (1024 * 1024)).toFixed(1).replace(".", ",")} Mo`;
}

export function formatPages(source: Pick<Source, "page_start" | "page_end">): string {
  return source.page_start === source.page_end
    ? `page ${source.page_start}`
    : `pages ${source.page_start}–${source.page_end}`;
}

export function pluralize(count: number, singular: string, plural = `${singular}s`): string {
  return `${count} ${count > 1 ? plural : singular}`;
}
