# Améliorations guidées par l'évaluation

Chaque piste a été mesurée avec `python -m eval.run` avant d'être adoptée ou écartée. Les
rapports complets sont dans [`eval/reports/`](../eval/reports/).

**Conditions de mesure.** Recherche seule (sans appel à Claude), sur les 23 questions du jeu
d'évaluation qui ont une réponse dans les documents. Embeddings `intfloat/multilingual-e5-base`,
k = 5, moteur en mémoire (cosinus exact, sans pgvector). Avec 23 questions, **une question pèse
4,3 points** : un écart d'une seule question n'est pas significatif.

## Résumé

| | Avant | Après |
|---|---|---|
| Configuration | passages de 450 tokens | 450 tokens + titre du document |
| Hit rate@1 | 73,9 % | **82,6 %** |
| Hit rate@5 | 95,7 % | **100 %** |
| MRR | 0,848 | **0,906** |
| Rappel des preuves | 93,5 % | **100 %** |
| Temps de recherche médian | 256 ms | 252 ms |

Rapports : `exp-chunks-450` (avant) et `v2-recherche` (après).

## 1. Taille des passages : l'hypothèse était fausse

Le premier rapport montrait des passages couvrant deux à trois pages. Hypothèse : des passages
plus petits, donc plus ciblés, seront mieux classés.

| Taille / chevauchement | Passages | Hit rate@1 | Hit rate@5 | MRR |
|---|---|---|---|---|
| 450 / 75 | 26 | 73,9 % | 95,7 % | 0,848 |
| 300 / 50 | 40 | 52,2 % | 91,3 % | 0,630 |
| 200 / 40 | 58 | 43,5 % | 78,3 % | 0,523 |
| 120 / 20 | 88 | 47,8 % | 73,9 % | 0,557 |

C'est l'inverse : plus les passages sont petits, plus la recherche se dégrade.

**Pourquoi.** En regardant les questions qui échouent : pour « Combien de jours de congés payés
a un salarié de Novalia ? », les premiers résultats sont des passages du bon document qui
contiennent le mot « Novalia » (l'accueil, le télétravail), mais pas celui sur les congés. Le
passage qui porte la réponse, « Chaque salarié bénéficie de 27 jours ouvrés… », ne dit pas de
quelle entreprise il s'agit. Sorti de son document, un petit passage perd son contexte. Les
grands passages s'en sortaient mieux uniquement parce qu'ils avaient plus de chances de contenir
le nom.

## 2. Ajouter le titre du document à chaque passage : adopté

Avant de calculer l'embedding d'un passage, on lui ajoute le titre de son document
(`Document : guide salarie novalia`). Le texte stocké et affiché ne change pas.

| Taille | Sans titre (MRR) | Avec titre (MRR) | Hit rate@5 avec titre |
|---|---|---|---|
| 450 / 75 | 0,848 | 0,906 | 100 % |
| 300 / 50 | 0,630 | 0,899 | 100 % |
| 200 / 40 | 0,523 | 0,899 | 100 % |

Le gain est net, il ne coûte rien à la recherche, et il rend le système robuste à la taille des
passages. La seule question dont le bon passage n'était pas retrouvé (`fact-04`) l'est désormais.
**Activé par défaut** (`EMBED_DOCUMENT_TITLE=true`).

Limite : le titre vient du nom du fichier. Un fichier nommé `scan_0042.pdf` n'apporte rien.

## 3. Taille des passages, une fois le titre ajouté : inchangée

Avec le titre, 450, 300 et 200 tokens donnent des résultats équivalents (écarts inférieurs à
une question). Rien ne justifie de changer : **450 / 75 est conservé**. Des passages plus petits
réduiraient le texte envoyé à Claude, donc le coût ; cela se décidera avec l'évaluation de la
génération.

## 4. Reranking par cross-encoder : écarté par défaut

Un second modèle (`cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`) reclasse les 20 premiers
résultats.

| Configuration | Hit rate@1 | MRR | Recherche médiane |
|---|---|---|---|
| 450, titre | 82,6 % | 0,906 | 0,25 s |
| 450, titre + reranking | 87,0 % | 0,935 | 24 s |
| 200, titre + reranking | 91,3 % | 0,936 | 13 s |

Le reranking gagne une à deux questions en première position, ce qui est à la limite du bruit
de mesure, et le hit rate@5 était déjà à 100 %. En échange, la recherche passe de 0,25 s à
plus de 10 s sur un processeur de portable (mesuré avec 4 questions en parallèle ; une question
seule serait plus rapide, mais resterait de l'ordre de plusieurs secondes). Comme Claude reçoit
les 5 passages et pas seulement le premier, l'ordre exact compte peu.
**Désactivé par défaut**, disponible avec `RERANK_ENABLED=true` pour une machine avec GPU ou un
corpus plus difficile.

## Ce qui n'a pas pu être mesuré

- **Recherche hybride** (vecteurs + plein texte, fusion RRF) : elle demande PostgreSQL. Le code
  et ses tests existent ; `python -m eval.run --mode hybrid` la mesurera. Elle devrait surtout
  aider les questions à mot-clé exact (`key-*`).
- **Génération** : fidélité, exactitude, citations et refus demandent une clé API Claude.
- **Index HNSW** : les mesures utilisent un cosinus exact. Sur un corpus de cette taille,
  l'index approché de pgvector devrait donner les mêmes résultats, mais ce n'est pas vérifié.

## Reproduire

```bash
uv run --project backend python -m eval.run --label essai --retrieval-only \
    --chunk-size 200 --chunk-overlap 40 --title-context --rerank
uv run --project backend python -m eval.compare eval/reports/A.json eval/reports/B.json
```
