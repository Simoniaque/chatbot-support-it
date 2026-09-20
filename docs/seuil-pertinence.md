# Justification du seuil de pertinence

> Document demandé explicitement lors de la réunion de suivi du 22/05/2026.
> À compléter avec des mesures réelles.

## Ce qu'est le seuil

Lors d'une recherche, ChromaDB renvoie pour chaque extrait une **distance**
entre la question et l'extrait. Plus la distance est faible, plus l'extrait
est proche du sens de la question.

Le chatbot ne retient que les extraits dont la distance est **inférieure ou
égale au seuil**. Si aucun ne passe, il refuse de répondre.

## Pourquoi un seuil est nécessaire

Sans seuil, la recherche renvoie toujours les extraits « les moins mauvais »,
même quand la question n'a aucun rapport avec le corpus. Le modèle rédige
alors une réponse à partir de documents hors sujet : c'est le mécanisme
principal de l'hallucination dans un système RAG.

## Arbitrage

| Seuil | Effet | Risque |
|---|---|---|
| Trop bas | Le bot refuse souvent | Outil perçu comme inutile, abandon par les utilisateurs |
| Trop haut | Le bot répond presque toujours | Réponses inventées, perte de confiance |

## Valeur retenue

Valeur actuelle : **1.0**

À justifier par des mesures :

1. Constituer un jeu de questions de test (`tests/questions_test.md`) :
   des questions dont la réponse est dans le corpus, et des questions
   volontairement hors sujet.
2. Pour chaque question, relever la distance du meilleur extrait
   (champ `meilleur_score` renvoyé par l'API).
3. Repérer la zone qui sépare les deux groupes, et placer le seuil dedans.

| Question | Type | Meilleur score | Réponse attendue | Comportement observé |
|---|---|---|---|---|
| | | | | |

## Limite connue

La distance dépend du modèle d'embeddings utilisé. Si `nomic-embed-text` est
remplacé, **le seuil doit être remesuré** : les valeurs ne sont pas
comparables d'un modèle à l'autre.
