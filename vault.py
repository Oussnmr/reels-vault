#!/usr/bin/env python3
"""Reels Vault command-line launcher."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_VAULT = Path.home() / "Vault"
URL_RE = re.compile(r"https?://[^\s\"'<>,\)\]]+", re.IGNORECASE)


def run_step(label: str, command: list[str]) -> None:
    print(f"\n==> {label}")
    print("    " + " ".join(command))
    result = subprocess.run(command)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def ingest_file(source: Path, vault: Path, cookies: str, limit: int = 0, model: str = "small") -> None:
    command = [sys.executable, str(ROOT / "ingest.py"), str(source), "--vault", str(vault)]
    if cookies:
        command += ["--cookies", cookies]
    if limit:
        command += ["--limite", str(limit)]
    if model:
        command += ["--modele", model]
    run_step("Ingestion et transcription", command)


def find_onedrive_root() -> Path | None:
    for name in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
        raw = os.environ.get(name)
        if raw:
            path = Path(raw).expanduser()
            if path.exists():
                return path
    return None


def sync_onedrive(vault: Path, quiet_if_missing: bool = True) -> bool:
    root = find_onedrive_root()
    if root is None:
        message = "OneDrive non détecté : synchronisation ignorée."
        if not quiet_if_missing:
            message = "OneDrive introuvable. Ouvre/configure OneDrive puis relance la synchronisation."
        print(message)
        return False

    source_md = vault / "Vault Instagram.md"
    if not source_md.exists():
        print(f"Index ChatGPT introuvable : {source_md}")
        return False

    destination = root / "Reels Vault"
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_md, destination / "Vault Instagram.md")
    source_json = vault / "vault_data.json"
    if source_json.exists():
        shutil.copy2(source_json, destination / "vault_data.json")
    print(f"OneDrive synchronisé : {destination / 'Vault Instagram.md'}")
    return True


def sync_github_index(vault: Path, quiet_if_missing: bool = True) -> bool:
    """Publish only the compact indexes to an optional private Git repository."""
    raw = os.environ.get("VAULT_INDEX_REPO")
    if not raw:
        if not quiet_if_missing:
            print("Dépôt GitHub d'index non configuré : VAULT_INDEX_REPO absent.")
        return False

    index_repo = Path(raw).expanduser()
    script = ROOT / "sync_github_index.ps1"
    if not index_repo.exists() or not script.exists() or os.name != "nt":
        print("Publication GitHub ignorée : dépôt ou script introuvable.")
        return False

    powershell = shutil.which("powershell") or shutil.which("pwsh")
    if not powershell:
        print("Publication GitHub ignorée : PowerShell introuvable.")
        return False

    print("\n==> Publication de l'index GitHub privé")
    result = subprocess.run([
        powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script),
        "-VaultPath", str(vault), "-IndexRepo", str(index_repo),
    ])
    if result.returncode != 0:
        print("Publication GitHub en échec : l'index local reste disponible.")
        return False
    return True


def rebuild(vault: Path, sync: bool = True) -> None:
    ocr_script = ROOT / "enrich_visual_ocr.py"
    if ocr_script.exists():
        run_step(
            "Lecture du texte affiché dans les Reels sans audio",
            [sys.executable, str(ocr_script), "--vault", str(vault)],
        )
    vision_script = ROOT / "enrich_visual_ollama.py"
    if vision_script.exists():
        run_step(
            "Analyse visuelle locale des Reels sans contexte textuel",
            [sys.executable, str(vision_script), "--vault", str(vault)],
        )
    run_step(
        "Reconstruction de l'interface de recherche",
        [sys.executable, str(ROOT / "build_vault.py"), "--vault", str(vault)],
    )
    if sync:
        sync_onedrive(vault)
        sync_github_index(vault)


def extract_urls(text: str) -> list[str]:
    """Extract supported URLs in order, without duplicates."""
    return list(dict.fromkeys(match.rstrip(".,;") for match in URL_RE.findall(text)))


def load_journal(vault: Path) -> dict:
    path = vault / "journal.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def prune_processed_inbox(inbox: Path, original_text: str, vault: Path) -> tuple[int, int]:
    """Remove only successfully processed URLs from inbox.

    Failed or not-yet-attempted URLs stay in the inbox so a scheduled run can
    retry them. This also makes --limit safe: untouched URLs are preserved.
    """
    urls = extract_urls(original_text)
    journal = load_journal(vault)
    processed = [url for url in urls if journal.get(url, {}).get("statut") == "ok"]
    pending = [url for url in urls if journal.get(url, {}).get("statut") != "ok"]

    if processed:
        archive_dir = vault / "inbox_archive"
        archive_dir.mkdir(parents=True, exist_ok=True)
        archive = archive_dir / "processed_urls.txt"
        existing = set(extract_urls(archive.read_text(encoding="utf-8", errors="ignore"))) if archive.exists() else set()
        new_processed = [url for url in processed if url not in existing]
        if new_processed:
            with archive.open("a", encoding="utf-8") as handle:
                if archive.exists() and archive.stat().st_size:
                    handle.write("\n")
                handle.write("\n".join(new_processed) + "\n")

    inbox.write_text("\n".join(pending) + ("\n" if pending else ""), encoding="utf-8")
    return len(processed), len(pending)


def cmd_import(args: argparse.Namespace) -> int:
    source = Path(args.source).expanduser().resolve()
    vault = Path(args.vault).expanduser().resolve()
    vault.mkdir(parents=True, exist_ok=True)
    clean_list = vault / "instagram_saved_urls.txt"
    run_step(
        "Préparation de l'export Instagram",
        [sys.executable, str(ROOT / "import_instagram.py"), str(source), "-o", str(clean_list)],
    )
    ingest_file(clean_list, vault, args.cookies, args.limit, args.model)
    rebuild(vault, sync=not args.no_sync)
    print("\nTerminé.")
    print(f"Vault : {vault}")
    print(f"Interface : {vault / 'vault.html'}")
    return 0


def resolve_inbox(value: str | None) -> Path:
    raw = value or os.environ.get("VAULT_INBOX")
    if not raw:
        raise SystemExit("Aucun fichier inbox configuré. Utilise --file CHEMIN ou définis VAULT_INBOX.")
    path = Path(raw).expanduser().resolve()
    if not path.exists():
        raise SystemExit(f"Inbox introuvable : {path}")
    return path


def cmd_inbox(args: argparse.Namespace) -> int:
    vault = Path(args.vault).expanduser().resolve()
    vault.mkdir(parents=True, exist_ok=True)
    inbox = resolve_inbox(args.file)
    before = inbox.read_text(encoding="utf-8", errors="ignore")
    urls = extract_urls(before)
    media_dir = inbox.parent / "Media"
    media_files = [
        path for path in media_dir.glob("*")
        if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".mp4", ".mov", ".m4v", ".webm"}
    ] if media_dir.exists() else []
    if not urls and not media_files:
        print("Inbox vide : aucun lien ou média à traiter.")
        return 0

    media_url_hosts = ("instagram.com", "tiktok.com", "youtube.com", "youtu.be")
    social_urls = [url for url in urls if any(host in url.lower() for host in media_url_hosts)]
    if social_urls:
        ingest_file(inbox, vault, args.cookies, args.limit, args.model)
    if urls:
        web_script = ROOT / "ingest_web.py"
        if web_script.exists():
            run_step(
                "Archivage textuel des pages web",
                [sys.executable, str(web_script), str(inbox), "--vault", str(vault)],
            )
    media_script = ROOT / "ingest_media.py"
    if media_files and media_script.exists():
        run_step(
            "Ingestion des fichiers image et vidéo",
            [sys.executable, str(media_script), "--inbox-dir", str(media_dir), "--vault", str(vault)],
        )
    rebuild(vault, sync=not args.no_sync)

    if args.clear:
        processed, pending = prune_processed_inbox(inbox, before, vault)
        print(f"Inbox nettoyée : {processed} traité(s), {pending} restant(s) à retenter/traiter.")

    print(f"Interface mise à jour : {vault / 'vault.html'}")
    return 0


def cmd_add(args: argparse.Namespace) -> int:
    vault = Path(args.vault).expanduser().resolve()
    vault.mkdir(parents=True, exist_ok=True)
    inbox = vault / "manual_inbox.txt"
    existing = extract_urls(inbox.read_text(encoding="utf-8", errors="ignore")) if inbox.exists() else []
    if args.url not in existing:
        with inbox.open("a", encoding="utf-8") as handle:
            handle.write(args.url.strip() + "\n")
    ingest_file(inbox, vault, args.cookies, 0, args.model)
    rebuild(vault, sync=not args.no_sync)
    print(f"Ajout terminé : {args.url}")
    return 0


def cmd_rebuild(args: argparse.Namespace) -> int:
    rebuild(Path(args.vault).expanduser().resolve(), sync=not args.no_sync)
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    vault = Path(args.vault).expanduser().resolve()
    onedrive_ok = sync_onedrive(vault, quiet_if_missing=False)
    github_ok = sync_github_index(vault, quiet_if_missing=False)
    return 0 if onedrive_ok or github_ok else 1


def cmd_doctor(args: argparse.Namespace) -> int:
    script = ROOT / "diagnose.ps1"
    if not script.exists() or os.name != "nt":
        print("La commande doctor nécessite Windows et diagnose.ps1.")
        return 1
    powershell = shutil.which("powershell") or shutil.which("pwsh")
    if not powershell:
        print("PowerShell introuvable.")
        return 1
    command = [
        powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script),
        "-VaultPath", str(Path(args.vault).expanduser().resolve()),
    ]
    if args.inbox:
        command += ["-InboxPath", str(Path(args.inbox).expanduser().resolve())]
    print("\n==> Diagnostic Reels Vault")
    return subprocess.run(command).returncode


def cmd_test(_args: argparse.Namespace) -> int:
    script = ROOT / "smoke_test.py"
    if not script.exists():
        print(f"Test introuvable : {script}")
        return 1
    return subprocess.run([sys.executable, str(script)]).returncode


def add_sync_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--no-sync", action="store_true", help="ne pas synchroniser l'index vers OneDrive")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Point d'entrée simple pour Reels Vault")
    sub = parser.add_subparsers(dest="command", required=True)

    p_import = sub.add_parser("import", help="Importer un export Instagram et construire le Vault")
    p_import.add_argument("source", help="ZIP Instagram ou fichier exporté")
    p_import.add_argument("--vault", default=str(DEFAULT_VAULT))
    p_import.add_argument("--cookies", default="firefox")
    p_import.add_argument("--limit", type=int, default=0)
    p_import.add_argument("--model", default="small")
    add_sync_flag(p_import)
    p_import.set_defaults(func=cmd_import)

    p_inbox = sub.add_parser("inbox", help="Traiter l'inbox Dropbox/iPhone")
    p_inbox.add_argument("--file", help="chemin vers inbox.txt (sinon VAULT_INBOX)")
    p_inbox.add_argument("--vault", default=str(DEFAULT_VAULT))
    p_inbox.add_argument("--cookies", default="firefox")
    p_inbox.add_argument("--limit", type=int, default=0)
    p_inbox.add_argument("--model", default="small")
    p_inbox.add_argument(
        "--clear", action="store_true",
        help="retirer seulement les URLs réussies; conserver les échecs et non-traitées",
    )
    add_sync_flag(p_inbox)
    p_inbox.set_defaults(func=cmd_inbox)

    p_add = sub.add_parser("add", help="Ajouter immédiatement une URL au Vault")
    p_add.add_argument("url")
    p_add.add_argument("--vault", default=str(DEFAULT_VAULT))
    p_add.add_argument("--cookies", default="firefox")
    p_add.add_argument("--model", default="small")
    add_sync_flag(p_add)
    p_add.set_defaults(func=cmd_add)

    p_rebuild = sub.add_parser("rebuild", help="Régénérer l'index et synchroniser OneDrive")
    p_rebuild.add_argument("--vault", default=str(DEFAULT_VAULT))
    add_sync_flag(p_rebuild)
    p_rebuild.set_defaults(func=cmd_rebuild)

    p_sync = sub.add_parser("sync", help="Synchroniser l'index vers OneDrive")
    p_sync.add_argument("--vault", default=str(DEFAULT_VAULT))
    p_sync.set_defaults(func=cmd_sync)

    p_doctor = sub.add_parser("doctor", help="Vérifier l'installation Windows")
    p_doctor.add_argument("--vault", default=str(DEFAULT_VAULT))
    p_doctor.add_argument("--inbox")
    p_doctor.set_defaults(func=cmd_doctor)

    p_test = sub.add_parser("test", help="Lancer les tests rapides sans Instagram ni réseau")
    p_test.set_defaults(func=cmd_test)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
