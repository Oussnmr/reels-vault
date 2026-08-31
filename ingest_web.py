#!/usr/bin/env python3
"""Save public web pages as searchable, text-first Vault entries."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import urllib.request
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

URL_RE = re.compile(r"https?://[^\s\"'<>,\)\]]+", re.I)
MEDIA_HOSTS = ("instagram.com", "tiktok.com", "youtube.com", "youtu.be")


def urls_from(path: Path) -> list[str]:
    values = [item.rstrip(".,;") for item in URL_RE.findall(path.read_text(encoding="utf-8", errors="ignore"))]
    return list(dict.fromkeys(value for value in values if not any(host in urlparse(value).netloc.lower() for host in MEDIA_HOSTS)))


def clean(value: str) -> str:
    value = re.sub(r"(?is)<script.*?</script>|<style.*?</style>|<noscript.*?</noscript>", " ", value)
    value = re.sub(r"(?i)<br\s*/?>|</p>|</li>|</h[1-6]>", "\n", value)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def section(source: str, pattern: str) -> str:
    found = re.search(pattern, source, re.I | re.S)
    return clean(found.group(1)) if found else ""


def fetch(url: str) -> tuple[str, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Media Vault; personal archive)"})
    with urllib.request.urlopen(request, timeout=30) as response:
        source = response.read(2_000_000).decode(response.headers.get_content_charset() or "utf-8", errors="ignore")
        return response.url, source


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("urls_file")
    parser.add_argument("--vault", required=True)
    args = parser.parse_args()
    vault = Path(args.vault)
    raw = vault / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    journal_path = vault / "journal.json"
    journal = json.loads(journal_path.read_text(encoding="utf-8")) if journal_path.exists() else {}
    ok = failed = 0
    for url in urls_from(Path(args.urls_file)):
        if journal.get(url, {}).get("statut") == "ok":
            continue
        try:
            final_url, source = fetch(url)
            title = section(source, r"<title[^>]*>(.*?)</title>") or urlparse(final_url).netloc
            description = section(source, r"<meta[^>]+(?:name|property)=[\"'](?:description|og:description)[\"'][^>]+content=[\"'](.*?)[\"']")[:900]
            main_html = section(source, r"<(?:article|main)[^>]*>(.*?)</(?:article|main)>") or clean(source)
            body = main_html[:7000] or "(contenu textuel indisponible)"
            ident = "web_" + hashlib.sha256(final_url.encode()).hexdigest()[:16]
            (raw / f"{ident}.md").write_text(
                f"---\nsource: {final_url}\nplateforme: Web\ngenre: page_web\nauteur: {urlparse(final_url).netloc}\ntraite_le: {datetime.now():%Y-%m-%d}\nstatut: brut\n---\n\n"
                f"# {title[:160]}\n\n## Description\n{description or '(vide)'}\n\n## Contenu de la page\n{body}\n\n"
                "## Transcription audio\n(pas d'audio exploitable)\n\n## Images\n(aucune)\n",
                encoding="utf-8",
            )
            journal[url] = {"statut": "ok", "fiche": f"{ident}.md"}
            ok += 1
        except Exception as error:  # keep the URL in inbox for retry
            journal[url] = {"statut": "echec", "erreur": str(error)[:300]}
            failed += 1
        journal_path.write_text(json.dumps(journal, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Pages web : {ok} réussite(s), {failed} échec(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
