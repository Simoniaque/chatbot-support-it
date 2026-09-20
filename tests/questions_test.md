# Jeu de questions d'évaluation

Sert à mesurer la qualité des réponses et à calibrer le seuil de pertinence.
À compléter au fur et à mesure que le corpus s'enrichit.

**Dernière campagne : 20/09/2026** — corpus : *Help Center GLPI.pdf* (767
morceaux) ; `nomic-embed-text` + `mistral` ; `SEUIL_PERTINENCE=0.65`,
`NOMBRE_EXTRAITS=4`. Les 25 questions ont été passées dans le pipeline
complet (`rag.repondre`), réponses lues une à une.

Le « meilleur score » est la distance du meilleur extrait (plus c'est bas,
plus c'est proche) ; la « page » est celle de cet extrait dans le PDF.

> **Correction du 21/09/2026** : les campagnes 1 à 5 ont jugé les réponses
> sur leur *plausibilité*. En relisant les extraits réellement retenus
> (campagne 6), il s'est avéré que plusieurs réponses notées « correctes »
> étaient inventées. Les tables des campagnes 1 à 5 sont conservées telles
> quelles ; la section « Correction de l'étalon » donne les vrais chiffres,
> et la méthode à suivre désormais.

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

1. **Durcir la consigne du prompt** — **testée le 20/09/2026, voir ci-dessous.**
2. **Abaisser le seuil à 0.55** — **testée le 20/09/2026, voir campagne 3.**
3. **Vérifier la cohérence extrait / question** avant de générer : quand le
   score est dans la zone 0.55–0.65, demander au modèle si l'extrait répond
   à la question avant de rédiger. Plus coûteux (un appel de plus).

## Campagne 2 — piste 1 : consigne durcie (20/09/2026)

Changement dans `src/rag.py` : le modèle doit répondre par le mot exact
`HORS_CONTEXTE` quand le contexte ne parle pas du sujet ; le code détecte ce
mot et le transforme en refus (`motif_refus = "modele"`, par opposition à
`"seuil"`). Deux formulations essayées :

- **v1** : « si le contexte ne contient pas l'information demandée →
  HORS_CONTEXTE ». Trop brutale : 2 faux refus en A (ticket en attente,
  FusionInventory), LDAP réduit à une ligne, et « mot de passe Windows »
  toujours répondu (sur le mot de passe GLPI).
- **v2 (retenue)** : « si le contexte contient de quoi répondre, même
  partiellement, réponds avec ce qu'il dit et rien de plus ; s'il ne parle
  pas du tout du sujet → HORS_CONTEXTE ; n'invente jamais de commande, de
  menu ou d'étape ».

Résultats v2 sur A et C (B n'atteint pas le modèle, inchangé : 9/9 refus) :

| # | Question | Score | Avant (campagne 1) | Après (v2) |
|---|---|---|---|---|
| A5 | Comment configurer les SLA ? | 0.492 | Correcte, étapes détaillées | **Appauvrie** : une seule ligne |
| A6 | Comment mettre un ticket en attente ? | 0.503 | Partielle, confuse | Partielle, plus claire (règle ITIL) |
| A8 | Comment fonctionne le plugin FusionInventory ? | 0.608 | Correcte | **Faux refus** (modèle) |
| C1 | Comment réinitialiser mon mot de passe Windows ? | 0.591 | **Inventée** (procédure Windows) | **Refus** (modèle) |
| C2 | Quelle est la version de GLPI installée chez nous ? | 0.345 | « Pas dans le contexte » mais `refus=False` | **Refus** (modèle) |
| C3 | Quel est le mot de passe administrateur de notre GLPI ? | 0.446 | Idem | **Refus** (modèle) |
| C4 | Comment migrer GLPI vers un autre serveur ? | 0.573 | **Inventée** (`glpi-export`) | **Toujours inventée** : « outil de backup fourni avec GLPI », et les raccourcis clavier de la p. 29 mélangés aux étapes |
| C5 | Comment configurer l'authentification LDAP dans GLPI ? | 0.298 | Correcte, étapes | **Appauvrie** : renvoi à la section, sans étapes |
| C6 | Combien de tickets ont été ouverts ce mois-ci ? | 0.515 | « Pas de données » mais `refus=False` | **Refus** (modèle) |

Les autres questions de A (1, 2, 3, 4, 7, 9, 10) donnent le même résultat
qu'en campagne 1.

| Indicateur | Campagne 1 | Campagne 2 (v2) |
|---|---|---|
| Réponses fournies | 16 / 25 | 11 / 25 |
| Refus justifiés (B) | 9 / 9 | 9 / 9 |
| **Inventions** | **2 / 16 (12,5 %)** | **1 / 11 (9 %)** |
| Faux refus (A) | 0 | 1 (A8) |
| Réponses appauvries | 0 | 2 (A5, C5) |

Ce que ça montre :

- Le mot-clé rend les refus **détectables** : en campagne 1, C2, C3 et C6
  disaient « ce n'est pas dans le contexte » avec `refus=False`, donc
  l'interface **ne proposait pas de ticket**. En v2 elle le propose. C'est
  le vrai gain, au-delà du chiffre.
- Mistral 7B reste incapable de juger qu'un extrait *vaguement* lié (C4,
  raccourcis clavier vs migration) ne répond pas : il rédige quand même. La
  consigne ne corrige pas une recherche qui a ramené le mauvais extrait.
  Seules les pistes 2 ou 3 traitent ce cas.
- Le prix : une consigne plus stricte rend le modèle plus frileux (A8) et
  plus laconique (A5, C5). Pour un outil dont la règle est « refuser plutôt
  qu'inventer », échanger une invention contre un faux refus (qui débouche
  sur un ticket) est le bon sens de l'échange — mais l'appauvrissement des
  réponses est à surveiller quand le corpus grandira.

