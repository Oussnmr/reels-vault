#!/usr/bin/env python3
"""Cheap local smoke tests for deterministic Reels Vault pieces.

No Instagram login, download, Whisper model, or network access is required.
The goal is to catch packaging/regression mistakes before spending time on a
real 5-10 Reel test.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True)


def assert_ok(result: subprocess.CompletedProcess[str], label: str) -> None:
    if result.returncode != 0:
        raise AssertionError(f"{label} failed\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")


def main() -> int:
    checks = 0
    with tempfile.TemporaryDirectory(prefix="reels-vault-smoke-") as tmp:
        tmp = Path(tmp)

        # 1) Instagram ZIP import + normalization + de-duplication.
        export_zip = tmp / "instagram.zip"
        with zipfile.ZipFile(export_zip, "w") as z:
            z.writestr(
                "your_instagram_activity/saved/saved_posts.html",
                '<a href="https://www.instagram.com/reel/ABC123/?utm_source=x">A</a>\n'
                '<a href="https://instagram.com/reel/ABC123/">duplicate</a>\n'
                '<a href="https://www.instagram.com/p/POST456/?igsh=x">B</a>',
            )
            z.writestr(
                "your_instagram_activity/saved/saved_collections.html",
                '<a href="https://www.instagram.com/reel/XYZ789/">C</a>',
            )

        urls = tmp / "urls.txt"
        result = run([sys.executable, str(ROOT / "import_instagram.py"), str(export_zip), "-o", str(urls)])
        assert_ok(result, "import_instagram.py")
        imported = [x.strip() for x in urls.read_text(encoding="utf-8").splitlines() if x.strip()]
        assert imported == [
            "https://www.instagram.com/reel/ABC123/",
            "https://www.instagram.com/p/POST456/",
            "https://www.instagram.com/reel/XYZ789/",
        ], imported
        checks += 1

        # 2) Build a Vault from one representative raw Markdown record.
        vault = tmp / "Vault"
        raw = vault / "raw"
        raw.mkdir(parents=True)
        (raw / "insta_demo.md").write_text(
            """---\nsource: https://www.instagram.com/reel/ABC123/\nplateforme: Instagram\ngenre: video\nauteur: demo_creator\ntraite_le: 2026-08-29\nstatut: brut\n---\n\n# Restaurant japonais à Bruxelles\n\n## Description\nBon ramen près du centre, environ 18 euros.\n\n## Transcription audio\nAdresse pratique et réservation conseillée le week-end.\n\n## Images\n(aucune)\n""",
            encoding="utf-8",
        )
        result = run([sys.executable, str(ROOT / "build_vault.py"), "--vault", str(vault)])
        assert_ok(result, "build_vault.py")
        assert (vault / "vault.html").exists()
        assert (vault / "Vault Instagram.md").exists()
        data = json.loads((vault / "vault_data.json").read_text(encoding="utf-8"))
        assert len(data) == 1 and "Restaurant japonais" in data[0]["title"]
        compact = (vault / "Vault Instagram.md").read_text(encoding="utf-8")
        assert "demo_creator" in compact and "ABC123" in compact
        checks += 1

        # 3) Launcher parser/help remains usable without doing network work.
        result = run([sys.executable, str(ROOT / "vault.py"), "--help"])
        assert_ok(result, "vault.py --help")
        assert "doctor" in result.stdout and "import" in result.stdout
        checks += 1

    print(f"SMOKE TEST OK — {checks} groupes de vérifications réussis.")
    print("Étape suivante : `python vault.py doctor`, puis un vrai import avec `--limit 5` ou `--limit 10`.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
