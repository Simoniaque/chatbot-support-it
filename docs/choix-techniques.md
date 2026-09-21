# Justification des choix techniques

> Document demandé lors de la réunion de suivi du 22/05/2026.
> Première partie : choix de conception. Seconde partie : décisions prises
> pendant la mise au point, chiffres à l'appui.

## Architecture RAG plutôt qu'un modèle seul

Un modèle de langage seul répond de mémoire : il ne connaît pas les procédures
internes de l'organisation et ne peut pas citer de source. Le RAG apporte les
deux éléments exigés par le cahier des charges : des réponses **fondées sur le
corpus** et **traçables**.

L'alternative — réentraîner un modèle sur les documents internes — a été
écartée : coût matériel élevé, réentraînement complet à chaque mise à jour de
la documentation, et aucune citation de source possible.

## Exécution 100 % locale (Ollama)

Le corpus contient des procédures internes et de l'information sur
l'infrastructure. Une API externe impliquerait d'envoyer ces contenus à un
tiers. L'exécution locale supprime la question, sans coût par requête.

Contrepartie assumée : des réponses de qualité inférieure à celles d'un modèle
de premier plan, et une vitesse dépendante du poste.

## ChromaDB

Base vectorielle locale, qui fonctionne comme un simple dossier de fichiers :
aucun serveur à installer ni à administrer. Suffisant pour le volume visé.

**Point de vigilance soulevé en réunion** : la montée en charge à long terme.
Une stratégie de mise à jour et d'archivage du corpus reste à définir.

## LangChain

Fournit les briques déjà assemblées (lecture des PDF, découpage,
interrogation de la base vectorielle, appel du modèle). Écrire ces briques à
la main n'apporterait rien au projet.

## FastAPI

Séparer l'API de l'interface permet de réutiliser le chatbot depuis un autre
outil — l'intégration GLPI validée en réunion en est le premier cas. FastAPI
génère de plus une documentation d'API automatique (`/docs`), qui sert de
documentation développeur.

## Découpage : 1000 caractères, 150 de chevauchement

Des morceaux trop grands diluent l'information utile dans du bruit ; trop
petits, ils perdent leur contexte. Le chevauchement évite qu'une réponse
coupée en deux entre deux morceaux devienne introuvable.

Valeurs conservées après les campagnes de mesure : les problèmes observés
venaient de la pertinence des extraits, pas de leur taille.

---

# Décisions prises pendant la mise au point (20–21/09/2026)

Les sections précédentes datent de la conception. Celles-ci ont été prises
en mesurant, avec le jeu de questions de `tests/questions_test.md`
(25 questions, 7 campagnes). Chaque décision est accompagnée du chiffre qui
l'a motivée.

## Modèle d'embeddings dédié, et seuil remesuré pour lui

`nomic-embed-text` transforme les textes en vecteurs ; `mistral` rédige.
Deux modèles, parce que ce sont deux métiers : un modèle d'embeddings est
plus rapide et plus précis pour comparer des sens qu'un modèle de langage
généraliste.

Conséquence pratique : la distance renvoyée par ChromaDB dépend du modèle
d'embeddings. Le seuil de pertinence livré à 1.0 ne refusait **aucune**
question hors sujet (« Bonjour » recevait une réponse sur les enquêtes de
satisfaction). Remesuré sur 20 questions : questions couvertes entre 0.31
et 0.63, hors sujet entre 0.70 et 0.97. Seuil placé à **0.65**. Détail dans
`docs/seuil-pertinence.md`.

## Deux seuils plutôt qu'un

Un seul seuil jouait deux rôles : décider de répondre, et choisir quels
extraits envoyer au modèle. En l'abaissant à 0.55 pour refuser davantage,
une question acceptée de justesse n'avait plus qu'un extrait de contexte et
sa réponse se dégradait.

`SEUIL_PERTINENCE` ne s'applique donc qu'au meilleur extrait (répondre ou
refuser) ; `SEUIL_CONTEXTE` décide quels extraits suivants l'accompagnent.
Les deux valent 0.65 aujourd'hui ; la séparation prépare le jour où le
corpus justifiera un refus plus strict.

## Le seuil ne suffit pas : vérification extrait par extrait

C'est la décision la plus importante, et la moins prévue.

La distance mesure une proximité de **vocabulaire**, pas la capacité d'un
extrait à répondre. « Comment ajouter un utilisateur dans GLPI ? » obtient
un excellent score (0.416) avec quatre extraits sans aucun rapport
(inventaire, formulaires, raccourcis clavier). Le modèle, à qui l'on donne
ces extraits, rédige alors une procédure de mémoire — plausible, et inventée.

En relisant les extraits réellement retenus pour chaque réponse, la
première campagne comptait **7 inventions sur 16 réponses** (44 %), alors
qu'elles avaient d'abord été jugées correctes sur leur seule plausibilité.

Solution retenue : avant de rédiger, chaque extrait est soumis au modèle
avec une question fermée (« cet extrait contient-il de quoi répondre, même
partiellement ? OUI ou NON »). Les NON sont écartés ; s'il ne reste rien, le
chatbot refuse. Résultat : **1 invention sur 9 réponses**, au prix d'un faux
refus. Coût : un appel court par extrait, quelques secondes par question.

Ce que ça change dans l'architecture :

```
question → recherche (ChromaDB) → seuil → vérification par extrait → rédaction
```

