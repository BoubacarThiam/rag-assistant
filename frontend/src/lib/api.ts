import type { ChatEvent, ChatMode, DocumentInfo, StoredMessage } from "../types";
import { createSseParser } from "./sse";

const BASE_URL: string = import.meta.env.VITE_API_URL ?? "/api";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public code?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

const NETWORK_ERROR = "Impossible de joindre le serveur. Vérifiez qu'il est démarré.";

async function toApiError(response: Response): Promise<ApiError> {
  let message = `Erreur ${response.status}`;
  let code: string | undefined;
  try {
    const body = await response.json();
    // Our API returns {detail: string, code}; FastAPI validation errors return {detail: [...]}.
    if (typeof body.detail === "string") message = body.detail;
    else if (Array.isArray(body.detail)) message = "Requête invalide.";
    code = body.code;
  } catch {
    // not JSON: keep the generic message
  }
  return new ApiError(message, response.status, code);
}

async function request(path: string, init?: RequestInit): Promise<Response> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, init);
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError(NETWORK_ERROR, 0, "network");
  }
  if (!response.ok) throw await toApiError(response);
  return response;
}

export async function listDocuments(): Promise<DocumentInfo[]> {
  return (await request("/documents")).json();
}

export async function uploadDocuments(files: File[]): Promise<DocumentInfo[]> {
  const form = new FormData();
  for (const file of files) form.append("files", file);
  return (await request("/documents", { method: "POST", body: form })).json();
}

export async function deleteDocument(id: string): Promise<void> {
  await request(`/documents/${id}`, { method: "DELETE" });
}

export async function getMessages(conversationId: string): Promise<StoredMessage[]> {
  return (await request(`/conversations/${conversationId}/messages`)).json();
}

export interface ChatRequest {
  message: string;
  conversation_id?: string;
  document_ids?: string[];
  mode?: ChatMode;
}

/** POST /chat and call `onEvent` for each Server-Sent Event until the stream ends. */
export async function streamChat(
  body: ChatRequest,
  onEvent: (event: ChatEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const response = await request("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!response.body) throw new ApiError(NETWORK_ERROR, 0, "network");

  const parser = createSseParser(({ event, data }) => {
    onEvent({ event, data: JSON.parse(data) } as ChatEvent);
  });
  const reader = response.body.getReader();
  // stream: true keeps multi-byte characters (é, à…) intact when split across two chunks.
  const decoder = new TextDecoder();
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    parser.push(decoder.decode(value, { stream: true }));
  }
}
