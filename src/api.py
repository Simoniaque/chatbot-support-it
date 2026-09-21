"""
Étape 3 : exposer le chatbot via une API et une page web.

Deux livrables du cahier des charges en un seul fichier :
 - l'API      : POST /ask (question), POST /ticket (escalade vers GLPI),
                POST /avis (retour utilisateur), POST /connexion et
                /deconnexion, GET /moi ;
 - l'interface: la page statique servie sur /.

Connexion : si GLPI est configuré, l'utilisateur doit se connecter avec ses
identifiants GLPI avant de poser des questions. Le chatbot garde en mémoire
la session GLPI ouverte en son nom, repérée par un cookie. Sans GLPI, pas
de connexion : usage anonyme, sans création de ticket.

À lancer :  uvicorn src.api:app --reload
Puis ouvrir http://localhost:8000
"""

import secrets
import time
from datetime import datetime, timedelta

from fastapi import Cookie, FastAPI, HTTPException, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src import config, glpi, journal, rag

app = FastAPI(title="Chatbot Support IT")


@app.middleware("http")
async def pas_de_cache_html(request, call_next):
    """Force le navigateur à revérifier la page HTML à chaque visite.

    Sans cet en-tête, le navigateur garde l'ancienne interface en cache
    après une mise à jour de static/index.html. "no-cache" ne désactive pas
    le cache : il oblige seulement à demander au serveur si la page a changé
    (réponse 304 sinon, très légère).
    """
    reponse = await call_next(request)
    if reponse.headers.get("content-type", "").startswith("text/html"):
        reponse.headers["Cache-Control"] = "no-cache"
    return reponse


# --- Sessions -------------------------------------------------------------
# Sessions ouvertes, en mémoire : {identifiant du cookie: {...}}. Perdues au
# redémarrage du serveur, ce qui oblige simplement à se reconnecter. Un
# stockage persistant n'apporterait rien pour l'usage visé.
NOM_COOKIE = "chatbot_session"
_sessions: dict[str, dict] = {}


def _connexion_requise() -> bool:
    return glpi.est_configure()


def _session_courante(cookie: str | None) -> dict | None:
    """Renvoie la session liée au cookie, ou None si absente ou expirée."""
    if not cookie:
        return None
    session = _sessions.get(cookie)
    if session is None:
        return None
    if datetime.now() > session["expire"]:
        _sessions.pop(cookie, None)
        glpi.fermer_session(session["session_token"])
        return None
    return session


def _exiger_session(cookie: str | None) -> dict | None:
    """Session courante, ou 401 si la connexion est requise et absente."""
    session = _session_courante(cookie)
    if session is None and _connexion_requise():
        raise HTTPException(status_code=401,
                            detail="Connectez-vous pour utiliser le chatbot.")
    return session


class Identifiants(BaseModel):
    login: str = Field(min_length=1, max_length=200)
    mot_de_passe: str = Field(min_length=1, max_length=500)


@app.post("/connexion")
def connexion(payload: Identifiants, reponse: Response):
    """Ouvre une session GLPI au nom de l'utilisateur et pose un cookie."""
    if not _connexion_requise():
        raise HTTPException(status_code=503,
                            detail="La connexion n'est pas activée (GLPI non configuré).")
    try:
        ouverture = glpi.ouvrir_session(payload.login, payload.mot_de_passe)
    except glpi.IdentifiantsRefuses as erreur:
        journal.enregistrer("connexion_refusee", login=payload.login)
        raise HTTPException(status_code=401, detail=str(erreur))
    except glpi.ErreurGLPI as erreur:
        raise HTTPException(status_code=502, detail=str(erreur))

    identifiant = secrets.token_urlsafe(32)
    _sessions[identifiant] = {
        "session_token": ouverture["session_token"],
        "utilisateur": ouverture["utilisateur"],
        "expire": datetime.now() + timedelta(hours=config.DUREE_SESSION_HEURES),
    }
    # HttpOnly : le JavaScript de la page ne peut pas lire le cookie.
    # SameSite=Lax : il n'est pas envoyé depuis un autre site.
    reponse.set_cookie(NOM_COOKIE, identifiant, httponly=True, samesite="lax",
                       max_age=int(config.DUREE_SESSION_HEURES * 3600))
    journal.enregistrer("connexion", utilisateur=ouverture["utilisateur"]["login"])
    return ouverture["utilisateur"]


@app.post("/deconnexion")
def deconnexion(reponse: Response, chatbot_session: str | None = Cookie(default=None)):
    session = _sessions.pop(chatbot_session, None) if chatbot_session else None
    if session:
        glpi.fermer_session(session["session_token"])
        journal.enregistrer("deconnexion", utilisateur=session["utilisateur"]["login"])
    reponse.delete_cookie(NOM_COOKIE)
    return {"statut": "ok"}


@app.get("/moi")
def moi(chatbot_session: str | None = Cookie(default=None)):
    """L'utilisateur connecté. Sert à l'interface au chargement de la page."""
    session = _session_courante(chatbot_session)
    return {
        "connexion_requise": _connexion_requise(),
        "utilisateur": session["utilisateur"] if session else None,
    }


# --- Questions ------------------------------------------------------------

