# Rapport d'évaluation : baseline-recherche

- Date : 2026-11-15 19:31
- Version du code : `27e9f5d (+ modifications locales)`
- Moteur de recherche : memory (cosinus exact, sans pgvector) (mode `vector`, k = 5)
- Découpage : 450 tokens, chevauchement 75 ; 26 passages indexés
- Embeddings : `intfloat/multilingual-e5-base`
- Modèle de réponse : `non utilisé` ; juge : `non utilisé`
- Questions : 28 (23 avec réponse, 5 sans réponse dans les documents)

## Recherche (retrieval)

Sur les 23 questions ayant une réponse dans les documents.

| Mesure | Valeur |
|---|---|
| Hit rate@1 | 73.9 % |
| Hit rate@3 | 95.7 % |
| Hit rate@5 | 95.7 % |
| MRR | 0.848 |
| Rappel des preuves | 93.5 % |

## Génération

Non évaluée dans ce rapport (recherche seule).

## Par type de question

| Type | Questions | Hit rate@5 | MRR | Réussies |
|---|---|---|---|---|
| factual | 6 | 83.3 % | 0.833 | n/a |
| paraphrase | 9 | 100.0 % | 0.833 | n/a |
| keyword | 5 | 100.0 % | 0.800 | n/a |
| multi | 3 | 100.0 % | 1.000 | n/a |
| unanswerable | 5 | n/a | n/a | n/a |

## Détail par question

| Id | Rang du bon passage | Citations | Fidélité | Pertinence | Exactitude | Résultat |
|---|---|---|---|---|---|---|
| fact-01 | 1 | — | — | — | — | — |
| fact-02 | 1 | — | — | — | — | — |
| fact-03 | 1 | — | — | — | — | — |
| fact-04 | absent | — | — | — | — | — |
| fact-05 | 1 | — | — | — | — | — |
| fact-06 | 1 | — | — | — | — | — |
| para-01 | 1 | — | — | — | — | — |
| para-02 | 1 | — | — | — | — | — |
| para-03 | 1 | — | — | — | — | — |
| para-04 | 2 | — | — | — | — | — |
| para-05 | 1 | — | — | — | — | — |
| para-06 | 2 | — | — | — | — | — |
| para-07 | 1 | — | — | — | — | — |
| para-08 | 1 | — | — | — | — | — |
| para-09 | 2 | — | — | — | — | — |
| key-01 | 1 | — | — | — | — | — |
| key-02 | 1 | — | — | — | — | — |
| key-03 | 2 | — | — | — | — | — |
| key-04 | 2 | — | — | — | — | — |
| key-05 | 1 | — | — | — | — | — |
| multi-01 | 1 | — | — | — | — | — |
| multi-02 | 1 | — | — | — | — | — |
| multi-03 | 1 | — | — | — | — | — |
| none-01 | — | — | — | — | — | — |
| none-02 | — | — | — | — | — | — |
| none-03 | — | — | — | — | — | — |
| none-04 | — | — | — | — | — | — |
| none-05 | — | — | — | — | — | — |

## Bon passage non retrouvé

- **fact-04** : « Combien de documents peut-on emprunter à la médiathèque de Valmont, et pour combien de temps ? » (premier résultat : reglement-mediatheque-valmont.pdf, page 1)

## Comment lire ces chiffres

Avec 28 questions, une seule question pèse environ 3.6 points de pourcentage. Un écart plus petit que cela entre deux rapports ne prouve rien : relancez l'évaluation ou regardez le détail des questions qui ont changé.
