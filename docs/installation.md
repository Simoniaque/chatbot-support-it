# Démarrage — de zéro au premier dépôt GitHub

À suivre une fois, dans l'ordre. Chaque étape explique ce qu'elle fait et
pourquoi.

---

## 1. Installer Ollama

Ollama fait tourner un modèle de langage sur ton PC, sans passer par Internet.
C'est ce qui permet de traiter des procédures internes sans les envoyer chez
un fournisseur externe.

Télécharge-le sur https://ollama.com, installe-le, puis dans un terminal :

```bash
ollama pull mistral
ollama pull nomic-embed-text
```

Ces deux commandes téléchargent les modèles (environ 4 Go au total). Vérifie
ensuite avec :

```bash
ollama list
```

Tu dois voir les deux modèles listés.

---

## 2. Installer le projet

Décompresse ce dossier à un endroit que tu retrouveras — par exemple
`C:\Projets\chatbot-support-it`. Évite le Bureau et le dossier
Téléchargements, et évite OneDrive, qui synchronise en permanence des milliers
de fichiers Python et ralentit tout.

Puis, dans un terminal ouvert dans ce dossier :

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Si ton invite de commande affiche `(venv)` au début de la ligne,
l'environnement isolé est bien actif.

---

## 3. Vérifier que la chaîne fonctionne

Avant de collecter tout le corpus, teste avec **2 ou 3 documents seulement**.
Le principe : valider la mécanique sur un petit volume, où une erreur se
repère en quelques secondes plutôt qu'après vingt minutes d'indexation.

```bash
# Dépose 2-3 PDF dans data/corpus/, puis :
python -m src.ingestion
uvicorn src.api:app --reload
```

Ouvre http://localhost:8000 et pose une question dont tu connais la réponse
dans ces documents. Si la réponse arrive avec ses sources, la chaîne complète
fonctionne.

---

## 4. Mettre le projet sur GitHub

```bash
git init
git add .
git status
```

`git status` liste ce qui va être envoyé. **Vérifie cette liste avant de
continuer** : tu ne dois y voir ni `venv/`, ni `chroma_db/`, ni `.env`, ni tes
documents de `data/corpus/`. S'ils sont absents, le fichier `.gitignore` fait
son travail.

```bash
git commit -m "Initialise le projet chatbot de support IT"
```

Ensuite, sur github.com : bouton **New repository**, nom
`chatbot-support-it`, visibilité **Private** (le projet parle de
l'infrastructure interne), et surtout **ne coche rien** dans « Initialize this
repository » — le dépôt doit rester vide pour accueillir le tien.

GitHub affiche alors les commandes à copier, du type :

```bash
git remote add origin https://github.com/TON-COMPTE/chatbot-support-it.git
git branch -M main
git push -u origin main
```

Ligne par ligne : la première indique où envoyer le code, la deuxième nomme la
branche principale `main`, la troisième envoie tout.

---

## 5. Prendre l'habitude du commit

Après chaque avancée qui fonctionne :

```bash
git add .
git commit -m "Ajoute la journalisation des échanges"
git push
```

Un commit = un changement compréhensible. C'est aussi ta protection : c'est
précisément ce qui t'aurait évité de perdre ton dossier.

---

## 6. Continuer avec Claude Code

Ouvre Claude Code dans ce dossier. Il lira `CLAUDE.md` automatiquement et
connaîtra le contexte du projet.

Première consigne suggérée :

> « Lis CLAUDE.md et README.md. Lance le projet, vérifie que l'ingestion et
> l'API fonctionnent avec Ollama, et corrige les erreurs éventuelles
> (versions de bibliothèques, imports). Explique-moi chaque correction. »

Le code fourni est un squelette qui n'a pas été exécuté contre un vrai Ollama :
il est normal qu'une version de bibliothèque ou un import demande un
ajustement. C'est exactement le genre de mise au point où Claude Code est
utile, puisqu'il peut lancer le code et lire les erreurs.
