# Jeu de questions d'évaluation

Sert à mesurer la qualité des réponses et à calibrer le seuil de pertinence.
À compléter au fur et à mesure que le corpus s'enrichit.

## A. Questions couvertes par le corpus
Le bot doit répondre, avec la bonne source.

| # | Question | Document attendu | Meilleur score | Résultat |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |

## B. Questions hors périmètre
Le bot doit refuser de répondre.

| # | Question | Meilleur score | Refus obtenu ? |
|---|---|---|---|
| 1 | Quelle est la capitale de l'Australie ? | | |
| 2 | | | |

## C. Questions limites
Sujet proche du corpus, mais réponse absente. Ce sont les cas les plus
révélateurs : c'est là que le bot invente s'il le fait.

| # | Question | Meilleur score | Comportement |
|---|---|---|---|
| 1 | | | |

## Indicateurs à calculer

- **Taux de réponse** : réponses fournies / questions posées
- **Taux de refus justifié** : refus corrects / questions du groupe B
- **Taux d'hallucination** : réponses inventées / réponses fournies (le seul à devoir rester à zéro)