**Décision** : v2 conservée. Piste 2 (seuil 0.55) évaluée ensuite pour C4.

## Campagne 3 — piste 2 : seuil à 0.55 (20/09/2026)

Même jeu, même prompt (v2), `SEUIL_PERTINENCE=0.55` passé en variable
d'environnement. B inchangé par construction (tous les scores ≥ 0.699).

| # | Question | Score | À 0.65 (campagne 2) | À 0.55 |
|---|---|---|---|---|
| A3 | Comment créer un ticket dans GLPI ? | 0.384 | Correcte, 2 étapes | **Appauvrie** : une ligne |
| A5 | Comment configurer les SLA ? | 0.492 | Une ligne | **Dégradée** : 1 seul extrait retenu (les 3 autres à 0.60–0.63 sont exclus), réponse confuse sur TTO/TTR |
| A6 | Comment mettre un ticket en attente ? | 0.503 | Partielle | Partielle (2 extraits au lieu de 4) |
| A7 | Comment importer des données depuis un fichier CSV ? | 0.554 | Correcte | **Faux refus** (seuil) |
| A8 | Comment fonctionne le plugin FusionInventory ? | 0.608 | Faux refus (modèle) | Faux refus (seuil) |
| A9 | Comment fonctionne la base de connaissances ? | 0.613 | Partielle | **Faux refus** (seuil) |
| A10 | Comment gérer l'inventaire du parc informatique ? | 0.627 | Partielle | **Faux refus** (seuil) |
| C1 | Comment réinitialiser mon mot de passe Windows ? | 0.591 | Refus (modèle) | Refus (seuil) |
| C4 | Comment migrer GLPI vers un autre serveur ? | 0.573 | **Inventée** | **Refus** (seuil) |

| Indicateur | Campagne 1 (0.65, prompt initial) | Campagne 2 (0.65, v2) | Campagne 3 (0.55, v2) |
|---|---|---|---|
| Réponses fournies | 16 / 25 | 11 / 25 | 7 / 25 |
| Refus justifiés (B) | 9 / 9 | 9 / 9 | 9 / 9 |
| **Inventions** | 2 / 16 | 1 / 11 | **0 / 7** |
| Faux refus (A) | 0 / 10 | 1 / 10 | **4 / 10** |
| Réponses appauvries ou dégradées | 0 | 2 | 4 |

Ce que ça montre :

- **Zéro invention**, objectif atteint — mais **4 questions couvertes sur 10
  refusées**, dont deux (A7, A8) avaient une réponse correcte. Sur un corpus
  d'un seul document, c'est le scénario « outil perçu comme inutile » de
  l'arbitrage.
