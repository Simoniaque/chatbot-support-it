"""
Étape 2 : répondre à une question à partir du corpus (le coeur du RAG).

Enchaînement : question -> recherche des extraits les plus proches ->
filtrage par le seuil de pertinence -> rédaction de la réponse par le LLM
-> renvoi de la réponse ET de ses sources.
"""

import re

from langchain_chroma import Chroma
from langchain_ollama import ChatOllama, OllamaEmbeddings

from src import config

# Mot-clé que le modèle doit renvoyer, seul, quand le contexte ne répond pas
# à la question. Le code le détecte et le transforme en refus. Plus fiable
# qu'une consigne en langage naturel : la campagne du 20/09/2026 a montré que
# « dis-le clairement et n'invente rien » n'empêche pas Mistral 7B d'enchaîner
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

# Vérification extrait / question, pour la zone grise du seuil. Question
# fermée, réponse en un mot : appel court, et facile à interpréter.
GABARIT_VERIFICATION = """Voici un extrait de documentation et une question.

Extrait :
{extrait}

Question : {question}

L'extrait contient-il des informations qui répondent à cette question, même
partiellement ? Réponds uniquement par OUI ou par NON."""

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


_juge = None


def _get_juge():
    global _juge
    if _juge is None:
        if config.MODELE_JUGE == config.MODELE_LLM:
            _juge = _get_llm()
        else:
            _juge = ChatOllama(model=config.MODELE_JUGE,
                               base_url=config.URL_OLLAMA, temperature=0)
    return _juge


def _extrait_pertinent(question: str, extrait: str) -> bool:
    """Demande au modèle juge si l'extrait répond à la question (OUI/NON)."""
    prompt = GABARIT_VERIFICATION.format(extrait=extrait, question=question)
    verdict = _get_juge().invoke(prompt).content.strip().upper()
    return verdict.startswith("OUI")


def extrait_lisible(texte: str, longueur: int = 300) -> str:
    """Aperçu d'un morceau pour l'interface : syntaxe Markdown retirée
    (titres, gras, citations, code, tableaux), espaces normalisés, coupé à
    `longueur` caractères. Le texte envoyé au modèle, lui, n'est pas touché."""
    texte = re.sub(r"^\s{0,3}#{1,6}\s+", "", texte, flags=re.M)      # titres
    texte = re.sub(r"^\s{0,3}>\s?", "", texte, flags=re.M)           # citations
    texte = re.sub(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$",
                   "", texte, flags=re.M)                            # lignes |---|---|
    texte = texte.replace("|", " ")                                   # cellules
    texte = re.sub(r"(\*\*|__|`+)", "", texte)                        # gras, code
    texte = re.sub(r"^\s*[-*]\s+", "• ", texte, flags=re.M)          # puces
    texte = re.sub(r"[ \t]+", " ", texte)
    texte = re.sub(r"\s*\n\s*", " ", texte).strip()
    return texte[:longueur] + "..." if len(texte) > longueur else texte


def repondre(question: str) -> dict:
    """Renvoie {reponse, sources, refus, motif_refus, meilleur_score}.

    motif_refus : "seuil" (meilleur extrait trop loin), "verification" (les
    extraits de la zone grise ont tous été jugés hors sujet un par un),
    "modele" (le modèle a jugé, en rédigeant, que le contexte ne répond pas),
    ou None.
    """
    resultats = _get_base().similarity_search_with_score(
        question, k=config.NOMBRE_EXTRAITS
    )

    if not resultats:
        return {"reponse": MESSAGE_REFUS, "sources": [], "refus": True,
                "motif_refus": "seuil", "meilleur_score": None,
                "extraits_verifies": 0, "extraits_ecartes": 0}

    # ATTENTION : ici le score est une DISTANCE. Plus il est bas, plus
    # l'extrait est proche de la question.
    meilleur_score = resultats[0][1]

    if meilleur_score > config.SEUIL_PERTINENCE:
        # Même le meilleur extrait est trop loin : on refuse plutôt que
        # d'halluciner.
        return {"reponse": MESSAGE_REFUS, "sources": [], "refus": True,
                "motif_refus": "seuil", "meilleur_score": float(meilleur_score),
                "extraits_verifies": 0, "extraits_ecartes": 0}

    # Deux seuils distincts : SEUIL_PERTINENCE décide si on répond (sur le
    # meilleur extrait), SEUIL_CONTEXTE décide quels extraits suivants
    # accompagnent le meilleur. Avec un seul seuil, une question acceptée de
    # justesse n'avait plus qu'un extrait de contexte et sa réponse se
    # dégradait (campagne 3 du jeu de test).
    retenus = [(doc, score) for doc, score in resultats
               if score <= config.SEUIL_CONTEXTE]

    # Troisième filtre : la distance mesure une proximité de vocabulaire,
    # pas la capacité d'un extrait à répondre (campagne 6 du jeu de test :
    # « ajouter un utilisateur » a un score de 0.416 et aucun extrait utile).
    # Chaque extrait dont le score dépasse SEUIL_VERIFICATION est soumis au
    # modèle juge (« cet extrait répond-il ? OUI/NON ») ; seuls les OUI sont
    # envoyés au rédacteur, et s'il n'en reste aucun on refuse. Un extrait
    # sans rapport dans le contexte est ce qui pousse le rédacteur à
    # inventer : mieux vaut un contexte court qu'un contexte pollué.
    # Coût : un appel court par extrait vérifié.
    verifies = 0
    ecartes = 0
    pertinents = []
    for doc, score in retenus:
        if score > config.SEUIL_VERIFICATION:
            verifies += 1
            if not _extrait_pertinent(question, doc.page_content):
                ecartes += 1
                continue
        pertinents.append((doc, score))
    retenus = pertinents

    if not retenus:
        return {"reponse": MESSAGE_REFUS, "sources": [], "refus": True,
                "motif_refus": "verification",
                "meilleur_score": float(meilleur_score),
                "extraits_verifies": verifies, "extraits_ecartes": ecartes}

    contexte = "\n\n---\n\n".join(doc.page_content for doc, _ in retenus)
    prompt = GABARIT_PROMPT.format(contexte=contexte, question=question)
    # Certains modèles commencent leur réponse par un espace ou un saut de ligne.
    reponse = _get_llm().invoke(prompt).content.strip()

    # Second filtre, après le seuil : le modèle a jugé que les extraits
    # (pourtant assez proches) ne répondent pas à la question.
    if MARQUEUR_HORS_CONTEXTE in reponse.upper():
        return {"reponse": MESSAGE_REFUS, "sources": [], "refus": True,
                "motif_refus": "modele",
                "meilleur_score": float(meilleur_score),
                "extraits_verifies": verifies, "extraits_ecartes": ecartes}

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
            "extrait": extrait_lisible(doc.page_content),
        }
        sources.append(source)

    return {"reponse": reponse, "sources": sources, "refus": False,
            "motif_refus": None, "meilleur_score": float(meilleur_score),
            "extraits_verifies": verifies, "extraits_ecartes": ecartes}


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
