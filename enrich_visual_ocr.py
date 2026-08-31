#!/usr/bin/env python3
"""Add local OCR text to Vault entries that have no usable audio transcript."""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
from pathlib import Path

EMPTY_TRANSCRIPTS = {"", "(vide)", "(pas d'audio exploitable)", "(aucune)"}


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
    if value.casefold() in EMPTY_TRANSCRIPTS:
        return False
    words = re.findall(r"[A-Za-zÀ-ÿ0-9']+", value)
    return len(words) >= 4 and len("".join(words)) >= 18


def tesseract_path() -> str | None:
    return shutil.which("tesseract") or next(
        (str(path) for path in (
            Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
            Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
        ) if path.exists()),
        None,
    )


def extract_layout(executable: str, image: Path, language: str, psm: str) -> str:
    """Read one Tesseract layout, retaining only reasonably confident words."""
    result = subprocess.run(
        [executable, str(image), "stdout", "-l", language, "--psm", psm, "tsv"],
        capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=45,
    )
    if result.returncode:
        return ""
    words = []
    # TSV includes an OCR confidence per word. It prevents visual texture,
    # subtitles in motion, and decorative fonts from polluting search results.
    for line in result.stdout.splitlines()[1:]:
        columns = line.split("\t")
        if len(columns) < 12:
            continue
        try:
            confidence = float(columns[10])
        except ValueError:
            continue
        word = columns[11].strip()
        if confidence >= 55 and re.search(r"[A-Za-zÀ-ÿ0-9]", word):
            words.append(word)
    return " ".join(words)


def extract_text(executable: str, image: Path, language: str) -> str:
    # PSM 6 works well for ordinary subtitles.  PSM 11 also detects isolated
    # blocks such as a price, address or phone number in an Instagram story.
    # Keep both layouts: they complement each other and make a saved image
    # searchable even when it has no usable audio.
    values = [extract_layout(executable, image, language, psm) for psm in ("6", "11")]
    value = " ".join(dict.fromkeys(item for item in values if item))
    readable = [
        word for word in re.findall(r"[A-Za-zÀ-ÿ]{3,}", value)
        if re.search(r"[aeiouyàâäéèêëîïôöùûüÿ]", word, re.IGNORECASE)
    ]
    # Decorative imagery often produces isolated pseudo-words. Keep only
    # meaningful text runs; missing visual text is safer than false context.
    return value if len(readable) >= 3 else ""


def enrich(vault: Path, force: bool = False) -> tuple[int, int]:
    executable = tesseract_path()
    if not executable:
        print("OCR ignoré : Tesseract n'est pas installé.")
        return 0, 0
    langs = subprocess.run(
        [executable, "--list-langs"], capture_output=True, text=True, encoding="utf-8",
        errors="ignore",
    ).stdout
    language = "fra+eng" if "fra" in langs and "eng" in langs else "eng"
    enriched = skipped = 0
    for raw in sorted((vault / "raw").glob("*.md")):
        text = raw.read_text(encoding="utf-8", errors="ignore")
        if has_usable_transcript(section(text, "Transcription audio")):
            skipped += 1
            continue
        if section(text, "Texte détecté à l'écran") and not force:
            skipped += 1
            continue
        image_lines = section(text, "Images").splitlines()
        images = [vault / line[2:].strip() for line in image_lines if line.strip().startswith("- ")]
        parts, seen = [], set()
        for image in images:
            if not image.exists():
                continue
            value = extract_text(executable, image, language)
            key = value.casefold()
            if value and key not in seen:
                seen.add(key)
                parts.append(value)
        visual = " ".join(parts)
        visual = visual[:1400].rstrip()
        replacement = f"## Texte détecté à l'écran\n{visual or '(aucun texte détecté)'}\n\n"
        # A captured backslash must remain literal (not a regex replacement
        # escape) when OCR happens to read code, a path, or a formula.
        if section(text, "Texte détecté à l'écran"):
            text = re.sub(
                r"(?ms)^## Texte détecté à l'écran\s*$\n.*?(?=^## Images)",
                lambda _match: replacement,
                text,
                count=1,
            )
        else:
            text = re.sub(r"## Images", lambda _match: replacement + "## Images", text, count=1)
        raw.write_text(text, encoding="utf-8")
        enriched += 1
    print(f"OCR visuel : {enriched} fiche(s) enrichie(s), {skipped} inchangée(s).")
    return enriched, skipped


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OCR local des captures de Reels sans audio exploitable.")
    parser.add_argument("--vault", required=True)
    parser.add_argument("--force", action="store_true", help="rejouer l'OCR des fiches déjà enrichies")
    args = parser.parse_args()
    enrich(Path(args.vault).expanduser().resolve(), force=args.force)
