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

Valeur actuelle : **0.65**

### Métrique mesurée

La collection ChromaDB utilise la distance par défaut, `l2` (distance
euclidienne au carré). Les vecteurs de `nomic-embed-text` étant normalisés,
cette distance vaut `2 × (1 − similarité cosinus)` : elle varie de 0 (extrait
identique à la question) à 4 (opposé), et une valeur de 0.65 correspond à une
similarité cosinus d'environ 0.67.

### Mesures (20/09/2026, corpus : Help Center GLPI, 767 morceaux)

Distance du meilleur extrait pour chaque question, sans passer par le LLM.

| Question | Type | Meilleur score | Comportement attendu |
|---|---|---|---|
| Qu'est-ce qu'une entité dans GLPI ? | couverte | 0.313 | répond |
| Comment configurer les notifications par e-mail dans GLPI ? | couverte | 0.346 | répond |
| Comment créer un ticket dans GLPI ? | couverte | 0.384 | répond |
| Comment ajouter un utilisateur dans GLPI ? | couverte | 0.416 | répond |
| Comment configurer les SLA ? | couverte | 0.492 | répond |
| Comment mettre un ticket en attente ? | couverte | 0.503 | répond |
| Comment importer des données depuis un fichier CSV ? | couverte | 0.554 | répond |
| Comment fonctionne le plugin FusionInventory ? | couverte | 0.608 | répond |
| Comment fonctionne la base de connaissances ? | couverte | 0.613 | répond |
| Comment gérer l'inventaire du parc informatique ? | couverte | 0.627 | répond |
| Comment réinitialiser mon mot de passe Windows ? | limite | 0.591 | zone grise (voir ci-dessous) |
| Quelle est la recette de la tarte aux pommes ? | hors sujet | 0.699 | refuse |
| Merci beaucoup | hors sujet | 0.701 | refuse |
| Qui a gagné la coupe du monde de football 2018 ? | hors sujet | 0.726 | refuse |
| Quel temps fait-il demain à Toulouse ? | hors sujet | 0.766 | refuse |
| Raconte-moi une blague | hors sujet | 0.779 | refuse |
| Quelle est la capitale de l'Australie ? | hors sujet | 0.782 | refuse |
| Écris un poème sur la mer | hors sujet | 0.804 | refuse |
| Bonjour | hors sujet | 0.835 | refuse |
| Comment installer Photoshop ? | hors sujet | 0.965 | refuse |

### Lecture

- Questions couvertes : meilleur score entre **0.31 et 0.63**.
- Questions hors sujet : entre **0.70 et 0.97**.
- La zone de séparation se situe entre 0.63 et 0.70 : le seuil est placé à
  **0.65**, au plus près des questions couvertes pour laisser le moins de
  place possible aux hors sujet.

Avec l'ancienne valeur de 1.0, **aucune** de ces questions n'était refusée :
« Bonjour » recevait une réponse inventée sur les enquêtes de satisfaction, et
« coupe du monde 2018 » affichait quatre sources GLPI sans rapport.

### Zone grise

« Comment réinitialiser mon mot de passe Windows ? » passe le seuil (0.591)
car le manuel GLPI décrit la réinitialisation du mot de passe **GLPI** depuis
la page de connexion. Le LLM répond alors en parlant de GLPI, ce qui n'est pas
la question. Ce cas relève de la catégorie C du jeu de test (sujet proche,
réponse absente) : c'est la consigne du prompt (« n'invente rien ») qui sert
de second filtre, et c'est sur ces questions-là que le seuil devra être
affiné quand le corpus s'enrichira.

### Reproduire la mesure

Relever le champ `meilleur_score` renvoyé par `POST /ask`, ou appeler
directement `similarity_search_with_score` sans passer par le LLM (plus
rapide). À refaire à chaque changement de corpus ou de modèle d'embeddings.

## Limite connue

La distance dépend du modèle d'embeddings utilisé. Si `nomic-embed-text` est
remplacé, **le seuil doit être remesuré** : les valeurs ne sont pas
comparables d'un modèle à l'autre.
