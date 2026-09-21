"""Ingestion (src/ingestion.py) : identifiants stables, reprise sans doublon,
purge des morceaux obsolètes, lecture UTF-8."""

from langchain_core.documents import Document

from src import ingestion


def doc(texte, source="a.md", page=0):
    return Document(page_content=texte, metadata={"source": source, "page": page})


class FausseBase:
    """Juste ce que l'ingestion utilise de Chroma : get(ids), get(), delete."""
    def __init__(self, ids=()):
        self.ids = set(ids)
        self.supprimes = []

    def get(self, ids=None, include=None):
        if ids is None:
            return {"ids": sorted(self.ids)}
        return {"ids": [i for i in ids if i in self.ids]}

    def delete(self, ids):
        self.supprimes.extend(ids)
        self.ids -= set(ids)


def test_identifiant_stable_et_sensible_a_la_source_et_a_la_page():
    assert ingestion.identifiant(doc("x")) == ingestion.identifiant(doc("x"))
    assert ingestion.identifiant(doc("x")) != ingestion.identifiant(doc("y"))
    assert ingestion.identifiant(doc("x", "a.md")) != ingestion.identifiant(doc("x", "b.md"))
    # Même texte sur deux pages d'un PDF (en-têtes répétés) : deux morceaux.
    assert ingestion.identifiant(doc("x", page=1)) != ingestion.identifiant(doc("x", page=2))


def test_ecarter_deja_indexes_ignore_les_presents_et_les_doublons():
    morceaux = [doc("a"), doc("b"), doc("a")]  # "a" deux fois, strictement
    base = FausseBase(ids=[ingestion.identifiant(doc("b"))])
    nouveaux, ignores = ingestion.ecarter_deja_indexes(base, morceaux)
    assert [m.page_content for m in nouveaux] == ["a"]
    assert ignores == 2


def test_purger_obsoletes_supprime_ce_qui_n_est_plus_dans_le_corpus():
    ancien = ingestion.identifiant(doc("ancien texte"))
    actuel = ingestion.identifiant(doc("texte actuel"))
    base = FausseBase(ids=[ancien, actuel])
    supprimes = ingestion.purger_obsoletes(base, [doc("texte actuel")])
    assert supprimes == 1
    assert base.supprimes == [ancien]
    assert base.ids == {actuel}


def test_fichiers_texte_lus_en_utf8(tmp_path, monkeypatch):
    fichier = tmp_path / "procedure.md"
    fichier.write_text("Réinitialiser le mot de passe : « étape » 1", encoding="utf-8")
    monkeypatch.setattr(ingestion.config, "DOSSIER_CORPUS", tmp_path)
    documents = ingestion.charger_documents()
    assert len(documents) == 1
    assert "Réinitialiser" in documents[0].page_content
    assert "Ã" not in documents[0].page_content
    assert documents[0].metadata["source"] == "procedure.md"
