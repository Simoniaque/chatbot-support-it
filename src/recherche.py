"""
Recherche hybride : vecteurs (ChromaDB) et mots-clés, fusionnés.

Pourquoi les deux : la recherche vectorielle compare des sens, et rate les
questions dont le vocabulaire diffère du document. « Comment installer
Photoshop ? » ne trouvait pas le passage « Photoshop […] est hors catalogue »
(distance 0.965, au-delà du seuil) alors que le mot y est. La recherche par
mots-clés, elle, ne comprend pas les synonymes mais ne rate jamais un mot
rare. Les vecteurs classent ; quand ils ne trouvent rien d'assez proche,
les mots-clés repêchent ce qui contient un mot rare de la question.

L'index par mots-clés est écrit ici plutôt qu'importé : le corpus tient
en mémoire, et ça évite une dépendance. Le score d'un morceau est la somme
des poids (idf) des mots de la question qu'il contient : un mot rare dans le
corpus pèse lourd, un mot courant presque rien. On ne compte pas les
répétitions (comme le ferait BM25) : pour une question courte, un morceau
qui répète cinq fois « installer » ne doit pas battre celui qui contient
une fois « Photoshop ».
"""

import math
import re
import unicodedata
from collections import Counter

from langchain_core.documents import Document

from src import config

# Mots trop fréquents pour aider à retrouver un passage.
MOTS_VIDES = set("""
le la les l un une des du de d et ou où à a au aux en dans sur sous par pour
avec sans ce cet cette ces se sa son ses mon ma mes ton ta tes leur leurs notre
nos votre vos je tu il elle on nous vous ils elles me te lui y ne pas plus
que qui quoi dont quel quelle quels quelles est sont être été suis es sommes
êtes ai as avons avez ont avoir fait faire faut peut peux pouvez comment
pourquoi quand combien si oui non mais donc car ni or très tout tous toute
toutes autre autres même aussi encore bien après avant chez vers entre
moi toi soi merci bonjour beaucoup peu svp
""".split())

# Un mot est « rare » s'il apparaît dans moins de cette fraction des morceaux.
# Un morceau qui contient un mot rare de la question est examiné même si sa
# distance vectorielle dépasse le seuil : le mot lui-même est un indice fort,
# et la vérification par extrait tranche ensuite.
FRACTION_MOT_RARE = 0.01

# Nombre maximal de morceaux que les mots-clés peuvent ajouter aux résultats
# vectoriels. Ils prennent la place des derniers candidats vectoriels, jamais
# des premiers.
AJOUTS_MOTS_CLES = 2


def tokeniser(texte: str) -> list[str]:
    """Minuscules, accents retirés, mots de 3 lettres et plus, sans mots vides."""
    texte = unicodedata.normalize("NFKD", texte.lower())
    texte = "".join(c for c in texte if not unicodedata.combining(c))
    return [m for m in re.findall(r"[a-z0-9]+", texte)
            if len(m) >= 3 and m not in MOTS_VIDES]


class IndexMotsCles:
    """Index par mots-clés sur des morceaux {identifiant: texte}."""

    def __init__(self, morceaux: dict[str, str]):
        self.identifiants = list(morceaux)
        self.mots = [set(tokeniser(t)) for t in morceaux.values()]
        # Nombre de morceaux contenant chaque mot.
        self.documents_par_mot = Counter()
        for m in self.mots:
            self.documents_par_mot.update(m)
        self.nombre = len(self.identifiants)

    def idf(self, mot: str) -> float:
        n = self.documents_par_mot.get(mot, 0)
        return math.log(1 + (self.nombre - n + 0.5) / (n + 0.5))

    def est_rare(self, mot: str) -> bool:
        n = self.documents_par_mot.get(mot, 0)
        return 0 < n <= max(1, int(self.nombre * FRACTION_MOT_RARE))

    def chercher(self, question: str, k: int) -> list[tuple[str, float, set]]:
        """Les k meilleurs morceaux : (identifiant, score, mots rares trouvés)."""
        mots = set(tokeniser(question))
        resultats = []
        for i, presents in enumerate(self.mots):
            communs = mots & presents
            if not communs:
                continue
            score = sum(self.idf(mot) for mot in communs)
            rares = {mot for mot in communs if self.est_rare(mot)}
            resultats.append((self.identifiants[i], score, rares))
        resultats.sort(key=lambda r: r[1], reverse=True)
        return resultats[:k]


