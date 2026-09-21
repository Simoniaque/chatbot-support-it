# Démo pour l'oral — déroulé, questions, plans B

Durée cible : **8 à 10 minutes** de démonstration, à insérer après la
présentation du contexte et avant la discussion des résultats. Tout tourne
en local ; aucune connexion Internet nécessaire pendant la démo.

Fil conducteur : *un chatbot qui préfère se taire plutôt qu'inventer, et
qui donne une issue quand il se tait.* Chaque étape montre une des cinq
protections, dans l'ordre où une question les traverse.

---

## Avant l'oral (la veille, puis 30 minutes avant)

La veille :

1. `git pull`, puis `python -m pytest` : 56 tests verts en moins de 2 s.
2. `python -m src.ingestion` : doit afficher « 784 déjà présent(s), 0 indexé ».
3. Docker Desktop lancé, puis dans `outils\glpi-test` : `docker compose up -d`.
   Ouvrir http://localhost:8080 et vérifier que GLPI répond (glpi / glpi).
4. Dans `.env` : `GLPI_URL=http://localhost:8080`, `GLPI_APP_TOKEN` renseigné
   (le jeton est dans `outils/glpi-test/app_token.txt`).
5. Lancer `uvicorn src.api:app` (sans `--reload`), ouvrir http://localhost:8000,
   se connecter avec `m.dupont` (mot de passe dans
   `outils/glpi-test/utilisateur_test.json`), poser une question pour
   **charger le modèle en mémoire** — le premier appel prend 20 s, les
   suivants 1 à 8 s.
6. Vérifier http://localhost:8000/sante : `modele_llm: qwen2.5:7b`,
   `glpi_configure: true`, `connexion_requise: true`.

30 minutes avant : refaire les étapes 3, 5 et 6. Fermer tout ce qui utilise
le GPU (jeux, navigateurs lourds) : la RAM et la VRAM partagées ont fait
passer une campagne de 2 s à 90 s par question.

Garder ouverts, dans des onglets séparés : l'interface (8000), GLPI (8080,
connecté en `glpi`, page *Assistance > Tickets*), et `/sante`.

---

## Déroulé

### 0. Cadre (30 s) — sans écran

« Un assistant de support interne, qui répond à partir de la documentation
de l'organisation, cite ses sources, et refuse de répondre plutôt que
d'inventer. Tout tourne sur ce poste : aucun document ne sort. »

Montrer `/sante` : les modèles (Qwen 2.5 7B pour rédiger, nomic-embed-text
pour chercher), le seuil, GLPI configuré.

### 1. Une question couverte (1 min) — la base

Se connecter dans l'interface avec `m.dupont`. Faire remarquer : *ce sont
ses identifiants GLPI, le chatbot n'a pas de base d'utilisateurs.*

Poser : **« Comment mettre un ticket en attente ? »**

À montrer :
- la réponse (règle ITIL, tirée du manuel GLPI) ;
- déplier **« 1 source »** : Help Center GLPI, page 222, l'extrait ;
- la ligne « 4 extraits analysés, 3 écartés » : *quatre passages trouvés,
  un seul jugé utile, la réponse est rédigée à partir de celui-là seulement.*

### 2. Une question hors sujet (30 s) — le seuil

Poser : **« Quelle est la capitale de l'Australie ? »**

Réponse immédiate (0 s) : refus, « Aucun passage de la documentation ne se
rapproche de cette question ». *Le seuil de distance coupe avant même
d'appeler le modèle.* Ne pas cliquer sur le ticket ici : « Non merci ».

### 3. Une question proche mais sans réponse (1 min) — la vérification

Poser : **« Quel est le mot de passe administrateur de notre GLPI ? »**

Refus, mais avec l'autre explication : « Des passages proches ont été
trouvés, mais aucun ne répond réellement à la question ». *Le manuel parle
de profils et d'administrateurs, donc la recherche trouve des passages
proches ; chacun a été soumis au modèle avec une question fermée — « cet
extrait répond-il ? » — et tous ont été écartés. C'est ce filtre qui a fait
passer les inventions de 44 % à 0.*

### 4. L'escalade vers GLPI (2 min) — l'issue

Poser : **« Comment installer Photoshop ? »**

