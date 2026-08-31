import json
import unittest
from unittest.mock import patch

from ingest import LIMITE_TRANSCRIPTION_YOUTUBE_S, est_video, fallback_tiktok_oembed, limite_youtube_longue


class IngestMetadataTests(unittest.TestCase):
    def test_video_is_detected_from_duration(self):
        self.assertTrue(est_video({"duration": 12.5}))

    def test_video_is_detected_from_formats_without_duration(self):
        self.assertTrue(est_video({
            "duration": None,
            "formats": [
                {"vcodec": "none", "acodec": "mp4a.40.5"},
                {"vcodec": "vp09.00.31.08", "acodec": "none"},
            ],
        }))

    def test_empty_metadata_is_not_a_video(self):
        self.assertFalse(est_video({}))

    def test_long_youtube_video_is_limited_to_five_minutes(self):
        self.assertEqual(
            limite_youtube_longue("https://www.youtube.com/watch?v=long", {"duration": 3600}),
            LIMITE_TRANSCRIPTION_YOUTUBE_S,
        )

    def test_youtube_short_and_tiktok_keep_full_transcription(self):
        self.assertEqual(limite_youtube_longue("https://youtube.com/shorts/abc", {"duration": 3600}), 0)
        self.assertEqual(limite_youtube_longue("https://www.tiktok.com/@x/video/1", {"duration": 3600}), 0)

    @patch("ingest.subprocess.run")
    def test_tiktok_oembed_fallback_uses_public_title_and_author(self, run):
        response = {
            "title": "Sujet TikTok", "author_name": "Auteur",
            "html": '<blockquote cite="https://www.tiktok.com/@a/video/123">',
        }
        run.return_value.returncode = 0
        run.return_value.stdout = json.dumps(response).encode()
        with self.subTest("metadata"):
            from tempfile import TemporaryDirectory
            from pathlib import Path
            with TemporaryDirectory() as directory:
                meta, images = fallback_tiktok_oembed("https://vm.tiktok.com/abc/", Path(directory), "tiktok_123")
        self.assertEqual(meta["title"], "Sujet TikTok")
        self.assertEqual(meta["uploader"], "Auteur")
        self.assertIn("https://www.tiktok.com/@a/video/123", meta["description"])
        self.assertEqual(images, [])


if __name__ == "__main__":
    unittest.main()
