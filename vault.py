#!/usr/bin/env python3
"""Reels Vault command-line launcher.

Goal: one simple entry point for the common workflow.

Examples:
  python vault.py import instagram-export.zip
  python vault.py import instagram-export.zip --limit 10
  python vault.py inbox --file "C:\\...\\inbox.txt"
  python vault.py add "https://www.instagram.com/reel/.../"
  python vault.py rebuild
  python vault.py sync
  python vault.py doctor

The launcher delegates the heavy lifting to the existing project scripts and,
on Windows, mirrors the compact ChatGPT index into OneDrive automatically.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_VAULT = Path.home() / "Vault"


def run_step(label: str, command: list[str]) -> None:
    print(f"\n==> {label}")
    print("    " + " ".join(command))
    result = subprocess.run(command)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def ingest_file(source: Path, vault: Path, cookies: str, limit: int = 0, model: str = "small") -> None:
    ingest_cmd = [
        sys.executable,
        str(ROOT / "ingest.py"),
        str(source),
        "--vault",
        str(vault),
    ]
    if cookies:
        ingest_cmd += ["--cookies", cookies]
    if limit:
        ingest_cmd += ["--limite", str(limit)]
    if model:
        ingest_cmd += ["--modele", model]
    run_step("Ingestion et transcription", ingest_cmd)


def find_onedrive_root() -> Path | None:
    """Return the locally synced OneDrive root when available."""
    for name in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
        raw = os.environ.get(name)
        if raw:
            path = Path(raw).expanduser()
            if path.exists():
                return path
    return None


def sync_onedrive(vault: Path, quiet_if_missing: bool = True) -> bool:
    """Mirror compact Vault outputs into OneDrive/Reels Vault.

    This uses the normal local OneDrive sync client: no API, token or paid
    service is involved. Missing OneDrive is non-fatal by default so ingestion
    still succeeds on machines where OneDrive has not been configured yet.
    """
    root = find_onedrive_root()
    if root is None:
        if not quiet_if_missing:
            print("OneDrive introuvable. Ouvre/configure OneDrive sur Windows puis relance la synchronisation.")
        else:
            print("OneDrive non détecté : synchronisation ignorée pour cette exécution.")
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


def rebuild(vault: Path, sync: bool = True) -> None:
    run_step(
        "Reconstruction de l'interface de recherche",
        [sys.executable, str(ROOT / "build_vault.py"), "--vault", str(vault)],
    )
    if sync:
        sync_onedrive(vault)


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

    html = vault / "vault.html"
    print("\nTerminé.")
    print(f"Vault : {vault}")
    print(f"Interface : {html}")
    print("Astuce : commence avec --limit 10 pour valider le pipeline avant l'import complet.")
    return 0


def resolve_inbox(value: str | None) -> Path:
    raw = value or os.environ.get("VAULT_INBOX")
    if not raw:
        raise SystemExit(
            "Aucun fichier inbox configuré. Utilise --file CHEMIN ou définis la variable VAULT_INBOX."
        )
    path = Path(raw).expanduser().resolve()
    if not path.exists():
        raise SystemExit(f"Inbox introuvable : {path}")
    return path


def cmd_inbox(args: argparse.Namespace) -> int:
    vault = Path(args.vault).expanduser().resolve()
    vault.mkdir(parents=True, exist_ok=True)
    inbox = resolve_inbox(args.file)

    before = inbox.read_text(encoding="utf-8", errors="ignore")
    if not before.strip():
        print("Inbox vide : rien à traiter.")
        return 0

    ingest_file(inbox, vault, args.cookies, args.limit, args.model)
    rebuild(vault, sync=not args.no_sync)

    if args.clear:
        archive_dir = vault / "inbox_archive"
        archive_dir.mkdir(parents=True, exist_ok=True)
        archive = archive_dir / "processed_urls.txt"
        with archive.open("a", encoding="utf-8") as handle:
            if archive.exists() and archive.stat().st_size:
                handle.write("\n")
            handle.write(before.strip() + "\n")
        inbox.write_text("", encoding="utf-8")
        print(f"Inbox vidée après traitement. Archive : {archive}")

    print(f"Interface mise à jour : {vault / 'vault.html'}")
    return 0


def cmd_add(args: argparse.Namespace) -> int:
    vault = Path(args.vault).expanduser().resolve()
    vault.mkdir(parents=True, exist_ok=True)
    inbox = vault / "manual_inbox.txt"

    existing = inbox.read_text(encoding="utf-8", errors="ignore") if inbox.exists() else ""
    urls = [line.strip() for line in existing.splitlines() if line.strip()]
    if args.url not in urls:
        with inbox.open("a", encoding="utf-8") as handle:
            handle.write(args.url.strip() + "\n")

    ingest_file(inbox, vault, args.cookies, 0, args.model)
    rebuild(vault, sync=not args.no_sync)
    print(f"Ajout terminé : {args.url}")
    return 0


def cmd_rebuild(args: argparse.Namespace) -> int:
    vault = Path(args.vault).expanduser().resolve()
    rebuild(vault, sync=not args.no_sync)
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    vault = Path(args.vault).expanduser().resolve()
    return 0 if sync_onedrive(vault, quiet_if_missing=False) else 1


def cmd_doctor(args: argparse.Namespace) -> int:
    """Run the Windows diagnostic through the same simple CLI entry point."""
    script = ROOT / "diagnose.ps1"
    if not script.exists():
        print(f"Diagnostic introuvable : {script}")
        return 1
    if os.name != "nt":
        print("La commande doctor est actuellement prévue pour Windows.")
        return 1

    powershell = shutil.which("powershell") or shutil.which("pwsh")
    if not powershell:
        print("PowerShell introuvable.")
        return 1

    command = [
        powershell,
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        "-VaultPath",
        str(Path(args.vault).expanduser().resolve()),
    ]
    if args.inbox:
        command += ["-InboxPath", str(Path(args.inbox).expanduser().resolve())]

    print("\n==> Diagnostic Reels Vault")
    result = subprocess.run(command)
    return result.returncode


def add_sync_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--no-sync",
        action="store_true",
        help="ne pas copier automatiquement l'index compact vers OneDrive",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Point d'entrée simple pour Reels Vault")
    sub = parser.add_subparsers(dest="command", required=True)

    p_import = sub.add_parser("import", help="Importer un export Instagram et construire le Vault")
    p_import.add_argument("source", help="ZIP Instagram ou fichier exporté")
    p_import.add_argument("--vault", default=str(DEFAULT_VAULT), help="dossier du Vault")
    p_import.add_argument("--cookies", default="firefox", help="navigateur ou fichier cookies.txt")
    p_import.add_argument("--limit", type=int, default=0, help="limiter le nombre d'éléments à traiter")
    p_import.add_argument("--model", default="small", help="modèle Whisper")
    add_sync_flag(p_import)
    p_import.set_defaults(func=cmd_import)

    p_inbox = sub.add_parser("inbox", help="Traiter un fichier inbox alimenté depuis l'iPhone")
    p_inbox.add_argument("--file", help="chemin vers inbox.txt (sinon variable VAULT_INBOX)")
    p_inbox.add_argument("--vault", default=str(DEFAULT_VAULT), help="dossier du Vault")
    p_inbox.add_argument("--cookies", default="firefox", help="navigateur ou fichier cookies.txt")
    p_inbox.add_argument("--limit", type=int, default=0, help="limiter le nombre d'éléments à traiter")
    p_inbox.add_argument("--model", default="small", help="modèle Whisper")
    p_inbox.add_argument(
        "--clear",
        action="store_true",
        help="archiver puis vider inbox.txt après un traitement réussi",
    )
    add_sync_flag(p_inbox)
    p_inbox.set_defaults(func=cmd_inbox)

    p_add = sub.add_parser("add", help="Ajouter immédiatement une URL au Vault")
    p_add.add_argument("url", help="URL Instagram/TikTok")
    p_add.add_argument("--vault", default=str(DEFAULT_VAULT), help="dossier du Vault")
    p_add.add_argument("--cookies", default="firefox", help="navigateur ou fichier cookies.txt")
    p_add.add_argument("--model", default="small", help="modèle Whisper")
    add_sync_flag(p_add)
    p_add.set_defaults(func=cmd_add)

    p_rebuild = sub.add_parser("rebuild", help="Régénérer la page de recherche et synchroniser OneDrive")
    p_rebuild.add_argument("--vault", default=str(DEFAULT_VAULT), help="dossier du Vault")
    add_sync_flag(p_rebuild)
    p_rebuild.set_defaults(func=cmd_rebuild)

    p_sync = sub.add_parser("sync", help="Synchroniser uniquement l'index compact vers OneDrive")
    p_sync.add_argument("--vault", default=str(DEFAULT_VAULT), help="dossier du Vault")
    p_sync.set_defaults(func=cmd_sync)

    p_doctor = sub.add_parser("doctor", help="Vérifier automatiquement l'installation Windows")
    p_doctor.add_argument("--vault", default=str(DEFAULT_VAULT), help="dossier du Vault")
    p_doctor.add_argument("--inbox", help="chemin optionnel vers inbox.txt à vérifier")
    p_doctor.set_defaults(func=cmd_doctor)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
