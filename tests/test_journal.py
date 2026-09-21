"""Journal des échanges (src/journal.py)."""

from src import config, journal


def test_enregistrer_puis_lire(journal_temporaire):
    journal.enregistrer("question", question="q1", refus=False, meilleur_score=0.3, duree_s=2.0)
    journal.enregistrer("question", question="q2", refus=True, meilleur_score=0.8, duree_s=1.0)
    entrees = journal.lire()
    assert [e["question"] for e in entrees] == ["q1", "q2"]
    assert all("horodatage" in e for e in entrees)
    assert journal_temporaire.read_text(encoding="utf-8").count("\n") == 2


def test_lire_sans_fichier(journal_temporaire):
    assert journal.lire() == []


def test_desactivee(journal_temporaire, monkeypatch):
    monkeypatch.setattr(config, "JOURNALISATION", False)
    journal.enregistrer("question", question="q")
    assert not journal_temporaire.exists()


def test_erreur_d_ecriture_n_interrompt_pas(journal_temporaire, monkeypatch, capsys):
    # Un fichier à la place du dossier : mkdir échoue, l'appel doit survivre.
    monkeypatch.setattr(config, "DOSSIER_JOURNAL", journal_temporaire)
    journal_temporaire.write_text("x")
    journal.enregistrer("question", question="q")
    assert "écriture impossible" in capsys.readouterr().out


def test_statistiques():
    entrees = [
        {"type": "connexion", "utilisateur": "a"},
        {"type": "question", "refus": False, "meilleur_score": 0.3, "duree_s": 2.0},
        {"type": "question", "refus": False, "meilleur_score": 0.5, "duree_s": 4.0},
        {"type": "question", "refus": True, "meilleur_score": 0.8, "duree_s": 1.0},
        {"type": "ticket", "ticket_id": 1},
        {"type": "avis", "utile": True},
        {"type": "avis", "utile": False},
        {"type": "erreur", "origine": "glpi"},
    ]
    s = journal.statistiques(entrees)
    assert s["questions"] == 3 and s["repondues"] == 2 and s["refus"] == 1
    assert s["taux_refus"] == round(1 / 3, 3)
    assert s["tickets_crees"] == 1 and s["erreurs"] == 1
    assert s["avis"] == 2 and s["avis_utiles"] == 1 and s["taux_avis_utiles"] == 0.5
    assert s["score_moyen_repondues"] == 0.4
    assert s["score_moyen_refus"] == 0.8
    assert s["duree_moyenne_s"] == round(7 / 3, 3)


def test_statistiques_vides():
    s = journal.statistiques([])
    assert s["questions"] == 0
    assert s["taux_refus"] is None
    assert s["taux_avis_utiles"] is None
