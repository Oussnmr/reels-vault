#!/usr/bin/env python3
"""Build a zero-cost searchable Vault from raw Markdown files.

This is the deterministic layer: no API and no AI model is required. It reads
`raw/*.md`, extracts metadata/content, writes `vault_data.json`, and generates a
single self-contained `vault.html` that can be opened locally in a browser.

Later, an AI enrichment step can add better summaries/categories without
changing the daily interface.
"""
from __future__ import annotations

import argparse
import html
import json
import re
from collections import Counter
from pathlib import Path

FIELD_RE = re.compile(r"^([A-Za-z0-9_-]+):\s*(.*)$")
SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


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
    images_text = section("Images")
    images = [
        line[2:].strip()
        for line in images_text.splitlines()
        if line.strip().startswith("- ")
    ]

    source = meta.get("source", "")
    platform = meta.get("plateforme", "")
    genre = meta.get("genre", "")
    author = meta.get("auteur", "")
    searchable = " ".join([title, author, description, transcription]).lower()

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
        "images": images,
        "searchable": searchable,
    }


def collect(raw_dir: Path) -> list[dict]:
    return [parse_markdown(p) for p in sorted(raw_dir.glob("*.md"))]


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
    p = argparse.ArgumentParser(description="Génère vault_data.json et vault.html depuis raw/*.md")
    p.add_argument("--vault", default=str(Path.home() / "vault"))
    args = p.parse_args()
    vault = Path(args.vault).expanduser()
    raw = vault / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    items = collect(raw)
    (vault / "vault_data.json").write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    (vault / "vault.html").write_text(render_html(items), encoding="utf-8")
    print(f"Vault généré : {len(items)} éléments")
    print(vault / "vault.html")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
