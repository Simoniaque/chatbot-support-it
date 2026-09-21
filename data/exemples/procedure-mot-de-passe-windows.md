# Procédure — Mot de passe Windows et compte utilisateur

> Document d'exemple, fictif. À remplacer par la procédure réelle de
> l'organisation avant toute mise en service.

Concerne : tous les utilisateurs disposant d'un compte Windows (domaine
`ENTREPRISE`). Service responsable : support informatique.

## Règles en vigueur

- Longueur minimale : 12 caractères, avec au moins une majuscule, une
  minuscule, un chiffre et un caractère spécial.
- Validité : 180 jours. Un rappel est envoyé par e-mail 14 jours, puis
  3 jours avant l'expiration.
- Les 5 derniers mots de passe ne peuvent pas être réutilisés.
- Après 5 tentatives échouées, le compte est verrouillé pendant 15 minutes.

## Changer son mot de passe (compte non expiré)

1. Sur un poste connecté au réseau de l'entreprise, appuyer sur
   `Ctrl` + `Alt` + `Suppr`.
2. Choisir **Modifier un mot de passe**.
3. Saisir l'ancien mot de passe, puis deux fois le nouveau.
4. Valider avec `Entrée`. Le changement est immédiat sur le poste ; compter
   jusqu'à 15 minutes pour la messagerie et le VPN.

En télétravail, se connecter d'abord au VPN (voir la procédure VPN), sinon
le nouveau mot de passe n'est pas transmis au domaine.

## Mot de passe oublié ou compte expiré

1. Ouvrir le portail self-service : `https://motdepasse.entreprise.local`
   (accessible depuis le réseau interne et depuis Internet).
2. Cliquer sur **J'ai oublié mon mot de passe**.
3. Saisir son identifiant (format `prenom.nom`).
4. Un code à usage unique est envoyé sur le téléphone mobile déclaré dans
   l'annuaire. Le saisir dans les 10 minutes.
5. Choisir un nouveau mot de passe respectant les règles ci-dessus.

Si aucun numéro de mobile n'est déclaré, ou si le code n'arrive pas :
contacter le support au **poste 4242** (ou `support@entreprise.local`)
depuis un autre poste. L'agent vérifie l'identité (matricule et date de
naissance) avant de réinitialiser. Un mot de passe temporaire est alors
communiqué **oralement uniquement**, jamais par e-mail, et doit être changé
à la première connexion.

## Compte verrouillé

Le verrouillage se lève seul après 15 minutes. Pour le lever plus tôt,
appeler le support (poste 4242). Avant d'appeler, vérifier qu'un ancien mot
de passe n'est pas enregistré quelque part : messagerie sur le téléphone,
connexion Wi-Fi, lecteur réseau — ce sont les causes les plus fréquentes de
verrouillages répétés.

## Ce que le support ne fait jamais

- Demander un mot de passe par e-mail, par téléphone ou par messagerie
  instantanée.
- Envoyer un mot de passe par e-mail.

Tout message de ce type est une tentative d'hameçonnage : le signaler à
`securite@entreprise.local`.
