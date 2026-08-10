from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("rerc_intake_watcher_privacy", ROOT / "scripts" / "rerc_intake_watcher.py")
WATCHER = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(WATCHER)


class IntakePrivacyTests(unittest.TestCase):
    def test_contact_values_inside_free_text_are_redacted(self) -> None:
        result = WATCHER.redact_row(
            {"Description": "Email person@example.com or call 202-555-0199.", "Program name": "Public Program"}
        )
        self.assertEqual(
            result["Description"],
            "Email [redacted email] or call [redacted phone].",
        )


if __name__ == "__main__":
    unittest.main()
