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
| Langage | Python **3.12** | Écosystème IA/RAG le plus fourni. 3.13 est trop récent : plusieurs dépendances n'ont pas de version précompilée (voir « Problèmes connus ») |
| Orchestration | LangChain | Lecture, découpage, recherche et génération déjà assemblés |
| LLM | Mistral via Ollama | Local, gratuit, pas de fuite de données |
| Embeddings | nomic-embed-text | Modèle dédié à la mise en vecteurs, plus rapide et plus précis qu'un LLM généraliste pour cette tâche |
| Base vectorielle | ChromaDB | Locale, sans serveur à administrer |
| Backend | FastAPI | API documentée automatiquement, réutilisable (intégration GLPI prévue) |
| Interface | HTML + JavaScript | Aucune dépendance supplémentaire, suffisant pour l'usage visé |

---

## Installation

### Prérequis

- **Python 3.12** — `winget install Python.Python.3.12`
  (Python 3.13 fait échouer la compilation de NumPy ; voir « Problèmes connus »)
- **Git**
- **Ollama** — https://ollama.com

### Modèles Ollama

À faire une seule fois, environ 4 Go :

```powershell
ollama pull mistral
ollama pull nomic-embed-text
ollama list          # doit afficher les deux modèles
```

### Environnement Python

```powershell
py -3.12 -m venv venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass   # PowerShell uniquement
venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
```

Sous macOS / Linux : `python3.12 -m venv venv`, `source venv/bin/activate`,
`cp .env.example .env`.

L'environnement isolé (`venv`) évite que les bibliothèques de ce projet
entrent en conflit avec celles d'un autre projet sur la même machine.

La ligne `Set-ExecutionPolicy` n'est nécessaire que sous PowerShell, qui bloque
par défaut l'exécution des scripts. Portée `Process` : la règle ne vaut que
pour ce terminal et disparaît à sa fermeture. Rien n'est modifié durablement
sur le poste.

### Vérification

```powershell
python -c "import langchain_chroma, langchain_ollama, chromadb; print('OK')"
```

---

## Utilisation

### 1. Construire la base vectorielle

Déposer les documents dans `data/corpus/` (`.pdf`, `.txt`, `.md`), puis :

```powershell
python -m src.ingestion
```

Le traitement affiche sa progression. Compter plusieurs minutes pour un corpus
de quelques centaines de pages.

À relancer à chaque modification du corpus. Pour repartir d'une base propre :

```powershell
Remove-Item -Recurse -Force chroma_db
```

### 2. Lancer le serveur

```powershell
uvicorn src.api:app --reload
```

- Interface : http://localhost:8000
- Documentation de l'API générée automatiquement : http://localhost:8000/docs
- État de la configuration : http://localhost:8000/sante

Ollama doit tourner en arrière-plan pendant toute l'utilisation.

---

## Structure

```
├── src/
│   ├── config.py      # Tous les réglages, lus depuis .env
│   ├── ingestion.py   # Documents → morceaux → base vectorielle
│   ├── rag.py         # Question → recherche → seuil → réponse
│   └── api.py         # API FastAPI + service de la page web
├── static/index.html  # Interface utilisateur
├── data/corpus/       # Documents sources (hors dépôt Git)
├── chroma_db/         # Base vectorielle générée (hors dépôt Git)
├── tests/             # Jeu de questions d'évaluation
└── docs/              # Justification des choix, documentation
```

---

## Réglages

Tout se règle dans `.env`, sans toucher au code.

| Variable | Défaut | Rôle |
|---|---|---|
| `MODELE_LLM` | `mistral` | Modèle qui rédige la réponse |
| `MODELE_EMBEDDINGS` | `nomic-embed-text` | Modèle qui vectorise les textes |
| `TAILLE_CHUNK` | `1000` | Taille des morceaux, en caractères |
| `CHEVAUCHEMENT_CHUNK` | `150` | Recouvrement entre deux morceaux consécutifs |
| `NOMBRE_EXTRAITS` | `4` | Extraits envoyés au modèle par question |
| `SEUIL_PERTINENCE` | `0.65` | Distance maximale acceptée (voir ci-dessous) |

### Le seuil de pertinence

Le réglage le plus important du projet. C'est une **distance** : plus la valeur
est basse, plus l'extrait doit être proche de la question pour être retenu. Si
aucun extrait ne passe sous le seuil, le chatbot refuse de répondre.

- Seuil trop bas → le bot bloque trop souvent, il devient inutilisable.
- Seuil trop haut → il répond à partir d'extraits hors sujet, donc il invente.

**La valeur dépend du modèle d'embeddings.** Changer de modèle impose de
remesurer le seuil : les distances ne sont pas comparables d'un modèle à
l'autre.

Justification et mesures : `docs/seuil-pertinence.md`.

---

## Problèmes connus et solutions

| Symptôme | Cause | Solution |
|---|---|---|
| `ollama n'est pas reconnu` | Terminal ouvert avant l'installation d'Ollama | Fermer et rouvrir le terminal (ou VS Code) |
| Compilation de NumPy qui échoue (`Unknown compiler`) | Python 3.13 : pas de version précompilée disponible | Recréer le `venv` avec `py -3.12` |
| `ResolutionImpossible` à l'installation | Versions figées incompatibles entre elles | Installer sans numéros de version, puis `pip freeze > requirements.txt` |
| `connection refused` sur un port aléatoire pendant l'ingestion | Tous les morceaux envoyés à Ollama en une seule requête ; son moteur sature | Déjà corrigé : envoi par lots (`TAILLE_LOT` dans `src/ingestion.py`). Si cela revient, descendre à 8 puis 4 |
| L'activation du `venv` est refusée | PowerShell bloque les scripts par défaut | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` |
| `Impossible de joindre Ollama` dans l'interface | Ollama n'est pas lancé | Le démarrer, puis reposer la question |
| L'interface ne change pas après une modification de `index.html` | Cache du navigateur | Recharger la page (F5) |

Les versions de `requirements.txt` ont été figées **après** validation, avec
`pip freeze`, à partir d'une combinaison réellement testée sur le poste de
développement.

---

## État d'avancement

**Fonctionnel**

- Pipeline d'ingestion complet, avec traitement par lots et reprise sur erreur
- Recherche vectorielle et filtrage par seuil de pertinence (seuil calibré)
- Génération des réponses avec citation des sources
- API et interface web

**En cours**

- Enrichissement du corpus documentaire
- Journalisation des échanges (question, extraits retenus, scores, réponse)
- Mesure des indicateurs de qualité sur le jeu de test
- Rédaction de `docs/choix-techniques.md`

**À planifier**

- Intégration GLPI : base de connaissances et historique des tickets
- Stratégie de mise à jour et d'archivage du corpus (montée en charge de ChromaDB)
