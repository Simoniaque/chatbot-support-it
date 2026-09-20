# Justification des choix techniques

> Document demandé lors de la réunion de suivi du 22/05/2026.

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

Valeurs de départ à ajuster après mesure sur le jeu de test.
