"""Logique de décision de rag.repondre : seuils, vérification, refus."""

from src import rag
from tests.conftest import FauxDocument as Doc


def test_refus_par_seuil_quand_meilleur_extrait_trop_loin(faux_rag):
    faux_rag([(Doc("pertinent", 1), 0.80)], seuil=0.65)
    r = rag.repondre("question")
    assert r["refus"] is True
    assert r["motif_refus"] == "seuil"
    assert r["sources"] == []
    assert r["meilleur_score"] == 0.80
    assert r["extraits_verifies"] == 0


def test_reponse_avec_sources_quand_extraits_pertinents(faux_rag):
    modele = faux_rag([(Doc("texte pertinent A", 1), 0.30),
                       (Doc("texte pertinent B", 2), 0.40)])
    r = rag.repondre("question")
    assert r["refus"] is False
    assert r["reponse"] == "Réponse rédigée."
    assert [s["page"] for s in r["sources"]] == [1, 2]
    assert r["extraits_verifies"] == 2 and r["extraits_ecartes"] == 0
    # Le prompt de rédaction contient bien les deux extraits.
    assert "texte pertinent A" in modele.prompts[-1]
    assert "texte pertinent B" in modele.prompts[-1]


def test_verification_ecarte_les_extraits_hors_sujet(faux_rag):
    modele = faux_rag([(Doc("hors sujet", 1), 0.30),
                       (Doc("texte pertinent", 2), 0.40),
                       (Doc("autre hors sujet", 3), 0.50)])
    r = rag.repondre("question")
    assert r["refus"] is False
    assert [s["page"] for s in r["sources"]] == [2]
    assert r["extraits_verifies"] == 3 and r["extraits_ecartes"] == 2
    assert "hors sujet" not in modele.prompts[-1]


def test_refus_par_verification_quand_aucun_extrait_ne_repond(faux_rag):
    faux_rag([(Doc("hors sujet", 1), 0.30), (Doc("bruit", 2), 0.40)])
    r = rag.repondre("question")
    assert r["refus"] is True
    assert r["motif_refus"] == "verification"
    assert r["extraits_ecartes"] == 2


def test_verification_desactivee_au_dessus_du_seuil_de_verification(faux_rag):
    # SEUIL_VERIFICATION = 0.65 : rien n'est vérifié, même un extrait sans rapport.
    faux_rag([(Doc("hors sujet", 1), 0.30)], verification=0.65)
    r = rag.repondre("question")
    assert r["refus"] is False
    assert r["extraits_verifies"] == 0


def test_seuil_contexte_limite_les_extraits_suivants(faux_rag):
    modele = faux_rag([(Doc("pertinent A", 1), 0.50),
                       (Doc("pertinent B", 2), 0.62)],
                      seuil=0.55, contexte=0.60)
    r = rag.repondre("question")
    assert r["refus"] is False
    assert [s["page"] for s in r["sources"]] == [1]
    assert "pertinent B" not in modele.prompts[-1]


def test_refus_par_le_modele_avec_le_mot_cle(faux_rag):
    faux_rag([(Doc("pertinent", 1), 0.30)], hors_contexte=True)
    r = rag.repondre("question")
    assert r["refus"] is True
    assert r["motif_refus"] == "modele"
    assert r["reponse"] == rag.MESSAGE_REFUS


def test_sources_dedoublonnees_par_page(faux_rag):
    faux_rag([(Doc("pertinent 1", 5), 0.30), (Doc("pertinent 2", 5), 0.35),
              (Doc("pertinent 3", 6), 0.40)])
    r = rag.repondre("question")
    assert [s["page"] for s in r["sources"]] == [5, 6]
    assert r["sources"][0]["score"] == 0.30  # le plus proche est conservé


def test_extrait_tronque_seulement_si_long(faux_rag):
    faux_rag([(Doc("pertinent " * 100, 1), 0.30), (Doc("pertinent court", 2), 0.40)])
    r = rag.repondre("question")
    assert r["sources"][0]["extrait"].endswith("...")
    assert r["sources"][1]["extrait"] == "pertinent court"


def test_reponse_nettoyee_des_espaces(faux_rag):
    faux_rag([(Doc("pertinent", 1), 0.30)], reponse="  \nRéponse.\n")
    assert rag.repondre("question")["reponse"] == "Réponse."
