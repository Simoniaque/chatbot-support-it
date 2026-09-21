"""Recherche hybride (src/recherche.py) : tokenisation, index par mots-clés,
fusion avec les vecteurs, règle du mot rare dans rag.repondre."""

from langchain_core.documents import Document

from src import config, rag, recherche


def test_tokeniser_normalise_et_filtre():
    assert recherche.tokeniser("Comment réinitialiser mon Mot-de-passe Windows ?") == \
        ["reinitialiser", "mot", "passe", "windows"]
    assert recherche.tokeniser("Merci beaucoup !") == []


def test_index_mots_cles_classe_par_poids_des_mots():
    index = recherche.IndexMotsCles({
        "a": "installer installer installer un logiciel",
        "b": "Photoshop est hors catalogue",
        "c": "installer un logiciel du catalogue",
        "d": "texte sans rapport",
    })
    resultats = index.chercher("Comment installer Photoshop ?", k=3)
    identifiants = [r[0] for r in resultats]
    # "photoshop" (1 morceau sur 4) pèse plus que "installer" (2 sur 4) ;
    # les répétitions ne comptent pas.
    assert identifiants[0] == "b"
    assert set(identifiants[1:]) == {"a", "c"}
    assert "d" not in identifiants
    assert resultats[0][2] == {"photoshop"}


def test_mot_rare_selon_la_fraction_de_morceaux():
    morceaux = {str(i): "commun" for i in range(200)}
    morceaux["x"] = "commun et unique"
    index = recherche.IndexMotsCles(morceaux)
    assert index.est_rare("unique") is True
    assert index.est_rare("commun") is False
    assert index.est_rare("absent") is False


class FausseBaseHybride:
    """Doublure de Chroma : recherche vectorielle fixée, morceaux connus."""
    def __init__(self, morceaux, vecteur):
        self.morceaux = morceaux      # {id: (texte, metadata)}
        self.vecteur = vecteur        # [(id, distance)] renvoyés par les vecteurs
        self._collection = type("C", (), {"count": lambda s: len(morceaux)})()
        self.embeddings = type("E", (), {"embed_query": lambda s, q: [1.0, 0.0]})()

    def similarity_search_with_score(self, question, k):
        return [(Document(page_content=self.morceaux[i][0], metadata=self.morceaux[i][1], id=i), d)
                for i, d in self.vecteur[:k]]

    def get(self, ids=None, include=None):
        ids = list(self.morceaux) if ids is None else ids
        return {"ids": ids,
                "documents": [self.morceaux[i][0] for i in ids],
                "metadatas": [self.morceaux[i][1] for i in ids],
                "embeddings": [[0.0, 1.0] for _ in ids]}   # distance 2.0 de la question


def _base_avec_photoshop(vecteur):
    morceaux = {"v1": ("gestion des tickets", {"source": "a.pdf", "page": 1}),
                "v2": ("statut du ticket", {"source": "a.pdf", "page": 2}),
                "m1": ("Photoshop est hors catalogue", {"source": "b.md"})}
    for i in range(150):   # de quoi rendre « photoshop » rare
        morceaux[f"bruit{i}"] = ("texte de remplissage", {"source": "c.pdf", "page": i})
    return FausseBaseHybride(morceaux, vecteur=vecteur)


def test_chercher_repeche_par_mot_rare_quand_les_vecteurs_echouent(monkeypatch):
    monkeypatch.setattr(config, "RECHERCHE_HYBRIDE", True)
    monkeypatch.setattr(config, "SEUIL_PERTINENCE", 0.65)
    monkeypatch.setattr(recherche, "_index", None)
    base = _base_avec_photoshop(vecteur=[("v1", 0.9), ("v2", 0.95)])

    candidats = recherche.chercher(base, "Comment installer Photoshop ?", k=4)
    par_id = {c["doc"].id: c for c in candidats}
    assert par_id["m1"]["via"] == "mots-clés"
    assert par_id["m1"]["mots_rares"] == {"photoshop"}
    assert par_id["m1"]["distance"] == 2.0          # calculée depuis le vecteur stocké
    assert par_id["v1"]["via"] == "vecteur" and par_id["v1"]["distance"] == 0.9


def test_chercher_ne_touche_pas_aux_vecteurs_quand_ils_suffisent(monkeypatch):
    monkeypatch.setattr(config, "RECHERCHE_HYBRIDE", True)
    monkeypatch.setattr(config, "SEUIL_PERTINENCE", 0.65)
    monkeypatch.setattr(recherche, "_index", None)
    base = _base_avec_photoshop(vecteur=[("v1", 0.3), ("v2", 0.95)])

    candidats = recherche.chercher(base, "Comment installer Photoshop ?", k=4)
    assert [c["doc"].id for c in candidats] == ["v1", "v2"]   # rien d'ajouté


def test_chercher_marque_les_morceaux_trouves_des_deux_facons(monkeypatch):
    monkeypatch.setattr(config, "RECHERCHE_HYBRIDE", True)
    monkeypatch.setattr(recherche, "_index", None)
    base = _base_avec_photoshop(vecteur=[("m1", 0.5)])
    candidats = recherche.chercher(base, "Photoshop", k=4)
    assert candidats[0]["via"] == "les deux"
    assert candidats[0]["mots_rares"] == {"photoshop"}


def test_chercher_sans_hybride_se_limite_aux_vecteurs(monkeypatch):
    monkeypatch.setattr(config, "RECHERCHE_HYBRIDE", False)
    base = FausseBaseHybride({"v1": ("Photoshop", {"source": "a.md"})}, vecteur=[("v1", 0.3)])
    candidats = recherche.chercher(base, "Photoshop", k=4)
    assert [c["via"] for c in candidats] == ["vecteur"]


def test_repondre_examine_un_mot_rare_au_dela_du_seuil(monkeypatch, faux_rag):
    # Le faux modèle dit OUI aux extraits contenant « pertinent ».
    modele = faux_rag([], seuil=0.65)
    monkeypatch.setattr(recherche, "chercher", lambda base, q, k: [
        {"doc": Document(page_content="Photoshop pertinent", metadata={"source": "b.md"}, id="m1"),
         "distance": 1.06, "via": "mots-clés", "mots_rares": {"photoshop"}},
        {"doc": Document(page_content="bruit", metadata={"source": "a.pdf", "page": 3}, id="v1"),
         "distance": 0.96, "via": "vecteur", "mots_rares": set()},
    ])
    r = rag.repondre("Comment installer Photoshop ?")
    assert r["refus"] is False
    assert r["sources"][0]["via"] == "mots-clés"
    assert r["meilleur_score"] == 0.96


def test_repondre_refuse_par_seuil_sans_mot_rare(monkeypatch, faux_rag):
    faux_rag([], seuil=0.65)
    monkeypatch.setattr(recherche, "chercher", lambda base, q, k: [
        {"doc": Document(page_content="pertinent", metadata={"source": "a.pdf", "page": 3}, id="v1"),
         "distance": 0.90, "via": "vecteur", "mots_rares": set()},
    ])
    r = rag.repondre("question")
    assert r["refus"] is True and r["motif_refus"] == "seuil"
