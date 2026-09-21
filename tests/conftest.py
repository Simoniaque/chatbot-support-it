"""
Doublures partagées par les tests.

Aucun test ne dépend d'Ollama, de ChromaDB ni d'un GLPI réel : tout ce qui
sort du projet est remplacé ici. Les tests vérifient la logique du projet
(seuils, vérification, sessions, tickets, journal), pas la qualité du modèle
— celle-ci se mesure avec tests/questions_test.md.

Lancer :  python -m pytest
"""

import base64
import json

import httpx
import pytest

from src import config, glpi, journal, rag


# --- Journal dans un dossier temporaire -----------------------------------

@pytest.fixture(autouse=True)
def journal_temporaire(tmp_path, monkeypatch):
    """Chaque test écrit son journal et ses sessions dans un dossier jetable."""
    monkeypatch.setattr(config, "JOURNALISATION", True)
    monkeypatch.setattr(config, "DOSSIER_JOURNAL", tmp_path)
    monkeypatch.setattr(config, "FICHIER_JOURNAL", tmp_path / "echanges.jsonl")
    monkeypatch.setattr(config, "FICHIER_SESSIONS", tmp_path / "sessions.sqlite")
    return tmp_path / "echanges.jsonl"


def lire_journal(fichier):
    if not fichier.exists():
        return []
    return [json.loads(l) for l in fichier.read_text(encoding="utf-8").splitlines() if l]


# --- Faux ChromaDB et faux modèle -----------------------------------------

class FauxDocument:
    def __init__(self, contenu, page, source="doc.pdf"):
        self.page_content = contenu
        self.metadata = {"source": source, "page": page}


class FausseBase:
    """Renvoie toujours la même liste (document, score), triée par score."""
    def __init__(self, resultats):
        self.resultats = sorted(resultats, key=lambda r: r[1])

    def similarity_search_with_score(self, question, k):
        return self.resultats[:k]


class FauxModele:
    """Répond selon le contenu du prompt reçu.

    - prompt de vérification (contient « OUI ou par NON ») : OUI si le mot
      « pertinent » est dans l'extrait, NON sinon ;
    - prompt de rédaction : la réponse fixée, ou HORS_CONTEXTE si demandé.
    """
    def __init__(self, reponse="Réponse rédigée.", hors_contexte=False):
        self.reponse = reponse
        self.hors_contexte = hors_contexte
        self.prompts = []

    def invoke(self, prompt):
        self.prompts.append(prompt)
        class Resultat:
            content = ""
        r = Resultat()
        if "OUI ou par NON" in prompt:
            r.content = "OUI" if "pertinent" in prompt else "NON"
        else:
            r.content = "HORS_CONTEXTE" if self.hors_contexte else self.reponse
        return r


@pytest.fixture
def faux_rag(monkeypatch):
    """Installe une base et un modèle factices ; renvoie une fonction pour
    les paramétrer depuis le test."""
    def installer(resultats, reponse="Réponse rédigée.", hors_contexte=False,
                  seuil=0.65, contexte=0.65, verification=0.0):
        modele = FauxModele(reponse, hors_contexte)
        monkeypatch.setattr(rag, "_get_base", lambda: FausseBase(resultats))
        monkeypatch.setattr(rag, "_get_llm", lambda: modele)
        monkeypatch.setattr(rag, "_get_juge", lambda: modele)
        monkeypatch.setattr(config, "SEUIL_PERTINENCE", seuil)
        monkeypatch.setattr(config, "SEUIL_CONTEXTE", max(contexte, seuil))
        monkeypatch.setattr(config, "SEUIL_VERIFICATION", verification)
        return modele
    return installer


# --- Faux GLPI, branché dans httpx ----------------------------------------

APP_TOKEN = "app-test"
COMPTES = {"m.dupont": ("secret", 7, "Marie", "Dupont")}


class FauxGLPI:
    """Imite les quatre appels de l'API REST GLPI utilisés par le projet."""
    def __init__(self):
        self.tickets = []
        self.sessions_fermees = 0
        self.panne = False

    @staticmethod
    def _erreur(code, message, statut):
        return httpx.Response(statut, json=[code, message])

    def gerer(self, requete: httpx.Request) -> httpx.Response:
        if self.panne:
            raise httpx.ConnectError("connexion refusée")
        if requete.headers.get("App-Token") != APP_TOKEN:
            return self._erreur("ERROR_WRONG_APP_TOKEN_PARAMETER", "app_token", 400)
        chemin = requete.url.path.rsplit("/", 1)[-1]

        if chemin == "initSession":
            auth = requete.headers.get("Authorization", "")
            if not auth.startswith("Basic "):
                return self._erreur("ERROR_LOGIN_PARAMETERS_MISSING", "identifiants", 400)
            login, _, mdp = base64.b64decode(auth[6:]).decode().partition(":")
            if login not in COMPTES or COMPTES[login][0] != mdp:
                return self._erreur("ERROR_GLPI_LOGIN", "identifiants incorrects", 401)
            return httpx.Response(200, json={"session_token": "session-" + login})

        jeton = requete.headers.get("Session-Token", "")
        login = jeton.removeprefix("session-")
        if not jeton.startswith("session-") or login not in COMPTES:
            return self._erreur("ERROR_SESSION_TOKEN_INVALID", "session invalide", 401)

        if chemin == "getFullSession":
            _, uid, prenom, nom = COMPTES[login]
            return httpx.Response(200, json={"session": {
                "glpiID": uid, "glpiname": login,
                "glpifirstname": prenom, "glpirealname": nom}})
        if chemin == "Ticket":
            self.tickets.append(json.loads(requete.content)["input"])
            return httpx.Response(201, json={"id": len(self.tickets), "message": ""})
        if chemin == "killSession":
            self.sessions_fermees += 1
            return httpx.Response(200)
        return self._erreur("ERROR_RESOURCE_NOT_FOUND", chemin, 404)


@pytest.fixture
def faux_glpi(monkeypatch):
    """GLPI configuré dans la config, et httpx.Client détourné vers FauxGLPI."""
    serveur = FauxGLPI()
    monkeypatch.setattr(config, "GLPI_URL", "http://glpi.test/glpi")
    monkeypatch.setattr(config, "GLPI_APP_TOKEN", APP_TOKEN)
    vrai_client = httpx.Client

    def client_detourne(**options):
        options["transport"] = httpx.MockTransport(serveur.gerer)
        return vrai_client(**options)

    monkeypatch.setattr(glpi.httpx, "Client", client_detourne)
    return serveur


@pytest.fixture
def sans_glpi(monkeypatch):
    monkeypatch.setattr(config, "GLPI_URL", "")
    monkeypatch.setattr(config, "GLPI_APP_TOKEN", "")
