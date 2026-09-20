"""
Configuration centrale du projet.

Pourquoi un fichier dédié : tous les réglages (modèles, seuil, chemins) sont
au même endroit. Pour changer le seuil de pertinence, on modifie une seule
ligne du fichier .env, jamais le code.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Charge les variables définies dans le fichier .env, s'il existe.
load_dotenv()

# --- Chemins ---------------------------------------------------------------
# RACINE = le dossier du projet (src/config.py -> src -> racine)
RACINE = Path(__file__).resolve().parent.parent
DOSSIER_CORPUS = RACINE / "data" / "corpus"      # les documents sources
DOSSIER_BASE_VECTORIELLE = RACINE / "chroma_db"  # la base générée

# --- Modèles (servis en local par Ollama) ----------------------------------
# Deux modèles différents, car ce sont deux métiers différents :
#  - le modèle d'embeddings transforme un texte en vecteur de nombres,
#    pour pouvoir comparer des sens ;
#  - le modèle de langage rédige la réponse finale.
MODELE_EMBEDDINGS = os.getenv("MODELE_EMBEDDINGS", "nomic-embed-text")
MODELE_LLM = os.getenv("MODELE_LLM", "mistral")
URL_OLLAMA = os.getenv("URL_OLLAMA", "http://localhost:11434")

# --- Découpage des documents ----------------------------------------------
# Un document entier est trop gros pour être envoyé au modèle : on le coupe
# en morceaux ("chunks"). Le chevauchement évite de couper une phrase en deux
# et de perdre le sens à la frontière de deux morceaux.
TAILLE_CHUNK = int(os.getenv("TAILLE_CHUNK", "1000"))
CHEVAUCHEMENT_CHUNK = int(os.getenv("CHEVAUCHEMENT_CHUNK", "150"))

# --- Recherche -------------------------------------------------------------
NOMBRE_EXTRAITS = int(os.getenv("NOMBRE_EXTRAITS", "4"))

# Seuil de pertinence : il s'agit d'une DISTANCE, donc plus c'est BAS, plus
# l'extrait est proche de la question.
#   - seuil trop bas  -> le bot refuse de répondre trop souvent
#   - seuil trop haut -> il répond à partir d'extraits hors sujet (hallucination)
# Valeur à justifier dans docs/seuil-pertinence.md, mesures à l'appui.
SEUIL_PERTINENCE = float(os.getenv("SEUIL_PERTINENCE", "0.65"))

# --- GLPI (facultatif) -----------------------------------------------------
# Si GLPI_URL et GLPI_APP_TOKEN sont renseignés :
#  - les utilisateurs se connectent au chatbot avec leurs identifiants GLPI ;
#  - quand le chatbot ne trouve pas de réponse, il propose de créer un ticket
#    GLPI, au nom de l'utilisateur connecté.
# Sinon, pas de connexion : le chatbot est utilisable anonymement, sans ticket.
#   GLPI_URL       : adresse de GLPI, sans /apirest.php (ex. http://glpi.local/glpi)
#   GLPI_APP_TOKEN : jeton du client API (Configuration > Générale > API)
GLPI_URL = os.getenv("GLPI_URL", "").strip()
GLPI_APP_TOKEN = os.getenv("GLPI_APP_TOKEN", "").strip()

# Durée de vie d'une connexion au chatbot, en heures. Au-delà, l'utilisateur
# doit se reconnecter (GLPI a aussi sa propre expiration de session).
DUREE_SESSION_HEURES = float(os.getenv("DUREE_SESSION_HEURES", "8"))

# --- Journalisation --------------------------------------------------------
# Chaque question (extraits retenus, scores, réponse) est ajoutée à un fichier
# JSON Lines. Sert à mesurer la qualité et à calibrer le seuil.
# JOURNALISATION=0 dans .env pour désactiver.
JOURNALISATION = os.getenv("JOURNALISATION", "1").strip() not in ("0", "false", "non")
DOSSIER_JOURNAL = RACINE / "logs"
FICHIER_JOURNAL = DOSSIER_JOURNAL / "echanges.jsonl"
