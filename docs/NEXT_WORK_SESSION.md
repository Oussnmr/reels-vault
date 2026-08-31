# Prochaine session Work — plan d'exécution optimisé

Objectif : utiliser le quota Work uniquement pour les tâches qui bénéficient réellement d'un agent de code : exécution réelle, débogage Windows, robustesse de l'ingestion et tests de régression.

## Architecture désormais retenue

Flux quotidien cible :

1. iPhone / Instagram → **Partager → Envoyer au Vault** ;
2. le raccourci ajoute l'URL dans `Dropbox/Reels Vault/Inbox/inbox.txt` ;
3. Dropbox synchronise le fichier sur Windows ;
4. la tâche Windows lance `vault.py inbox --clear` ;
5. le PC télécharge/transcrit/indexe localement ;
6. `Vault Instagram.md` et `vault_data.json` sont synchronisés vers `OneDrive/Reels Vault/` ;
7. ChatGPT sert d'interface principale de consultation ; `vault.html` reste une interface locale de secours.

Le raccourci iPhone + Dropbox est déjà validé : les URLs sont ajoutées correctement dans `inbox.txt`.

## État déjà préparé sur `chatgpt-foundation`

- `import_instagram.py` — import ZIP Meta et déduplication ;
- `vault.py` — commandes `import`, `inbox`, `add`, `rebuild`, `sync`, `doctor`, `test` ;
- `build_vault.py` — `vault.html`, `vault_data.json`, `Vault Instagram.md` ;
- `setup_windows.ps1` — installation Windows ;
- `install_windows_automation.ps1` — tâche planifiée Windows ;
- `diagnose.ps1` — diagnostic environnement ;
- `smoke_test.py` — test local gratuit ;
- synchronisation automatique des index vers OneDrive ;
- documentation iPhone mise à jour pour Dropbox ;
- `.gitignore` et `requirements.txt`.

## Avant d'utiliser Work — à faire manuellement sur le PC

Ces étapes ne justifient pas de consommer du quota Work :

1. Installer Dropbox pour Windows et vérifier que `inbox.txt` se synchronise.
2. Installer/ouvrir OneDrive pour Windows.
3. Cloner ou mettre à jour la branche `chatgpt-foundation`.
4. Exécuter :

```powershell
.\setup_windows.ps1
python vault.py test
python vault.py doctor --inbox "CHEMIN_DROPBOX\Reels Vault\Inbox\inbox.txt"
```

5. Copier/coller ici les sorties si une erreur apparaît.

Tant que `test` et `doctor` ne sont pas propres, ne pas utiliser Work pour l'import massif.

## Session Work — Bloc 1 PRIORITAIRE : essai réel très petit

Lancer uniquement 5 éléments :

```powershell
python vault.py import "EXPORT_INSTAGRAM.zip" --limit 5
```

ou traiter quelques URLs présentes dans Dropbox :

```powershell
python vault.py inbox --file "CHEMIN_DROPBOX\Reels Vault\Inbox\inbox.txt" --limit 5
```

Pendant cette étape, Work doit uniquement :

1. observer les erreurs réelles ;
2. corriger les chemins Windows / encodages ;
3. vérifier Firefox + cookies Instagram avec `yt-dlp` ;
4. vérifier FFmpeg ;
5. vérifier faster-whisper sur CPU ;
6. vérifier Reel vidéo + post/carrousel ;
7. vérifier contenu supprimé / privé / inaccessible ;
8. vérifier que les erreurs restent retryables ;
9. vérifier la reconstruction et la synchro OneDrive.

Ne pas lancer 838 éléments tant que ce bloc n'est pas stable.

## Session Work — Bloc 2 : rendre l'ingestion robuste

Une fois l'essai de 5 réussi :

- ne jamais marquer `ok` sans contenu utile ;
- journaliser une raison d'échec exploitable ;
- distinguer supprimé / privé / cookies / réseau / téléchargement / transcription ;
- conserver les échecs pour retry ;
- rendre les reprises après interruption réellement idempotentes ;
- produire un résumé final : réussites, échecs, raisons, à retenter ;
- éviter de recharger Whisper inutilement quand aucune vidéo n'est à transcrire.

## Session Work — Bloc 3 : modèle de données durable

Faire évoluer le format structuré sans casser les fiches existantes. Champs minimum :

- `id`
- `source_url`
- `platform`
- `content_type`
- `author`
- `title`
- `description`
- `transcript`
- `images`
- `saved_at`
- `processed_at`
- `status`
- `error_reason`

Champs enrichis optionnels, uniquement si on décide plus tard d'ajouter une couche IA :

- `summary`
- `themes`
- `entities`
- `places`
- `price_mentions`
- `language`

Le pipeline principal doit rester 100 % fonctionnel sans API IA payante.

## Session Work — Bloc 4 : recherche ChatGPT / index compact

Valider que `Vault Instagram.md` reste compact et utile pour ChatGPT :

- une entrée concise par élément ;
- titre / auteur / type / date / URL ;
- description ou transcription utile tronquée intelligemment ;
- éviter les répétitions ;
- conserver `vault_data.json` comme source structurée complète ;
- garder `vault.html` comme interface locale de secours.

Le but est de limiter la quantité de contexte/tokens nécessaire côté ChatGPT.

## Session Work — Bloc 5 : automatisation réelle

Une fois le traitement manuel validé :

```powershell
.\install_windows_automation.ps1 -InboxPath "CHEMIN_DROPBOX\Reels Vault\Inbox\inbox.txt"
```

Puis vérifier :

- tâche `Reels Vault Inbox` ;
- exécution avec PC sur batterie ;
- `StartWhenAvailable` ;
- pas de double exécution ;
- logs dans `~/Vault/logs/inbox-task.log` ;
- inbox vidée uniquement après traitement réussi ;
- archive conservée ;
- OneDrive mis à jour après traitement.

## Session Work — Bloc 6 : montée en charge

Progression recommandée :

1. 5 éléments ;
2. 20 éléments ;
3. 50 éléments ;
4. seulement ensuite l'import complet.

À chaque palier, vérifier : temps moyen, RAM, espace disque, erreurs et qualité des transcriptions.

## Ce qu'il ne faut PAS dépenser du quota Work à faire

- rédiger de la documentation ;
- décider de l'architecture ;
- écrire des checklists ;
- expliquer Raccourcis iPhone ;
- petits changements de configuration ;
- examiner des sorties/logs simples que Chat normal peut analyser ;
- lancer directement l'import massif.

Ces tâches doivent rester dans Chat normal autant que possible.

## Critère de réussite final

L'usage quotidien doit être :

1. Instagram → **Partager → Envoyer au Vault**.
2. Rien d'autre à faire sur l'iPhone.
3. Le PC traite automatiquement quand il est disponible.
4. OneDrive contient toujours un index à jour.
5. ChatGPT peut servir d'interface principale pour retrouver les sauvegardes.

Aucune manipulation GitHub, Python ou PowerShell ne doit être requise au quotidien après l'installation initiale.
