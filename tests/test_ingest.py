import unittest

from ingest import est_video


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


if __name__ == "__main__":
    unittest.main()
