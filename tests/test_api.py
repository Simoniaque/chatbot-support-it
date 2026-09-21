"""Routes de l'API (src/api.py) : sessions, questions, tickets, avis, journal."""

import pytest
from fastapi.testclient import TestClient

from src import api, config, rag, sessions
from tests.conftest import FauxDocument as Doc, lire_journal


@pytest.fixture
def client():
    return TestClient(api.app)


def rag_repond(faux_rag):
    faux_rag([(Doc("texte pertinent", 3), 0.30)])


def rag_refuse(faux_rag):
    faux_rag([(Doc("hors sujet", 1), 0.90)])


# --- Mode anonyme (GLPI non configuré) -------------------------------------

def test_sante(client, sans_glpi):
    corps = client.get("/sante").json()
    assert corps["statut"] == "ok"
    assert corps["glpi_configure"] is False
    assert corps["connexion_requise"] is False


def test_page_html_servie_sans_cache(client, sans_glpi):
    r = client.get("/")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert r.headers["cache-control"] == "no-cache"


def test_ask_anonyme_repond_et_journalise(client, sans_glpi, faux_rag, journal_temporaire):
    rag_repond(faux_rag)
    r = client.post("/ask", json={"question": "  Ma question ?  "})
    assert r.status_code == 200
    assert r.json()["refus"] is False
    assert r.json()["sources"][0]["page"] == 3
    entree = lire_journal(journal_temporaire)[-1]
    assert entree["type"] == "question"
    assert entree["question"] == "Ma question ?"
    assert entree["utilisateur"] is None
    assert entree["sources"][0]["page"] == 3
    assert "extrait" not in entree["sources"][0]


def test_ask_question_vide(client, sans_glpi):
    assert client.post("/ask", json={"question": ""}).status_code == 422
    assert client.post("/ask", json={"question": "   "}).status_code == 422


def test_ask_ollama_injoignable(client, sans_glpi, monkeypatch):
    def plante(question):
        raise ConnectionError("Failed to connect to Ollama")
    monkeypatch.setattr(rag, "repondre", plante)
    r = client.post("/ask", json={"question": "q"})
    assert r.status_code == 503
    assert "Ollama" in r.json()["detail"]


def test_ticket_impossible_sans_glpi(client, sans_glpi):
    r = client.post("/ticket", json={"question": "q"})
    assert r.status_code == 503


def test_connexion_impossible_sans_glpi(client, sans_glpi):
    r = client.post("/connexion", json={"login": "a", "mot_de_passe": "b"})
    assert r.status_code == 503


# --- Mode connecté (GLPI configuré) ----------------------------------------

def test_acces_refuse_sans_session(client, faux_glpi):
    assert client.get("/moi").json() == {"connexion_requise": True, "utilisateur": None}
    assert client.post("/ask", json={"question": "q"}).status_code == 401
    assert client.post("/ticket", json={"question": "q"}).status_code == 401
    assert client.post("/avis", json={"question": "q", "utile": True}).status_code == 401


def test_connexion_refusee(client, faux_glpi, journal_temporaire):
    r = client.post("/connexion", json={"login": "m.dupont", "mot_de_passe": "faux"})
    assert r.status_code == 401
    assert api.NOM_COOKIE not in client.cookies
    assert lire_journal(journal_temporaire)[-1]["type"] == "connexion_refusee"


def test_connexion_glpi_en_panne(client, faux_glpi):
    faux_glpi.panne = True
    r = client.post("/connexion", json={"login": "m.dupont", "mot_de_passe": "secret"})
    assert r.status_code == 502


