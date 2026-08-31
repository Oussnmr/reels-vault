#!/usr/bin/env python3
"""
ingest.py — transforme une liste de liens TikTok / Instagram en fiches Markdown.

Pour chaque vidéo :
  1. récupère les métadonnées (titre, description, auteur, hashtags)
  2. télécharge l'audio et le transcrit en local avec faster-whisper
  3. extrait 3 images de la vidéo (pour le texte incrusté à l'écran)
  4. écrit une fiche Markdown dans vault/raw/

Le script reprend là où il s'est arrêté : on peut le couper (Ctrl+C) et le
relancer sans retraiter ce qui est déjà fait.

Usage :
    python ingest.py mes_liens.txt
    python ingest.py saved_posts.json --cookies chrome
    python ingest.py liens.txt --limite 20        (pour tester sur 20 vidéos)
"""

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

# ---------------------------------------------------------------- configuration

VAULT = Path.home() / "vault"          # modifiable avec --vault
MODELE_WHISPER = "small"               # tiny / base / small / medium
PAUSE_ENTRE_VIDEOS = 3                 # secondes, pour ne pas se faire bloquer
NB_IMAGES = 3
# Les Shorts/Reels sont transcrits en entier. Pour les vidéos YouTube longues,
# le début suffit généralement à la recherche et évite de bloquer la file.
LIMITE_TRANSCRIPTION_YOUTUBE_S = 5 * 60

YTDLP = [sys.executable, "-m", "yt_dlp"]
GALLERYDL = [sys.executable, "-m", "gallery_dl"]

MOTIF_LIEN = re.compile(
    r"https?://(?:www\.|vm\.|vt\.)?(?:tiktok\.com|instagram\.com|youtube\.com|youtu\.be)/[^\s\"'<>,\)\]]+"
)


# ---------------------------------------------------------------- utilitaires

def log(message):
    print(f"[{datetime.now():%H:%M:%S}] {message}", flush=True)


