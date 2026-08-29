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

## 4. Configuration permanente

Pour ne plus fournir le chemin à chaque fois :

```powershell
[Environment]::SetEnvironmentVariable("VAULT_INBOX", "CHEMIN_COMPLET_VERS_INBOX.txt", "User")
```

Fermer puis rouvrir PowerShell. Ensuite :

```powershell
python vault.py inbox --clear
```

## 5. Automatisation Windows

La tâche planifiée finale devra lancer cette commande périodiquement :

```powershell
python CHEMIN_DU_REPO\vault.py inbox --clear
```

Le journal de `ingest.py` évite de retraiter les mêmes publications, même si une URL réapparaît.

## 6. Ajout ponctuel depuis le PC

Sans passer par l'iPhone :

```powershell
python vault.py add "https://www.instagram.com/reel/XXXXXXXX/"
```

Cela traite immédiatement le lien puis régénère la page de recherche.