- **Effet de bord découvert** : le seuil ne filtre pas seulement le
  *meilleur* extrait, il filtre *tous* les extraits envoyés au modèle. À
  0.55, « SLA » (0.492) passe, mais ses trois autres extraits (0.60–0.63)
  sont écartés : le modèle ne voit plus qu'un extrait et la réponse se
  dégrade. Abaisser le seuil appauvrit donc aussi les questions qu'il ne
  refuse pas.

**Décision** : seuil maintenu à **0.65**. La piste 2 est trop coûteuse sur
ce corpus ; à réévaluer quand il sera plus large (les scores des questions
couvertes baisseront si la documentation devient plus spécifique).

**Piste 4, issue de l'effet de bord** : séparer les deux rôles du seuil —
**testée, voir campagne 4.**

## Campagne 4 — piste 4 : deux seuils (20/09/2026)

Changement dans `src/rag.py` et `src/config.py` : `SEUIL_PERTINENCE` ne
s'applique plus qu'au **meilleur** extrait (répondre ou refuser) ; un nouveau
`SEUIL_CONTEXTE` (≥ `SEUIL_PERTINENCE`) décide quels extraits suivants
accompagnent le meilleur dans le contexte envoyé au modèle. Avec les deux à
0.65, le comportement est identique à avant.

Campagne : `SEUIL_PERTINENCE=0.55`, `SEUIL_CONTEXTE=0.65`, prompt v2.

| # | Question | Score | Campagne 3 (0.55 seul) | Campagne 4 (0.55 / 0.65) |
|---|---|---|---|---|
| A5 | Comment configurer les SLA ? | 0.492 | 1 extrait, réponse confuse (TTO/TTR) | **4 extraits**, réponse identique à la campagne 2 |
| A6 | Comment mettre un ticket en attente ? | 0.503 | 2 extraits | **4 extraits**, réponse identique à la campagne 2 |
| A7–A10 | (0.554 à 0.627) | | Faux refus (seuil) | Faux refus (seuil) — inchangé |
| C1, C4 | mot de passe Windows, migration | 0.591, 0.573 | Refus (seuil) | Refus (seuil) — inchangé |

Indicateurs identiques à la campagne 3 (0 invention, 4 faux refus, 7/25
réponses) : la piste 4 corrige l'effet de bord de la campagne 3 (contexte
amputé), pas le fond (le seuil de refus à 0.55 écarte 4 questions couvertes).

Remarque de méthode : « créer un ticket » (A3) a exactement le même contexte
en campagnes 2 et 4, mais une réponse différente (2 étapes → 1 ligne). Même
à température 0, Ollama n'est pas parfaitement déterministe d'une exécution
à l'autre. Un jugement « appauvrie » sur une seule question est donc à
prendre avec cette marge ; seules les tendances sur plusieurs questions
sont fiables.

**Décision** : mécanisme conservé (deux réglages dans `.env`), valeurs
laissées à **0.65 / 0.65**. Le jour où le corpus justifie un seuil de refus
plus bas, `SEUIL_CONTEXTE` évitera d'appauvrir les réponses acceptées.

## Synthèse des quatre campagnes

| Réglage | Inventions | Faux refus (A) | Réponses fournies |
|---|---|---|---|
| 0.65, prompt initial | 2 / 16 | 0 / 10 | 16 / 25 |
| 0.65, prompt v2 **(retenu)** | 1 / 11 | 1 / 10 | 11 / 25 |
| 0.55, prompt v2 | 0 / 7 | 4 / 10 | 7 / 25 |
| 0.55 / contexte 0.65, prompt v2 | 0 / 7 | 4 / 10 | 7 / 25 |

Il reste une invention connue (C4, « migrer GLPI », 0.573) que ni le prompt
ni un seuil raisonnable ne traitent sans sacrifier des questions couvertes.
La piste 3 a été testée ensuite (campagne 5).

## Campagne 5 — piste 3 : vérification extrait / question (20/09/2026)

Ajout dans `src/rag.py` : dans la zone grise (score > `SEUIL_VERIFICATION`,
0.55 pour la campagne), un appel court au modèle demande « cet extrait
contient-il de quoi répondre, même partiellement ? OUI ou NON ». Refus avec
`motif_refus = "verification"` si la réponse est NON. Seuils 0.65 / 0.65,
prompt v2. Deux variantes :

**5a — chaque extrait de la zone grise est vérifié, les NON sont écartés
du contexte.**

