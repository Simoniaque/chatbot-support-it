#!/usr/bin/env bash
# Configure l'API REST de l'instance GLPI de test, sans passer par l'interface :
#   - active l'API et la connexion par identifiants (login / mot de passe),
#     ce qui permet aux utilisateurs de se connecter au chatbot avec leur
#     compte GLPI ;
#   - ouvre le client API par défaut à toutes les adresses IP ;
#   - génère un App-Token et l'enregistre (chiffré) ;
#   - écrit le jeton dans app_token.txt.
#
# À lancer depuis ce dossier, une fois GLPI démarré (docker compose up -d) :
#   bash configurer-api.sh
#
# Point important : GLPI chiffre le jeton en base avec la clé de l'instance
# (glpicrypt.key). On ne peut donc pas écrire un jeton en clair par SQL : on
# passe par un script PHP exécuté dans le conteneur pour chiffrer.

set -euo pipefail
cd "$(dirname "$0")"
export MSYS_NO_PATHCONV=1   # Git Bash : ne pas convertir /tmp/... en chemin Windows

DOCKER=docker
command -v docker >/dev/null 2>&1 || DOCKER=docker.exe

APP_TOKEN=$(python -c "import secrets; print(secrets.token_hex(20))")

# Chiffrement par GLPI lui-même
cat > chiffrer.php <<'EOF'
<?php
chdir('/var/www/glpi');
require '/var/www/glpi/vendor/autoload.php';
$kernel = new \Glpi\Kernel\Kernel();
$kernel->boot();
$cle = new GLPIKey();
foreach (array_slice($argv, 1) as $valeur) {
    echo $cle->encrypt($valeur), "\n";
}
EOF
$DOCKER compose cp chiffrer.php glpi:/tmp/chiffrer.php >/dev/null
APP_CHIFFRE=$($DOCKER compose exec -T glpi php /tmp/chiffrer.php "$APP_TOKEN" | sed -n 1p)
rm -f chiffrer.php

if [ ${#APP_CHIFFRE} -lt 40 ]; then
    echo "Échec du chiffrement du jeton : $APP_CHIFFRE" >&2
    exit 1
fi

# Mise à jour de la base (mot de passe : voir .env de ce dossier)
$DOCKER compose exec -T db mysql -uglpi -pglpi-test glpi 2>/dev/null <<EOF
UPDATE glpi_configs SET value='1' WHERE name IN ('enable_api', 'enable_api_login_credentials');
UPDATE glpi_apiclients SET app_token='$APP_CHIFFRE', app_token_date=NOW(),
       ipv4_range_start=NULL, ipv4_range_end=NULL WHERE id=1;
EOF
$DOCKER compose exec -T glpi php bin/console cache:clear >/dev/null

echo "$APP_TOKEN" > app_token.txt

# Vérification : l'API doit reconnaître le jeton d'application. Sans
# identifiants, elle répond ERROR_LOGIN_PARAMETERS_MISSING : c'est le
# comportement attendu (un mauvais jeton donnerait ERROR_WRONG_APP_TOKEN_PARAMETER).
REPONSE=$(curl -s -H "App-Token: $APP_TOKEN" http://localhost:8080/apirest.php/initSession)
if echo "$REPONSE" | grep -q "ERROR_LOGIN_PARAMETERS_MISSING"; then
    echo "API GLPI opérationnelle. À copier dans le .env du projet :"
    echo
    echo "GLPI_URL=http://localhost:8080"
    echo "GLPI_APP_TOKEN=$APP_TOKEN"
    echo
    echo "Connexion au chatbot avec un compte GLPI (glpi / glpi par défaut)."
else
    echo "L'API refuse le jeton : $REPONSE" >&2
    exit 1
fi
