"""
Étape 2 : répondre à une question à partir du corpus (le coeur du RAG).

Enchaînement : question -> recherche des extraits les plus proches ->
filtrage par le seuil de pertinence -> rédaction de la réponse par le LLM
-> renvoi de la réponse ET de ses sources.
"""

from langchain_chroma import Chroma
from langchain_ollama import ChatOllama, OllamaEmbeddings

from src import config

# Consigne donnée au modèle. C'est elle qui l'empêche d'inventer :
# on lui interdit explicitement de sortir du contexte fourni.
GABARIT_PROMPT = """Tu es un assistant de support informatique interne.

Réponds à la question en t'appuyant UNIQUEMENT sur le contexte ci-dessous.
Si le contexte ne permet pas de répondre, dis-le clairement et n'invente rien.
Réponds en français, de façon concise et concrète.

Contexte :
{contexte}

Question : {question}

Réponse :"""

MESSAGE_REFUS = (
    "Je n'ai pas trouvé d'information suffisamment proche de votre question "
    "dans la documentation. Je préfère ne pas répondre plutôt que de vous "
    "donner une information inexacte."
)

# On garde la base et le modèle en mémoire : les recharger à chaque question
# serait lent.
_base = None
_llm = None


def _get_base():
    global _base
    if _base is None:
        embeddings = OllamaEmbeddings(
            model=config.MODELE_EMBEDDINGS,
            base_url=config.URL_OLLAMA,
        )
        _base = Chroma(
            persist_directory=str(config.DOSSIER_BASE_VECTORIELLE),
            embedding_function=embeddings,
        )
    return _base


def _get_llm():
    global _llm
    if _llm is None:
        _llm = ChatOllama(
            model=config.MODELE_LLM,
            base_url=config.URL_OLLAMA,
            temperature=0,  # 0 = le plus factuel possible, peu de créativité
        )
    return _llm


def repondre(question: str) -> dict:
    """Renvoie {reponse, sources, refus, meilleur_score}."""
    resultats = _get_base().similarity_search_with_score(
        question, k=config.NOMBRE_EXTRAITS
    )

    if not resultats:
        return {"reponse": MESSAGE_REFUS, "sources": [], "refus": True,
                "meilleur_score": None}

    # ATTENTION : ici le score est une DISTANCE. Plus il est bas, plus
    # l'extrait est proche de la question.
    meilleur_score = resultats[0][1]
    retenus = [(doc, score) for doc, score in resultats
               if score <= config.SEUIL_PERTINENCE]

    if not retenus:
        # Aucun extrait assez proche : on refuse plutôt que d'halluciner.
        return {"reponse": MESSAGE_REFUS, "sources": [], "refus": True,
                "meilleur_score": float(meilleur_score)}

    contexte = "\n\n---\n\n".join(doc.page_content for doc, _ in retenus)
    prompt = GABARIT_PROMPT.format(contexte=contexte, question=question)
    # Mistral commence souvent sa réponse par un espace ou un saut de ligne.
    reponse = _get_llm().invoke(prompt).content.strip()

    sources = []
    deja_vues = set()
    for doc, score in retenus:
        cle = (doc.metadata.get("source"), doc.metadata.get("page"))
        if cle in deja_vues:
            continue  # même page déjà citée par un extrait plus proche
        deja_vues.add(cle)
        source = {
            "document": doc.metadata.get("source", "inconnu"),
            "page": doc.metadata.get("page"),
            "score": round(float(score), 3),
            "extrait": (doc.page_content[:300] + "..."
                        if len(doc.page_content) > 300
                        else doc.page_content),
        }
        sources.append(source)

    return {"reponse": reponse, "sources": sources, "refus": False,
            "meilleur_score": float(meilleur_score)}


if __name__ == "__main__":
    # Test rapide en ligne de commande : python -m src.rag
    while True:
        question = input("\nQuestion (vide pour quitter) : ").strip()
        if not question:
            break
        resultat = repondre(question)
        print(f"\n{resultat['reponse']}")
        for source in resultat["sources"]:
            print(f"  - {source['document']} (score {source['score']})")
