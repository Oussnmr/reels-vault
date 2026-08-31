#!/usr/bin/env python3
"""Generate local, searchable visual summaries for context-poor Reels."""
from __future__ import annotations

import argparse
import base64
import json
import re
import urllib.error
import urllib.request
from pathlib import Path

MODEL = "qwen3-vl:4b"
EMPTY = {"", "(vide)", "(pas d'audio exploitable)", "(aucune)"}


def section(text: str, name: str) -> str:
    match = re.search(
        rf"^##\s+{re.escape(name)}\s*$\n(.*?)(?=^##\s+|\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    return match.group(1).strip() if match else ""


def has_usable_transcript(value: str) -> bool:
    """Avoid treating a stray word from Whisper as meaningful Reel context."""
    value = re.sub(r"\s+", " ", value).strip()
    if value.casefold() in EMPTY:
        return False
    words = re.findall(r"[A-Za-zÀ-ÿ0-9']+", value)
    return len(words) >= 4 and len("".join(words)) >= 18


def has_usable_visual_text(value: str) -> bool:
    """Require enough OCR context before omitting an actual visual description."""
    if value.strip().casefold() in {"", "(aucun texte détecté)"}:
        return False
    words = re.findall(r"[A-Za-zÀ-ÿ0-9']+", value)
    return len(words) >= 8 and len("".join(words)) >= 45


def analyse(images: list[Path]) -> str:
    payload = {
        "model": MODEL,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 130},
        "prompt": (
            "Analyse ces captures d'un même Reel Instagram. Décris uniquement ce qui est "
            "visible, en français, en 1 ou 2 phrases concises. Ajoute des mots-clés utiles "
            "pour une recherche (objets, activité, thème). N'invente ni dialogue, ni marque, "
            "ni contexte absent des images."
        ),
        "images": [base64.b64encode(image.read_bytes()).decode("ascii") for image in images],
    }
    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Ollama indisponible : {error}") from error
    summary = re.sub(r"\s+", " ", data.get("response", "")).strip()
    # A model can exceptionally emit punctuation-only noise. Never make that
    # searchable context, and leave the entry eligible for a later retry.
    words = re.findall(r"[A-Za-zÀ-ÿ0-9']+", summary)
    return summary if len(words) >= 3 and len("".join(words)) >= 12 else ""


def model_available() -> bool:
    """Return false instead of disrupting normal ingestion when Ollama is not ready."""
    request = urllib.request.Request("http://127.0.0.1:11434/api/tags")
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            models = json.loads(response.read().decode("utf-8")).get("models", [])
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return False
    return any(item.get("name") == MODEL or item.get("model") == MODEL for item in models)


def enrich(vault: Path) -> tuple[int, int]:
    if not model_available():
        print(f"Analyse visuelle locale ignorée : Ollama ou le modèle {MODEL} n'est pas disponible.")
        return 0, 0

    enriched = skipped = 0
    for raw in sorted((vault / "raw").glob("*.md")):
        text = raw.read_text(encoding="utf-8", errors="ignore")
        if has_usable_transcript(section(text, "Transcription audio")):
            skipped += 1
            continue
        if has_usable_visual_text(section(text, "Texte détecté à l'écran")):
            skipped += 1
            continue
        if section(text, "Description visuelle"):
            skipped += 1
            continue
        relative_images = [
            line[2:].strip() for line in section(text, "Images").splitlines()
            if line.strip().startswith("- ")
        ]
        candidates = [vault / item for item in relative_images]
        candidates = [item for item in candidates if item.exists()]
        if not candidates:
            skipped += 1
            continue
        # First, middle and last frame capture both the setup and change.
        indexes = sorted(set([0, len(candidates) // 2, len(candidates) - 1]))
        summary = analyse([candidates[index] for index in indexes])
        if not summary:
            skipped += 1
            continue
        text = re.sub(
            r"## Images",
            lambda _match: f"## Description visuelle\n{summary}\n\n## Images",
            text,
            count=1,
        )
        raw.write_text(text, encoding="utf-8")
        enriched += 1
    print(f"Analyse visuelle locale : {enriched} fiche(s) enrichie(s), {skipped} inchangée(s).")
    return enriched, skipped


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyse visuelle locale des Reels sans contexte textuel.")
    parser.add_argument("--vault", required=True)
    args = parser.parse_args()
    enrich(Path(args.vault).expanduser().resolve())
