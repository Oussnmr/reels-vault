#!/usr/bin/env python3
"""Reels Vault command-line launcher.

Goal: one simple entry point for the common workflow.

Examples:
  python vault.py import instagram-export.zip
  python vault.py import instagram-export.zip --limit 10
  python vault.py inbox --file "C:\\...\\inbox.txt"
  python vault.py add "https://www.instagram.com/reel/.../"
  python vault.py rebuild

The launcher delegates the heavy lifting to the existing project scripts:
- import_instagram.py: parse/deduplicate an Instagram export
- ingest.py: download/transcribe saved posts
- build_vault.py: rebuild the local search interface
"""

from __future__ import annotations

import argparse
import os
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


def rebuild(vault: Path) -> None:
    run_step(
        "Reconstruction de l'interface de recherche",
        [sys.executable, str(ROOT / "build_vault.py"), "--vault", str(vault)],
    )


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
    rebuild(vault)

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
    rebuild(vault)

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
    rebuild(vault)
    print(f"Ajout terminé : {args.url}")
    return 0


def cmd_rebuild(args: argparse.Namespace) -> int:
    vault = Path(args.vault).expanduser().resolve()
    rebuild(vault)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Point d'entrée simple pour Reels Vault")
    sub = parser.add_subparsers(dest="command", required=True)

    p_import = sub.add_parser("import", help="Importer un export Instagram et construire le Vault")
    p_import.add_argument("source", help="ZIP Instagram ou fichier exporté")
    p_import.add_argument("--vault", default=str(DEFAULT_VAULT), help="dossier du Vault")
    p_import.add_argument("--cookies", default="firefox", help="navigateur ou fichier cookies.txt")
    p_import.add_argument("--limit", type=int, default=0, help="limiter le nombre d'éléments à traiter")
    p_import.add_argument("--model", default="small", help="modèle Whisper")
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
    p_inbox.set_defaults(func=cmd_inbox)

    p_add = sub.add_parser("add", help="Ajouter immédiatement une URL au Vault")
    p_add.add_argument("url", help="URL Instagram/TikTok")
    p_add.add_argument("--vault", default=str(DEFAULT_VAULT), help="dossier du Vault")
    p_add.add_argument("--cookies", default="firefox", help="navigateur ou fichier cookies.txt")
    p_add.add_argument("--model", default="small", help="modèle Whisper")
    p_add.set_defaults(func=cmd_add)

    p_rebuild = sub.add_parser("rebuild", help="Régénérer uniquement la page de recherche")
    p_rebuild.add_argument("--vault", default=str(DEFAULT_VAULT), help="dossier du Vault")
    p_rebuild.set_defaults(func=cmd_rebuild)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
