"""
Journalisation des échanges.

Chaque question posée via l'API est enregistrée avec ce qui a servi à y
répondre : extraits retenus, scores, réponse, durée. Deux usages :
 - mesurer la qualité (taux de refus, scores observés, questions fréquentes)
   pour affiner le seuil et enrichir le corpus ;
 - comprendre après coup pourquoi le bot a répondu (ou refusé) telle chose.

Format : un fichier JSON Lines (une ligne JSON par échange) dans logs/.
Choisi plutôt qu'une base de données : lisible tel quel, s'ouvre dans un
tableur, et s'analyse en quelques lignes de Python.

Le fichier contient les questions réelles des utilisateurs : il est exclu du
dépôt Git (voir .gitignore).

Statistiques rapides :  python -m src.journal
"""

import json
from datetime import datetime

from src import config


def enregistrer(type_evenement: str, **champs) -> None:
    """Ajoute une ligne au journal. Ne lève jamais : un problème d'écriture
    ne doit pas empêcher de répondre à l'utilisateur."""
    if not config.JOURNALISATION:
        return
    entree = {"horodatage": datetime.now().isoformat(timespec="seconds"),
              "type": type_evenement, **champs}
    try:
        config.DOSSIER_JOURNAL.mkdir(parents=True, exist_ok=True)
        with open(config.FICHIER_JOURNAL, "a", encoding="utf-8") as fichier:
            fichier.write(json.dumps(entree, ensure_ascii=False) + "\n")
    except OSError as erreur:
        print(f"[journal] écriture impossible : {erreur}")


def lire() -> list[dict]:
    """Renvoie toutes les entrées du journal (liste vide s'il n'existe pas)."""
    if not config.FICHIER_JOURNAL.exists():
        return []
    entrees = []
    with open(config.FICHIER_JOURNAL, encoding="utf-8") as fichier:
        for ligne in fichier:
            ligne = ligne.strip()
            if ligne:
                entrees.append(json.loads(ligne))
    return entrees


def statistiques(entrees: list[dict]) -> dict:
    """Indicateurs de base sur les questions posées."""
    questions = [e for e in entrees if e["type"] == "question"]
    refus = [e for e in questions if e.get("refus")]
    repondues = [e for e in questions if not e.get("refus")]
    tickets = [e for e in entrees if e["type"] == "ticket"]
    erreurs = [e for e in entrees if e["type"] == "erreur"]
    avis = [e for e in entrees if e["type"] == "avis"]
    avis_utiles = [e for e in avis if e.get("utile")]

    def moyenne(valeurs):
        valeurs = [v for v in valeurs if v is not None]
        return round(sum(valeurs) / len(valeurs), 3) if valeurs else None

    return {
        "questions": len(questions),
        "repondues": len(repondues),
        "refus": len(refus),
        "taux_refus": round(len(refus) / len(questions), 3) if questions else None,
        "tickets_crees": len(tickets),
        "erreurs": len(erreurs),
        "avis": len(avis),
        "avis_utiles": len(avis_utiles),
        "taux_avis_utiles": round(len(avis_utiles) / len(avis), 3) if avis else None,
        "score_moyen_repondues": moyenne(e.get("meilleur_score") for e in repondues),
        "score_moyen_refus": moyenne(e.get("meilleur_score") for e in refus),
        "duree_moyenne_s": moyenne(e.get("duree_s") for e in questions),
    }


if __name__ == "__main__":
    entrees = lire()
    if not entrees:
        print(f"Journal vide ou absent : {config.FICHIER_JOURNAL}")
        raise SystemExit

    print(f"Journal : {config.FICHIER_JOURNAL}\n")
    for cle, valeur in statistiques(entrees).items():
        print(f"  {cle:<24} {valeur}")

    print("\nDernières questions :")
    for e in [e for e in entrees if e["type"] == "question"][-10:]:
        etat = "REFUS " if e.get("refus") else "réponse"
        score = e.get("meilleur_score")
        score = f"{score:.3f}" if score is not None else "  -  "
        print(f"  {e['horodatage']}  {etat}  {score}  {e['question'][:60]}")
