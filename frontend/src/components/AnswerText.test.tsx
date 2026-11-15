import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { Source } from "../types";
import { AnswerText } from "./AnswerText";

const SOURCE: Source = {
  index: 1,
  chunk_id: "c1",
  document_id: "d1",
  document_name: "guide.pdf",
  page_start: 3,
  page_end: 3,
  excerpt: "Chaque salarié a droit à 25 jours de congés payés.",
  score: 0.83,
};

describe("AnswerText", () => {
  it("renders citations as buttons that open their source", async () => {
    const onClick = vi.fn();
    render(<AnswerText text="Vous avez 25 jours [1]." sources={[SOURCE]} onCitationClick={onClick} />);

    await userEvent.click(screen.getByRole("button", { name: /Voir la source 1 : guide\.pdf, page 3/ }));

    expect(onClick).toHaveBeenCalledWith(1);
    expect(screen.getByText(/Vous avez 25 jours/)).toBeInTheDocument();
  });

  it("shows inert numbers while sources have not arrived yet", () => {
    render(<AnswerText text="Vous avez 25 jours [1]." sources={[]} onCitationClick={vi.fn()} />);

    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(screen.getByText("1")).toBeInTheDocument();
  });

  it("renders Markdown formatting", () => {
    render(<AnswerText text={"**Important** :\n\n- un\n- deux"} sources={[]} onCitationClick={vi.fn()} />);

    expect(screen.getByText("Important").tagName).toBe("STRONG");
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
  });
});
