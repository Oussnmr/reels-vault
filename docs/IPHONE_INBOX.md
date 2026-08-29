# iPhone → Reels Vault

Objectif : depuis Instagram, utiliser **Partager → Envoyer au Vault**, puis laisser le PC traiter les nouveaux liens automatiquement.

## 1. Raccourci iPhone

Dans l'app **Raccourcis** :

1. Créer un nouveau raccourci nommé **Envoyer au Vault**.
2. Activer **Afficher dans la feuille de partage**.
3. Limiter l'entrée aux **URL**.
4. Ajouter l'action **Ajouter au fichier texte**.
5. Utiliser **Entrée du raccourci** comme texte à ajouter.
6. Fichier : `inbox.txt` dans le dossier Shortcuts/iCloud Drive.
7. Activer **Créer une nouvelle ligne**.

Usage quotidien : Instagram → Partager → Plus → Envoyer au Vault.

## 2. Côté Windows

Installer iCloud pour Windows et activer iCloud Drive. Après le premier partage depuis l'iPhone, repérer `inbox.txt` avec PowerShell :

```powershell
Get-ChildItem "$HOME\iCloudDrive" -Recurse -Filter "inbox.txt" | Select-Object FullName
```

Faire un clic droit sur le fichier dans l'Explorateur → **Toujours conserver sur cet appareil**.

## 3. Tester manuellement

Depuis le dépôt Reels Vault :

```powershell
python vault.py inbox --file "CHEMIN_COMPLET_VERS_INBOX.txt" --clear
```

`--clear` archive les URLs traitées dans le Vault puis vide l'inbox après succès.

## 4. Installer l'automatisation en une commande

Depuis le dépôt Reels Vault :

```powershell
.\install_windows_automation.ps1 -InboxPath "CHEMIN_COMPLET_VERS_INBOX.txt"
```

Par défaut, Windows vérifie l'inbox toutes les 30 minutes. Pour changer l'intervalle :

```powershell
.\install_windows_automation.ps1 -InboxPath "CHEMIN_COMPLET_VERS_INBOX.txt" -IntervalMinutes 15
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

## 5. Usage quotidien

Une fois l'installation terminée, tu ne dois normalement plus ouvrir PowerShell.

1. Sur Instagram : **Partager → Envoyer au Vault**.
2. Le lien arrive dans `inbox.txt` via iCloud Drive.
3. Le PC le détecte au prochain passage de la tâche planifiée.
4. Le Reel est téléchargé/transcrit et ajouté au Vault.
5. `vault.html` est régénéré automatiquement.

Si le PC est éteint, la tâche est configurée avec `StartWhenAvailable` et reprendra au prochain démarrage possible.

## 6. Ajout ponctuel depuis le PC

Sans passer par l'iPhone :

```powershell
python vault.py add "https://www.instagram.com/reel/XXXXXXXX/"
```

Cela traite immédiatement le lien puis régénère la page de recherche.