def verifier_outils():
    """Verifie que yt-dlp et ffmpeg repondent avant de commencer."""
    manquants = []

    try:
        subprocess.run(YTDLP + ["--version"], capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        manquants.append("yt-dlp  ->  pip install yt-dlp")

    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        manquants.append("ffmpeg  ->  winget install Gyan.FFmpeg  (puis rouvrir PowerShell)")

    if manquants:
        log("ERREUR : outil(s) manquant(s)")
        for m in manquants:
            log(f"   {m}")
        sys.exit(1)


def extraire_liens(chemin):
    """Récupère toutes les URLs TikTok/Instagram d'un fichier, quel que soit
    son format (txt, csv, json d'export). Les doublons sont supprimés."""
    texte = Path(chemin).read_text(encoding="utf-8", errors="ignore")
    liens, vus = [], set()
    for lien in MOTIF_LIEN.findall(texte):
        lien = lien.rstrip(".,;")
        if lien not in vus:
            vus.add(lien)
            liens.append(lien)
    return liens


def options_cookies(cookies):
    """--cookies accepte soit un nom de navigateur (firefox, edge...),
    soit le chemin d'un fichier cookies.txt exporte depuis le navigateur."""
    if not cookies:
        return []
    if Path(cookies).exists():
        return ["--cookies", str(Path(cookies).resolve())]
    return ["--cookies-from-browser", cookies]


def charger_journal(chemin):
    if chemin.exists():
        return json.loads(chemin.read_text(encoding="utf-8"))
    return {}


def sauver_journal(chemin, journal):
    chemin.write_text(
        json.dumps(journal, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def identifiant(lien):
    """Un nom de fichier court et sûr, dérivé de l'URL."""
    fin = lien.rstrip("/").split("/")[-1].split("?")[0]
    fin = re.sub(r"[^A-Za-z0-9_-]", "", fin)[:40]
    if "tiktok" in lien:
        plateforme = "tiktok"
    elif "youtu" in lien:
        plateforme = "youtube"
    else:
        plateforme = "insta"
    return f"{plateforme}_{fin or str(abs(hash(lien)))[:10]}"


# ---------------------------------------------------------------- étapes

def recuperer_metadonnees(lien, cookies):
    commande = YTDLP + ["--dump-single-json", "--ignore-no-formats-error",
                        "--no-warnings", "--skip-download"]
    commande += options_cookies(cookies)
    commande.append(lien)
    resultat = subprocess.run(commande, capture_output=True, text=True, timeout=120)
    if resultat.returncode != 0:
        raise RuntimeError((resultat.stderr or "yt-dlp a échoué").strip()[:300])
    return json.loads(resultat.stdout.splitlines()[0])


def est_video(meta):
    """Reconnaît une vidéo même si yt-dlp ne fournit plus sa durée."""
    if meta.get("duration"):
        return True
    return any(
        format_.get("vcodec") not in (None, "none")
        for format_ in (meta.get("formats") or [])
    )


def limite_youtube_longue(lien, meta):
    """Retourne la durée à analyser pour une longue vidéo YouTube, sinon 0."""
    if "youtu" not in lien.lower() or "/shorts/" in lien.lower():
        return 0
    try:
        duree = float(meta.get("duration") or 0)
    except (TypeError, ValueError):
        return 0
    return LIMITE_TRANSCRIPTION_YOUTUBE_S if duree > LIMITE_TRANSCRIPTION_YOUTUBE_S else 0


def telecharger_media(lien, dossier, nom, cookies, limite_s=0):
    """Télécharge l'audio (m4a) et la vidéo en basse qualité (pour les images)."""
    audio = dossier / f"{nom}.m4a"
    video = dossier / f"{nom}.mp4"

    # Une interruption peut laisser un téléchargement complet dans .temp.
    # Il ne doit jamais être repris à la place d'un nouvel extrait limité.
    for fichier in (audio, video):
        if fichier.exists():
            fichier.unlink()

    base = YTDLP + ["--no-warnings", "--quiet"] + options_cookies(cookies)
    if limite_s:
        # yt-dlp délègue le découpage à ffmpeg : on ne télécharge donc pas le
        # reste d'une conférence ou d'un podcast de plusieurs heures.
        base += ["--download-sections", f"*0-{limite_s}"]

    audio_resultat = subprocess.run(
        base + ["-f", "bestaudio", "-x", "--audio-format", "m4a",
                "-o", str(dossier / f"{nom}.%(ext)s"), lien],
        capture_output=True, text=True, timeout=300,
    )
    video_resultat = subprocess.run(
        base + ["-f", "worstvideo[height>=480]/worst",
                "-o", str(video), lien],
        capture_output=True, text=True, timeout=300,
    )
    audio = audio if audio.exists() else None
    video = video if video.exists() else None
    if audio is None and video is None:
        details = (audio_resultat.stderr or video_resultat.stderr or
                   "yt-dlp n'a produit aucun fichier").strip()
        raise RuntimeError(details[:300])
    return audio, video


def transcrire(audio, modele):
    if audio is None:
        return ""
    segments, _ = modele.transcribe(str(audio), vad_filter=True)
    return " ".join(s.text.strip() for s in segments).strip()


def fallback_tiktok_oembed(lien, dossier_images, nom):
    """Crée une fiche TikTok minimale lorsque le défi anti-bot bloque yt-dlp.

    L'endpoint oEmbed de TikTok fournit un titre, l'auteur, l'URL canonique et
    une miniature publique. La fiche reste donc retrouvable même sans l'audio.
    """
    endpoint = f"https://www.tiktok.com/oembed?url={quote(lien, safe='')}"
    resultat = subprocess.run(
        ["curl.exe", "--location", "--fail", "--silent", "--show-error", "--max-time", "30", endpoint],
        capture_output=True, timeout=40,
    )
    if resultat.returncode:
        raise RuntimeError((resultat.stderr.decode("utf-8", errors="ignore") or "oEmbed TikTok inaccessible").strip()[:300])
    donnees = json.loads(resultat.stdout.decode("utf-8", errors="ignore"))
    titre = (donnees.get("title") or "TikTok sans titre").strip()
    auteur = (donnees.get("author_name") or "inconnu").strip()
    canonique = ""
    html_embed = donnees.get("html") or ""
    match = re.search(r'cite=["\']([^"\']+)', html_embed)
    if match:
        canonique = match.group(1)

    meta = {
        "title": titre,
        "uploader": auteur,
        "description": "TikTok archivé via son aperçu public. "
                       + (f"Lien canonique : {canonique}" if canonique else ""),
    }
    images = []
    miniature = donnees.get("thumbnail_url")
    if miniature:
        sortie = dossier_images / f"{nom}_1.jpg"
        image_resultat = subprocess.run(
            ["curl.exe", "--location", "--fail", "--silent", "--show-error", "--max-time", "45", "-o", str(sortie), miniature],
            capture_output=True, timeout=55,
        )
        if image_resultat.returncode == 0 and sortie.exists() and sortie.stat().st_size > 0:
            images.append(sortie)
    return meta, images


def telecharger_carrousel(lien, dossier_images, nom, cookies):
    """Post Instagram sans vidéo : on télécharge les images du carrousel.

    Sur un carrousel, ce sont les images QUI SONT le contenu (les slides
    "10 meilleurs restos de Lisbonne"). On récupère aussi la légende, que
    yt-dlp ne sait pas lire sur ce type de post.
    """
    cible = dossier_images / nom
    cible.mkdir(parents=True, exist_ok=True)

    commande = GALLERYDL + ["--write-metadata", "-D", str(cible)]
    commande += options_cookies(cookies)
    commande.append(lien)
    resultat_gallery = subprocess.run(
        commande, capture_output=True, text=True, timeout=300,
    )

    images = sorted(
        p for p in cible.glob("*")
        if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")
    )

    # Les posts publics exposent encore leurs images à yt-dlp même quand
    # l'API utilisée par gallery-dl redirige vers la page de connexion.
    if not images:
        commande_fallback = YTDLP + [
            "--ignore-no-formats-error", "--skip-download", "--write-thumbnail",
            "--no-warnings", "--quiet",
        ] + options_cookies(cookies) + [
            "-o", str(cible / f"{nom}_%(playlist_index)s.%(ext)s"), lien,
        ]
        resultat_fallback = subprocess.run(
            commande_fallback, capture_output=True, text=True, timeout=300,
        )
        images = sorted(
            p for p in cible.glob("*")
            if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")
        )
        if not images:
            details = (resultat_gallery.stderr or resultat_fallback.stderr or
                       "aucune image produite").strip()
            raise RuntimeError(f"téléchargement du carrousel impossible : {details[:240]}")

    legende = ""
    for fichier_meta in sorted(cible.glob("*.json")):
        try:
            donnees = json.loads(fichier_meta.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        legende = donnees.get("description") or donnees.get("caption") or ""
        if legende:
            break

    return images, legende


def extraire_images(video, dossier_images, nom, duree):
    """Prend NB_IMAGES captures réparties dans la vidéo."""
    if video is None:
        return []
    if not duree:
        resultat = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(video)],
            capture_output=True, text=True, timeout=30,
        )
        try:
            duree = float(resultat.stdout.strip())
        except (TypeError, ValueError):
            return []
    chemins = []
    for i in range(NB_IMAGES):
        instant = duree * (i + 1) / (NB_IMAGES + 1)
        sortie = dossier_images / f"{nom}_{i + 1}.jpg"
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{instant:.1f}",
             "-i", str(video), "-frames:v", "1", "-vf", "scale=720:-1",
             str(sortie)],
            capture_output=True, timeout=90,
        )
        if sortie.exists():
            chemins.append(sortie)
    return chemins


