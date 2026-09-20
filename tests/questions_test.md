# Jeu de questions d'évaluation

Sert à mesurer la qualité des réponses et à calibrer le seuil de pertinence.
À compléter au fur et à mesure que le corpus s'enrichit.

**Dernière campagne : 20/09/2026** — corpus : *Help Center GLPI.pdf* (767
morceaux) ; `nomic-embed-text` + `mistral` ; `SEUIL_PERTINENCE=0.65`,
`NOMBRE_EXTRAITS=4`. Les 25 questions ont été passées dans le pipeline
complet (`rag.repondre`), réponses lues une à une.

Le « meilleur score » est la distance du meilleur extrait (plus c'est bas,
plus c'est proche) ; la « page » est celle de cet extrait dans le PDF.

## A. Questions couvertes par le corpus
Le bot doit répondre, avec la bonne source.

| # | Question | Document attendu | Meilleur score | Résultat |
|---|---|---|---|---|
| 1 | Qu'est-ce qu'une entité dans GLPI ? | Help Center GLPI, p. 417 | 0.313 | **Correcte** : définition fidèle (structuration hiérarchique, isolation) |
| 2 | Comment configurer les notifications par e-mail dans GLPI ? | Help Center GLPI, chap. Notifications | 0.346 | **Hors cible** : répond sur les alertes des recherches enregistrées (p. 46), pas sur la configuration des notifications. Contenu tiré du corpus, mais mauvaise section |
| 3 | Comment créer un ticket dans GLPI ? | Help Center GLPI, p. 264 | 0.384 | **Correcte mais partielle** : décrit la création depuis un élément d'inventaire, pas le cas général (Assistance > Tickets) |
| 4 | Comment ajouter un utilisateur dans GLPI ? | Help Center GLPI, p. 70 | 0.416 | **Correcte** |
| 5 | Comment configurer les SLA ? | Help Center GLPI, p. 533 | 0.492 | **Correcte** : chemin de menu et étapes cohérents avec le corpus |
| 6 | Comment mettre un ticket en attente ? | Help Center GLPI, p. 222 | 0.503 | **Partielle** : cite bien la règle ITIL (mise en attente par le demandeur) mais la formulation est confuse (« pas possible depuis le contexte fourni ») |
| 7 | Comment importer des données depuis un fichier CSV ? | Help Center GLPI, p. 40 | 0.554 | **Correcte** |
| 8 | Comment fonctionne le plugin FusionInventory ? | Help Center GLPI, p. 70 | 0.608 | **Correcte** : indique qu'il est remplacé par GLPI Inventory |
| 9 | Comment fonctionne la base de connaissances ? | Help Center GLPI, p. 493 | 0.613 | **Partielle** : liste des droits associés plutôt qu'une explication du fonctionnement |
| 10 | Comment gérer l'inventaire du parc informatique ? | Help Center GLPI, p. 339 | 0.627 | **Partielle** : vague, phrase mal construite (« permissions modifiées automatiquement ») |

Bilan A : 10 réponses sur 10, dont 5 correctes, 4 partielles, 1 hors cible.
Aucune invention : tout ce qui est dit vient du corpus. Les scores au-dessus
de 0.55 donnent des réponses nettement plus faibles (questions 7 à 10).

## B. Questions hors périmètre
Le bot doit refuser de répondre.

| # | Question | Meilleur score | Refus obtenu ? |
|---|---|---|---|
| 1 | Quelle est la capitale de l'Australie ? | 0.782 | **Oui** |
| 2 | Quelle est la recette de la tarte aux pommes ? | 0.699 | **Oui** |
| 3 | Qui a gagné la coupe du monde de football 2018 ? | 0.726 | **Oui** |
| 4 | Quel temps fait-il demain à Toulouse ? | 0.766 | **Oui** |
| 5 | Raconte-moi une blague | 0.779 | **Oui** |
| 6 | Écris un poème sur la mer | 0.804 | **Oui** |
| 7 | Comment installer Photoshop ? | 0.965 | **Oui** |
| 8 | Bonjour | 0.835 | **Oui** |
| 9 | Merci beaucoup | 0.701 | **Oui** |

Bilan B : 9 refus sur 9. Le plus proche du seuil est « tarte aux pommes » à
0.699, soit 0.05 au-dessus de 0.65 : la marge est mince, à surveiller si le
corpus s'élargit.

Pour mémoire, avec l'ancien seuil de 1.0, **aucune** de ces questions n'était
refusée (« Bonjour » recevait une réponse sur les enquêtes de satisfaction).

## C. Questions limites
Sujet proche du corpus, mais réponse absente. Ce sont les cas les plus
révélateurs : c'est là que le bot invente s'il le fait.

| # | Question | Meilleur score | Comportement |
|---|---|---|---|
| 1 | Comment réinitialiser mon mot de passe Windows ? | 0.591 | **INVENTÉE.** Dit d'abord que le contexte n'en parle pas, puis donne quand même une procédure Windows sortie de sa mémoire (« Oubli de mot de passe » dans le menu Démarrer : absent du corpus) |
| 2 | Quelle est la version de GLPI installée chez nous ? | 0.345 | **Bon** : reconnaît que l'information n'est pas dans le contexte |
| 3 | Quel est le mot de passe administrateur de notre GLPI ? | 0.446 | **Bon** : reconnaît l'absence, ajoute un conseil général de sécurité |
| 4 | Comment migrer GLPI vers un autre serveur ? | 0.573 | **INVENTÉE.** Décrit des commandes `glpi-export` / `glpi-import` qui **n'existent pas** (0 occurrence dans le corpus). L'extrait retenu (p. 29) parle de raccourcis clavier |
| 5 | Comment configurer l'authentification LDAP dans GLPI ? | 0.298 | Finalement couverte par le corpus (p. 48) : **réponse correcte**. À reclasser en A |
| 6 | Combien de tickets ont été ouverts ce mois-ci ? | 0.515 | **Bon** : reconnaît l'absence de données, oriente vers la liste des tickets (contenu du corpus) |

Bilan C : sur les 5 questions réellement sans réponse, 3 refus « par le
modèle » corrects, **2 inventions**. Les deux inventions ont des scores de
0.573 et 0.591 : elles passent le seuil (0.65), mais l'extrait retenu n'a pas
grand-chose à voir avec la question. Le modèle, avec un contexte hors sujet
sous les yeux, comble avec ses propres connaissances malgré la consigne.

## Indicateurs (campagne du 20/09/2026)

| Indicateur | Définition | Valeur |
|---|---|---|
| **Taux de réponse** | réponses fournies / questions posées | 16 / 25 = **64 %** (A : 10/10, B : 0/9, C : 6/6) |
| **Taux de refus justifié** | refus corrects / questions du groupe B | 9 / 9 = **100 %** |
| **Taux d'hallucination** | réponses inventées / réponses fournies | 2 / 16 = **12,5 %** — objectif : 0 |

L'objectif « zéro invention » n'est pas atteint. Les deux cas viennent du
groupe C, avec des scores entre 0.55 et 0.65.

## Pistes (à trancher)

1. **Durcir la consigne du prompt** (`GABARIT_PROMPT` dans `src/rag.py`) :
   aujourd'hui « dis-le clairement et n'invente rien » n'empêche pas Mistral
   d'enchaîner par « Cependant, voici comment faire… ». Imposer une réponse
   fixe quand le contexte ne suffit pas (par exemple exactement le message
   de refus), sans rien ajouter.
2. **Abaisser le seuil à 0.55** : refuserait les deux inventions (0.573,
   0.591) mais aussi les questions A7 à A10 (0.554 à 0.627), dont les
   réponses étaient de toute façon les plus faibles. À mesurer sur un corpus
   plus large avant de décider.
3. **Vérifier la cohérence extrait / question** avant de générer : quand le
   score est dans la zone 0.55–0.65, demander au modèle si l'extrait répond
   à la question avant de rédiger. Plus coûteux (un appel de plus).

## Reproduire la campagne

Sans passer par l'interface (et sans connexion GLPI) :

```python
from src import rag
r = rag.repondre("Comment migrer GLPI vers un autre serveur ?")
print(r["refus"], r["meilleur_score"], r["reponse"])
```

Ou en lot : voir le champ `meilleur_score` et `sources` de chaque ligne de
`logs/echanges.jsonl` après avoir posé les questions dans l'interface.
