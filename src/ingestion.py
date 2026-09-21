"""
Étape 1 du projet : transformer les documents du corpus en base vectorielle.

Enchaînement : lire les fichiers -> découper en morceaux -> calculer les
embeddings -> stocker dans ChromaDB.

À lancer depuis la racine du projet :  python -m src.ingestion
À relancer à chaque fois que le corpus change : seuls les morceaux nouveaux
sont calculés, les autres sont reconnus et ignorés, et les morceaux des
fichiers modifiés ou retirés sont supprimés (voir identifiant()).
"""

import hashlib
import time

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src import config

# Lecteurs de fichiers, écrits ici plutôt qu'importés de langchain-community
# (paquet en fin de vie). Chacun renvoie une liste de Document : un par page
# pour un PDF (avec son numéro, à partir de 0, pour citer la source), un
# seul pour un fichier texte.

def lire_pdf(chemin):
    return [Document(page_content=page.extract_text() or "",
                     metadata={"page": numero})
            for numero, page in enumerate(PdfReader(chemin).pages)]


def lire_texte(chemin):
    """UTF-8 d'abord : lu avec l'encodage par défaut de Windows (cp1252), un
    fichier UTF-8 voit ses accents devenir « Ã© », ce qui pollue les
    embeddings et dégrade la recherche. Repli cp1252 pour un vieux fichier."""
    try:
        texte = chemin.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        texte = chemin.read_text(encoding="cp1252")
    # Pas de numéro de page : un fichier texte n'en a pas, et l'interface
    # n'affiche alors que le nom du fichier.
    return [Document(page_content=texte, metadata={})]


# Quel lecteur utiliser selon l'extension du fichier.
LECTEURS = {
    ".pdf": lire_pdf,
    ".txt": lire_texte,
    ".md": lire_texte,
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
            pages = lecteur(chemin)
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


def identifiant(morceau):
    """Identifiant stable d'un morceau : empreinte du fichier, de la page et
    du texte. Relancer l'ingestion sur un corpus inchangé ne crée donc pas de
    doublons, et un fichier ajouté ne coûte que ses propres morceaux. La page
    fait partie de l'empreinte parce qu'un PDF répète souvent le même texte
    (en-têtes, pieds de page) sur plusieurs pages."""
    contenu = (f"{morceau.metadata.get('source', '')}\n"
               f"{morceau.metadata.get('page', '')}\n{morceau.page_content}")
    return hashlib.sha1(contenu.encode("utf-8")).hexdigest()


def ecarter_deja_indexes(base, morceaux):
    """Renvoie les morceaux absents de la base, et le nombre d'ignorés
    (déjà indexés, ou doublons stricts dans le corpus lui-même)."""
    uniques = {}
    for m in morceaux:
        uniques.setdefault(identifiant(m), m)
    identifiants = list(uniques)
    presents = set()
    for debut in range(0, len(identifiants), 500):
        presents.update(base.get(ids=identifiants[debut:debut + 500])["ids"])
    nouveaux = [m for i, m in uniques.items() if i not in presents]
    return nouveaux, len(morceaux) - len(nouveaux)


def purger_obsoletes(base, morceaux):
    """Supprime de la base les morceaux qui ne correspondent plus au corpus :
    fichier modifié (ses anciens morceaux ont d'autres identifiants) ou
    fichier retiré de data/corpus. Renvoie le nombre supprimé."""
    actuels = {identifiant(m) for m in morceaux}
    existants = base.get(include=[])["ids"]
    obsoletes = [i for i in existants if i not in actuels]
    for debut in range(0, len(obsoletes), 500):
        base.delete(ids=obsoletes[debut:debut + 500])
    return len(obsoletes)


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

    supprimes = purger_obsoletes(base, morceaux)
    if supprimes:
        print(f"  {supprimes} morceau(x) obsolète(s) supprimé(s) de la base")
    morceaux, ignores = ecarter_deja_indexes(base, morceaux)
    if ignores:
        print(f"  {ignores} morceau(x) déjà dans la base, ignoré(s)")
    if not morceaux:
        return 0, 0, ignores

    total = len(morceaux)
    traites = 0
    echecs = 0

    for debut in range(0, total, TAILLE_LOT):
        lot = morceaux[debut:debut + TAILLE_LOT]

        for tentative in range(1, TENTATIVES_MAX + 1):
            try:
                base.add_documents(lot, ids=[identifiant(m) for m in lot])
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

    return traites, echecs, ignores


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
    traites, echecs, ignores = indexer(morceaux)

    print(f"\nTerminé : {traites} morceau(x) indexé(s), {ignores} déjà présent(s), "
          f"{echecs} en échec.")
    print(f"Base vectorielle : {config.DOSSIER_BASE_VECTORIELLE}")
    if echecs:
        print("Des lots ont échoué. Réduis TAILLE_LOT en haut de ce fichier "
              "(32 -> 8) et relance.")


if __name__ == "__main__":
    main()