# CLAUDE.md — Assistant IA (RAG) sur documents PDF

## Le projet
Application de chat qui répond aux questions **uniquement à partir des PDF importés par l'utilisateur**,
en citant ses sources ([1], [2]…) avec document + page + extrait. Projet portfolio : l'objectif est de
montrer un pipeline RAG complet, **évalué et testé**, pas un simple appel d'API.

Pipeline : PDF → extraction page par page → nettoyage → découpage en passages (chunks) → embeddings
→ pgvector → recherche top-k (vectorielle, puis hybride + RRF) → prompt strict → Claude en streaming (SSE)
→ citations cliquables dans l'interface.

## Stack
| Couche | Choix |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2 (async, asyncpg), Alembic, Pydantic v2 / pydantic-settings |
| Gestion des dépendances | `uv` (pyproject.toml + uv.lock) |
| Base de données | PostgreSQL 16 + pgvector (image `pgvector/pgvector:pg16`), index HNSW cosinus, FTS `french` |
| Extraction PDF | PyMuPDF (`pymupdf`) |
| Embeddings | `intfloat/multilingual-e5-base` (768 dim) via sentence-transformers, derrière l'interface `EmbeddingProvider` |
| LLM | API Claude via le SDK officiel `anthropic` (AsyncAnthropic), modèle dans `.env` (`LLM_MODEL`, défaut `claude-opus-5-5`), derrière l'interface `LLMProvider`. Alternative gratuite : `LLM_PROVIDER=openai_compatible` (SDK `openai`, Groq/Gemini/Ollama), `openai_compatible_provider.py` |
| Frontend | React + Vite + TypeScript + Tailwind CSS (v4) |
| Tests | pytest + pytest-asyncio + httpx (backend), Vitest + Testing Library (frontend) |
| Lancement | `docker compose up` (services : `db`, `api`, `web`) |

## Arborescence
```
backend/
  app/
    main.py                 # création de l'app FastAPI, CORS, routers, lifespan
    api/                    # routes HTTP fines : health, documents, search, chat
    services/
      ingestion/            # extraction.py, cleaning.py, chunking.py, pipeline.py
      embeddings/           # base.py (EmbeddingProvider), e5.py, fake.py (tests)
      retrieval/            # vector.py, fulltext.py, hybrid.py (RRF), reranker.py (phase 7)
      llm/                  # base.py (LLMProvider), anthropic_provider.py, prompts.py, fake.py
      chat.py               # orchestration RAG : retrieval → prompt → stream → sources
    models/                 # modèles SQLAlchemy : Document, Chunk, Conversation, Message
    schemas/                # schémas Pydantic (entrées/sorties API)
    core/                   # config.py (Settings), db.py (engine/session), logging.py, errors.py
  alembic/                  # migrations
  tests/                    # unit/ et integration/ ; fixtures PDF dans tests/fixtures/
  pyproject.toml, Dockerfile
frontend/
  src/ components/ hooks/ lib/ (client API + parseur SSE) types/
eval/
  datasets/                 # questions.jsonl (question, réponse attendue, doc, page, passage attendu)
  pdfs/                     # PDF d'exemple utilisés par l'évaluation
  run.py                    # python -m eval.run
  metrics/                  # retrieval.py (hit@k, MRR), judge.py (LLM juge + grille)
  reports/                  # AAAA-MM-JJ_HHMM_<label>.md / .json
docs/PLAN.md                # plan détaillé par phases
docker-compose.yml, .env.example, README.md
```

## Conventions
- **Langue** : code, noms de variables et commits en anglais ; interface, messages d'erreur utilisateur,
  docs et README en français.
- **Commits** : Conventional Commits (`feat:`, `fix:`, `test:`, `chore:`, `docs:`, `refactor:`), un commit
  par étape ; on termine chaque phase par un commit. Jamais de `.env` ni de clé API commitée.
- **Typage** : annotations complètes, `mypy --strict` sur `app/`, `ruff` (lint + format). Côté front : `strict: true`.
- **Architecture** : routes fines dans `app/api`, logique dans `app/services`, accès DB via sessions async
  injectées (`Depends`). Les services ne dépendent que des interfaces (`EmbeddingProvider`, `LLMProvider`).
- **Erreurs** : exceptions métier dans `core/errors.py`, converties en réponses JSON `{"detail": ..., "code": ...}`.
  Jamais de stack trace renvoyée au client.
- **Logs** : `logging` standard, format structuré (niveau, module, message, contexte : document_id, durée…).
- **Config** : tout passe par `core/config.py` (pydantic-settings, lit `.env`). Pas de valeur magique dans le code.
- **Tests** : aucun test ne télécharge le modèle d'embedding ni n'appelle l'API Claude — on utilise
  `FakeEmbeddingProvider` (déterministe) et `FakeLLMProvider`. Les tests d'intégration utilisent une base
  Postgres+pgvector de test (pgvector ne tourne pas sous SQLite).
- **Embeddings e5** : préfixer `"query: "` pour les questions et `"passage: "` pour les chunks
  (obligatoire pour ce modèle). Vecteurs normalisés → distance cosinus.
- **Tokens** : la taille des chunks est mesurée avec le tokenizer du modèle d'embedding (limite 512 tokens).

## Commandes
```bash
docker compose up --build                       # tout lancer (db + api + web)
docker compose exec api alembic upgrade head    # migrations
docker compose exec api pytest                  # tests backend
cd frontend && npm test                         # tests frontend
docker compose exec api python -m eval.run      # évaluation (voir eval/README.md)
uv run --project backend python -m eval.run --retrieval-only   # hors Docker, depuis la racine

# Hors Docker (depuis backend/) : uv sync, puis
uv run pytest            # les tests d'intégration sont "skipped" si Postgres est injoignable
uv run ruff check . && uv run ruff format --check . && uv run mypy

# Frontend sans backend (depuis frontend/) : API de démonstration + Vite
npm run mock             # terminal 1 : fausse API sur :8000 (données d'exemple)
npm run dev              # terminal 2 : http://localhost:5173
npm test && npm run typecheck
```

## Méthode de travail
Le projet avance par phases (voir `docs/PLAN.md`). À la fin de chaque phase : lancer les tests, montrer ce
qui marche, expliquer brièvement ce qui a été fait et pourquoi, puis **attendre la validation** avant la
phase suivante. Expliquer simplement les concepts nouveaux (l'auteur est étudiant).
