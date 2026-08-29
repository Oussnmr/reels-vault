# Reels Vault — architecture cible

## Objectif

Transformer des Reels/posts sauvegardés en une mémoire personnelle consultable, avec le moins d'actions manuelles possible.

Usage quotidien visé :

1. Depuis Instagram/TikTok : **Partager → Envoyer au Vault**.
2. Le lien arrive dans une inbox.
3. Le PC traite automatiquement les nouveaux liens.
4. Le contenu est téléchargé/transcrit localement.
5. Une fiche structurée est générée et ajoutée à l'index.
6. L'interface locale est régénérée.
7. L'utilisateur recherche ensuite en langage naturel ou via filtres.

## Principes de conception

- **Local-first** : audio, images, transcriptions et index restent sur la machine par défaut.
- **Idempotent** : un même lien ne doit jamais être retraité inutilement.
- **Reprise après interruption** : journalisation systématique.
- **IA seulement là où elle apporte de la valeur** : téléchargement, transcription et extraction technique doivent rester locaux.
- **Coût/quota minimal** : ne jamais relire toutes les transcriptions à chaque requête.
- **Données structurées** : conserver les champs utiles séparément du texte libre.
- **Interface simple** : aucune interaction quotidienne avec GitHub ou PowerShell une fois installé.

## Pipeline cible

```text
Instagram / TikTok
        ↓
Raccourci iPhone
        ↓
inbox.txt
        ↓
ingest.py
        ├── métadonnées yt-dlp
        ├── audio
        ├── transcription faster-whisper
        ├── captures vidéo / images carrousel
        └── raw/*.md
        ↓
Enrichissement / structuration
        ├── résumé concret
        ├── thèmes
        ├── type de contenu
        ├── lieux
        ├── prix
        ├── adresses
        └── autres champs utiles
        ↓
data/index.json
        ↓
Interface locale / recherche
```

## Schéma de donnée visé

Chaque élément devra pouvoir être représenté au minimum comme ceci :

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
  "locations": [
    {
      "name": "...",
      "city": "Bruxelles",
      "country": "Belgique",
      "address": "..."
    }
  ],
  "prices": ["15-25 €"],
  "transcript": "...",
  "images": ["images/...jpg"],
  "processed_at": "2026-08-29"
}
```

Tous les champs spécialisés doivent rester optionnels afin de supporter aussi bien des restaurants que des voyages, recettes, conseils business, produits, tutoriels, etc.

## Séparation des responsabilités

### `ingest.py`
Responsable uniquement de l'acquisition : URL → contenu brut fiable.

### Enrichissement
Responsable de transformer le brut en données courtes et structurées. Cette couche pourra évoluer indépendamment du téléchargement.

### Index
Une représentation compacte de tout le Vault. Les recherches courantes ne doivent pas nécessiter de relire les fichiers bruts.

### Interface
Doit fonctionner localement, idéalement sans serveur et sans dépendance externe pour l'usage courant.

## Priorités d'implémentation

1. Stabiliser l'ingestion et la gestion des erreurs.
2. Ajouter un format de donnée structuré stable.
3. Générer automatiquement l'index.
4. Générer une interface de recherche locale.
5. Simplifier l'installation Windows.
6. Ajouter l'inbox iPhone + tâche planifiée.
7. Tester sur un petit échantillon réel avant import massif.

## Critère de réussite

Le projet est considéré utilisable lorsque, après installation initiale, l'ajout d'un nouveau contenu ne demande pas plus que :

**Partager → Envoyer au Vault**

et que le contenu devient ensuite retrouvable sans manipulation technique supplémentaire.
