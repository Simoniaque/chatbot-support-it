"""
Création de tickets dans GLPI via son API REST.

Cas d'usage : le chatbot n'a pas trouvé de réponse dans la documentation.
Plutôt que de laisser l'utilisateur sans rien, on lui propose d'ouvrir un
ticket auprès du support, pré-rempli avec sa question. Le ticket n'est créé
qu'après confirmation explicite de sa part (bouton dans l'interface).

Enchaînement côté GLPI (trois appels HTTP) :
  1. GET  /apirest.php/initSession  -> jeton de session
  2. POST /apirest.php/Ticket       -> {"id": ..}
  3. GET  /apirest.php/killSession

Prérequis côté GLPI (Configuration > Générale > API) :
  - activer l'API REST ;
  - créer un client API -> App-Token ;
  - sur un utilisateur dédié (ex. "chatbot"), générer un jeton d'API
    personnel -> User-Token. Ce compte sera le demandeur des tickets.
"""

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


def est_configure() -> bool:
    """Vrai si les trois réglages GLPI sont renseignés dans .env."""
    return bool(config.GLPI_URL and config.GLPI_APP_TOKEN
                and config.GLPI_USER_TOKEN)


def _url(point_entree: str) -> str:
    return f"{config.GLPI_URL.rstrip('/')}/apirest.php/{point_entree}"


def _message_erreur(reponse: httpx.Response) -> str:
    """GLPI renvoie ses erreurs sous la forme ["CODE", "message"]."""
    try:
        corps = reponse.json()
        if isinstance(corps, list) and len(corps) == 2:
            return f"{corps[0]} : {corps[1]}"
        return str(corps)
    except ValueError:
        return reponse.text[:200]


def _contenu_ticket(question: str, precisions: str, demandeur: str) -> str:
    """Corps du ticket. GLPI attend du HTML : on échappe le texte saisi."""
    parties = [
        "<p><b>Question posée au chatbot de support :</b></p>",
        f"<p>{html.escape(question)}</p>",
        "<p><i>Le chatbot n'a trouvé aucune réponse dans la documentation "
        "interne. Ticket créé à la demande de l'utilisateur.</i></p>",
    ]
    if precisions.strip():
        parties.append("<p><b>Précisions de l'utilisateur :</b></p>")
        parties.append("<p>" + html.escape(precisions.strip())
                       .replace("\n", "<br>") + "</p>")
    if demandeur.strip():
        parties.append(f"<p><b>Contact :</b> {html.escape(demandeur.strip())}</p>")
    return "".join(parties)


def creer_ticket(question: str, precisions: str = "", demandeur: str = "") -> dict:
    """Crée un ticket GLPI et renvoie {"id": .., "url": ..}.

    Lève ErreurGLPI avec un message lisible si quelque chose échoue.
    """
    if not est_configure():
        raise ErreurGLPI("GLPI n'est pas configuré (GLPI_URL, GLPI_APP_TOKEN "
                         "et GLPI_USER_TOKEN dans .env).")

    entetes = {
        "App-Token": config.GLPI_APP_TOKEN,
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=DELAI_SECONDES) as client:
            # 1. Ouverture de session
            reponse = client.get(
                _url("initSession"),
                headers={**entetes,
                         "Authorization": f"user_token {config.GLPI_USER_TOKEN}"},
            )
            if reponse.status_code != 200:
                raise ErreurGLPI("Connexion à GLPI refusée : "
                                 + _message_erreur(reponse))
            entetes["Session-Token"] = reponse.json()["session_token"]

            try:
                # 2. Création du ticket
                # Titre limité : GLPI tronque de toute façon, et la question
                # complète est dans le contenu.
                titre = question.strip().replace("\n", " ")
                if len(titre) > 120:
                    titre = titre[:117] + "..."
                reponse = client.post(
                    _url("Ticket"),
                    headers=entetes,
                    json={"input": {
                        "name": titre,
                        "content": _contenu_ticket(question, precisions, demandeur),
                        "type": TYPE_DEMANDE,
                    }},
                )
                if reponse.status_code != 201:
                    raise ErreurGLPI("Création du ticket refusée : "
                                     + _message_erreur(reponse))
                identifiant = reponse.json()["id"]
            finally:
                # 3. Fermeture de session, même si la création a échoué :
                # GLPI limite le nombre de sessions ouvertes.
                client.get(_url("killSession"), headers=entetes)

    except httpx.HTTPError as erreur:
        raise ErreurGLPI(f"Impossible de joindre GLPI ({config.GLPI_URL}) : "
                         f"{erreur}") from erreur

    return {
        "id": identifiant,
        "url": f"{config.GLPI_URL.rstrip('/')}/front/ticket.form.php?id={identifiant}",
    }