# --- Index en cache, reconstruit quand la base change ------------------------

_index = None
_index_taille = None


def index_mots_cles(base) -> IndexMotsCles:
    """L'index sur le contenu actuel de la base. Reconstruit si le nombre de
    morceaux a changé (après une ingestion) : quelques millisecondes pour
    quelques centaines de morceaux."""
    global _index, _index_taille
    taille = base._collection.count()
    if _index is None or taille != _index_taille:
        tout = base.get(include=["documents"])
        _index = IndexMotsCles(dict(zip(tout["ids"], tout["documents"])))
        _index_taille = taille
    return _index


def _distance(a, b) -> float:
    """Distance euclidienne au carré : celle que ChromaDB renvoie (`l2`)."""
    return float(sum((x - y) ** 2 for x, y in zip(a, b)))


def chercher(base, question: str, k: int) -> list[dict]:
    """Recherche hybride : les vecteurs classent, les mots-clés repêchent.

    Renvoie au plus k candidats {"doc", "distance", "via", "mots_rares"}.
    Les k meilleurs morceaux par distance vectorielle forment la base. Les
    mots-clés n'interviennent que si aucun d'eux ne passe le seuil de
    pertinence : un morceau contenant un mot rare de la question est alors
    ajouté (au plus AJOUTS_MOTS_CLES), à la place des derniers candidats.
    Deux autres règles ont été essayées et écartées : la fusion à égalité des
    deux classements (rang réciproque), puis l'ajout systématique des mots
    rares — dans les deux cas, des morceaux sémantiquement très loin
    évinçaient de bons candidats vectoriels (« fonctionne » ou « monde »
    sont rares dans un petit corpus sans rien apporter).
    Sans RECHERCHE_HYBRIDE : vecteurs seuls.
    """
    candidats = [{"doc": doc, "distance": float(distance), "via": "vecteur",
                  "mots_rares": set()}
                 for doc, distance in base.similarity_search_with_score(question, k=k)]
    if not config.RECHERCHE_HYBRIDE:
        return candidats

    presents = {c["doc"].id: c for c in candidats}
    vecteurs_suffisants = any(c["distance"] <= config.SEUIL_PERTINENCE for c in candidats)
    ajouts = []
    for ident, _, rares in index_mots_cles(base).chercher(question, k=max(2 * k, 8)):
        if ident in presents:
            presents[ident]["via"] = "les deux"
            presents[ident]["mots_rares"] |= rares
        elif rares and not vecteurs_suffisants and len(ajouts) < AJOUTS_MOTS_CLES:
            ajouts.append((ident, rares))

    if ajouts:
        # Morceaux trouvés par les mots-clés seulement : on calcule leur
        # distance vectorielle nous-mêmes, à partir des vecteurs stockés.
        tout = base.get(ids=[i for i, _ in ajouts],
                        include=["documents", "metadatas", "embeddings"])
        vecteur_question = base.embeddings.embed_query(question)
        rares_par_id = dict(ajouts)
        nouveaux = [{"doc": Document(page_content=texte, metadata=meta, id=ident),
                     "distance": _distance(vecteur_question, emb),
                     "via": "mots-clés", "mots_rares": set(rares_par_id[ident])}
                    for ident, texte, meta, emb in zip(tout["ids"], tout["documents"],
                                                       tout["metadatas"], tout["embeddings"])]
        candidats = candidats[:max(0, k - len(nouveaux))] + nouveaux
    return candidats
