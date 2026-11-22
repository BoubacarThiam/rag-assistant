// Demo backend: lets you try the interface without Docker, database or API key.
//   npm run mock   (then, in another terminal: npm run dev)
// It imitates the real API (documents, upload, streamed chat with sources) with canned data.
import { createServer } from "node:http";
import { randomUUID } from "node:crypto";

const PORT = Number(process.env.MOCK_PORT ?? 8000);

const now = () => new Date().toISOString();
const documents = [
  {
    id: randomUUID(),
    filename: "guide-du-salarie.pdf",
    size_bytes: 1_258_291,
    page_count: 24,
    chunk_count: 61,
    status: "ready",
    error_message: null,
    created_at: now(),
    updated_at: now(),
  },
  {
    id: randomUUID(),
    filename: "charte-teletravail.pdf",
    size_bytes: 342_016,
    page_count: 8,
    chunk_count: 19,
    status: "ready",
    error_message: null,
    created_at: now(),
    updated_at: now(),
  },
  {
    id: randomUUID(),
    filename: "contrat-scanne.pdf",
    size_bytes: 2_411_724,
    page_count: null,
    chunk_count: 0,
    status: "error",
    error_message: "Aucun texte n'a pu être extrait de ce PDF (document scanné ?).",
    created_at: now(),
    updated_at: now(),
  },
];

const SOURCES = [
  {
    index: 1,
    document_name: "guide-du-salarie.pdf",
    page_start: 7,
    page_end: 7,
    excerpt:
      "Chaque salarié bénéficie de 25 jours ouvrés de congés payés par année civile. Les congés doivent être posés au moins un mois à l'avance via le portail RH. Le report des congés non pris est limité à 5 jours, à utiliser avant le 31 mars de l'année suivante.",
    score: 0.8421,
  },
  {
    index: 2,
    document_name: "charte-teletravail.pdf",
    page_start: 2,
    page_end: 3,
    excerpt:
      "Le télétravail est autorisé jusqu'à trois jours par semaine après la période d'essai. Le salarié doit rester joignable entre 10 h et 16 h les jours télétravaillés. Une indemnité mensuelle de 30 euros couvre les frais de connexion et d'électricité.",
    score: 0.8173,
  },
].map((s) => ({ ...s, chunk_id: randomUUID(), document_id: documents[s.index - 1].id }));

const ANSWER =
  "Voici ce que disent vos documents :\n\n" +
  "- **Congés payés** : vous avez droit à 25 jours ouvrés par année civile, à poser au moins un mois à l'avance [1].\n" +
  "- **Report** : au maximum 5 jours peuvent être reportés, à utiliser avant le 31 mars [1].\n" +
  "- **Télétravail** : jusqu'à trois jours par semaine après la période d'essai, avec une indemnité de 30 euros par mois [2].";
const REFUSAL = "Je ne trouve pas cette information dans tes documents.";
// "General knowledge" mode, for a question outside the documents (no citation).
const GENERAL_ANSWER =
  "Vos documents n'en parlent pas, mais voici une réponse générale : Paris est la capitale " +
  "de la France. C'est aussi sa plus grande ville, avec environ 2 millions d'habitants.";

const conversations = new Map();
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function send(res, status, body) {
  res.writeHead(status, { "Content-Type": "application/json" });
  res.end(body === undefined ? undefined : JSON.stringify(body));
}

async function readBody(req) {
  const chunks = [];
  for await (const chunk of req) chunks.push(chunk);
  return Buffer.concat(chunks);
}

async function chat(req, res) {
  const { message, conversation_id, mode = "documents" } = JSON.parse(
    (await readBody(req)).toString("utf8"),
  );
  const id = conversation_id ?? randomUUID();
  if (!conversations.has(id)) conversations.set(id, []);
  const unknown = /salaire|météo|capitale/i.test(message);
  const answer = unknown ? (mode === "general" ? GENERAL_ANSWER : REFUSAL) : ANSWER;
  const sources = unknown ? [] : SOURCES;

  res.writeHead(200, { "Content-Type": "text/event-stream", "Cache-Control": "no-cache" });
  const emit = (event, data) => res.write(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);
  emit("meta", { conversation_id: id });
  await sleep(900); // "Réflexion…"
  for (const word of answer.split(/(?<=\s)/)) {
    emit("token", { text: word });
    await sleep(35);
  }
  const messageId = randomUUID();
  conversations.get(id).push(
    { id: randomUUID(), role: "user", content: message, sources: null, created_at: now() },
    { id: messageId, role: "assistant", content: answer, sources, mode, created_at: now() },
  );
  emit("sources", { sources });
  emit("done", { message_id: messageId });
  res.end();
}

createServer(async (req, res) => {
  const { pathname } = new URL(req.url, "http://localhost");
  try {
    if (pathname === "/health") return send(res, 200, { status: "ok", database: "ok" });
    if (pathname === "/documents" && req.method === "GET") return send(res, 200, documents);
    if (pathname === "/documents" && req.method === "POST") {
      const body = (await readBody(req)).toString("latin1");
      const names = [...body.matchAll(/filename="([^"]+)"/g)].map((m) => m[1]);
      const created = names.map((filename) => ({
        id: randomUUID(),
        filename: Buffer.from(filename, "latin1").toString("utf8"),
        size_bytes: Math.round(body.length / names.length),
        page_count: null,
        chunk_count: 0,
        status: "processing",
        error_message: null,
        created_at: now(),
        updated_at: now(),
      }));
      documents.unshift(...created);
      // Pretend ingestion takes a few seconds.
      setTimeout(() => {
        for (const doc of created) Object.assign(doc, { status: "ready", page_count: 12, chunk_count: 30 });
      }, 4000);
      return send(res, 202, created);
    }
    const docMatch = pathname.match(/^\/documents\/([\w-]+)$/);
    if (docMatch && req.method === "DELETE") {
      const index = documents.findIndex((d) => d.id === docMatch[1]);
      if (index === -1) return send(res, 404, { detail: "Document introuvable.", code: "not_found" });
      documents.splice(index, 1);
      res.writeHead(204);
      return res.end();
    }
    if (pathname === "/conversations" && req.method === "GET") {
      const list = [...conversations.entries()]
        .filter(([, messages]) => messages.length > 0)
        .map(([id, messages]) => ({
          id,
          title: messages[0].content.slice(0, 80),
          updated_at: messages.at(-1).created_at,
        }))
        .sort((a, b) => b.updated_at.localeCompare(a.updated_at));
      return send(res, 200, list);
    }
    const deleteMatch = pathname.match(/^\/conversations\/([\w-]+)$/);
    if (deleteMatch && req.method === "DELETE") {
      if (!conversations.delete(deleteMatch[1])) {
        return send(res, 404, { detail: "Conversation introuvable.", code: "not_found" });
      }
      res.writeHead(204);
      return res.end();
    }
    const convMatch = pathname.match(/^\/conversations\/([\w-]+)\/messages$/);
    if (convMatch && req.method === "GET") {
      const messages = conversations.get(convMatch[1]);
      if (!messages) return send(res, 404, { detail: "Conversation introuvable.", code: "not_found" });
      return send(res, 200, messages);
    }
    if (pathname === "/chat" && req.method === "POST") return await chat(req, res);
    send(res, 404, { detail: "Introuvable.", code: "not_found" });
  } catch (error) {
    console.error(error);
    send(res, 500, { detail: "Erreur interne du serveur.", code: "internal_error" });
  }
}).listen(PORT, () => console.log(`Mock API (demo data) on http://localhost:${PORT}`));
