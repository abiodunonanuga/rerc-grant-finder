from __future__ import annotations

from datetime import datetime
import importlib.util
from pathlib import Path
import tempfile
import unittest
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("rerc_intake_watcher", ROOT / "scripts" / "rerc_intake_watcher.py")
WATCHER = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(WATCHER)


class IntakeWatcherTests(unittest.TestCase):
    def test_dst_safe_schedule_gate(self) -> None:
        eastern = ZoneInfo("America/New_York")
        self.assertTrue(WATCHER.scheduled_now(datetime(2026, 1, 10, 3, 33, tzinfo=eastern)))
        self.assertTrue(WATCHER.scheduled_now(datetime(2026, 7, 10, 3, 33, tzinfo=eastern)))
        self.assertFalse(WATCHER.scheduled_now(datetime(2026, 7, 10, 3, 32, tzinfo=eastern)))

    def test_google_sheet_link_becomes_csv_export(self) -> None:
        result = WATCHER.google_csv_url(
            "https://docs.google.com/spreadsheets/d/test_sheet_id/edit?gid=123#gid=123"
        )
        self.assertEqual(result, "https://docs.google.com/spreadsheets/d/test_sheet_id/gviz/tq?tqx=out:csv&gid=123")

    def test_contact_columns_are_removed(self) -> None:
        row = {
            "Email address": "private@example.com",
            "Contact name": "Private Person",
            "Program name": "Public Program",
        }
        self.assertEqual(WATCHER.redact_row(row), {"Program name": "Public Program"})

    def test_item_validation_and_duplicate_detection(self) -> None:
        index = {
            "ids": set(),
            "urls": {"https://example.gov/program"},
            "titles": {"existing program"},
        }
        row = {
            "What are you submitting?": "Grant",
            "Program name": "A New Program",
            "Official URL": "https://example.gov/program",
            "Description": "A public funding program.",
        }
        result = WATCHER.classify_item(row, index, check_network=False)
        self.assertEqual(result["item_type"], "Funding")
        self.assertEqual(result["disposition"], "possible_update_to_existing")
        self.assertEqual(result["duplicate_note"], "official URL already exists")

    def test_issue_requires_description(self) -> None:
        result = WATCHER.classify_issue(
            {"Issue type": "Broken link", "Page URL": "https://example.gov"},
            {"ids": set(), "urls": set(), "titles": set()},
            check_network=False,
        )
        self.assertEqual(result["disposition"], "rejected_or_incomplete")

    def test_csv_fixture_reader(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "responses.csv"
            path.write_text("Program name,Official URL\nTest,https://example.gov\n", encoding="utf-8")
            rows = WATCHER.read_csv_source(path.as_uri())
        self.assertEqual(rows[0]["Program name"], "Test")


if __name__ == "__main__":
    unittest.main()