Les pistes écartées, et pourquoi (chiffres dans `tests/questions_test.md`) :

| Piste | Effet mesuré | Verdict |
|---|---|---|
| Consigne plus stricte dans le prompt | Réduit les inventions franches, mais Mistral 7B enchaîne quand même par « cependant… » face à un extrait vaguement lié | Conservée (v2), insuffisante seule |
| Seuil abaissé à 0.55 | Zéro invention, mais 4 questions couvertes sur 10 refusées | Trop coûteux sur ce corpus |
| Vérifier seulement en zone grise (0.55–0.65) | Ne voit pas les extraits sans rapport à score bas | Remplacé par la vérification de tous les extraits |
| Modèle juge plus gros (`qwen2.5:7b`) | 14/16 verdicts corrects contre 13/16 pour Mistral ; de bout en bout, écart dans le bruit ; coûte une bascule de modèle sur le GPU | Sans gain net ; réglage `MODELE_JUGE` laissé disponible |

## Refus explicite et détectable

Le modèle renvoie le mot `HORS_CONTEXTE` quand les extraits ne parlent pas
du sujet ; le code le transforme en refus avec un motif (`seuil`,
`verification`, `modele`). Avant, le modèle écrivait « ce n'est pas dans le
contexte » en texte libre, avec `refus = false` : l'interface ne proposait
alors pas de ticket. Rendre le refus détectable est ce qui permet d'offrir
une issue à chaque question sans réponse — y compris aux faux refus, qui
deviennent une gêne plutôt qu'une impasse.

## Méthode d'évaluation : l'ancrage, pas la plausibilité

Une réponse de Mistral sur GLPI sonne juste même quand elle est inventée,
parce que le modèle connaît GLPI de mémoire. Le seul contrôle valable est de
comparer chaque affirmation de la réponse au **texte des extraits retenus**.
Une étape, un chemin de menu, une commande absents des extraits = invention,
même si c'est vrai dans GLPI. Cette règle est écrite dans
`tests/questions_test.md` ; elle a corrigé l'étalon des cinq premières
campagnes.

## Ce qui reste vrai malgré tout : Mistral 7B, un compromis

Aucun réglage n'a atteint zéro invention sans refuser des questions
couvertes. L'invention restante vient du **rédacteur** (« pas de mention…
cependant… ») malgré une consigne explicite. Le levier suivant serait un
rédacteur qui obéit mieux ; `qwen2.5:7b` est installé pour le mesurer. Le
choix de Mistral reste défendable : gratuit, local, 4 Go, et le pipeline est
conçu pour que ses limites aient une issue (refus + ticket) plutôt que d'être
masquées.

## Connexion avec les identifiants GLPI

Le chatbot n'a pas de base d'utilisateurs : l'utilisateur se connecte avec
son compte GLPI, le chatbot ouvre une session GLPI en son nom (API REST,
login / mot de passe) et la garde côté serveur, repérée par un cookie
`HttpOnly`. Le mot de passe ne sert qu'à cet appel.

Pourquoi ce choix plutôt que des comptes propres au chatbot : pas de mots de
passe à stocker, pas d'administration en double, et surtout le ticket créé
porte l'utilisateur comme **demandeur** dans GLPI, avec son vrai nom. La
protection est du côté de GLPI : avec le profil Self-Service, l'API refuse
qu'un utilisateur crée un ticket au nom d'un autre, quoi que fasse
l'interface.

Découverte en chemin : via l'API, GLPI 11 n'ajoute pas automatiquement le
créateur comme acteur « demandeur » (l'interface web le fait) ; le chatbot
passe `_users_id_requester` explicitement. Validé sur une instance GLPI 11
(`docs/glpi-test.md`).

Contrainte : en production, GLPI doit être en HTTPS.

## Ticket seulement après confirmation

Le chatbot ne crée jamais de ticket de lui-même. Sur un refus, il propose ;
l'utilisateur ajoute des précisions s'il veut, et clique. Un ticket ouvert
sans qu'on l'ait demandé serait perçu comme du bruit par le support et par
l'utilisateur.

## Journal en JSON Lines

Une ligne JSON par événement (question, refus et motif, extraits vérifiés et
écartés, sources, réponse, durée ; connexions ; tickets ; avis utile / pas
utile). Choisi plutôt qu'une base de données : lisible tel quel, s'analyse en
quelques lignes de Python (`python -m src.journal`), et c'est la matière
première pour recalibrer les seuils à chaque changement de corpus. Le fichier
contient les questions réelles des utilisateurs : hors dépôt Git.

## Interface sans dépendance

HTML et JavaScript seuls, un fichier. Un cadre (React, Vue) n'apporterait
rien pour un fil de conversation, un formulaire et quelques états, et
ajouterait une chaîne de compilation à maintenir. L'interface montre ce que
le pipeline a fait (« 4 extraits analysés, 2 écartés »), explique les refus
selon leur motif, et recueille un avis par réponse.

## Tests automatisés hors ligne

Une quarantaine de tests (`python -m pytest`, moins d'une seconde) couvrent
la logique de décision, le dialogue GLPI, les sessions et le journal, avec
des doublures pour Ollama, ChromaDB et GLPI. Ils protègent contre les
régressions ; ils ne mesurent pas la qualité des réponses, qui relève du jeu
de questions et d'une lecture humaine des extraits.