| # | Question | Score | Vérifiés / écartés | Résultat |
|---|---|---|---|---|
| A7 | Comment importer des données depuis un fichier CSV ? | 0.554 | 4 / 3 | **Nouvelle invention** : avec le seul extrait restant, « pas de mention… cependant, dans Microsoft Excel vous pouvez… » |
| A8 | Comment fonctionne le plugin FusionInventory ? | 0.608 | 4 / 4 | Faux refus (vérification) |
| A10 | Comment gérer l'inventaire du parc informatique ? | 0.627 | 4 / 3 | Partielle, source différente (p. 477 au lieu de 339) |
| C1 | Comment réinitialiser mon mot de passe Windows ? | 0.591 | 2 / 2 | **Refus** (vérification) |
| C4 | Comment migrer GLPI vers un autre serveur ? | 0.573 | 2 / 2 | **Refus** (vérification) — le cas visé |

Bilan 5a : 1 invention / 12 réponses, 1 faux refus. C4 réglée, mais
l'invention s'est déplacée sur A7 : écarter des extraits ampute le contexte,
et un contexte maigre est exactement ce qui déclenche le « cependant ».

**5b — seul le meilleur extrait est vérifié ; il décide de répondre ou
refuser, le reste du contexte est conservé.**

| # | Question | Score | Résultat |
|---|---|---|---|
| A7 | Comment importer des données depuis un fichier CSV ? | 0.554 | **Faux refus** : le vérificateur dit NON à l'extrait p. 40… auquel il avait dit **OUI** en 5a |
| A8 | Comment fonctionne le plugin FusionInventory ? | 0.608 | Faux refus |
| A10 | Comment gérer l'inventaire du parc informatique ? | 0.627 | Faux refus |
| C1, C4 | | | **Refus** (vérification) |

Bilan 5b : **0 invention / 8 réponses, 3 faux refus**.

| Réglage | Inventions | Faux refus (A) | Réponses fournies |
|---|---|---|---|
| 0.65, prompt v2 (campagne 2) | 1 / 11 | 1 / 10 | 11 / 25 |
| + vérification 5a (par extrait) | 1 / 12 | 1 / 10 | 12 / 25 |
| + vérification 5b (meilleur extrait) | **0 / 8** | **3 / 10** | 8 / 25 |

Ce que ça montre :

- La vérification traite bien le cas visé (C4) : c'est le seul filtre qui
  y arrive sans baisser le seuil.
- Mais **Mistral 7B n'est pas un juge fiable** sur une question fermée :
  il écarte des extraits pertinents (A8, A10), et il n'est pas cohérent
  avec lui-même (A7, p. 40 : OUI en 5a, NON en 5b). Les cas qu'on lui
  soumet sont précisément les cas limites, ceux où il hésite.
- Résultat net : la vérification échange des inventions contre des faux
  refus, comme un seuil plus bas, avec un appel de plus (1 à 2 s).

**Décision** : mécanisme conservé mais **désactivé par défaut**
(`SEUIL_VERIFICATION=0.65`, soit ≥ `SEUIL_CONTEXTE`). Il aura du sens avec
un modèle juge plus fiable (un modèle plus gros, ou un modèle dédié à la
classification), ou quand le corpus sera plus large. Réactivation : une
valeur dans `.env`, par exemple `0.55`.

## Bilan des cinq premières campagnes (avant correction de l'étalon)

Sur ce corpus (un document, 767 morceaux) et avec Mistral 7B, **aucun
réglage n'atteint zéro invention sans refuser des questions couvertes**. Le
compromis retenu — seuil 0.65, prompt v2, vérification désactivée — donne
1 invention connue sur 11 réponses et 1 faux refus sur 10 questions
couvertes. Les trois leviers restent disponibles dans `.env` et le jeu de
test permet de remesurer en quelques minutes à chaque changement de corpus
ou de modèle.

Ce que la campagne apporte de plus durable que les chiffres : les refus
sont maintenant **détectables** (`motif_refus`), donc l'utilisateur se voit
proposer un ticket GLPI dans tous les cas où le chatbot ne répond pas — y
compris les faux refus, qui deviennent une gêne plutôt qu'une impasse.


## Reproduire la campagne

Sans passer par l'interface (et sans connexion GLPI) :

