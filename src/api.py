"""
Étape 3 : exposer le chatbot via une API et une page web.

Deux livrables du cahier des charges en un seul fichier :
 - l'API      : POST /ask, réutilisable par un autre outil (GLPI plus tard) ;
 - l'interface: la page statique servie sur /.

À lancer :  uvicorn src.api:app --reload
Puis ouvrir http://localhost:8000
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src import config, rag

app = FastAPI(title="Chatbot Support IT")


class Question(BaseModel):
    """Décrit ce que l'API attend en entrée : {"question": "..."}"""
    question: str


@app.post("/ask")
def ask(payload: Question):
    return rag.repondre(payload.question)


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
app.mount("/", StaticFiles(directory="static", html=True), name="static")
