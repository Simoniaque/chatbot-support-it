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
         → vérification extrait par extrait (le modèle juge : répond-il ?)
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

## Tests

```powershell
python -m pytest
```

Une quarantaine de tests, en moins d'une seconde, sans Ollama ni GLPI : la
base vectorielle, le modèle et l'API GLPI sont remplacés par des doublures
(`tests/conftest.py`). Ils couvrent la logique de décision (seuils,
vérification des extraits, refus), le dialogue avec GLPI, les sessions et les
routes de l'API, et le journal.

La **qualité des réponses**, elle, ne se teste pas automatiquement : c'est
l'objet de `tests/questions_test.md`, à rejouer à chaque changement de corpus
ou de modèle.

---

## Structure

```
├── src/
│   ├── config.py      # Tous les réglages, lus depuis .env
│   ├── ingestion.py   # Documents → morceaux → base vectorielle
│   ├── rag.py         # Question → recherche → seuil → réponse
│   ├── glpi.py        # Création de ticket GLPI (API REST)
│   ├── journal.py     # Journalisation des échanges (JSON Lines)
│   └── api.py         # API FastAPI + service de la page web
├── static/index.html  # Interface utilisateur
├── data/corpus/       # Documents sources (hors dépôt Git)
├── chroma_db/         # Base vectorielle générée (hors dépôt Git)
├── logs/              # Journal des échanges (hors dépôt Git)
├── outils/glpi-test/  # Instance GLPI jetable (Docker) pour tester l'escalade
├── tests/             # Tests automatisés (pytest) et jeu de questions d'évaluation
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
| `SEUIL_PERTINENCE` | `0.65` | Distance maximale du **meilleur** extrait pour répondre (voir ci-dessous) |
| `SEUIL_CONTEXTE` | `0.65` | Distance maximale des extraits **suivants** inclus dans le contexte (≥ `SEUIL_PERTINENCE`) |
| `GLPI_URL` | *(vide)* | Adresse de GLPI, sans `/apirest.php` (voir « Connexion et escalade vers GLPI ») |
| `GLPI_APP_TOKEN` | *(vide)* | Jeton du client API GLPI |
| `DUREE_SESSION_HEURES` | `8` | Durée d'une connexion au chatbot avant de devoir se reconnecter |
| `JOURNALISATION` | `1` | Enregistre chaque échange dans `logs/echanges.jsonl` (`0` pour désactiver) |

### Le seuil de pertinence

Le réglage le plus important du projet. C'est une **distance** : plus la valeur
est basse, plus l'extrait doit être proche de la question pour être retenu. Si
le meilleur extrait est au-dessus du seuil, le chatbot refuse de répondre.
`SEUIL_CONTEXTE` règle à part quels extraits suivants accompagnent le meilleur :
on peut ainsi refuser plus strictement sans priver de contexte les questions
acceptées.

- Seuil trop bas → le bot bloque trop souvent, il devient inutilisable.
- Seuil trop haut → il répond à partir d'extraits hors sujet, donc il invente.

**La valeur dépend du modèle d'embeddings.** Changer de modèle impose de
remesurer le seuil : les distances ne sont pas comparables d'un modèle à
l'autre.

Justification et mesures : `docs/seuil-pertinence.md`.

---

## Connexion et escalade vers GLPI

Quand GLPI est configuré, le chatbot demande une **connexion avec les
identifiants GLPI** de la personne. Il n'a pas de base d'utilisateurs à lui :
il ouvre une session GLPI au nom de l'utilisateur (API REST, authentification
par login/mot de passe) et la garde côté serveur, repérée par un cookie. Le
mot de passe ne sert qu'à cet appel et n'est ni conservé ni journalisé.

Ce que la connexion apporte :

- **Identité sur les tickets** : quand le chatbot refuse de répondre, il
  propose de transmettre la question au support. Le ticket est créé avec la
  session de l'utilisateur, qui en est le **demandeur** dans GLPI — pas un
  compte technique.
- **Journal nominatif** : chaque question est tracée avec le login.

Le ticket n'est créé **qu'après confirmation explicite** (bouton « Créer le
ticket ») ; le chatbot ne crée jamais de ticket de lui-même. Il contient la
question posée, un rappel que le chatbot n'a pas trouvé de réponse, et les
précisions facultatives saisies par l'utilisateur. Type « Demande ».

Sans GLPI configuré, pas de connexion : le chatbot est utilisable
anonymement, sans création de ticket.

### Activer

Côté GLPI (*Configuration > Générale > API*) :

1. Activer l'API REST et **la connexion avec identifiants**.
2. Créer un client API sans restriction d'adresse IP, et régénérer son
   jeton d'application → `GLPI_APP_TOKEN`.

Côté projet, dans `.env` :

```
GLPI_URL=http://glpi.exemple.local/glpi
GLPI_APP_TOKEN=...
```

Puis **relancer** le serveur (`.env` n'est lu qu'au démarrage).
`http://localhost:8000/sante` affiche `"connexion_requise": true`.

