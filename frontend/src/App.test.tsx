// Whole-app tests with the backend replaced by a fake `fetch`.
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import type { DocumentInfo, Source } from "./types";

const DOCUMENT: DocumentInfo = {
  id: "doc-1",
  filename: "guide.pdf",
  size_bytes: 204800,
  page_count: 12,
  chunk_count: 30,
  status: "ready",
  error_message: null,
  created_at: "2026-11-15T10:00:00Z",
};

const SOURCE: Source = {
  index: 1,
  chunk_id: "c1",
  document_id: "doc-1",
  document_name: "guide.pdf",
  page_start: 3,
  page_end: 3,
  excerpt: "Chaque salarié a droit à 25 jours ouvrés de congés payés.",
  score: 0.83,
};

function sse(events: [string, unknown][]): string[] {
  return events.map(([event, data]) => `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);
}

/** A streaming HTTP response whose chunks are released one by one. */
function streamResponse(chunks: string[], gate?: Promise<void>): Response {
  const encoder = new TextEncoder();
  const body = new ReadableStream<Uint8Array>({
    async start(controller) {
      for (const [i, chunk] of chunks.entries()) {
        if (i === 1 && gate) await gate; // hold the stream after the first event
        controller.enqueue(encoder.encode(chunk));
      }
      controller.close();
    },
  });
  return new Response(body, { headers: { "Content-Type": "text/event-stream" } });
}

const json = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json" } });

interface Backend {
  documents: DocumentInfo[];
  chat: () => Response;
  chatBodies: unknown[];
}

function mockBackend(overrides: Partial<Backend> = {}): Backend {
  const backend: Backend = {
    documents: [DOCUMENT],
    chat: () =>
      streamResponse(
        sse([
          ["meta", { conversation_id: "conv-1" }],
          ["token", { text: "Vous avez **25 jours** " }],
          ["token", { text: "de congés [1]." }],
          ["sources", { sources: [SOURCE] }],
          ["done", { message_id: "m-1" }],
        ]),
      ),
    chatBodies: [],
    ...overrides,
  };
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      if (url === "/api/documents" && !init?.method) return json(backend.documents);
      if (url === "/api/chat") {
        backend.chatBodies.push(JSON.parse(init!.body as string));
        return backend.chat();
      }
      if (url.startsWith("/api/documents/") && init?.method === "DELETE") {
        return new Response(null, { status: 204 });
      }
      return json({ detail: "Introuvable.", code: "not_found" }, 404);
    }),
  );
  return backend;
}

async function ask(question: string) {
  await userEvent.type(screen.getByLabelText("Votre question"), `${question}{Enter}`);
}

beforeEach(() => {
  vi.spyOn(window, "confirm").mockReturnValue(true);
});

describe("App", () => {
  it("lists documents with their status and page count", async () => {
    mockBackend({
      documents: [
        DOCUMENT,
        { ...DOCUMENT, id: "doc-2", filename: "scan.pdf", status: "error", error_message: "Aucun texte." },
        { ...DOCUMENT, id: "doc-3", filename: "nouveau.pdf", status: "processing" },
      ],
    });
    render(<App />);

    expect(await screen.findByText("guide.pdf")).toBeInTheDocument();
    expect(screen.getByText("12 pages · 200 Ko")).toBeInTheDocument();
    expect(screen.getByText("Aucun texte.")).toBeInTheDocument();
    expect(screen.getByText("Traitement en cours…")).toBeInTheDocument();
  });

  it("streams an answer, then opens the cited source when its number is clicked", async () => {
    let release!: () => void;
    const gate = new Promise<void>((resolve) => (release = resolve));
    const backend = mockBackend();
    backend.chat = () => {
      const chunks = sse([
        ["meta", { conversation_id: "conv-1" }],
        ["token", { text: "Vous avez **25 jours** " }],
        ["token", { text: "de congés [1]." }],
        ["sources", { sources: [SOURCE] }],
        ["done", { message_id: "m-1" }],
      ]);
      return streamResponse(chunks, gate);
    };
    render(<App />);
    await screen.findByText("guide.pdf");

    await ask("Combien de congés ?");

    // Question shown, and the assistant is "thinking" until the first token arrives.
    expect(screen.getByText("Combien de congés ?")).toBeInTheDocument();
    expect(await screen.findByText("Réflexion…")).toBeInTheDocument();
    expect(screen.getByLabelText("Arrêter la réponse")).toBeInTheDocument();

    release();
    const citation = await screen.findByRole("button", { name: /Voir la source 1/ });
    expect(screen.getByText("25 jours").tagName).toBe("STRONG");
    expect(screen.queryByText("Réflexion…")).not.toBeInTheDocument();

    await userEvent.click(citation);

    const panel = screen.getByRole("complementary", { name: "Sources de la réponse" });
    expect(within(panel).getByText(SOURCE.excerpt)).toBeInTheDocument();
    expect(within(panel).getByText("page 3")).toBeInTheDocument();

    await userEvent.click(within(panel).getByLabelText("Fermer le panneau des sources"));
    expect(screen.queryByRole("complementary", { name: "Sources de la réponse" })).not.toBeInTheDocument();
  });

  it("keeps the conversation id for follow-up questions", async () => {
    const backend = mockBackend();
    render(<App />);
    await screen.findByText("guide.pdf");

    await ask("Q1");
    await screen.findByRole("button", { name: /Voir la source 1/ });
    await ask("Q2");
    await waitFor(() => expect(backend.chatBodies).toHaveLength(2));

    expect(backend.chatBodies[0]).toEqual({ message: "Q1", mode: "documents" });
    expect(backend.chatBodies[1]).toEqual({ message: "Q2", conversation_id: "conv-1", mode: "documents" });
  });

  it("restricts the search to the checked documents", async () => {
    const backend = mockBackend();
    render(<App />);

    await userEvent.click(await screen.findByLabelText("Limiter la recherche à guide.pdf"));
    expect(screen.getByText("Recherche limitée à 1 document.")).toBeInTheDocument();
    await ask("Q");

    await waitFor(() => expect(backend.chatBodies).toHaveLength(1));
    expect(backend.chatBodies[0]).toEqual({ message: "Q", document_ids: ["doc-1"], mode: "documents" });
  });

  it("answers from general knowledge when that mode is chosen, and says so", async () => {
    const backend = mockBackend({
      chat: () =>
        streamResponse(
          sse([
            ["meta", { conversation_id: "conv-1" }],
            ["token", { text: "Paris est la capitale de la France." }],
            ["sources", { sources: [] }],
            ["done", { message_id: "m-1" }],
          ]),
        ),
    });
    render(<App />);
    await screen.findByText("guide.pdf");

    await userEvent.click(screen.getByRole("radio", { name: /Connaissances générales/ }));
    expect(screen.getByLabelText("Votre question")).toHaveAttribute(
      "placeholder",
      "Posez n'importe quelle question…",
    );
    await ask("Capitale de la France ?");

    expect(await screen.findByText("Réponse hors de vos documents, sans source")).toBeInTheDocument();
    expect(backend.chatBodies[0]).toEqual({ message: "Capitale de la France ?", mode: "general" });
    // The choice is remembered for the next visit.
    expect(localStorage.getItem("chat_mode")).toBe("general");
  });

  it("does not flag cited answers or answers given in documents mode", async () => {
    mockBackend();
    render(<App />);
    await screen.findByText("guide.pdf");

    expect(screen.getByRole("radio", { name: /Mes documents/ })).toBeChecked();
    await ask("Combien de congés ?");

    await screen.findByRole("button", { name: /Voir la source 1/ });
    expect(screen.queryByText("Réponse hors de vos documents, sans source")).not.toBeInTheDocument();
  });

  it("shows the error sent by the server in the stream", async () => {
    mockBackend({
      chat: () =>
        streamResponse(
          sse([
            ["meta", { conversation_id: "conv-1" }],
            ["error", { detail: "Clé API Anthropic absente ou invalide.", code: "llm_auth" }],
          ]),
        ),
    });
    render(<App />);
    await screen.findByText("guide.pdf");

    await ask("Q");

    expect(await screen.findByRole("alert")).toHaveTextContent("Clé API Anthropic absente");
    expect(screen.getByLabelText("Envoyer la question")).toBeInTheDocument(); // can ask again
  });

  it("shows a clear message when the server is unreachable", async () => {
    mockBackend({
      chat: () => {
        throw new TypeError("Failed to fetch");
      },
    });
    render(<App />);
    await screen.findByText("guide.pdf");

    await ask("Q");

    expect(await screen.findByRole("alert")).toHaveTextContent("Impossible de joindre le serveur");
  });

  it("deletes a document after confirmation", async () => {
    mockBackend();
    render(<App />);

    await userEvent.click(await screen.findByLabelText("Supprimer guide.pdf"));

    await waitFor(() => expect(screen.queryByText("guide.pdf")).not.toBeInTheDocument());
    expect(window.confirm).toHaveBeenCalled();
  });

  it("starts a new conversation", async () => {
    const backend = mockBackend();
    render(<App />);
    await screen.findByText("guide.pdf");
    await ask("Q1");
    await screen.findByRole("button", { name: /Voir la source 1/ });

    await userEvent.click(screen.getByRole("button", { name: /Nouvelle conversation/ }));
    expect(screen.queryByText("Q1")).not.toBeInTheDocument();
    await ask("Q2");

    await waitFor(() => expect(backend.chatBodies).toHaveLength(2));
    expect(backend.chatBodies[1]).toEqual({ message: "Q2", mode: "documents" });
  });

  it("toggles dark mode and remembers the choice", async () => {
    mockBackend();
    render(<App />);

    await userEvent.click(screen.getByLabelText("Passer en mode sombre"));

    expect(document.documentElement).toHaveClass("dark");
    expect(localStorage.getItem("theme")).toBe("dark");
    await userEvent.click(screen.getByLabelText("Passer en mode clair"));
    expect(document.documentElement).not.toHaveClass("dark");
  });
});
