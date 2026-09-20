"""
Dialogue avec GLPI via son API REST : connexion des utilisateurs et
création de tickets.

Principe : l'utilisateur se connecte au chatbot avec ses identifiants GLPI.
Le chatbot ouvre une session GLPI en son nom et la garde côté serveur. Quand
le chatbot ne trouve pas de réponse et que l'utilisateur confirme, le ticket
est créé avec cette session : dans GLPI, il apparaît comme créé par
l'utilisateur lui-même, qui en est le demandeur. Aucune base d'utilisateurs
propre au chatbot : GLPI reste la seule référence.

Appels utilisés :
  GET  /apirest.php/initSession     (Authorization: Basic login:mdp) -> session
  GET  /apirest.php/getFullSession  -> identité de l'utilisateur connecté
  POST /apirest.php/Ticket          -> {"id": ..}
  GET  /apirest.php/killSession

Prérequis côté GLPI (Configuration > Générale > API) :
  - activer l'API REST ;
  - activer la connexion avec identifiants (login/mot de passe) ;
  - un client API avec un App-Token, sans restriction d'adresse IP.
"""

import base64
import html

import httpx

from src import config

# Types de ticket GLPI. Une question sans réponse est une demande, pas une
# panne : on l'ouvre en "Demande" par défaut.
TYPE_INCIDENT = 1
TYPE_DEMANDE = 2

DELAI_SECONDES = 15


class ErreurGLPI(Exception):
    """GLPI injoignable, jetons refusés, ou création de ticket échouée."""


class SessionExpiree(ErreurGLPI):
    """La session GLPI n'est plus valide : l'utilisateur doit se reconnecter."""


class IdentifiantsRefuses(ErreurGLPI):
    """Login ou mot de passe incorrect."""


def est_configure() -> bool:
    """Vrai si GLPI est renseigné dans .env (adresse et jeton d'application)."""
    return bool(config.GLPI_URL and config.GLPI_APP_TOKEN)


def _url(point_entree: str) -> str:
    return f"{config.GLPI_URL.rstrip('/')}/apirest.php/{point_entree}"


def _entetes(session_token: str | None = None) -> dict:
    entetes = {"App-Token": config.GLPI_APP_TOKEN,
               "Content-Type": "application/json"}
    if session_token:
        entetes["Session-Token"] = session_token
    return entetes


def _message_erreur(reponse: httpx.Response) -> str:
    """GLPI renvoie ses erreurs sous la forme ["CODE", "message"]."""
    try:
        corps = reponse.json()
        if isinstance(corps, list) and len(corps) == 2:
            return f"{corps[0]} : {corps[1]}"
        return str(corps)
    except ValueError:
        return reponse.text[:200]


def _code_erreur(reponse: httpx.Response) -> str:
    try:
        corps = reponse.json()
        return corps[0] if isinstance(corps, list) and corps else ""
    except ValueError:
        return ""


def _appeler(methode: str, point_entree: str, session_token: str | None = None,
             **options) -> httpx.Response:
    """Un appel HTTP vers GLPI, avec traduction des erreurs réseau."""
    try:
        with httpx.Client(timeout=DELAI_SECONDES) as client:
            return client.request(methode, _url(point_entree),
                                  headers=_entetes(session_token), **options)
    except httpx.HTTPError as erreur:
        raise ErreurGLPI(f"Impossible de joindre GLPI ({config.GLPI_URL}) : "
                         f"{erreur}") from erreur


# --- Connexion ------------------------------------------------------------