Pour tester sur une vraie instance sans en installer une à la main :
`docs/glpi-test.md` (GLPI jetable sous Docker, `outils/glpi-test/`).

### Fonctionnement

```
POST /connexion   {login, mot_de_passe}
   → GET {GLPI_URL}/apirest.php/initSession     (App-Token + Basic login:mdp)
   → GET {GLPI_URL}/apirest.php/getFullSession  (identité)
   ← cookie de session + {id, login, nom}

POST /ask         {question}              (cookie requis)
POST /ticket      {question, precisions?} (cookie requis)
   → POST {GLPI_URL}/apirest.php/Ticket  (Session-Token de l'utilisateur,
                                           _users_id_requester = lui)
   ← {id, url}

POST /deconnexion → GET killSession, cookie supprimé
GET  /moi         → {connexion_requise, utilisateur}
```

Code : `src/glpi.py` (dialogue avec GLPI) et `src/api.py` (sessions).
Erreurs : identifiants faux → **401** ; session expirée → **401** (l'interface
réaffiche la connexion) ; GLPI injoignable ou refus → **502** avec le message.

**En production** : GLPI doit être en HTTPS, sinon le mot de passe transite
en clair entre le chatbot et GLPI.

---

## Journalisation des échanges

Chaque question posée via l'API est ajoutée à `logs/echanges.jsonl` : une
ligne JSON par échange avec l'utilisateur connecté, la question, le meilleur
score, le seuil en vigueur, les extraits vérifiés et écartés, les sources
retenues (document, page, score), la réponse et la durée. Connexions,
créations de tickets, erreurs GLPI et **avis des utilisateurs** (boutons
« utile / pas utile » sous chaque réponse) y sont aussi tracés.

```powershell
python -m src.journal      # statistiques : taux de refus, scores moyens, dernières questions
```

C'est la matière première pour calibrer le seuil (`docs/seuil-pertinence.md`)
et repérer les questions fréquentes auxquelles le corpus ne répond pas.

Le fichier contient les questions réelles des utilisateurs : il est exclu du
dépôt Git. `JOURNALISATION=0` dans `.env` pour désactiver.

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
| `uvicorn --reload` affiche « Reloading... » mais l'ancien code reste actif | Sous Windows, le rechargement automatique reste parfois bloqué | Arrêter uvicorn (Ctrl+C) et le relancer |
| `Connexion à GLPI refusée : ERROR_...` à la connexion | Jeton d'application invalide, API REST ou connexion par identifiants désactivée | Vérifier `GLPI_*` dans `.env` et l'onglet API de GLPI |
| « Votre session a expiré » juste après avoir posé une question | Serveur redémarré (les sessions sont en mémoire) | Se reconnecter |

Les versions de `requirements.txt` ont été figées **après** validation, avec
`pip freeze`, à partir d'une combinaison réellement testée sur le poste de
développement.

---

## État d'avancement

**Fonctionnel**

- Pipeline d'ingestion complet, avec traitement par lots et reprise sur erreur
- Recherche vectorielle et filtrage par seuil de pertinence (seuil calibré)
- Génération des réponses avec citation des sources
- API et interface web : fil de conversation, sources repliables, refus expliqués, avis utile / pas utile
- Connexion avec les identifiants GLPI ; escalade vers GLPI : ticket créé au nom de l'utilisateur sur refus, après confirmation (validé sur GLPI 11, `docs/glpi-test.md`)
- Journalisation des échanges (question, extraits retenus, scores, réponse)

**En cours**

- Enrichissement du corpus documentaire
- Réduction du taux d'invention : 7/16 → 1/9 réponses après vérification des extraits (voir `tests/questions_test.md`) ; le cas restant (« cependant… ») tient au rédacteur Mistral 7B
- Rédaction de `docs/choix-techniques.md`

**À planifier**

- Intégration GLPI côté lecture : base de connaissances et historique des tickets dans le corpus
- Stratégie de mise à jour et d'archivage du corpus (montée en charge de ChromaDB)