def test_parcours_complet_connecte(client, faux_glpi, faux_rag, journal_temporaire):
    # Connexion : cookie posé, identité renvoyée
    r = client.post("/connexion", json={"login": "m.dupont", "mot_de_passe": "secret"})
    assert r.status_code == 200
    assert r.json()["nom"] == "Marie Dupont"
    assert api.NOM_COOKIE in client.cookies
    assert client.get("/moi").json()["utilisateur"]["login"] == "m.dupont"

    # Question refusée, journalisée au nom de l'utilisateur
    rag_refuse(faux_rag)
    r = client.post("/ask", json={"question": "Hors sujet ?"})
    assert r.json()["refus"] is True
    assert lire_journal(journal_temporaire)[-1]["utilisateur"] == "m.dupont"

    # Ticket créé avec la session de l'utilisateur, qui en est le demandeur
    r = client.post("/ticket", json={"question": "Hors sujet ?", "precisions": "détail"})
    assert r.status_code == 200
    assert r.json()["id"] == 1
    assert faux_glpi.tickets[0]["_users_id_requester"] == 7
    assert lire_journal(journal_temporaire)[-1]["type"] == "ticket"

    # Avis
    r = client.post("/avis", json={"question": "Hors sujet ?", "utile": False})
    assert r.status_code == 200
    assert lire_journal(journal_temporaire)[-1] == {
        **lire_journal(journal_temporaire)[-1],
        "type": "avis", "utilisateur": "m.dupont", "utile": False}

    # Déconnexion : session GLPI fermée, cookie supprimé, accès refusé
    assert client.post("/deconnexion").status_code == 200
    assert faux_glpi.sessions_fermees == 1
    assert client.get("/moi").json()["utilisateur"] is None
    assert client.post("/ask", json={"question": "q"}).status_code == 401


def test_session_glpi_expiree_deconnecte(client, faux_glpi):
    client.post("/connexion", json={"login": "m.dupont", "mot_de_passe": "secret"})
    # GLPI ne reconnaît plus la session : on change le login connu.
    from tests import conftest
    conftest.COMPTES.pop("m.dupont")
    try:
        r = client.post("/ticket", json={"question": "q"})
    finally:
        conftest.COMPTES["m.dupont"] = ("secret", 7, "Marie", "Dupont")
    assert r.status_code == 401
    assert "expiré" in r.json()["detail"]
    assert client.get("/moi").json()["utilisateur"] is None


def expirer_toutes_les_sessions():
    import sqlite3
    with sqlite3.connect(config.FICHIER_SESSIONS) as connexion:
        connexion.execute("UPDATE sessions SET expire = '2000-01-01T00:00:00'")


def test_session_chatbot_expiree(client, faux_glpi):
    client.post("/connexion", json={"login": "m.dupont", "mot_de_passe": "secret"})
    expirer_toutes_les_sessions()
    assert client.get("/moi").json()["utilisateur"] is None
    assert faux_glpi.sessions_fermees == 1  # la session GLPI a été fermée
    assert client.get("/moi").json()["utilisateur"] is None
    assert faux_glpi.sessions_fermees == 1  # une seule fois


def test_session_survit_a_un_redemarrage(faux_glpi):
    # Deux clients = deux processus serveur successifs ; le cookie du premier
    # est reconnu par le second parce que la session est dans SQLite.
    premier = TestClient(api.app)
    premier.post("/connexion", json={"login": "m.dupont", "mot_de_passe": "secret"})
    cookie = premier.cookies[api.NOM_COOKIE]
    second = TestClient(api.app)
    r = second.get("/moi", cookies={api.NOM_COOKIE: cookie})
    assert r.json()["utilisateur"]["login"] == "m.dupont"


def test_purge_des_sessions_expirees_a_la_connexion(faux_glpi):
    sessions.creer("expiree", "session-m.dupont", {"login": "y"})
    expirer_toutes_les_sessions()
    sessions.creer("valide", "session-m.dupont", {"login": "x"})
    TestClient(api.app).post("/connexion", json={"login": "m.dupont", "mot_de_passe": "secret"})
    assert sessions.lire("expiree") is None
    assert sessions.lire("valide") is not None
    assert faux_glpi.sessions_fermees == 1
