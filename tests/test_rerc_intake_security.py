from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("rerc_intake_watcher_security", ROOT / "scripts" / "rerc_intake_watcher.py")
WATCHER = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(WATCHER)


class IntakeSecurityTests(unittest.TestCase):
    def test_private_and_credentialed_targets_are_blocked(self) -> None:
        blocked = (
            "https://127.0.0.1/admin",
            "https://10.0.0.5/",
            "https://169.254.169.254/latest/meta-data/",
            "https://localhost/",
            "https://user:password@example.gov/",
        )
        self.assertTrue(all(not WATCHER.is_public_https_url(url) for url in blocked))
        self.assertTrue(WATCHER.is_public_https_url("https://www.epa.gov/smartgrowth"))

    def test_duplicate_rows_are_collapsed_and_queue_is_bounded(self) -> None:
        duplicate = {"Program name": "Same", "Official URL": "https://example.gov"}
        rows = [duplicate.copy() for _ in range(WATCHER.MAX_ROWS_PER_SHEET + 10)]
        self.assertEqual(len(WATCHER.distinct_rows("new_item", rows)), 1)

    def test_markdown_control_characters_are_escaped(self) -> None:
        value = WATCHER.markdown_text("[click](https://bad.example) *bold* # heading")
        self.assertNotIn("[click]", value)
        self.assertIn("\\[click\\]", value)
        self.assertIn("\\*bold\\*", value)
        self.assertIn("\\# heading", value)


if __name__ == "__main__":
    unittest.main()
