# iPhone → Reels Vault

Objectif : depuis Instagram, utiliser **Partager → Envoyer au Vault**, puis laisser le PC traiter les nouveaux liens automatiquement.

## Architecture retenue

Le flux final est volontairement simple :

1. iPhone / Instagram → raccourci **Envoyer au Vault** ;
2. le raccourci ajoute l'URL dans `Dropbox/Reels Vault/Inbox/inbox.txt` ;
3. Dropbox synchronise ce fichier sur le PC ;
4. `vault.py inbox --clear` traite les nouvelles URLs ;
5. le Vault est reconstruit ;
6. `Vault Instagram.md` et `vault_data.json` sont copiés dans `OneDrive/Reels Vault/` pour la consultation depuis ChatGPT.

Dropbox sert uniquement de petite boîte aux lettres pour les URLs. OneDrive reste la destination du Vault final.

## 1. Raccourci iPhone — configuration validée

Dans l'app **Raccourcis** :

1. créer un raccourci nommé **Envoyer au Vault** ;
2. activer **Afficher dans la feuille de partage** ;
3. accepter les **URL** ;
4. ajouter l'action **Texte** avec **Entrée du raccourci** ;
5. ajouter l'action Dropbox **Ajouter à la suite au fichier texte** ;
6. contenu : sortie de l'action **Texte** ;
7. chemin : `Reels Vault/Inbox/inbox.txt` ;
8. activer **Créer une nouvelle ligne**.

Usage quotidien : Instagram → Partager → Envoyer au Vault.

Ce raccourci a été validé sur iPhone : chaque partage ajoute correctement une nouvelle URL au fichier Dropbox.

## 2. Côté Windows

Installer **Dropbox pour Windows** avec le même compte que sur l'iPhone.

Une fois Dropbox synchronisé, repérer le fichier `inbox.txt`. Exemple typique :

```powershell
$HOME\Dropbox\Reels Vault\Inbox\inbox.txt
```

Le chemin exact peut varier selon l'installation Dropbox.

Vérifier ensuite que le fichier est disponible localement et qu'il contient bien les URLs ajoutées depuis l'iPhone.

## 3. Diagnostic

Depuis le dépôt Reels Vault :

```powershell
python vault.py doctor --inbox "CHEMIN_COMPLET_VERS_DROPBOX\Reels Vault\Inbox\inbox.txt"
```

Puis lancer le smoke test local :

```powershell
python vault.py test
```

## 4. Tester manuellement l'inbox

```powershell
python vault.py inbox --file "CHEMIN_COMPLET_VERS_DROPBOX\Reels Vault\Inbox\inbox.txt" --clear
```

`--clear` archive les URLs traitées dans le Vault puis vide l'inbox après succès.

## 5. Installer l'automatisation Windows

```powershell
.\install_windows_automation.ps1 -InboxPath "CHEMIN_COMPLET_VERS_DROPBOX\Reels Vault\Inbox\inbox.txt"
```

Par défaut, Windows vérifie l'inbox toutes les 30 minutes. Pour changer l'intervalle :

```powershell
.\install_windows_automation.ps1 -InboxPath "CHEMIN_COMPLET_VERS_DROPBOX\Reels Vault\Inbox\inbox.txt" -IntervalMinutes 15
```

Le script :

- mémorise le chemin de `inbox.txt` dans `VAULT_INBOX` ;
- crée automatiquement la tâche planifiée **Reels Vault Inbox** ;
- traite l'inbox avec `vault.py inbox --clear` ;
- ignore un nouveau lancement si le précédent tourne encore ;
- fonctionne aussi sur batterie ;
- écrit les logs dans `~/Vault/logs/inbox-task.log`.

Pour tester immédiatement la tâche :

```powershell
Start-ScheduledTask -TaskName "Reels Vault Inbox"
```

Pour la supprimer :

```powershell
Unregister-ScheduledTask -TaskName "Reels Vault Inbox" -Confirm:$false
```

## 6. Usage quotidien final

Une fois l'installation terminée, aucune manipulation technique ne doit être nécessaire au quotidien :

1. Instagram → **Partager → Envoyer au Vault** ;
2. Dropbox synchronise l'URL vers le PC ;
3. Windows traite automatiquement l'inbox ;
4. le Reel est téléchargé/transcrit et ajouté au Vault ;
5. le Vault compact est synchronisé vers OneDrive ;
6. ChatGPT peut utiliser ce Vault comme source de consultation.

Si le PC est éteint, les URLs restent simplement en attente dans Dropbox jusqu'au prochain démarrage et à la prochaine exécution de la tâche.

## 7. Ajout ponctuel depuis le PC

```powershell
python vault.py add "https://www.instagram.com/reel/XXXXXXXX/"
```

Cela traite immédiatement le lien puis régénère la page de recherche et l'index compact.
