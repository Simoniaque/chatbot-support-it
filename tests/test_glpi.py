"""Dialogue avec GLPI (src/glpi.py), contre un faux GLPI branché dans httpx."""

import pytest

from src import config, glpi


def test_non_configure_sans_url_ni_jeton(sans_glpi):
    assert glpi.est_configure() is False
    with pytest.raises(glpi.ErreurGLPI):
        glpi.ouvrir_session("x", "y")


def test_ouvrir_session_renvoie_identite(faux_glpi):
    assert glpi.est_configure() is True
    s = glpi.ouvrir_session("m.dupont", "secret")
    assert s["session_token"] == "session-m.dupont"
    assert s["utilisateur"] == {"id": 7, "login": "m.dupont", "nom": "Marie Dupont"}


def test_identifiants_refuses(faux_glpi):
    with pytest.raises(glpi.IdentifiantsRefuses):
        glpi.ouvrir_session("m.dupont", "faux")


def test_mauvais_jeton_application(faux_glpi, monkeypatch):
    monkeypatch.setattr(config, "GLPI_APP_TOKEN", "faux")
    with pytest.raises(glpi.ErreurGLPI, match="ERROR_WRONG_APP_TOKEN_PARAMETER"):
        glpi.ouvrir_session("m.dupont", "secret")


def test_glpi_injoignable(faux_glpi):
    faux_glpi.panne = True
    with pytest.raises(glpi.ErreurGLPI, match="Impossible de joindre GLPI"):
        glpi.ouvrir_session("m.dupont", "secret")


def test_creer_ticket_au_nom_de_l_utilisateur(faux_glpi):
    r = glpi.creer_ticket("session-m.dupont", 7, "Ma question ?", "Précisions\nligne 2")
    assert r == {"id": 1, "url": "http://glpi.test/glpi/front/ticket.form.php?id=1"}
    ticket = faux_glpi.tickets[0]
    assert ticket["name"] == "Ma question ?"
    assert ticket["type"] == glpi.TYPE_DEMANDE
    assert ticket["_users_id_requester"] == 7
    assert "Ma question ?" in ticket["content"]
    assert "Précisions<br>ligne 2" in ticket["content"]


def test_contenu_du_ticket_echappe_le_html(faux_glpi):
    glpi.creer_ticket("session-m.dupont", 7, "<script>alert(1)</script>")
    assert "<script>" not in faux_glpi.tickets[0]["content"]
    assert "&lt;script&gt;" in faux_glpi.tickets[0]["content"]


def test_titre_tronque_a_120_caracteres(faux_glpi):
    glpi.creer_ticket("session-m.dupont", 7, "x" * 200)
    assert len(faux_glpi.tickets[0]["name"]) == 120
    assert faux_glpi.tickets[0]["name"].endswith("...")


def test_session_expiree_levee_specifiquement(faux_glpi):
    with pytest.raises(glpi.SessionExpiree):
        glpi.creer_ticket("session-inconnue", 1, "question")


def test_fermer_session_silencieuse_meme_en_panne(faux_glpi):
    glpi.fermer_session("session-m.dupont")
    assert faux_glpi.sessions_fermees == 1
    faux_glpi.panne = True
    glpi.fermer_session("session-m.dupont")  # ne lève pas