Refus (le manuel GLPI et la procédure matériel n'expliquent pas comment
l'installer). Cette fois cliquer sur **Créer le ticket** après avoir saisi
une précision (« Poste 12, licence à prévoir »). Montrer « Ticket n°N créé
à votre nom », cliquer **Voir le ticket** : dans GLPI, le ticket porte la
question, la précision, et **Marie Dupont comme demandeur** — pas un compte
technique. *Le chatbot ne crée jamais de ticket seul ; c'est l'utilisateur
qui confirme.*

Basculer sur l'onglet GLPI *Assistance > Tickets* pour le voir dans la liste.

### 5. Une procédure interne (1 min) — le corpus

Poser : **« Ma boîte mail est pleine, que faire ? »**

Réponse tirée de la FAQ messagerie (procédure d'exemple), source
`faq-messagerie.md`. *Même mécanisme pour n'importe quel document déposé
dans le dossier du corpus : PDF, texte, Markdown. L'ingestion est
incrémentale — ajouter une page prend quelques secondes.*

Puis **« Comment réinitialiser mon mot de passe Windows ? »** : *cette
question était refusée quand le corpus ne contenait que le manuel GLPI ;
avec la procédure interne, elle est couverte. Le comportement suit le
corpus, pas le modèle.*

### 6. Le journal (1 min) — la mesure

Dans un terminal : `python -m src.journal`

Montrer les compteurs : questions, refus, tickets, avis. *Chaque échange
est tracé avec l'utilisateur, les extraits vérifiés et écartés, le score,
la durée. C'est avec ça que le seuil a été calibré et que les campagnes de
mesure ont été faites.*

Cliquer 👍 sur une réponse, relancer la commande : le compteur d'avis bouge.

### 7. Conclusion (30 s)

Revenir sur `tests/questions_test.md`, tableau de synthèse : *neuf
campagnes ; de 7 inventions sur 16 réponses à 0 sur 9 ; le hors sujet
refusé à 100 %. Et une leçon de méthode : la première évaluation notait
« correctes » des réponses inventées, parce qu'elles étaient plausibles —
depuis, chaque réponse est vérifiée contre le texte des extraits.*

---

## Ce que le jury peut demander, et où est la réponse

| Question probable | Réponse courte | Où c'est écrit |
|---|---|---|
| Pourquoi 0,65 ? | Mesuré : couvertes 0,31–0,63, hors sujet 0,70–0,97 ; dépend du modèle d'embeddings | `docs/seuil-pertinence.md` |
| Pourquoi pas Mistral, annoncé au départ ? | Mesuré à réglage égal : 1 invention sur 9 contre 0 sur 8 pour Qwen, et un contresens sur un extrait | `tests/questions_test.md`, campagne 8 |
| Comment savez-vous qu'une réponse n'est pas inventée ? | Chaque affirmation est comparée au texte des extraits retenus, jamais à ce qu'on sait du sujet | `tests/questions_test.md`, « Correction de l'étalon » |
| Que se passe-t-il si le modèle se trompe quand même ? | Le journal le tracera, l'utilisateur peut cliquer 👎, et le support voit la question via le ticket | `README.md`, journalisation |
| Et la sécurité des mots de passe ? | Ils ne servent qu'à ouvrir la session GLPI, ne sont ni stockés ni journalisés ; en production GLPI doit être en HTTPS ; le profil Self-Service empêche de créer un ticket au nom d'un autre | `docs/choix-techniques.md`, connexion GLPI |
| Un modèle plus gros ferait mieux ? | Comme juge : non mesurable (14/16 contre 13/16). Comme rédacteur : oui, Qwen 7B a suffi | campagnes 6 et 8 |
| Combien ça coûte ? | Rien : tout est local et gratuit ; 5 Go de modèles, un GPU de 8 Go suffit | `README.md`, installation |
| Ça tient à l'échelle ? | Ingestion incrémentale ; ChromaDB suffit pour quelques milliers de pages ; l'archivage reste à définir | `README.md`, « À planifier » |

---

## Plans B

| Problème | Que faire |
|---|---|
| Ollama ne répond pas (bulle rouge « Impossible de joindre Ollama ») | Lancer Ollama (icône dans la barre des tâches) ; la question suivante passe |
| Première réponse très lente | C'est le chargement du modèle : dire « le modèle se charge en mémoire, ça n'arrive qu'une fois » ; d'où l'étape 5 de la préparation |
| GLPI ne répond pas (connexion impossible, 502) | Vider `GLPI_URL` dans `.env`, relancer uvicorn : la démo fonctionne en anonyme, sans les étapes 4 et connexion ; dire que l'escalade a été validée sur GLPI 11 (`docs/glpi-test.md`) |
| Docker refuse de démarrer | Idem ; ne pas essayer de réparer en séance |
| Le modèle répond à côté | Ne pas masquer : déplier les sources et montrer que l'extrait ne dit pas ça — c'est précisément le contrôle qui a servi à mesurer ; puis cliquer 👎 |
| Le modèle refuse une question couverte | Dire que c'est le compromis choisi : un faux refus mène à un ticket, une invention mène à une mauvaise manipulation |
| Pas d'écran / vidéoprojecteur en panne | Les tableaux de `tests/questions_test.md` et le schéma du README suffisent pour raconter la même histoire |

À ne pas faire en séance : changer un réglage dans `.env`, relancer
l'ingestion, montrer le mot de passe de `m.dupont` à l'écran.
