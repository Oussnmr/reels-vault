#!/usr/bin/env python3
"""Reels Vault command-line launcher.

Goal: one simple entry point for the common workflow.

Examples:
  python vault.py import instagram-export.zip
  python vault.py import instagram-export.zip --limit 10
  python vault.py rebuild

The launcher delegates the heavy lifting to the existing project scripts:
- import_instagram.py: parse/deduplicate an Instagram export
- ingest.py: download/transcribe saved posts
- build_vault.py: rebuild the local search interface
"""

from __future__ import annotations

import argparse
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


def cmd_import(args: argparse.Namespace) -> int:
    source = Path(args.source).expanduser().resolve()
    vault = Path(args.vault).expanduser().resolve()
    vault.mkdir(parents=True, exist_ok=True)
    inbox = vault / "instagram_saved_urls.txt"

    run_step(
        "Préparation de l'export Instagram",
        [sys.executable, str(ROOT / "import_instagram.py"), str(source), "-o", str(inbox)],
    )

    ingest_cmd = [
        sys.executable,
        str(ROOT / "ingest.py"),
        str(inbox),
        "--vault",
        str(vault),
    ]
    if args.cookies:
        ingest_cmd += ["--cookies", args.cookies]
    if args.limit:
        ingest_cmd += ["--limite", str(args.limit)]
    if args.model:
        ingest_cmd += ["--modele", args.model]

    run_step("Ingestion et transcription", ingest_cmd)
    run_step(
        "Reconstruction de l'interface de recherche",
        [sys.executable, str(ROOT / "build_vault.py"), "--vault", str(vault)],
    )

    html = vault / "vault.html"
    print("\nTerminé.")
    print(f"Vault : {vault}")
    print(f"Interface : {html}")
    print("Astuce : commence avec --limit 10 pour valider le pipeline avant l'import complet.")
    return 0


def cmd_rebuild(args: argparse.Namespace) -> int:
    vault = Path(args.vault).expanduser().resolve()
    run_step(
        "Reconstruction de l'interface de recherche",
        [sys.executable, str(ROOT / "build_vault.py"), "--vault", str(vault)],
    )
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
