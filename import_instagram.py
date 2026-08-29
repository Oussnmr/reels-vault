#!/usr/bin/env python3
"""Extract saved Instagram post/reel URLs from an Instagram export.

Accepted inputs:
- the ZIP downloaded from Meta Accounts Center
- saved_posts.html / saved_collections.html
- JSON, TXT or CSV files containing Instagram URLs

The script never contacts Instagram. It only reads the export and writes a clean,
deduplicated list of URLs that can be passed to ingest.py.
"""

from __future__ import annotations

import argparse
import html
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

INSTAGRAM_URL = re.compile(
    r"https?://(?:www\.)?instagram\.com/(?:reel|p|tv)/[^\s\"'<>,\)\]]+",
    re.IGNORECASE,
)

EXPORT_CANDIDATES = (
    "saved_posts.html",
    "saved_collections.html",
    "saved_posts.json",
    "saved_collections.json",
)


def normalize_instagram_url(url: str) -> str:
    """Return a stable canonical Instagram URL without query/fragment noise."""
    url = html.unescape(url).strip().rstrip(".,;")
    parts = urlsplit(url)
    host = parts.netloc.lower()
    if host == "instagram.com":
        host = "www.instagram.com"
    path = re.sub(r"/+", "/", parts.path)
    if not path.endswith("/"):
        path += "/"
    return urlunsplit(("https", host, path, "", ""))


def extract_urls(text: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for match in INSTAGRAM_URL.findall(text):
        url = normalize_instagram_url(match)
        if url not in seen:
            seen.add(url)
            out.append(url)
    return out


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def collect_from_zip(path: Path) -> tuple[list[str], list[str]]:
    urls: list[str] = []
    used_files: list[str] = []
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            base = Path(name).name.lower()
            if base not in EXPORT_CANDIDATES:
                continue
            used_files.append(name)
            text = archive.read(name).decode("utf-8", errors="ignore")
            urls.extend(extract_urls(text))
    return dedupe(urls), used_files


def dedupe(urls: list[str]) -> list[str]:
    return list(dict.fromkeys(urls))


def classify(urls: list[str]) -> Counter:
    counts: Counter = Counter()
    for url in urls:
        parts = urlsplit(url).path.strip("/").split("/")
        kind = parts[0].lower() if parts else "other"
        counts[kind] += 1
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prépare une liste propre de sauvegardes Instagram pour ingest.py."
    )
    parser.add_argument("source", help="ZIP Instagram ou fichier exporté")
    parser.add_argument(
        "-o", "--output", default="instagram_saved_urls.txt",
        help="fichier de sortie (défaut: instagram_saved_urls.txt)",
    )
    args = parser.parse_args()

    source = Path(args.source).expanduser()
    if not source.exists():
        print(f"ERREUR: fichier introuvable: {source}", file=sys.stderr)
        return 2

    if source.suffix.lower() == ".zip":
        try:
            urls, used_files = collect_from_zip(source)
        except zipfile.BadZipFile:
            print("ERREUR: le fichier n'est pas un ZIP valide.", file=sys.stderr)
            return 2
        if not used_files:
            print(
                "ERREUR: aucun saved_posts/saved_collections trouvé dans le ZIP.",
                file=sys.stderr,
            )
            return 2
    else:
        urls = extract_urls(read_text(source))
        used_files = [str(source)]

    output = Path(args.output).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(urls) + ("\n" if urls else ""), encoding="utf-8")

    counts = classify(urls)
    print(f"Sources lues : {len(used_files)}")
    for name in used_files:
        print(f"  - {name}")
    print(f"Liens uniques : {len(urls)}")
    print(f"  Reels : {counts.get('reel', 0)}")
    print(f"  Posts/carrousels : {counts.get('p', 0)}")
    print(f"  IGTV : {counts.get('tv', 0)}")
    print(f"Sortie : {output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