class Question(BaseModel):
    """Décrit ce que l'API attend en entrée : {"question": "..."}"""
    # min_length : une question vide n'a pas de sens, FastAPI renvoie
    # une erreur 422 avant même d'appeler le RAG.
    question: str = Field(min_length=1, max_length=2000)


@app.post("/ask")
def ask(payload: Question, chatbot_session: str | None = Cookie(default=None)):
    session = _exiger_session(chatbot_session)
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="La question est vide.")
    debut = time.perf_counter()
    try:
        resultat = rag.repondre(question)
    except ConnectionError:
        # Levée par langchain_ollama quand Ollama ne répond pas. Sans ce
        # bloc, l'utilisateur reçoit une page "Internal Server Error"
        # sans explication.
        raise HTTPException(
            status_code=503,
            detail="Impossible de joindre Ollama. Vérifiez qu'il est lancé "
                   f"(adresse configurée : {config.URL_OLLAMA}).",
        )

    # Trace de l'échange : ce qui a été retenu et pourquoi. On ne garde des
    # sources que l'identification et le score, pas le texte des extraits.
    journal.enregistrer(
        "question",
        utilisateur=session["utilisateur"]["login"] if session else None,
        question=question,
        refus=resultat["refus"],
        motif_refus=resultat["motif_refus"],
        extraits_verifies=resultat["extraits_verifies"],
        extraits_ecartes=resultat["extraits_ecartes"],
        meilleur_score=resultat["meilleur_score"],
        seuil=config.SEUIL_PERTINENCE,
        sources=[{"document": s["document"], "page": s["page"],
                  "score": s["score"]} for s in resultat["sources"]],
        reponse=resultat["reponse"],
        duree_s=round(time.perf_counter() - debut, 2),
    )
    return resultat


# --- Tickets --------------------------------------------------------------

class DemandeTicket(BaseModel):
    """Ce que l'interface envoie quand l'utilisateur confirme la création
    d'un ticket. Seule la question est obligatoire."""
    question: str = Field(min_length=1, max_length=2000)
    precisions: str = Field(default="", max_length=5000)


@app.post("/ticket")
def ticket(payload: DemandeTicket, chatbot_session: str | None = Cookie(default=None)):
    """Crée un ticket GLPI au nom de l'utilisateur connecté. N'est appelé
    qu'après confirmation dans l'interface : le chatbot ne crée jamais de
    ticket de lui-même."""
    if not glpi.est_configure():
        raise HTTPException(
            status_code=503,
            detail="La création de tickets n'est pas activée (GLPI non "
                   "configuré dans .env).",
        )
    session = _exiger_session(chatbot_session)
    utilisateur = session["utilisateur"]["login"]
    question = payload.question.strip()
    try:
        resultat = glpi.creer_ticket(session["session_token"],
                                     session["utilisateur"]["id"],
                                     question, payload.precisions)
    except glpi.SessionExpiree as erreur:
        _sessions.pop(chatbot_session, None)
        raise HTTPException(status_code=401, detail=str(erreur))
    except glpi.ErreurGLPI as erreur:
        journal.enregistrer("erreur", origine="glpi", utilisateur=utilisateur,
                            question=question, detail=str(erreur))
        # 502 : le problème est entre nous et GLPI, pas dans la requête.
        raise HTTPException(status_code=502, detail=str(erreur))

    journal.enregistrer("ticket", utilisateur=utilisateur, question=question,
                        ticket_id=resultat["id"], url=resultat["url"])
    return resultat


# --- Avis sur les réponses --------------------------------------------------

class Avis(BaseModel):
    """Retour de l'utilisateur sur une réponse : utile ou non, avec un
    commentaire facultatif. Sert à mesurer la qualité perçue."""
    question: str = Field(min_length=1, max_length=2000)
    utile: bool
    commentaire: str = Field(default="", max_length=2000)


@app.post("/avis")
def avis(payload: Avis, chatbot_session: str | None = Cookie(default=None)):
    session = _exiger_session(chatbot_session)
    journal.enregistrer(
        "avis",
        utilisateur=session["utilisateur"]["login"] if session else None,
        question=payload.question.strip(),
        utile=payload.utile,
        commentaire=payload.commentaire.strip(),
    )
    return {"statut": "ok"}


# --- Divers ---------------------------------------------------------------

@app.get("/sante")
def sante():
    """Vérification rapide de la configuration active."""
    return {
        "statut": "ok",
        "modele_llm": config.MODELE_LLM,
        "modele_embeddings": config.MODELE_EMBEDDINGS,
        "seuil_pertinence": config.SEUIL_PERTINENCE,
        "glpi_configure": glpi.est_configure(),
        "glpi_url": config.GLPI_URL or None,
        "connexion_requise": _connexion_requise(),
        "journalisation": config.JOURNALISATION,
    }


# Monté en dernier : cette ligne attrape toutes les autres URL, donc elle doit
# venir après les routes définies ci-dessus.
# Chemin absolu : avec "static" tout court, le serveur ne démarre que si on
# le lance depuis la racine du projet.
app.mount("/", StaticFiles(directory=str(config.RACINE / "static"), html=True),
          name="static")
