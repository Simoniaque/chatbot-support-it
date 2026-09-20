"""
Étape 3 : exposer le chatbot via une API et une page web.

Deux livrables du cahier des charges en un seul fichier :
 - l'API      : POST /ask, réutilisable par un autre outil (GLPI plus tard) ;
 - l'interface: la page statique servie sur /.

À lancer :  uvicorn src.api:app --reload
Puis ouvrir http://localhost:8000
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src import config, rag

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


class Question(BaseModel):
    """Décrit ce que l'API attend en entrée : {"question": "..."}"""
    # min_length : une question vide n'a pas de sens, FastAPI renvoie
    # une erreur 422 avant même d'appeler le RAG.
    question: str = Field(min_length=1, max_length=2000)


@app.post("/ask")
def ask(payload: Question):
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="La question est vide.")
    try:
        return rag.repondre(question)
    except ConnectionError:
        # Levée par langchain_ollama quand Ollama ne répond pas. Sans ce
        # bloc, l'utilisateur reçoit une page "Internal Server Error"
        # sans explication.
        raise HTTPException(
            status_code=503,
            detail="Impossible de joindre Ollama. Vérifiez qu'il est lancé "
                   f"(adresse configurée : {config.URL_OLLAMA}).",
        )


@app.get("/sante")
def sante():
    """Vérification rapide de la configuration active."""
    return {
        "statut": "ok",
        "modele_llm": config.MODELE_LLM,
        "modele_embeddings": config.MODELE_EMBEDDINGS,
        "seuil_pertinence": config.SEUIL_PERTINENCE,
    }


# Monté en dernier : cette ligne attrape toutes les autres URL, donc elle doit
# venir après les routes définies ci-dessus.
# Chemin absolu : avec "static" tout court, le serveur ne démarre que si on
# le lance depuis la racine du projet.
app.mount("/", StaticFiles(directory=str(config.RACINE / "static"), html=True),
          name="static")
