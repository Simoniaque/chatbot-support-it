# Documents d'exemple

Cinq procédures de support IT **fictives** (mot de passe Windows, VPN,
imprimantes, messagerie, demande de matériel), rédigées pour essayer le
chatbot avec un corpus qui ne se limite pas au manuel GLPI.

Pour les utiliser :

```powershell
copy data\exemples\*.md data\corpus\
python -m src.ingestion
```

Chaque fichier commence par un avertissement « document d'exemple, fictif ».
À remplacer par les procédures réelles de l'organisation avant toute mise
en service — et à retirer de `data/corpus/` à ce moment-là (l'ingestion
supprime alors leurs morceaux de la base).
