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

### Zone grise : 0.55 – 0.65

La campagne complète du 20/09/2026 (`tests/questions_test.md`, 25 questions
passées dans le pipeline entier) a révélé **deux réponses inventées**, toutes
deux avec un score dans cette zone :

| Question | Score | Ce qui s'est passé |
|---|---|---|
| Comment réinitialiser mon mot de passe Windows ? | 0.591 | L'extrait retenu parle du mot de passe **GLPI**. Le modèle constate que le contexte ne répond pas… puis donne une procédure Windows de mémoire |
| Comment migrer GLPI vers un autre serveur ? | 0.573 | L'extrait retenu (p. 29) parle de raccourcis clavier. Le modèle invente des commandes `glpi-export` / `glpi-import` absentes du corpus |

Dans les deux cas le seuil a laissé passer un extrait sans rapport réel avec
la question, et la consigne « n'invente rien » n'a pas suffi. À l'inverse,
les questions couvertes situées dans la même zone (0.554 à 0.627) ont reçu
les réponses les plus faibles de la campagne.

Conclusion provisoire : 0.65 est correct pour séparer le hors sujet franc,
mais la zone 0.55–0.65 est peu fiable.

Second filtre ajouté le même jour (campagne 2 de `tests/questions_test.md`) :
le modèle doit répondre `HORS_CONTEXTE` quand les extraits ne parlent pas du
sujet, ce que le code transforme en refus (`motif_refus = "modele"`). Cela a
réglé le cas « mot de passe Windows » (0.591) mais pas « migration » (0.573) :
quand l'extrait retenu est vaguement lié, le modèle rédige quand même. Ce
cas-là relève du seuil ou d'une vérification extrait/question avant
génération.

Seuil à 0.55 essayé le même jour (campagne 3) : zéro invention, mais 4
questions couvertes sur 10 refusées, et un effet de bord : le seuil filtre
*tous* les extraits, pas seulement le meilleur, donc une question acceptée
de justesse n'a plus qu'un extrait de contexte et sa réponse se dégrade.
**0.65 maintenu.** Piste à creuser : deux seuils distincts, l'un pour
refuser (sur le meilleur extrait), l'autre pour inclure les extraits
suivants dans le contexte.

### Reproduire la mesure

Relever le champ `meilleur_score` renvoyé par `POST /ask`, ou appeler
directement `similarity_search_with_score` sans passer par le LLM (plus
rapide). À refaire à chaque changement de corpus ou de modèle d'embeddings.

## Limite connue

La distance dépend du modèle d'embeddings utilisé. Si `nomic-embed-text` est
remplacé, **le seuil doit être remesuré** : les valeurs ne sont pas
comparables d'un modèle à l'autre.
