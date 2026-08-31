import json
import tempfile
import unittest
from pathlib import Path

from vault import extract_urls, prune_processed_inbox


class VaultInboxTests(unittest.TestCase):
    def test_extract_urls_deduplicates_and_keeps_order(self):
        text = "\n".join([
            "https://www.instagram.com/reel/AAA/",
            "https://www.instagram.com/reel/AAA/",
            "https://www.instagram.com/p/BBB/",
        ])
        self.assertEqual(
            extract_urls(text),
            [
                "https://www.instagram.com/reel/AAA/",
                "https://www.instagram.com/p/BBB/",
            ],
        )

    def test_prune_removes_only_successful_urls(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            vault = root / "Vault"
            vault.mkdir()
            inbox = root / "inbox.txt"
            ok = "https://www.instagram.com/reel/AAA/"
            failed = "https://www.instagram.com/reel/BBB/"
            untouched = "https://www.instagram.com/reel/CCC/"
            original = f"{ok}\n{failed}\n{untouched}\n"
            inbox.write_text(original, encoding="utf-8")
            (vault / "journal.json").write_text(
                json.dumps({
                    ok: {"statut": "ok"},
                    failed: {"statut": "echec", "erreur": "demo"},
                }),
                encoding="utf-8",
            )

            processed, pending = prune_processed_inbox(inbox, original, vault)

            self.assertEqual((processed, pending), (1, 2))
            self.assertEqual(inbox.read_text(encoding="utf-8"), f"{failed}\n{untouched}\n")
            archive = vault / "inbox_archive" / "processed_urls.txt"
            self.assertEqual(archive.read_text(encoding="utf-8").strip(), ok)

    def test_prune_is_idempotent_for_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            vault = root / "Vault"
            vault.mkdir()
            inbox = root / "inbox.txt"
            url = "https://www.instagram.com/reel/AAA/"
            original = url + "\n"
            (vault / "journal.json").write_text(
                json.dumps({url: {"statut": "ok"}}), encoding="utf-8"
            )
            inbox.write_text(original, encoding="utf-8")
            prune_processed_inbox(inbox, original, vault)
            inbox.write_text(original, encoding="utf-8")
            prune_processed_inbox(inbox, original, vault)

            archive = vault / "inbox_archive" / "processed_urls.txt"
            self.assertEqual(extract_urls(archive.read_text(encoding="utf-8")), [url])


if __name__ == "__main__":
    unittest.main()
