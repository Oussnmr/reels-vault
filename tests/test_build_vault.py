import json
import tempfile
import unittest
from pathlib import Path

from build_vault import render_search_index


class SearchDetailTests(unittest.TestCase):
    def test_detail_record_keeps_full_transcript_while_shard_is_compact(self):
        item = {
            "id": "youtube_example", "title": "Longue vidéo", "source": "https://youtube.com/watch?v=x",
            "platform": "YouTube", "genre": "video", "author": "Auteur", "date": "2026-08-31",
            "description": "Description", "transcription": "mot " * 400,
            "visual_text": "texte à l'écran", "visual_description": "une scène", "web_content": "",
            "images": ["images/youtube_example_1.jpg"],
        }
        with tempfile.TemporaryDirectory() as directory:
            vault = Path(directory)
            render_search_index([item], vault)
            detail = json.loads((vault / "vault_search" / "details" / "youtube_example.json").read_text(encoding="utf-8"))
            shard = json.loads((vault / "vault_search" / "shard_001.json").read_text(encoding="utf-8"))[0]
        self.assertEqual(detail["transcription"], item["transcription"])
        self.assertEqual(detail["image_references"], item["images"])
        self.assertEqual(shard["detail"], "details/youtube_example.json")
        self.assertLess(len(shard["transcription"]), len(detail["transcription"]))


if __name__ == "__main__":
    unittest.main()
