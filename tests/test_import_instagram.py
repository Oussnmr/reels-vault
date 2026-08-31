import tempfile
import unittest
import zipfile
from pathlib import Path

from import_instagram import collect_from_zip, extract_urls, normalize_instagram_url


class ImportInstagramTests(unittest.TestCase):
    def test_normalize_removes_query_and_fragment(self):
        self.assertEqual(
            normalize_instagram_url("https://instagram.com/reel/ABC123/?utm_source=x#foo"),
            "https://www.instagram.com/reel/ABC123/",
        )

    def test_extract_deduplicates_and_ignores_profile_urls(self):
        text = """
        https://www.instagram.com/reel/AAA/?igsh=123
        https://www.instagram.com/reel/AAA/
        https://www.instagram.com/p/BBB/?utm_source=copy_link
        https://www.instagram.com/some_profile/
        """
        self.assertEqual(
            extract_urls(text),
            [
                "https://www.instagram.com/reel/AAA/",
                "https://www.instagram.com/p/BBB/",
            ],
        )

    def test_zip_reads_posts_and_collections(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "instagram.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr(
                    "your_instagram_activity/saved/saved_posts.html",
                    '<a href="https://www.instagram.com/reel/AAA/">A</a>',
                )
                archive.writestr(
                    "your_instagram_activity/saved/saved_collections.html",
                    '<a href="https://www.instagram.com/p/BBB/">B</a>',
                )
                archive.writestr("start_here.html", "ignored")

            urls, used = collect_from_zip(path)
            self.assertEqual(
                urls,
                [
                    "https://www.instagram.com/reel/AAA/",
                    "https://www.instagram.com/p/BBB/",
                ],
            )
            self.assertEqual(len(used), 2)


if __name__ == "__main__":
    unittest.main()
