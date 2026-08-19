#!/usr/bin/env python3
"""Release checks for the August 2026 resilience and roadway-safety expansion."""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "window.RERC_CATALOG = "


def load_catalog() -> dict:
    raw = (ROOT / "data.js").read_text(encoding="utf-8").strip()
    assert raw.startswith(PREFIX) and raw.endswith(";")
    return json.loads(raw[len(PREFIX):-1])


def main() -> int:
    catalog = load_catalog()
    by_id = {item["item_id"]: item for item in catalog["items"]}
    with (ROOT / "maintenance" / "resilience_transportation_evidence_2026-08-17.csv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        evidence = list(csv.DictReader(handle))
    report = json.loads(
        (ROOT / "maintenance" / "resilience_transportation_integration_2026-08-17.json").read_text(encoding="utf-8")
    )
    source_health = json.loads(
        (ROOT / "maintenance" / "source_health_release_2026-08-19.json").read_text(encoding="utf-8")
    )

    assert len(evidence) == 116
    assert len({row["item_id"] for row in evidence}) == 116
    assert all(row["support_type"] for row in evidence)
    assert "RERC-FND-WA-2026-008" in {row["item_id"] for row in evidence}
    assert report["coverage_evidence_records"] == 116
    assert len(report["hazard_jurisdictions"]) == 56
    assert source_health["hard_failures"] == 0

    protect = by_id["RERC-FND-2026-NAT-PROTECT"]
    thp = by_id["RERC-FND-2026-NAT-THP"]
    emergency_relief = by_id["RERC-FND-2026-NAT-ER"]
    small_territories = {"American Samoa", "Guam", "Northern Mariana Islands", "U.S. Virgin Islands"}
    assert protect["geography"] == "Multi-State"
    assert set(protect["covered_states"]).isdisjoint(small_territories)
    assert "Puerto Rico" in protect["covered_states"] and len(protect["covered_states"]) == 52
    assert thp["geography"] == "Multi-State"
    assert set(thp["covered_states"]) == small_territories
    assert "roadway safety" not in protect["topic_tags"]
    assert "roadway safety" not in emergency_relief["topic_tags"]
    assert "roadway safety" in thp["topic_tags"]

    for item_id in (
        "RERC-FND-2026-HSIP-DELAWARE",
        "RERC-FND-2026-HSIP-IDAHO",
        "RERC-FND-2026-HSIP-MARYLAND",
        "RERC-FND-2026-HSIP-SOUTH-CAROLINA",
    ):
        status = by_id[item_id]["status"].lower()
        assert "active" not in status and "ongoing" not in status

    print(json.dumps({
        "status": "PASS",
        "coverage_evidence_records": len(evidence),
        "hazard_jurisdictions": len(report["hazard_jurisdictions"]),
        "protect_covered_places": len(protect["covered_states"]),
        "territorial_highway_places": len(thp["covered_states"]),
        "hard_source_failures": source_health["hard_failures"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