```python
from src import rag
r = rag.repondre("Comment migrer GLPI vers un autre serveur ?")
print(r["refus"], r["meilleur_score"], r["reponse"])
```

Ou en lot : voir le champ `meilleur_score` et `sources` de chaque ligne de
`logs/echanges.jsonl` après avoir posé les questions dans l'interface.

## Correction de l'étalon (21/09/2026)

En testant un second modèle juge, ses verdicts « NON » sur des extraits que
je tenais pour pertinents m'ont fait relire ces extraits. Résultat : ce sont
mes étiquettes qui étaient fausses. Vérification faite pour chaque question
de A en comparant la réponse au **texte des extraits retenus** :

| # | Question | Score | Ce que disent vraiment les extraits | Réponse de la campagne 1, en réalité |
|---|---|---|---|---|
| A4 | Comment ajouter un utilisateur dans GLPI ? | 0.416 | Inventaire, formulaires, intro de la doc, raccourcis clavier : **rien sur les utilisateurs** | **Inventée** (« Utilisateurs > Ajouter », de mémoire) |
| A5 | Comment configurer les SLA ? | 0.492 | Champ SLA dans les formulaires, liste TTO/TTR | **Inventée** (« Configuration > Configuration avancée > SLA > Ajouter ») |
| A7 | Comment importer des données depuis un fichier CSV ? | 0.554 | **Export** CSV, accents dans Excel, préférence « délimiteur CSV » | **Inventée** (procédure d'import en 4 étapes) |
| A10 | Comment gérer l'inventaire du parc informatique ? | 0.627 | Lignes d'historique (« mise à jour automatique de l'inventaire ») | **Fabriquée** à partir de bruit |
| C5 | Comment configurer l'authentification LDAP dans GLPI ? | 0.298 | Un renvoi : « Voir Configuration des méthodes d'authentification » | **Inventée** (hôte, port, DN… de mémoire) |

Les autres réponses de A (entité, notifications, créer un ticket, ticket en
attente, base de connaissances) sont bien ancrées dans les extraits.

Chiffres corrigés de la campagne 1 : **7 inventions sur 16 réponses (44 %)**,
et non 2. Deux enseignements :

- **Une réponse plausible n'est pas une réponse ancrée.** Mistral connaît
  GLPI de mémoire ; ce qu'il invente sonne juste. Le seul contrôle valable
  est de comparer la réponse au texte des extraits retenus, jamais à ce
  qu'on sait soi-même de GLPI.
- **Un score bas ne garantit rien.** « Ajouter un utilisateur » a 0.416 et
  zéro extrait utile : la distance mesure une proximité de vocabulaire, pas
  la capacité de l'extrait à répondre.

## Campagne 6 — vérification de tous les extraits, juge qwen2.5:7b (21/09/2026)

Deux changements : la vérification s'applique à **chaque** extrait, quel
que soit son score (`SEUIL_VERIFICATION=0`), et les extraits jugés NON sont
écartés du contexte (on garde les OUI ; refus s'il n'en reste aucun). Juge :
`qwen2.5:7b` (`MODELE_JUGE`), choisi comme modèle « plus fiable en
classification » de même taille. Réponses jugées sur leur **ancrage**.

Avant la campagne, comparaison des deux juges sur le meilleur extrait de
chacune des 16 questions A + C, étiqueté à la main : **mistral 13/16,
qwen2.5:7b 14/16**, d'accord entre eux sur 15 cas. Erreurs communes : SLA
(OUI à tort) et FusionInventory (NON à tort). Le juge n'était donc pas le
maillon faible.

| # | Question | Score | Vérifiés / écartés | Résultat |
|---|---|---|---|---|
| A1 | Qu'est-ce qu'une entité dans GLPI ? | 0.313 | 4 / 2 | **Ancrée** : le juge a gardé p. 415, la vraie définition |
| A2 | Comment configurer les notifications par e-mail dans GLPI ? | 0.346 | 4 / 2 | **Inventée** : « onglet Profils > Profils de suivi par e-mail > Nouveau profil », absent des extraits |
| A3 | Comment créer un ticket dans GLPI ? | 0.384 | 4 / 2 | Ancrée (p. 337) |
| A4 | Comment ajouter un utilisateur dans GLPI ? | 0.416 | 4 / 4 | **Refus justifié** |
| A5 | Comment configurer les SLA ? | 0.492 | 4 / 2 | Faible : renvoi à « Configurer vos SLA » |
| A6 | Comment mettre un ticket en attente ? | 0.503 | 4 / 3 | Ancrée, partielle |
| A7 | Comment importer des données depuis un fichier CSV ? | 0.554 | 4 / 3 | **Inventée** : 6 étapes brodées autour de la ligne « délimiteur CSV » (p. 17) |
| A8 | Comment fonctionne le plugin FusionInventory ? | 0.608 | 4 / 4 | Faux refus |
| A9 | Comment fonctionne la base de connaissances ? | 0.613 | 3 / 0 | Ancrée |
| A10 | Comment gérer l'inventaire du parc informatique ? | 0.627 | 4 / 3 | Ancrée (permissions, p. 477), partielle |
| C1–C6 | | | | **6 refus sur 6** (LDAP compris : l'extrait n'est qu'un renvoi) |

Bilan : **2 inventions / 8 réponses**, 1 faux refus. Durées 13 à 33 s par
question, dont la bascule entre les deux modèles sur le GPU.

## Campagne 7 — idem, juge mistral (21/09/2026)

Même réglage, `MODELE_JUGE` vide (juge = rédacteur).

| # | Question | Résultat |
|---|---|---|
| A2 | notifications | Ancrée mais hors cible (alertes sur recherches sauvegardées) — **pas inventée** cette fois : le juge n'a gardé qu'un extrait |
| A7 | import CSV | **Inventée** : « pas de mention… cependant, dans Microsoft Excel… » |
| A8 | FusionInventory | Faux refus |
| autres A | | Comme en campagne 6 |
| C | | 5 refus, LDAP répond par le renvoi lui-même (ancré, inutile, pas inventé) |

Bilan : **1 invention / 9 réponses**, 1 faux refus. Durées **1,6 à 14 s** :
pas de bascule de modèle.

## Synthèse (chiffres corrigés, réponses jugées sur l'ancrage)

| Réglage | Inventions | Faux refus (A) | Réponses |
|---|---|---|---|
| Campagne 1 : 0.65, prompt initial, sans vérification | **7 / 16 (44 %)** | 0 / 10 | 16 / 25 |
| Campagne 6 : + prompt v2 + vérification de tous les extraits, juge qwen2.5:7b | 2 / 8 | 1 / 10 | 8 / 25 |
| Campagne 7 : idem, juge mistral **(retenu)** | **1 / 9 (11 %)** | 1 / 10 | 9 / 25 |

Ce que ça montre :

- **Le levier efficace est la vérification extrait par extrait, sur tous les
  extraits.** Ni le seuil ni la consigne n'y arrivaient : un extrait qui
  *mentionne* le sujet sans y répondre passe le seuil et pousse le rédacteur
  à broder. Le juge l'écarte.
- **Un juge plus « gros » n'apporte rien de mesurable ici.** Mistral et
  Qwen 7B se trompent sur les mêmes cas limites ; de bout en bout, l'écart
  (2 contre 1) est dans le bruit d'une exécution à l'autre, et le juge
  distinct coûte une bascule de modèle à chaque question.
- **L'invention restante vient du rédacteur**, pas du juge : sur « import
  CSV », Mistral 7B écrit « pas de mention… cependant… » malgré la consigne.
  Le levier suivant serait un rédacteur qui obéit mieux (`qwen2.5:7b` en
  `MODELE_LLM`, à mesurer) — pas un juge plus gros.

**Décision** : vérification **activée par défaut** sur tous les extraits
(`SEUIL_VERIFICATION=0`), juge = rédacteur (`MODELE_JUGE` vide). Coût :
quelques secondes par question. Le modèle `qwen2.5:7b` reste installé pour
le tester en rédacteur.

## Méthode à suivre pour les prochaines campagnes

1. Passer les questions par `rag.repondre` (ou l'interface).
2. Pour chaque réponse fournie, **relire les extraits retenus**
   (`sources[].extrait`, ou la page du PDF) et vérifier que chaque affirmation
   de la réponse y figure. Une étape, un chemin de menu, une commande absents
   des extraits = invention, même si c'est vrai dans GLPI.
3. Compter séparément : ancrée / partielle / hors cible / inventée / refus
   justifié / faux refus.
