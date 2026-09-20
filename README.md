# Chatbot de support informatique

Assistant de support IT interne qui répond aux questions à partir d'un corpus
documentaire, **en citant ses sources** et en **refusant de répondre** plutôt
que d'inventer.

Projet de Fin d'Études 2026 — Simon Auriac, ESI Limayrac.

---

## Principe : le RAG

RAG signifie *Retrieval Augmented Generation* : génération augmentée par la
recherche. Le modèle de langage ne répond pas de mémoire ; on lui fournit
d'abord des extraits de la documentation interne, et il rédige uniquement à
partir de ceux-ci.

```
question → recherche des extraits proches (ChromaDB)
         → filtrage par seuil de pertinence
         → rédaction par Mistral (local, via Ollama)
         → réponse + sources citées
```

**Tout tourne en local.** Le corpus contient des procédures internes : aucune
donnée ne sort du poste.

---

## Choix techniques

| Élément | Choix | Pourquoi |
|---|---|---|
| Langage | Python | Écosystème IA/RAG le plus fourni |
| Orchestration | LangChain | Lecture, découpage, recherche et génération déjà assemblés |
| LLM | Mistral via Ollama | Local, gratuit, pas de fuite de données |
| Embeddings | nomic-embed-text | Modèle dédié à la mise en vecteurs, plus rapide et plus précis qu'un LLM généraliste pour cette tâche |
| Base vectorielle | ChromaDB | Locale, sans serveur à administrer |
| Backend | FastAPI | API documentée automatiquement, réutilisable (intégration GLPI prévue) |
| Interface | HTML + JavaScript | Aucune dépendance supplémentaire, suffisant pour l'usage visé |

---

## Installation

Prérequis : Python 3.10+, Git, et [Ollama](https://ollama.com).

```bash
# 1. Récupérer les modèles (une seule fois, environ 4 Go)
ollama pull mistral
ollama pull nomic-embed-text

# 2. Créer l'environnement Python isolé
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Créer la configuration locale
copy .env.example .env         # Windows
# cp .env.example .env         # macOS / Linux
```

L'environnement isolé (`venv`) évite que les bibliothèques de ce projet
entrent en conflit avec celles d'un autre projet sur la même machine.

---

## Utilisation

```bash
# 1. Déposer les documents dans data/corpus/  (.pdf, .txt, .md)

# 2. Construire la base vectorielle (à relancer quand le corpus change)
python -m src.ingestion

# 3. Lancer le serveur
uvicorn src.api:app --reload
```

Puis ouvrir http://localhost:8000

L'API est documentée automatiquement sur http://localhost:8000/docs

---

## Structure

```
├── src/
│   ├── config.py      # Tous les réglages au même endroit
│   ├── ingestion.py   # Documents → morceaux → base vectorielle
│   ├── rag.py         # Question → recherche → seuil → réponse
│   └── api.py         # API FastAPI + service de la page web
├── static/index.html  # Interface utilisateur
├── data/corpus/       # Documents sources (hors dépôt Git)
├── tests/             # Jeu de questions d'évaluation
└── docs/              # Justification des choix, documentation
```

---

## Le seuil de pertinence

Le réglage le plus important du projet, dans `.env` : `SEUIL_PERTINENCE`.

C'est une **distance** : plus la valeur est basse, plus l'extrait doit être
proche de la question pour être retenu. Si aucun extrait ne passe sous le
seuil, le chatbot refuse de répondre.

- Seuil trop bas → le bot bloque trop souvent, il devient inutilisable.
- Seuil trop haut → il répond à partir d'extraits hors sujet, donc il invente.

Le choix de la valeur et les mesures qui le justifient sont dans
`docs/seuil-pertinence.md`.
