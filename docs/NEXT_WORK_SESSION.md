# Prochaine session Work — plan d'exécution optimisé

Objectif : utiliser le quota Work uniquement pour l'implémentation et les tests qui justifient un agent de code.

## État déjà préparé

La branche `chatgpt-foundation` contient :

- `import_instagram.py` — lit directement un export ZIP Meta et produit une liste Instagram propre et dédupliquée ;
- `vault.py` — point d'entrée unique (`import` / `rebuild`) ;
- `build_vault.py` — génère l'interface locale de recherche ;
- `setup_windows.ps1` — installation Windows simplifiée ;
- `requirements.txt` et `.gitignore` ;
- documentation d'architecture et tests de base.

## Bloc 1 — robustesse de l'ingestion

1. Tester `vault.py import <zip> --limit 10` sur Windows 11.
2. Corriger les problèmes de chemins Windows et d'encodage.
3. Vérifier Firefox + cookies Instagram avec `yt-dlp`.
4. Vérifier les cas vidéo, Reel supprimé, post/carrousel et lien inaccessible.
5. Ne jamais marquer un élément comme réussi si aucun contenu utile n'a été récupéré.
6. Produire un résumé de fin clair : réussites, échecs, raisons, éléments à retenter.

## Bloc 2 — format structuré durable

Conserver la fiche Markdown brute, mais ajouter un enregistrement JSON par élément avec au minimum :

- `id`
- `source_url`
- `platform`
- `content_type`
- `author`
- `title`
- `description`
- `transcript`
- `images`
- `saved_at` si disponible
- `processed_at`
- `status`

Prévoir des champs enrichis optionnels :

- `summary`
- `themes`
- `entities`
- `places`
- `price_mentions`
- `language`

Le pipeline doit fonctionner même si ces champs IA sont absents.

## Bloc 3 — interface locale

Améliorer `build_vault.py` et `vault.html` :

- recherche instantanée ;
- filtres par auteur, type et thème ;
- compteur de résultats ;
- cartes compactes ;
- lien direct vers le Reel ;
- état "contenu pauvre / transcription absente" visible ;
- fonctionnement 100 % local sans API ;
- bonne utilisation sur mobile et desktop.

## Bloc 4 — traitement incrémental quotidien

Ajouter une commande :

```bash
python vault.py inbox
```

Elle doit :

1. lire un fichier `inbox.txt` contenant des URLs partagées depuis l'iPhone ;
2. traiter uniquement les URLs nouvelles ;
3. reconstruire l'interface ;
4. conserver les échecs pour une nouvelle tentative ;
5. être idempotente.

## Bloc 5 — automatisation Windows/iPhone

Préparer une installation simple :

- raccourci iPhone « Envoyer au Vault » ;
- fichier inbox synchronisé via iCloud Drive ;
- tâche Windows `Vault Inbox` ;
- exécution au démarrage si l'heure planifiée a été manquée ;
- aucun besoin d'ouvrir GitHub ou un terminal au quotidien.

## Bloc 6 — tests et validation

Créer/compléter des tests pour :

- déduplication ;
- normalisation URL ;
- reprise après interruption ;
- journal des erreurs ;
- génération de l'interface ;
- import d'un faux ZIP Meta ;
- reconstruction incrémentale.

Terminer par un essai réel sur 10 éléments avant tout import massif.

## Critère de réussite utilisateur

Une fois installé, l'usage normal doit être :

1. Instagram → Partager → Envoyer au Vault.
2. Le PC traite automatiquement l'élément.
3. L'utilisateur ouvre `vault.html` et recherche ce qu'il avait sauvegardé.

Aucune manipulation GitHub, Python ou PowerShell ne doit être requise au quotidien.
