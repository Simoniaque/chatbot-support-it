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

## 3. Activer l'API REST

Menu **Configuration > Générale**, onglet **API** :

1. **Activer l'API REST** : Oui
2. **Activer la connexion avec jeton externe** : Oui
   (c'est ce qui autorise l'authentification par `User-Token`)
3. Enregistrer.

En bas de cet onglet, la liste des **clients API** contient un client par
défaut « full access from localhost ». Cliquer dessus :

- **Plage IPv4** : vider les deux champs (début et fin). Depuis Docker, les
  requêtes du chatbot n'arrivent pas en `127.0.0.1` mais avec l'adresse du
  pont Docker ; avec la plage par défaut, elles seraient refusées.
- **Jeton d'application** : cliquer sur **Régénérer**, puis copier la valeur.
  C'est le `GLPI_APP_TOKEN`.
- Enregistrer.

## 4. Créer l'utilisateur qui portera les tickets

Menu **Administration > Utilisateurs > Ajouter** :

- Identifiant : `chatbot`
- Mot de passe : n'importe lequel (il ne servira pas, on passe par le jeton)
- Onglet **Habilitations** (après enregistrement) : ajouter le profil
  **Self-Service** sur l'entité racine. Ce profil suffit pour créer des
  tickets ; ne pas donner plus.

Revenir sur l'onglet principal de l'utilisateur, section **Clés d'accès
distant** : cliquer sur **Régénérer** à côté de **Jeton d'API**, et copier
la valeur. C'est le `GLPI_USER_TOKEN`.

(Pour aller vite, on peut utiliser le compte `glpi` lui-même : même endroit,
même bouton. Mais un compte dédié est ce qu'on fera en production.)

## 5. Configurer le chatbot

Dans le `.env` du projet (à la racine, pas celui de `outils/glpi-test`) :

```
GLPI_URL=http://localhost:8080
GLPI_APP_TOKEN=<jeton d'application copié à l'étape 3>
GLPI_USER_TOKEN=<jeton d'API copié à l'étape 4>
```

Relancer le serveur (`uvicorn src.api:app --reload`, ou Ctrl+C puis relance
s'il tournait déjà), puis vérifier sur http://localhost:8000/sante que
`"glpi_configure": true`.

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

## 7. Arrêter

```powershell
docker compose down        # arrêt, données conservées
docker compose down -v     # arrêt et suppression complète
```
