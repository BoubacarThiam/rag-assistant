import { describe, expect, it } from "vitest";
import { citationIndex, linkifyCitations } from "./citations";
import { formatPages, formatSize, pluralize } from "./format";

describe("linkifyCitations", () => {
  it("turns [n] into a citation link", () => {
    expect(linkifyCitations("25 jours [2].")).toBe("25 jours [2](#cite-2).");
  });

  it("handles adjacent and grouped citations", () => {
    expect(linkifyCitations("Oui [1][3].")).toBe("Oui [1](#cite-1)[3](#cite-3).");
    expect(linkifyCitations("Oui [1, 3].")).toBe("Oui [1](#cite-1)[3](#cite-3).");
  });

  it("leaves real Markdown links and other brackets alone", () => {
    expect(linkifyCitations("Voir [1](https://exemple.fr) et [note].")).toBe(
      "Voir [1](https://exemple.fr) et [note].",
    );
  });
});

describe("citationIndex", () => {
  it("extracts the number from a citation link only", () => {
    expect(citationIndex("#cite-3")).toBe(3);
    expect(citationIndex("https://exemple.fr")).toBeNull();
    expect(citationIndex("#cite-abc")).toBeNull();
    expect(citationIndex(undefined)).toBeNull();
  });
});

describe("format helpers", () => {
  it("formats sizes in French units", () => {
    expect(formatSize(512)).toBe("512 o");
    expect(formatSize(2048)).toBe("2 Ko");
    expect(formatSize(1.5 * 1024 * 1024)).toBe("1,5 Mo");
  });

  it("formats page ranges", () => {
    expect(formatPages({ page_start: 3, page_end: 3 })).toBe("page 3");
    expect(formatPages({ page_start: 3, page_end: 4 })).toBe("pages 3–4");
  });

  it("pluralizes", () => {
    expect(pluralize(1, "source")).toBe("1 source");
    expect(pluralize(2, "source")).toBe("2 sources");
  });
});
