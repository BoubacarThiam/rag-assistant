# Plan détaillé

## Phase 0 — Cadrage
- Plan, arborescence, `CLAUDE.md`, `.gitignore`, dépôt Git.

## Phase 1 — Fondations
- `docker-compose.yml` : `db` (pgvector/pgvector:pg16, volume, healthcheck `pg_isready`), `api`, plus tard `web`.
- Squelette FastAPI : `core/config.py`, `core/db.py` (engine async), logging, gestion d'erreurs.
- Alembic async + migration initiale : `CREATE EXTENSION vector`, tables `documents`, `chunks`,
  `conversations`, `messages`.
- `GET /health` : vérifie l'API **et** la base (`SELECT 1` + présence de l'extension vector).
- `.env.example`, Dockerfile (torch CPU uniquement pour alléger l'image, cache Hugging Face en volume).
- Tests : healthcheck, config.

## Phase 2 — Ingestion
- `POST /documents` (multipart, plusieurs fichiers) : contrôle de l'extension, du type MIME **et** des
  octets magiques `%PDF`, taille max (`MAX_UPLOAD_MB`), refus des PDF chiffrés ou sans texte.
- Traitement en tâche de fond (`BackgroundTasks`) : statut `processing` → `ready` | `error` (+ message).
- Extraction PyMuPDF page par page ; nettoyage : espaces, césures (`infor-\nmation` → `information`),
  suppression des en-têtes/pieds de page répétés (lignes présentes sur > 50 % des pages), numéros de page.
- Découpage : phrases → regroupées jusqu'à ~450 tokens, chevauchement ~75 tokens, sans couper une phrase ;
  chaque chunk garde `page_start`, `page_end`, `position`.
- Embeddings par lots, stockage dans `chunks.embedding vector(768)`.
- `GET /documents`, `GET /documents/{id}`, `DELETE /documents/{id}`.
- Tests : nettoyage, découpage (tailles, chevauchement, phrases intactes), extraction sur PDF fixture,
  API d'upload (types refusés, taille, statut).

## Phase 3 — Recherche
- Index HNSW (`vector_cosine_ops`), score = `1 - distance cosinus`.
- `POST /search` : `query`, `k`, `document_ids` (filtre optionnel) → passages + score + doc + page.
- Bonus : colonne `tsvector` générée (config `french`) + index GIN, recherche plein texte,
  fusion **RRF** (Reciprocal Rank Fusion), paramètre `mode = vector | fulltext | hybrid`.
- Tests : classement correct sur un corpus contrôlé, filtre par document, RRF (test unitaire pur).

## Phase 4 — Chat en streaming
- `POST /chat` (SSE) : `message`, `conversation_id?`, `document_ids?`.
- Événements : `meta` (conversation_id), `token` (morceau de texte), `sources` (fin), `done`, `error`.
- Prompt système strict (réponse uniquement depuis les passages, citation [n] de chaque affirmation,
  phrase de refus exacte si l'info manque). Passages numérotés dans le message utilisateur.
- Historique : les N derniers messages (`CHAT_HISTORY_MESSAGES`) stockés en base et renvoyés au LLM.
- Sources de fin : uniquement les passages réellement cités dans la réponse (doc, page, extrait).
- Gestion des erreurs API Claude (rate limit, surcharge, refus) → événement `error` propre.
- Tests avec `FakeLLMProvider` : format SSE, ordre des événements, sources filtrées, refus, historique.

## Phase 5 — Frontend
- Sidebar : liste des documents (statut, nb de pages), glisser-déposer, polling du statut.
- Chat : bulles, streaming au fil de l'eau (fetch + ReadableStream, car `EventSource` ne gère pas POST),
  indicateur « Réflexion… », citations [n] cliquables → panneau Sources (extrait surligné).
- Responsive (sidebar en tiroir sur mobile), mode sombre, interface en français.
- Tests Vitest : parseur SSE, rendu des citations, composants principaux.

## Phase 6 — Évaluation
- 2–3 PDF d'exemple + 25 questions (dont ~5 sans réponse dans les documents, pour tester le refus).
- `python -m eval.run` : hit rate@k et MRR ; LLM juge (sortie structurée) : fidélité, pertinence,
  citations, refus correct, notes 1–5 avec justification.
- Rapports Markdown + JSON horodatés dans `eval/reports/`, avec la config utilisée (modèle, k, taille des chunks…).

## Phase 7 — Améliorations guidées par l'évaluation
- Pistes, à mesurer une par une : recherche hybride, reranking (cross-encoder multilingue), taille/chevauchement
  des chunks, réécriture de la question à partir de l'historique, valeur de k.
- Tableau avant/après dans le README.

## Phase 8 — Finitions
- README (présentation, schéma Mermaid, installation, captures, résultats, choix techniques), nettoyage,
  CI GitHub Actions (lint + tests), préparation du déploiement.
