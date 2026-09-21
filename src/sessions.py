"""
Sessions des utilisateurs connectés, conservées dans un fichier SQLite.

Avant, les sessions vivaient en mémoire : chaque redémarrage du serveur
(y compris les rechargements automatiques en développement) déconnectait
tout le monde. SQLite, fourni avec Python, règle ça sans serveur ni
dépendance ; le fichier est hors dépôt Git, comme le journal.

Une session = un identifiant aléatoire (celui du cookie), le jeton de
session GLPI ouvert au nom de l'utilisateur, son identité, et une date
d'expiration. Le mot de passe n'y figure jamais.
"""

import json
import sqlite3
from datetime import datetime, timedelta

from src import config


def _connexion():
    connexion = sqlite3.connect(config.FICHIER_SESSIONS)
    connexion.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            identifiant   TEXT PRIMARY KEY,
            session_token TEXT NOT NULL,
            utilisateur   TEXT NOT NULL,
            expire        TEXT NOT NULL
        )""")
    return connexion


def creer(identifiant: str, session_token: str, utilisateur: dict) -> None:
    expire = datetime.now() + timedelta(hours=config.DUREE_SESSION_HEURES)
    with _connexion() as connexion:
        connexion.execute(
            "INSERT OR REPLACE INTO sessions VALUES (?, ?, ?, ?)",
            (identifiant, session_token, json.dumps(utilisateur), expire.isoformat()))


def lire(identifiant: str) -> dict | None:
    """La session, ou None si elle n'existe pas ou a expiré (elle est alors
    supprimée ; le jeton GLPI est renvoyé dans "expiree" pour être fermé)."""
    with _connexion() as connexion:
        ligne = connexion.execute(
            "SELECT session_token, utilisateur, expire FROM sessions WHERE identifiant = ?",
            (identifiant,)).fetchone()
        if ligne is None:
            return None
        session_token, utilisateur, expire = ligne
        if datetime.now() > datetime.fromisoformat(expire):
            connexion.execute("DELETE FROM sessions WHERE identifiant = ?", (identifiant,))
            return {"expiree": True, "session_token": session_token}
    return {"session_token": session_token, "utilisateur": json.loads(utilisateur)}


def supprimer(identifiant: str) -> dict | None:
    """Supprime la session et la renvoie (pour fermer la session GLPI)."""
    with _connexion() as connexion:
        ligne = connexion.execute(
            "SELECT session_token, utilisateur FROM sessions WHERE identifiant = ?",
            (identifiant,)).fetchone()
        connexion.execute("DELETE FROM sessions WHERE identifiant = ?", (identifiant,))
    if ligne is None:
        return None
    return {"session_token": ligne[0], "utilisateur": json.loads(ligne[1])}


def purger_expirees() -> list[str]:
    """Supprime les sessions expirées ; renvoie leurs jetons GLPI à fermer."""
    maintenant = datetime.now().isoformat()
    with _connexion() as connexion:
        jetons = [l[0] for l in connexion.execute(
            "SELECT session_token FROM sessions WHERE expire < ?", (maintenant,))]
        connexion.execute("DELETE FROM sessions WHERE expire < ?", (maintenant,))
    return jetons
