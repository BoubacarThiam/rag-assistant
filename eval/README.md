# Évaluation

Mesure la qualité du pipeline RAG pour pouvoir comparer deux versions avec des chiffres.

```bash
# Depuis la racine du dépôt
uv run --project backend python -m eval.run --label baseline                   # complet (appelle Claude : payant)
uv run --project backend python -m eval.run --label test --retrieval-only     # recherche seule (gratuit)
uv run --project backend python -m eval.run --label hybride --mode hybrid     # nécessite PostgreSQL

# Dans Docker
docker compose exec api python -m eval.run --label baseline
```

Chaque exécution réindexe les PDF d'exemple avec les réglages courants (`CHUNK_SIZE_TOKENS`,
`RETRIEVAL_TOP_K`, modèle…) et écrit `reports/AAAA-MM-JJ_HHMM_<label>.md` et `.json`.

## Contenu

| Fichier | Rôle |
|---|---|
| `corpus.py` | Texte des 6 documents fictifs (3 documents + 3 « jumeaux » aux chiffres différents) |
| `build_pdfs.py` | Génère `pdfs/` à partir du corpus (`python -m eval.build_pdfs`) |
| `datasets/questions.jsonl` | 28 questions : réponse attendue, document, page et citation exacte |
| `backends.py` | Indexation et recherche : PostgreSQL/pgvector, ou en mémoire si la base est absente |
| `metrics.py` | Hit rate@k, MRR, rappel des preuves ; détection des citations et des refus |
| `judge.py` | LLM juge : fidélité, pertinence, exactitude, notées de 1 à 5 selon une grille |
| `runner.py`, `report.py`, `run.py` | Exécution, agrégation, rapports |

## Le jeu de questions

| Type | Nombre | Ce qu'il teste |
|---|---|---|
| `factual` | 6 | Question directe, mots proches du texte |
| `paraphrase` | 9 | Même sens, autres mots (« travailler depuis chez lui » pour « télétravail ») |
| `keyword` | 5 | Terme exact : code d'erreur, référence, nom propre |
| `multi` | 3 | Réponse répartie sur deux passages |
| `unanswerable` | 5 | Information absente : la bonne réponse est le refus |

Un passage retrouvé est « bon » s'il vient du bon document et contient la citation attendue.
Ce critère reste valable quand on change la taille des passages.

## Limites à garder en tête

- **Petit jeu** : avec 28 questions, une question pèse 3,6 points. Un écart d'une question entre
  deux rapports n'est pas significatif.
- **Corpus synthétique** : les documents et les réponses attendues ont été écrits pour ce projet.
  Ils ne représentent pas toute la variété de vrais PDF (tableaux, colonnes, scans).
- **Juge de la même famille que le modèle évalué** par défaut : il peut être un peu indulgent.
  `JUDGE_MODEL` permet d'en choisir un autre.
- **Moteur en mémoire** : il calcule le même cosinus que pgvector mais sans index HNSW ni
  recherche plein texte. Les rapports indiquent toujours le moteur utilisé.
