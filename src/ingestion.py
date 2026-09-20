"""
Étape 1 du projet : transformer les documents du corpus en base vectorielle.

Enchaînement : lire les fichiers -> découper en morceaux -> calculer les
embeddings -> stocker dans ChromaDB.

À lancer depuis la racine du projet :  python -m src.ingestion
À relancer à chaque fois que le corpus change.
"""

import time

from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src import config

# Quel lecteur utiliser selon l'extension du fichier.
LECTEURS = {
    ".pdf": PyPDFLoader,
    ".txt": TextLoader,
    ".md": TextLoader,
}

# Nombre de morceaux envoyés à Ollama en une seule fois.
# Tout envoyer d'un bloc fait tomber le moteur d'Ollama sur un gros corpus :
# il traite chaque lot en mémoire. Un lot plus petit est plus lent mais tient
# toujours. Si l'erreur "connection refused" revient, descendre à 8, puis à 4.
TAILLE_LOT = 32

# Nombre de tentatives par lot. Quand le moteur d'Ollama redémarre, la requête
# suivante échoue le temps qu'il se relance : on réessaie au lieu de tout perdre.
TENTATIVES_MAX = 3


def charger_documents():
    """Lit tous les fichiers reconnus du dossier data/corpus."""
    documents = []
    for chemin in sorted(config.DOSSIER_CORPUS.rglob("*")):
        if not chemin.is_file():
            continue
        lecteur = LECTEURS.get(chemin.suffix.lower())
        if lecteur is None:
            print(f"  ignoré (format non géré) : {chemin.name}")
            continue
        try:
            pages = lecteur(str(chemin)).load()
        except Exception as erreur:
            print(f"  ERREUR sur {chemin.name} : {erreur}")
            continue
        # Métadonnées : indispensables pour citer la source dans la réponse.
        for page in pages:
            page.metadata["source"] = chemin.name
        documents.extend(pages)
        print(f"  lu : {chemin.name} ({len(pages)} page(s))")
    return documents


def decouper(documents):
    """Coupe les documents en morceaux de taille gérable par le modèle."""
    decoupeur = RecursiveCharacterTextSplitter(
        chunk_size=config.TAILLE_CHUNK,
        chunk_overlap=config.CHEVAUCHEMENT_CHUNK,
        # On coupe en priorité aux paragraphes, puis aux phrases, puis aux
        # mots : on préserve le sens autant que possible.
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    morceaux = decoupeur.split_documents(documents)

    # Un morceau vide ou quasi vide n'apporte rien et peut faire échouer le
    # calcul d'embedding. On les écarte ici plutôt que de les découvrir plus tard.
    return [m for m in morceaux if m.page_content and m.page_content.strip()]


def indexer(morceaux):
    """Calcule les embeddings par lots et les enregistre dans ChromaDB."""
    embeddings = OllamaEmbeddings(
        model=config.MODELE_EMBEDDINGS,
        base_url=config.URL_OLLAMA,
    )
    base = Chroma(
        persist_directory=str(config.DOSSIER_BASE_VECTORIELLE),
        embedding_function=embeddings,
    )

    total = len(morceaux)
    traites = 0
    echecs = 0

    for debut in range(0, total, TAILLE_LOT):
        lot = morceaux[debut:debut + TAILLE_LOT]

        for tentative in range(1, TENTATIVES_MAX + 1):
            try:
                base.add_documents(lot)
                traites += len(lot)
                pourcentage = traites * 100 // total
                print(f"  {traites}/{total} morceaux indexés ({pourcentage} %)")
                break
            except Exception as erreur:
                if tentative == TENTATIVES_MAX:
                    echecs += len(lot)
                    print(f"  LOT ABANDONNÉ après {TENTATIVES_MAX} tentatives "
                          f"(morceaux {debut}-{debut + len(lot)}) : {erreur}")
                else:
                    attente = 5 * tentative  # on laisse le temps à Ollama de repartir
                    print(f"  échec (tentative {tentative}/{TENTATIVES_MAX}), "
                          f"nouvelle tentative dans {attente} s...")
                    time.sleep(attente)

    return traites, echecs


def main():
    print(f"Corpus : {config.DOSSIER_CORPUS}")
    documents = charger_documents()
    if not documents:
        print("Aucun document trouvé. Dépose des fichiers dans data/corpus/.")
        return

    morceaux = decouper(documents)
    print(f"\n{len(documents)} document(s) -> {len(morceaux)} morceau(x)")

    print(f"Calcul des embeddings par lots de {TAILLE_LOT} "
          f"(plusieurs minutes)...")
    traites, echecs = indexer(morceaux)

    print(f"\nTerminé : {traites} morceau(x) indexé(s), {echecs} en échec.")
    print(f"Base vectorielle : {config.DOSSIER_BASE_VECTORIELLE}")
    if echecs:
        print("Des lots ont échoué. Réduis TAILLE_LOT en haut de ce fichier "
              "(32 -> 8) et relance.")


if __name__ == "__main__":
    main()