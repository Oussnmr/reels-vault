# Reels Vault — architecture cible

## Objectif

Transformer les Reels/posts sauvegardés en une mémoire personnelle consultable avec le moins d'actions manuelles possible, sans API IA payante.

## Usage quotidien visé

1. Sur l'iPhone : Instagram → **Partager → Envoyer à Vault**.
2. Le raccourci ajoute l'URL dans `Dropbox/Reels Vault/Inbox/inbox.txt`.
3. Dropbox synchronise ce petit fichier vers Windows.
4. Une tâche planifiée lance `python vault.py inbox --clear`.
5. Le PC télécharge/transcrit localement le contenu.
6. Le Vault est reconstruit.
7. L'index compact est copié dans `OneDrive/Reels Vault/`.
8. ChatGPT peut utiliser cet index comme source lorsque l'accès OneDrive approprié est disponible.

```text
Instagram sur iPhone
        ↓
Raccourci iOS « Envoyer à Vault »
        ↓
Dropbox / Reels Vault / Inbox / inbox.txt
        ↓
Windows Task Scheduler
        ↓
vault.py inbox
        ↓
ingest.py
 ├─ yt-dlp / gallery-dl
 ├─ faster-whisper local
 ├─ captures/images
 ├─ raw/*.md
 └─ journal.json
        ↓
build_vault.py
 ├─ vault_data.json
 ├─ vault.html
 └─ Vault Instagram.md
        ↓
OneDrive / Reels Vault
        ↓
ChatGPT + interface locale de secours
```

## Principes

- **Capture mobile minimale** : le téléphone ne fait qu'ajouter une URL à un fichier texte.
- **Local-first** : téléchargement, transcription et génération d'index se font sur le PC.
- **Zéro API payante obligatoire** : le pipeline principal ne nécessite aucun crédit IA.
- **Idempotence** : `journal.json` empêche de retraiter les URLs déjà réussies.
- **Aucune perte d'URL** : avec `--clear`, seules les URLs marquées `ok` sont retirées de l'inbox ; les échecs et URLs non encore traitées restent pour une prochaine exécution.
- **Reprise après interruption** : chaque URL est journalisée séparément.
- **Sortie compacte pour ChatGPT** : `Vault Instagram.md` évite d'envoyer toutes les données brutes à chaque recherche.
- **Interface locale de secours** : `vault.html` reste utilisable sans ChatGPT ni connexion cloud.

## Données actuelles

La couche brute est volontairement simple et robuste. Chaque fiche Markdown contient notamment :

- URL source ;
- plateforme ;
- type vidéo/carrousel ;
- auteur ;
- date de traitement ;
- description ;
- transcription ;
- références vers les images locales.

`build_vault.py` transforme ensuite ces fiches en `vault_data.json` et en index Markdown compact.

## Schéma enrichi futur

Les champs suivants pourront être ajoutés sans rendre le pipeline dépendant d'une IA :

```json
{
  "id": "insta_xxx",
  "source_url": "https://...",
  "platform": "Instagram",
  "content_type": "restaurant",
  "author": "...",
  "title": "...",
  "summary": "...",
  "topics": ["restaurant", "bruxelles", "japonais"],
  "locations": [{"name": "...", "city": "Bruxelles", "country": "Belgique"}],
  "prices": ["15-25 €"],
  "transcript": "...",
  "images": ["images/...jpg"],
  "processed_at": "2026-08-29"
}
```

Tous les champs enrichis restent optionnels.

## Séparation des responsabilités

### `import_instagram.py`
Import initial d'un export Meta → liste propre et dédupliquée.

### `ingest.py`
Acquisition fiable : URL → contenu brut local + journal d'état.

### `build_vault.py`
Génération déterministe et gratuite de l'index JSON, HTML et Markdown compact.

### `vault.py`
Point d'entrée unique : import, inbox, add, rebuild, sync, doctor, test.

### Dropbox
Transport uniquement des nouvelles URLs depuis l'iPhone. Le volume est négligeable.

### OneDrive
Sortie synchronisée destinée à la consultation, notamment depuis ChatGPT. Les vidéos/audio bruts n'ont pas besoin d'y être copiés.

## Validation avant import massif

1. `python vault.py test`
2. `python vault.py doctor --inbox "...\\Dropbox\\Reels Vault\\Inbox\\inbox.txt"`
3. Test réel de 5 URLs.
4. Corriger tout problème Windows/cookies/téléchargement.
5. Test de 20 puis 50 URLs.
6. Import complet seulement après validation.
7. Activer ensuite la tâche planifiée permanente.

## Critère de réussite

Après l'installation initiale, l'ajout quotidien doit demander uniquement :

**Instagram → Partager → Envoyer à Vault**

Aucune manipulation GitHub, Python ou PowerShell ne doit être requise au quotidien.
