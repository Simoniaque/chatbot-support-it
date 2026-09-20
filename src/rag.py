"""
Étape 2 : répondre à une question à partir du corpus (le coeur du RAG).

Enchaînement : question -> recherche des extraits les plus proches ->
filtrage par le seuil de pertinence -> rédaction de la réponse par le LLM
-> renvoi de la réponse ET de ses sources.
"""

from langchain_chroma import Chroma
from langchain_ollama import ChatOllama, OllamaEmbeddings

from src import config

# Mot-clé que le modèle doit renvoyer, seul, quand le contexte ne répond pas
# à la question. Le code le détecte et le transforme en refus. Plus fiable
# qu'une consigne en langage naturel : la campagne du 20/09/2026 a montré que
# « dis-le clairement et n'invente rien » n'empêche pas Mistral d'enchaîner
# par « Cependant, voici comment faire... » avec ses propres connaissances.
MARQUEUR_HORS_CONTEXTE = "HORS_CONTEXTE"

# Consigne donnée au modèle. C'est elle qui l'empêche d'inventer :
# on lui interdit explicitement de sortir du contexte fourni.
GABARIT_PROMPT = """Tu es un assistant de support informatique interne.

Règles, dans l'ordre :
1. Tu réponds UNIQUEMENT à partir du contexte ci-dessous. Tes connaissances
   générales ne comptent pas : si une information n'est pas dans le contexte,
   elle n'existe pas. N'invente jamais de commande, de menu ou d'étape.
2. Si le contexte contient de quoi répondre, même partiellement, réponds en
   français, de façon concise et concrète, avec ce que dit le contexte et
   rien de plus.
3. Si le contexte ne parle pas du tout du sujet de la question, ta réponse
   est exactement le mot HORS_CONTEXTE, et rien d'autre : pas d'explication,
   pas de conseil général, pas de « cependant ».

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
    """Renvoie {reponse, sources, refus, motif_refus, meilleur_score}.

    motif_refus : "seuil" (aucun extrait assez proche), "modele" (extraits
    proches mais le modèle a jugé qu'ils ne répondent pas), ou None.
    """
    resultats = _get_base().similarity_search_with_score(
        question, k=config.NOMBRE_EXTRAITS
    )

    if not resultats:
        return {"reponse": MESSAGE_REFUS, "sources": [], "refus": True,
                "motif_refus": "seuil", "meilleur_score": None}

    # ATTENTION : ici le score est une DISTANCE. Plus il est bas, plus
    # l'extrait est proche de la question.
    meilleur_score = resultats[0][1]
    retenus = [(doc, score) for doc, score in resultats
               if score <= config.SEUIL_PERTINENCE]

    if not retenus:
        # Aucun extrait assez proche : on refuse plutôt que d'halluciner.
        return {"reponse": MESSAGE_REFUS, "sources": [], "refus": True,
                "motif_refus": "seuil", "meilleur_score": float(meilleur_score)}

    contexte = "\n\n---\n\n".join(doc.page_content for doc, _ in retenus)
    prompt = GABARIT_PROMPT.format(contexte=contexte, question=question)
    # Mistral commence souvent sa réponse par un espace ou un saut de ligne.
    reponse = _get_llm().invoke(prompt).content.strip()

    # Second filtre, après le seuil : le modèle a jugé que les extraits
    # (pourtant assez proches) ne répondent pas à la question.
    if MARQUEUR_HORS_CONTEXTE in reponse.upper():
        return {"reponse": MESSAGE_REFUS, "sources": [], "refus": True,
                "motif_refus": "modele",
                "meilleur_score": float(meilleur_score)}

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
            "motif_refus": None, "meilleur_score": float(meilleur_score)}


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