def ouvrir_session(login: str, mot_de_passe: str) -> dict:
    """Authentifie l'utilisateur auprès de GLPI.

    Renvoie {"session_token": .., "utilisateur": {"id", "login", "nom"}}.
    Le mot de passe n'est ni conservé ni journalisé : il ne sert qu'à cet
    appel.
    """
    if not est_configure():
        raise ErreurGLPI("GLPI n'est pas configuré (GLPI_URL et "
                         "GLPI_APP_TOKEN dans .env).")

    identifiants = base64.b64encode(f"{login}:{mot_de_passe}".encode()).decode()
    try:
        with httpx.Client(timeout=DELAI_SECONDES) as client:
            reponse = client.get(
                _url("initSession"),
                headers={**_entetes(), "Authorization": f"Basic {identifiants}"},
            )
    except httpx.HTTPError as erreur:
        raise ErreurGLPI(f"Impossible de joindre GLPI ({config.GLPI_URL}) : "
                         f"{erreur}") from erreur

    if reponse.status_code == 401:
        raise IdentifiantsRefuses("Identifiant ou mot de passe incorrect.")
    if reponse.status_code != 200:
        raise ErreurGLPI("Connexion à GLPI refusée : " + _message_erreur(reponse))
    session_token = reponse.json()["session_token"]

    # Identité de la personne, pour l'afficher et la journaliser.
    reponse = _appeler("GET", "getFullSession", session_token)
    if reponse.status_code != 200:
        raise ErreurGLPI("Lecture de la session GLPI impossible : "
                         + _message_erreur(reponse))
    session = reponse.json().get("session", {})
    prenom = (session.get("glpifirstname") or "").strip()
    nom_famille = (session.get("glpirealname") or "").strip()
    nom_complet = " ".join(p for p in (prenom, nom_famille) if p) or login

    return {
        "session_token": session_token,
        "utilisateur": {
            "id": session.get("glpiID"),
            "login": session.get("glpiname") or login,
            "nom": nom_complet,
        },
    }


def fermer_session(session_token: str) -> None:
    """Ferme la session GLPI. Silencieux : une session déjà expirée n'est
    pas une erreur pour l'utilisateur."""
    try:
        _appeler("GET", "killSession", session_token)
    except ErreurGLPI:
        pass


# --- Tickets --------------------------------------------------------------

def _contenu_ticket(question: str, precisions: str) -> str:
    """Corps du ticket. GLPI attend du HTML : on échappe le texte saisi."""
    parties = [
        "<p><b>Question posée au chatbot de support :</b></p>",
        f"<p>{html.escape(question)}</p>",
        "<p><i>Le chatbot n'a trouvé aucune réponse dans la documentation "
        "interne. Ticket créé à la demande de l'utilisateur.</i></p>",
    ]
    if precisions.strip():
        parties.append("<p><b>Précisions :</b></p>")
        parties.append("<p>" + html.escape(precisions.strip())
                       .replace("\n", "<br>") + "</p>")
    return "".join(parties)


def creer_ticket(session_token: str, utilisateur_id: int, question: str,
                 precisions: str = "") -> dict:
    """Crée un ticket avec la session de l'utilisateur connecté, qui en
    devient le demandeur.

    Renvoie {"id": .., "url": ..}. Lève SessionExpiree si GLPI ne reconnaît
    plus la session, ErreurGLPI pour tout autre échec.
    """
    # Titre limité : GLPI tronque de toute façon, et la question complète
    # est dans le contenu.
    titre = question.strip().replace("\n", " ")
    if len(titre) > 120:
        titre = titre[:117] + "..."

    reponse = _appeler("POST", "Ticket", session_token, json={"input": {
        "name": titre,
        "content": _contenu_ticket(question, precisions),
        "type": TYPE_DEMANDE,
        # Via l'API, GLPI n'ajoute pas de lui-même l'utilisateur comme
        # demandeur (contrairement à l'interface web) : on le précise.
        "_users_id_requester": utilisateur_id,
    }})

    if reponse.status_code == 401 or _code_erreur(reponse) == "ERROR_SESSION_TOKEN_INVALID":
        raise SessionExpiree("Votre session GLPI a expiré, reconnectez-vous.")
    if reponse.status_code != 201:
        raise ErreurGLPI("Création du ticket refusée : " + _message_erreur(reponse))

    identifiant = reponse.json()["id"]
    return {
        "id": identifiant,
        "url": f"{config.GLPI_URL.rstrip('/')}/front/ticket.form.php?id={identifiant}",
    }
