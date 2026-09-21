# Procédure — Imprimantes et copieurs

> Document d'exemple, fictif. À remplacer par la procédure réelle de
> l'organisation avant toute mise en service.

## Ajouter une imprimante réseau sur son poste

Toutes les imprimantes sont publiées sur le serveur d'impression
`\\IMPRESSION`. Il n'y a rien à télécharger : le pilote est installé
automatiquement.

1. Ouvrir l'Explorateur de fichiers et taper `\\IMPRESSION` dans la barre
   d'adresse, puis `Entrée`.
2. Double-cliquer sur l'imprimante souhaitée. Les noms suivent le format
   `BAT-ETAGE-MODELE`, par exemple `A-2-CANON` pour le copieur Canon du
   2e étage du bâtiment A.
3. Attendre le message « L'imprimante a été ajoutée ».
4. Pour la définir par défaut : **Paramètres > Imprimantes et scanners**,
   choisir l'imprimante, **Définir par défaut**.

## Impression sécurisée (copieurs Canon)

Les copieurs Canon retiennent les documents jusqu'à ce que l'utilisateur
s'identifie sur l'appareil : rien ne sort avant.

1. Imprimer normalement depuis le poste.
2. Devant le copieur, passer son **badge** sur le lecteur (ou saisir son
   identifiant et son mot de passe Windows sur l'écran).
3. Sélectionner les documents à imprimer, puis **Imprimer**.

Les documents non récupérés sont supprimés après **24 heures**.

## Problèmes courants

**« Imprimante hors ligne »** : le poste n'arrive plus à joindre le serveur
d'impression. Vérifier que le poste est bien sur le réseau de l'entreprise
(câble ou VPN). Si oui, supprimer l'imprimante et la rajouter depuis
`\\IMPRESSION`.

**Le document reste « en attente » dans la file** : un document précédent
bloque la file. Ouvrir la file d'impression (double-clic sur l'imprimante
dans **Paramètres > Imprimantes**), annuler le document bloqué. Si la file
ne se vide pas, redémarrer le poste.

**Bourrage papier** : suivre les indications de l'écran du copieur, qui
montre où ouvrir. Retirer le papier sans le déchirer. Ne jamais forcer :
si une feuille résiste, appeler le support.

**Toner vide** : les toners sont stockés dans l'armoire du local reprographie
de chaque bâtiment (accès par badge). Remplacer le toner en suivant le guide
collé à l'intérieur de la trappe. Déposer l'ancien toner dans le bac de
recyclage du même local, et prévenir le support pour le réapprovisionnement.

**Impression décalée, traits, taches** : lancer le nettoyage depuis le menu
**Entretien** du copieur. Si le défaut persiste, ouvrir un ticket en précisant
le nom de l'imprimante : un technicien du prestataire intervient sous 48 h.

## Scanner vers e-mail

Sur le copieur : **Scanner > Envoyer vers moi**. Le document arrive en PDF
dans la boîte de messagerie de l'utilisateur identifié par le badge. Taille
maximale : 25 Mo (environ 150 pages en noir et blanc).
