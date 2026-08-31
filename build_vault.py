#!/usr/bin/env python3
"""Build a zero-cost searchable Vault from raw Markdown files.

This deterministic layer uses no API and no AI model. It reads raw/*.md and
writes three outputs:
- vault_data.json: structured machine-readable data
- vault.html: local searchable UI
- Vault Instagram.md: compact ChatGPT-friendly index meant to be synced to OneDrive

Later, an AI enrichment step can add better summaries/categories without
changing the daily interface.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

FIELD_RE = re.compile(r"^([A-Za-z0-9_-]+):\s*(.*)$")


def parse_markdown(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="ignore")
    meta: dict[str, str] = {}
    body = text
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            header = text[4:end]
            body = text[end + 5 :]
            for line in header.splitlines():
                m = FIELD_RE.match(line)
                if m:
                    meta[m.group(1)] = m.group(2).strip()

    title_match = re.search(r"^#\s+(.+?)\s*$", body, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else path.stem

    def section(name: str) -> str:
        m = re.search(
            rf"^##\s+{re.escape(name)}\s*$\n(.*?)(?=^##\s+|\Z)",
            body,
            re.MULTILINE | re.DOTALL,
        )
        return m.group(1).strip() if m else ""

    description = section("Description")
    transcription = section("Transcription audio")
    visual_text = section("Texte détecté à l'écran")
    images_text = section("Images")
    images = [line[2:].strip() for line in images_text.splitlines() if line.strip().startswith("- ")]

    source = meta.get("source", "")
    platform = meta.get("plateforme", "")
    genre = meta.get("genre", "")
    author = meta.get("auteur", "")
    searchable = " ".join([title, author, description, transcription, visual_text]).lower()

    return {
        "id": path.stem,
        "title": title,
        "source": source,
        "platform": platform,
        "genre": genre,
        "author": author,
        "date": meta.get("traite_le", ""),
        "description": description,
        "transcription": transcription,
        "visual_text": visual_text,
        "images": images,
        "searchable": searchable,
    }


def collect(raw_dir: Path) -> list[dict]:
    return [parse_markdown(p) for p in sorted(raw_dir.glob("*.md"))]


def compact_text(value: str, limit: int = 700) -> str:
    value = re.sub(r"\s+", " ", (value or "").strip())
    if value in {"(vide)", "(pas d'audio exploitable)", "(aucune)"}:
        return ""
    return value if len(value) <= limit else value[: limit - 1].rstrip() + "…"


def render_markdown(items: list[dict]) -> str:
    """Compact index optimized for retrieval by ChatGPT/OneDrive.

    Keep the caption and the audio transcription distinct. A caption alone is
    often promotional and is not a reliable summary of the video.
    """
    lines = [
        "# Vault Instagram",
        "",
        f"Nombre d'éléments : {len(items)}",
        "",
        "Index compact de contenus Instagram sauvegardés. Chaque entrée conserve le lien source.",
        "",
    ]
    for item in items:
        description = compact_text(item.get("description", ""), 240)
        transcription = compact_text(item.get("transcription", ""), 560)
        visual_text = compact_text(item.get("visual_text", ""), 420)
        lines.append(f"## {item.get('title') or item.get('id')}")
        if item.get("author"):
            lines.append(f"- Auteur : {item['author']}")
        if item.get("genre"):
            lines.append(f"- Type : {item['genre']}")
        if item.get("date"):
            lines.append(f"- Traité le : {item['date']}")
        if item.get("source"):
            lines.append(f"- Source : {item['source']}")
        if transcription:
            lines.append(f"- Transcription audio : {transcription}")
        if description:
            lines.append(f"- Description Instagram : {description}")
        if visual_text:
            lines.append(f"- Texte à l'écran : {visual_text}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


SEARCH_STOP_WORDS = {
    "avec", "aussi", "dans", "dont", "elle", "elles", "entre", "être", "faire",
    "from", "have", "just", "mais", "more", "pour", "plus", "pourquoi", "quel",
    "quoi", "that", "this", "tout", "tous", "une", "vous", "with", "your",
    "the", "and", "des", "les", "que", "qui", "est", "sur", "pas", "par",
}


def shard_keywords(chunk: list[dict], limit: int = 36) -> list[str]:
    """Return lightweight routing hints, not a replacement for the transcripts."""
    words = Counter()
    for item in chunk:
        text = " ".join([
            item.get("title", ""), item.get("author", ""),
            item.get("description", ""), item.get("transcription", ""),
            item.get("visual_text", ""),
        ]).lower()
        for word in re.findall(r"[\wÀ-ÿ'-]{4,}", text):
            word = word.strip("'-")
            if word and word not in SEARCH_STOP_WORDS and not word.isdigit():
                words[word] += 1
    return [word for word, _count in words.most_common(limit)]


def lookup_words(item: dict) -> set[str]:
    """Normalise meaningful words used to route a GPT query to a small shard."""
    text = " ".join([
        item.get("title", ""), item.get("author", ""),
        item.get("description", ""), item.get("transcription", ""),
        item.get("visual_text", ""),
    ]).lower()
    found = set()
    for word in re.findall(r"[\wÀ-ÿ'-]{4,}", text):
        word = unicodedata.normalize("NFKD", word).encode("ascii", "ignore").decode("ascii")
        word = re.sub(r"[^a-z0-9]", "", word)
        if word and word not in SEARCH_STOP_WORDS and not word.isdigit():
            found.add(word)
    return found


def render_search_index(items: list[dict], vault: Path, shard_size: int = 20) -> None:
    """Write small, read-only shards for remote GPT retrieval.

    The complete vault_data.json remains available locally, while the GPT
    action reads only compact shards so a single response stays below limits.
    """
    search_dir = vault / "vault_search"
    search_dir.mkdir(parents=True, exist_ok=True)
    # Remove only generated shard files; preserve no user-authored files here.
    for old in search_dir.glob("shard_*.json"):
        old.unlink()
    for old in search_dir.glob("terms_*.json"):
        old.unlink()
    compact = []
    for item in items:
        compact.append({
            "id": item.get("id", ""),
            "title": compact_text(item.get("title", ""), 160),
            "source": item.get("source", ""),
            "author": compact_text(item.get("author", ""), 100),
            "date": item.get("date", ""),
            "genre": item.get("genre", ""),
            # Keep these separate: a caption is not a transcription. The GPT
            # can therefore summarise what was actually said in the video.
            "description": compact_text(item.get("description", ""), 240),
            "transcription": compact_text(item.get("transcription", ""), 560),
            "visual_text": compact_text(item.get("visual_text", ""), 420),
        })
    shards = []
    for number, start in enumerate(range(0, len(compact), shard_size), start=1):
        chunk = compact[start:start + shard_size]
        filename = f"shard_{number:03d}.json"
        (search_dir / filename).write_text(
            json.dumps(chunk, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        titles = [x["title"] for x in chunk if x["title"]]
        shards.append({
            "file": filename,
            "count": len(chunk),
            "first_title": titles[0] if titles else "",
            "last_title": titles[-1] if titles else "",
            "keywords": shard_keywords(chunk),
        })

    # A full searchable index would again be too large for a GPT action.
    # Instead, one tiny terms_<letter>.json file maps exact query words to the
    # shard(s) that contain them. The GPT fetches only the needed term file.
    routes: dict[str, dict[str, set[str]]] = {}
    for position, item in enumerate(items):
        filename = f"shard_{position // shard_size + 1:03d}.json"
        for word in lookup_words(item):
            bucket = word[0] if "a" <= word[0] <= "z" else "other"
            routes.setdefault(bucket, {}).setdefault(word, set()).add(filename)
    term_files = []
    for bucket, words in sorted(routes.items()):
        filename = f"terms_{bucket}.json"
        payload = {word: sorted(files) for word, files in sorted(words.items())}
        (search_dir / filename).write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        term_files.append(filename)
    (search_dir / "manifest.json").write_text(
        json.dumps({"version": 3, "count": len(compact), "shard_size": shard_size,
                    "term_files": term_files, "shards": shards}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def render_html(items: list[dict]) -> str:
    data = json.dumps(items, ensure_ascii=False).replace("</", "<\\/")
    stats = Counter(i.get("genre") or "autre" for i in items)
    stat_text = " · ".join(f"{k}: {v}" for k, v in sorted(stats.items()))
    return f'''<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Reels Vault</title>
<style>
:root{{font-family:system-ui,-apple-system,Segoe UI,sans-serif;color-scheme:light dark}}body{{max-width:1000px;margin:auto;padding:24px}}h1{{margin-bottom:4px}}.muted{{opacity:.65}}input{{width:100%;box-sizing:border-box;font-size:18px;padding:14px;border-radius:12px;border:1px solid #888;margin:18px 0 10px}}.filters{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:18px}}button{{padding:8px 12px;border-radius:999px;border:1px solid #888;cursor:pointer}}article{{border:1px solid #7776;border-radius:14px;padding:16px;margin:12px 0}}article h2{{margin:0 0 6px;font-size:19px}}.meta{{font-size:13px;opacity:.7;margin-bottom:8px}}.text{{white-space:pre-wrap;line-height:1.4}}a{{word-break:break-all}}#empty{{display:none;padding:30px 0;text-align:center;opacity:.65}}
</style></head><body>
<h1>Reels Vault</h1><div class="muted">{len(items)} éléments · {html.escape(stat_text)}</div>
<input id="q" type="search" placeholder="Rechercher un lieu, restaurant, sujet, auteur…" autofocus>
<div class="filters"><button data-kind="">Tous</button><button data-kind="video">Vidéos</button><button data-kind="carrousel">Carrousels</button></div>
<div id="results"></div><div id="empty">Aucun résultat.</div>
<script>
const DATA={data}; let kind='';
const q=document.getElementById('q'), results=document.getElementById('results'), empty=document.getElementById('empty');
const esc=s=>String(s||'').replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
function render(){{const terms=q.value.toLowerCase().trim().split(/\\s+/).filter(Boolean);const found=DATA.filter(x=>(!kind||x.genre===kind)&&terms.every(t=>x.searchable.includes(t)));results.innerHTML=found.map(x=>`<article><h2>${{esc(x.title)}}</h2><div class="meta">${{esc(x.author)}}${{x.genre?' · '+esc(x.genre):''}}</div><div class="text">${{esc((x.description&&x.description!=='(vide)')?x.description:(x.transcription||'')).slice(0,900)}}</div>${{x.source?`<p><a href="${{esc(x.source)}}" target="_blank" rel="noopener">Ouvrir sur Instagram</a></p>`:''}}</article>`).join('');empty.style.display=found.length?'none':'block'}}
q.addEventListener('input',render);document.querySelectorAll('button[data-kind]').forEach(b=>b.onclick=()=>{{kind=b.dataset.kind;render()}});render();
</script></body></html>'''


def main() -> int:
    p = argparse.ArgumentParser(description="Génère les sorties du Vault depuis raw/*.md")
    p.add_argument("--vault", default=str(Path.home() / "vault"))
    args = p.parse_args()
    vault = Path(args.vault).expanduser()
    raw = vault / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    items = collect(raw)

    json_path = vault / "vault_data.json"
    html_path = vault / "vault.html"
    md_path = vault / "Vault Instagram.md"

    json_path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    html_path.write_text(render_html(items), encoding="utf-8")
    md_path.write_text(render_markdown(items), encoding="utf-8")
    render_search_index(items, vault)

    print(f"Vault généré : {len(items)} éléments")
    print(f"Interface : {html_path}")
    print(f"Index ChatGPT : {md_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
