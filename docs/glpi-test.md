# Tester l'escalade GLPI sur une vraie instance

Procédure pour monter une instance GLPI locale jetable avec Docker, la
configurer pour l'API REST, et vérifier que le chatbot y crée bien des tickets.

Durée : environ 20 minutes la première fois (téléchargements compris).

---

## 1. Installer Docker Desktop

```powershell
winget install Docker.DockerDesktop
```

Docker Desktop repose sur WSL 2, qui a besoin de deux fonctionnalités
Windows souvent désactivées sur un poste neuf. Si Docker Desktop affiche
« Docker Desktop is unable to start » (ou si ses logs mentionnent *Virtual
Machine Platform not enabled*), les activer dans un **PowerShell
administrateur** :

```powershell
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
```

Puis **redémarrer le PC**, lancer `wsl --update`, et ouvrir Docker Desktop.
Attendre que l'icône dans la barre des tâches indique « Docker Desktop is
running ». Si un terminal était ouvert avant l'installation, le fermer et
le rouvrir pour que `docker` soit dans le PATH. Vérifier :

```powershell
docker compose version
```

## 2. Démarrer GLPI

```powershell
cd outils\glpi-test
docker compose up -d
```

Le premier lancement télécharge les images (environ 1 Go) puis GLPI installe
sa base de données tout seul. Suivre l'avancement avec :

```powershell
docker compose logs -f glpi
```

Quand les lignes défilent avec des requêtes HTTP (ou après 2 à 3 minutes),
ouvrir **http://localhost:8080**. Identifiants par défaut : **glpi / glpi**.

GLPI affiche des avertissements de sécurité (comptes par défaut, dossier
`install` présent) : normal pour une instance de test, on les ignore.

## 3. Activer l'API et générer les jetons

### Par script (recommandé)

```powershell
bash configurer-api.sh
```

(Git Bash est installé avec Git ; depuis PowerShell, `bash` le trouve.)

Le script active l'API REST, ouvre le client API par défaut à toutes les
adresses, génère un jeton d'application et un jeton d'API pour le compte
`glpi`, vérifie qu'une session s'ouvre, puis affiche les trois lignes à
copier dans le `.env` du projet. Les jetons sont aussi gardés dans
`app_token.txt` et `user_token.txt` (ignorés par Git).

Pourquoi un script PHP dans le conteneur plutôt que du SQL direct : GLPI
**chiffre les jetons en base** avec la clé de l'instance (`glpicrypt.key`).
Un jeton écrit en clair par SQL est refusé avec
`ERROR_WRONG_APP_TOKEN_PARAMETER`. Le script fait chiffrer les valeurs par
GLPI lui-même avant de les enregistrer.

### À la main (pour comprendre ce que fait le script)

Se connecter sur http://localhost:8080 (glpi / glpi), puis :

**Configuration > Générale**, onglet **API** :

1. **Activer l'API REST** : Oui
2. **Activer la connexion avec jeton externe** : Oui (déjà le cas par défaut,
   vérifier)
3. Enregistrer.

En bas de cet onglet, cliquer sur le client API **full access from
localhost** :

- **Plage IPv4** : vider les deux champs. Depuis Docker, les requêtes du
  chatbot n'arrivent pas en `127.0.0.1` mais avec l'adresse du pont Docker
  (`172.18.0.1` dans nos essais) ; avec la plage par défaut, elles seraient
  refusées.
- **Jeton d'application** : **Régénérer**, copier la valeur → `GLPI_APP_TOKEN`.
- Enregistrer.

**Administration > Utilisateurs > glpi**, section **Clés d'accès distant** :
**Régénérer** le **Jeton d'API**, copier la valeur → `GLPI_USER_TOKEN`.

En production, on créera plutôt un compte dédié `chatbot` avec le seul
profil **Self-Service** (suffisant pour créer des tickets), et c'est son
jeton qu'on utilisera : les tickets apparaîtront alors avec ce compte comme
demandeur.

## 5. Configurer le chatbot

Dans le `.env` du projet (à la racine, pas celui de `outils/glpi-test`) :

```
GLPI_URL=http://localhost:8080
GLPI_APP_TOKEN=<jeton d'application copié à l'étape 3>
GLPI_USER_TOKEN=<jeton d'API copié à l'étape 4>
```

**Relancer le serveur** (Ctrl+C puis `uvicorn src.api:app --reload`) : le
`.env` n'est lu qu'au démarrage, `--reload` ne suffit pas. Vérifier sur
http://localhost:8000/sante que `"glpi_configure": true`.

## 6. Tester

### Par l'API directement

```powershell
curl.exe -s -X POST http://localhost:8000/ticket -H "Content-Type: application/json" -d "{\"question\": \"Test depuis le chatbot\", \"precisions\": \"Ticket de test\", \"demandeur\": \"moi\"}"
```

Réponse attendue : `{"id": 1, "url": "http://localhost:8080/front/ticket.form.php?id=1"}`.

En cas d'erreur, le message dit lequel des trois appels a échoué :

| Message | Cause probable |
|---|---|
| `Connexion à GLPI refusée : ERROR_WRONG_APP_TOKEN_PARAMETER` | `GLPI_APP_TOKEN` faux, ou plage IP du client API non vidée |
| `Connexion à GLPI refusée : ERROR_GLPI_LOGIN_USER_TOKEN` | `GLPI_USER_TOKEN` faux, ou « connexion avec jeton externe » non activée |
| `Connexion à GLPI refusée : ERROR_NOT_ALLOWED` | API REST non activée |
| `Création du ticket refusée : ERROR_GLPI_ADD` | L'utilisateur n'a pas le droit de créer des tickets (habilitation manquante) |
| `Impossible de joindre GLPI` | Conteneur arrêté, ou `GLPI_URL` faux |

### Par l'interface

1. http://localhost:8000, poser une question hors sujet
   (« Comment installer Photoshop ? »).
2. Le chatbot refuse et propose de transmettre au support.
3. Remplir les précisions, cliquer sur **Créer le ticket**.
4. Suivre le lien « Voir dans GLPI » : le ticket doit apparaître avec la
   question, les précisions et le contact, demandeur = `chatbot`.

Le ticket est aussi tracé dans `logs/echanges.jsonl` (type `ticket`).

### Résultat obtenu (20/09/2026)

Validé de bout en bout sur GLPI 11 (image `glpi/glpi:latest`) : ticket créé
par l'API du chatbot puis depuis l'interface après refus, relu via l'API
GLPI avec le bon type (Demande), le bon demandeur et le contenu complet
(question, précisions, contact).

## 7. Arrêter

```powershell
docker compose down        # arrêt, données conservées
docker compose down -v     # arrêt et suppression complète
```
