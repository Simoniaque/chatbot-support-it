# Procédure — Accès distant par VPN

> Document d'exemple, fictif. À remplacer par la procédure réelle de
> l'organisation avant toute mise en service.

Concerne : télétravail et déplacements. Le VPN donne accès aux lecteurs
réseau, à l'intranet et aux applications métier depuis l'extérieur.

## Prérequis

- Un ordinateur portable fourni par l'entreprise. Le VPN n'est pas autorisé
  sur les postes personnels.
- Le client **FortiClient VPN**, installé par le support lors de la remise du
  poste. S'il manque, ouvrir un ticket : l'installation nécessite les droits
  administrateur.
- L'application **Microsoft Authenticator** sur le téléphone mobile, activée
  lors de l'enrôlement du compte (second facteur obligatoire).

## Se connecter

1. Lancer FortiClient VPN depuis le menu Démarrer.
2. Choisir le profil **ENTREPRISE — Télétravail** (déjà configuré ; adresse
   `vpn.entreprise.local`, port 443).
3. Saisir son identifiant Windows (`prenom.nom`) et son mot de passe Windows.
4. Approuver la notification reçue dans Microsoft Authenticator dans les
   60 secondes.
5. L'icône FortiClient devient verte : la connexion est établie.

La session VPN se coupe automatiquement après **10 heures** ou après
30 minutes sans activité.

## Erreurs fréquentes

| Message | Cause | Solution |
|---|---|---|
| « Identifiants incorrects » (erreur -12) | Mot de passe Windows changé récemment ou expiré | Vérifier le mot de passe sur le portail self-service, puis réessayer |
| « Aucune notification reçue » | Téléphone sans réseau, ou Authenticator non enrôlé | Vérifier la connexion du téléphone ; sinon réenrôler via `https://mfa.entreprise.local` |
| « Impossible de joindre la passerelle » (erreur -5) | Le réseau utilisé bloque le port 443 sortant (hôtel, box avec contrôle parental) | Essayer le partage de connexion du téléphone |
| Connexion établie mais lecteurs réseau absents | Le poste s'est connecté avant le VPN | Se déconnecter de Windows et se reconnecter, VPN actif |
| Déconnexions toutes les quelques minutes | Wi-Fi instable | Se rapprocher de la box ou passer en câble |

## Bonnes pratiques

- Se déconnecter du VPN quand il n'est plus nécessaire : la bande passante
  de la passerelle est partagée.
- Ne jamais laisser une session VPN ouverte sur un poste sans surveillance
  dans un lieu public.
- En cas de perte ou de vol du poste, appeler immédiatement le support
  (poste 4242) pour révoquer l'accès.
