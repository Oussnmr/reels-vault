import unittest

from ingest import LIMITE_TRANSCRIPTION_YOUTUBE_S, est_video, limite_youtube_longue


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


if __name__ == "__main__":
    unittest.main()
