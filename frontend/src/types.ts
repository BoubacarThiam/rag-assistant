// Shapes returned by the FastAPI backend.

export type DocumentStatus = "processing" | "ready" | "error";

// "documents": answers only from the user's PDFs (cited), refusal otherwise.
// "general": the PDFs first when relevant, the model's general knowledge otherwise.
export type ChatMode = "documents" | "general";

export interface DocumentInfo {
  id: string;
  filename: string;
  size_bytes: number;
  page_count: number | null;
  chunk_count: number;
  status: DocumentStatus;
  error_message: string | null;
  created_at: string;
}

export interface Source {
  index: number; // the [n] used in the answer
  chunk_id: string;
  document_id: string;
  document_name: string;
  page_start: number;
  page_end: number;
  excerpt: string;
  score: number;
}

export interface StoredMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources: Source[] | null;
  mode?: ChatMode | null; // absent or null: user message, or answer stored before modes existed
  created_at: string;
}

export interface ConversationSummary {
  id: string;
  title: string; // the first question
  updated_at: string; // time of the last exchange
}

export type ChatEvent =
  | { event: "meta"; data: { conversation_id: string } }
  | { event: "token"; data: { text: string } }
  | { event: "sources"; data: { sources: Source[] } }
  | { event: "done"; data: { message_id: string } }
  | { event: "error"; data: { detail: string; code: string } };

// Messages as displayed in the chat.
export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources: Source[];
  mode?: ChatMode; // assistant messages only
  status: "streaming" | "done" | "error";
  error?: string;
}
