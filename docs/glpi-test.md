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

## 3. Activer l'API et générer le jeton d'application

### Par script (recommandé)

```powershell
bash configurer-api.sh
```

(Git Bash est installé avec Git ; depuis PowerShell, `bash` le trouve.)

Le script active l'API REST et la connexion par identifiants, ouvre le
client API par défaut à toutes les adresses, génère un jeton d'application,
vérifie que l'API le reconnaît, puis affiche les lignes à copier dans le
`.env` du projet. Le jeton est aussi gardé dans `app_token.txt` (ignoré par
Git).

Pourquoi un script PHP dans le conteneur plutôt que du SQL direct : GLPI
**chiffre le jeton en base** avec la clé de l'instance (`glpicrypt.key`).
Un jeton écrit en clair par SQL est refusé avec
`ERROR_WRONG_APP_TOKEN_PARAMETER`. Le script fait chiffrer la valeur par
GLPI lui-même avant de l'enregistrer.

### À la main (pour comprendre ce que fait le script)

Se connecter sur http://localhost:8080 (glpi / glpi), puis
**Configuration > Générale**, onglet **API** :

1. **Activer l'API REST** : Oui
2. **Activer la connexion avec identifiants** : Oui — c'est ce qui permet aux
   utilisateurs de se connecter au chatbot avec leur login/mot de passe GLPI.
3. Enregistrer.

En bas de cet onglet, cliquer sur le client API **full access from
localhost** :

- **Plage IPv4** : vider les deux champs. Depuis Docker, les requêtes du
  chatbot n'arrivent pas en `127.0.0.1` mais avec l'adresse du pont Docker
  (`172.18.0.1` dans nos essais) ; avec la plage par défaut, elles seraient
  refusées.
- **Jeton d'application** : **Régénérer**, copier la valeur → `GLPI_APP_TOKEN`.
- Enregistrer.

## 4. (Facultatif) Créer un utilisateur de test

Le compte `glpi` suffit pour tester. Pour voir un « vrai » demandeur sur le
ticket, créer un utilisateur dans **Administration > Utilisateurs > Ajouter**
(identifiant, mot de passe, prénom, nom), et lui donner le profil
**Self-Service** sur l'entité racine dans l'onglet **Habilitations**. Ce
profil suffit pour créer des tickets. Se connecter ensuite au chatbot avec ce
compte : le ticket portera son nom.

## 5. Configurer le chatbot

Dans le `.env` du projet (à la racine, pas celui de `outils/glpi-test`) :

```
GLPI_URL=http://localhost:8080
GLPI_APP_TOKEN=<jeton d'application de l'étape 3>
```

**Relancer le serveur** (Ctrl+C puis `uvicorn src.api:app --reload`) : le
`.env` n'est lu qu'au démarrage, `--reload` ne suffit pas. Vérifier sur
http://localhost:8000/sante que `"glpi_configure": true` et `"connexion_requise": true`.

## 6. Tester

### Par l'interface

1. http://localhost:8000 affiche l'écran de connexion. Se connecter avec un
   compte GLPI (`glpi` / `glpi`, ou l'utilisateur de test de l'étape 4).
2. Poser une question hors sujet (« Comment installer Photoshop ? »).
3. Le chatbot refuse et propose de transmettre au support.
4. Remplir les précisions, cliquer sur **Créer le ticket**.
5. Suivre le lien « Voir dans GLPI » : le ticket doit apparaître avec la
   question et les précisions, et **l'utilisateur connecté comme demandeur**.

Le ticket est aussi tracé dans `logs/echanges.jsonl` (type `ticket`, avec
le login).

### Par l'API directement

```powershell
curl.exe -s -c cookies.txt -X POST http://localhost:8000/connexion -H "Content-Type: application/json" -d "{\"login\": \"glpi\", \"mot_de_passe\": \"glpi\"}"
curl.exe -s -b cookies.txt -X POST http://localhost:8000/ticket -H "Content-Type: application/json" -d "{\"question\": \"Test depuis le chatbot\", \"precisions\": \"Ticket de test\"}"
```

Réponse attendue : `{"id": 1, "url": "http://localhost:8080/front/ticket.form.php?id=1"}`.

### Messages d'erreur

| Message | Cause probable |
|---|---|
| `Identifiant ou mot de passe incorrect.` | Compte GLPI inconnu, ou connexion par identifiants désactivée dans l'onglet API |
| `Connexion à GLPI refusée : ERROR_WRONG_APP_TOKEN_PARAMETER` | `GLPI_APP_TOKEN` faux, ou plage IP du client API non vidée |
| `Connexion à GLPI refusée : ERROR_NOT_ALLOWED` | API REST non activée |
| `Création du ticket refusée : ERROR_GLPI_ADD` | L'utilisateur n'a pas le droit de créer des tickets (habilitation manquante) |
| `Votre session GLPI a expiré` | Session GLPI fermée côté serveur : se reconnecter |
| `Impossible de joindre GLPI` | Conteneur arrêté, ou `GLPI_URL` faux |

### Résultat obtenu (20/09/2026)

Validé de bout en bout sur GLPI 11 (image `glpi/glpi:latest`) : connexion
avec un compte GLPI, refus du chatbot, ticket créé depuis l'interface, relu
via l'API GLPI avec le bon type (Demande), le contenu complet et
**l'utilisateur connecté comme acteur « demandeur »**. Point découvert en
chemin : via l'API, GLPI n'ajoute pas automatiquement le créateur comme
demandeur (contrairement à l'interface web) ; le chatbot passe donc
`_users_id_requester` explicitement.

## 7. Arrêter

```powershell
docker compose down        # arrêt, données conservées
docker compose down -v     # arrêt et suppression complète
```