def ecrire_fiche(dossier, vault, nom, lien, meta, transcription, images, genre,
                 transcription_partielle=False):
    liens_images = []
    for p in images:
        try:
            liens_images.append(f"- {p.relative_to(vault).as_posix()}")
        except ValueError:
            liens_images.append(f"- {p.name}")

    contenu = f"""---
source: {lien}
plateforme: {"TikTok" if "tiktok" in lien else "YouTube" if "youtu" in lien else "Instagram"}
genre: {genre}
auteur: {meta.get("uploader") or meta.get("channel") or "inconnu"}
duree_s: {meta.get("duration") or ""}
traite_le: {datetime.now():%Y-%m-%d}
statut: brut
---

# {(meta.get("title") or nom)[:120]}

## Description
{(meta.get("description") or "").strip() or "(vide)"}

## Transcription audio
{"*(Transcription partielle : cinq premières minutes de la vidéo.)*" if transcription_partielle else ""}
{transcription or "(pas d'audio exploitable)"}

## Images
{chr(10).join(liens_images) or "(aucune)"}
"""
    (dossier / f"{nom}.md").write_text(contenu, encoding="utf-8")


# ---------------------------------------------------------------- programme

def main():
    parseur = argparse.ArgumentParser()
    parseur.add_argument("fichier", help="fichier contenant les liens")
    parseur.add_argument("--vault", default=str(VAULT))
    parseur.add_argument("--cookies", default=None,
                         help="navigateur pour les cookies (chrome, firefox, edge)")
    parseur.add_argument("--limite", type=int, default=0,
                         help="ne traiter que les N premières vidéos")
    parseur.add_argument("--modele", default=MODELE_WHISPER)
    args = parseur.parse_args()

    verifier_outils()

    vault = Path(args.vault)
    dossier_raw = vault / "raw"
    dossier_images = vault / "images"
    dossier_temp = vault / ".temp"
    for d in (dossier_raw, dossier_images, dossier_temp):
        d.mkdir(parents=True, exist_ok=True)

    chemin_journal = vault / "journal.json"
    journal = charger_journal(chemin_journal)

    liens = extraire_liens(args.fichier)
    a_faire = [l for l in liens if journal.get(l, {}).get("statut") != "ok"]
    if args.limite:
        a_faire = a_faire[: args.limite]

    log(f"{len(liens)} liens trouvés, {len(a_faire)} à traiter.")
    if not a_faire:
        return

    log(f"Chargement du modèle Whisper « {args.modele} » (long la 1re fois)...")
    from faster_whisper import WhisperModel
    modele = WhisperModel(args.modele, device="cpu", compute_type="int8")

    reussites = echecs = 0
    for numero, lien in enumerate(a_faire, 1):
        nom = identifiant(lien)
        log(f"[{numero}/{len(a_faire)}] {lien}")
        try:
            erreur_meta = ""
            try:
                meta = recuperer_metadonnees(lien, args.cookies)
            except Exception as e:
                meta = {}  # carrousel, ou probleme d'acces
                erreur_meta = str(e).replace("\n", " ")[:300]

            audio = video = None
            if est_video(meta):
                genre = "video"
                limite_s = limite_youtube_longue(lien, meta)
                if limite_s:
                    log(f"    vidéo YouTube longue : transcription limitée aux {limite_s // 60} premières minutes.")
                audio, video = telecharger_media(lien, dossier_temp, nom,
                                                 args.cookies, limite_s)
                transcription = transcrire(audio, modele)
                images = extraire_images(video, dossier_images, nom,
                                         meta.get("duration"))
            else:
                genre = "carrousel"
                transcription = ""
                images, legende = telecharger_carrousel(lien, dossier_images,
                                                        nom, args.cookies)
                if not images:
                    raise RuntimeError(
                        "ni vidéo ni image récupérée | yt-dlp : "
                        + (erreur_meta or "aucun message")
                    )
                if legende and not meta.get("description"):
                    meta["description"] = legende

            ecrire_fiche(dossier_raw, vault, nom, lien, meta, transcription,
                         images, genre, transcription_partielle=bool(limite_s) if genre == "video" else False)

            for fichier in (audio, video):
                if fichier and fichier.exists():
                    fichier.unlink()

            journal[lien] = {"statut": "ok", "fiche": f"{nom}.md"}
            reussites += 1
        except Exception as erreur:  # noqa: BLE001 — on continue quoi qu'il arrive
            if "tiktok" in lien.lower():
                try:
                    meta, images = fallback_tiktok_oembed(lien, dossier_images, nom)
                    ecrire_fiche(
                        dossier_raw, vault, nom, lien, meta,
                        "(TikTok a bloqué le téléchargement audio ; aperçu public archivé.)",
                        images, "video",
                    )
                    journal[lien] = {"statut": "ok", "fiche": f"{nom}.md", "mode": "oembed"}
                    log("    TikTok bloqué par l'anti-bot : fiche d'aperçu public créée.")
                    reussites += 1
                except Exception as fallback_error:  # noqa: BLE001
                    log(f"    échec : {erreur} | secours TikTok : {fallback_error}")
                    journal[lien] = {"statut": "echec", "erreur": str(fallback_error)[:300]}
                    echecs += 1
            else:
                log(f"    échec : {erreur}")
                journal[lien] = {"statut": "echec", "erreur": str(erreur)[:300]}
                echecs += 1

        sauver_journal(chemin_journal, journal)
        time.sleep(PAUSE_ENTRE_VIDEOS)

    log(f"Terminé — {reussites} réussites, {echecs} échecs.")
    log(f"Fiches disponibles dans : {dossier_raw}")
    if echecs:
        log("Relance le script pour retenter uniquement les échecs.")


if __name__ == "__main__":
    main()
