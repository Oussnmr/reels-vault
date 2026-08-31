#!/usr/bin/env python3
"""Ingest image and video files dropped into the Media Vault inbox."""
from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm"}


def ffmpeg_image(source: Path, target: Path, instant: float | None = None) -> bool:
    command = ["ffmpeg", "-y", "-loglevel", "error"]
    if instant is not None:
        command += ["-ss", str(instant)]
    command += ["-i", str(source), "-frames:v", "1", "-vf", "scale=720:-1", str(target)]
    return subprocess.run(command, capture_output=True, timeout=120).returncode == 0 and target.exists()


def extract_audio(source: Path, target: Path) -> bool:
    return subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(source), "-vn", "-c:a", "aac", str(target)],
        capture_output=True, timeout=300,
    ).returncode == 0 and target.exists()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inbox-dir", required=True)
    parser.add_argument("--vault", required=True)
    parser.add_argument("--model", default="small")
    args = parser.parse_args()
    inbox, vault = Path(args.inbox_dir), Path(args.vault)
    inbox.mkdir(parents=True, exist_ok=True)
    raw, images, archive = vault / "raw", vault / "images", vault / "inbox_archive" / "media"
    for directory in (raw, images, archive):
        directory.mkdir(parents=True, exist_ok=True)
    processed = failed = 0
    whisper = None
    for source in sorted(path for path in inbox.iterdir() if path.is_file()):
        suffix = source.suffix.lower()
        if suffix not in IMAGE_EXTENSIONS | VIDEO_EXTENSIONS:
            continue
        identity = "media_" + hashlib.sha256(f"{source.name}:{source.stat().st_size}".encode()).hexdigest()[:16]
        output_images: list[Path] = []
        try:
            transcription = "(pas d'audio exploitable)"
            if suffix in IMAGE_EXTENSIONS:
                target = images / f"{identity}_1.jpg"
                if ffmpeg_image(source, target):
                    output_images.append(target)
            else:
                for number, instant in enumerate((1, 5, 10), start=1):
                    target = images / f"{identity}_{number}.jpg"
                    if ffmpeg_image(source, target, instant):
                        output_images.append(target)
                audio = vault / ".temp" / f"{identity}.m4a"
                audio.parent.mkdir(parents=True, exist_ok=True)
                if extract_audio(source, audio):
                    if whisper is None:
                        from faster_whisper import WhisperModel
                        whisper = WhisperModel(args.model, device="cpu", compute_type="int8")
                    segments, _ = whisper.transcribe(str(audio), vad_filter=True)
                    value = " ".join(segment.text.strip() for segment in segments).strip()
                    transcription = value or transcription
                audio.unlink(missing_ok=True)
            if not output_images:
                raise RuntimeError("conversion d'image impossible")
            image_lines = "\n".join(f"- {item.relative_to(vault).as_posix()}" for item in output_images)
            genre = "image_locale" if suffix in IMAGE_EXTENSIONS else "video_locale"
            (raw / f"{identity}.md").write_text(
                f"---\nsource: media://{source.name}\nplateforme: Fichier local\ngenre: {genre}\nauteur: iPhone\ntraite_le: {datetime.now():%Y-%m-%d}\nstatut: brut\n---\n\n"
                f"# {source.stem[:160]}\n\n## Description\nFichier envoyé depuis l'iPhone.\n\n"
                f"## Transcription audio\n{transcription}\n\n## Images\n" + image_lines + "\n",
                encoding="utf-8",
            )
            shutil.move(str(source), str(archive / source.name))
            processed += 1
        except Exception as error:
            print(f"Média ignoré ({source.name}) : {error}")
            failed += 1
    print(f"Médias locaux : {processed} réussite(s), {failed} échec(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
