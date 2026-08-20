from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "case_studies.js"
MANIFEST = ROOT / "case_studies.public_manifest.json"
PREFIX = "window.RERC_CASE_STUDIES="
PUBLIC_HOSTS = {"toolkit.climate.gov", "www.nrcs.usda.gov", "research.fs.usda.gov", "highways.dot.gov", "www.nps.gov", "www.fhwa.dot.gov", "www.fs.usda.gov", "npgallery.nps.gov"}
LIBRARY_PATHS = ("/case-study/", "/brownfields/success-stories", "/smartgrowth/examples-smart-growth", "/newsroom/success-stories/")

def main() -> int:
    raw = DATA.read_text(encoding="utf-8").strip()
    assert raw.startswith(PREFIX) and raw.endswith(";")
    payload = json.loads(raw[len(PREFIX):-1])
    items = payload["items"]
    assert payload["count"] == len(items) == 10
    assert len({item["item_id"] for item in items}) == len(items)
    assert all(item["item_type"] == "Case Study" for item in items)
    assert all(90 <= len(item["summary"]) <= 560 and item["summary"][-1] in ".!?" for item in items)
    assert all(urlparse(item["source_url"]).scheme == "https" and urlparse(item["source_url"]).hostname in PUBLIC_HOSTS for item in items)
    assert not any(any(path in item["source_url"] for path in LIBRARY_PATHS) for item in items)
    assert all(item["case_library_overlap"] == "Not in the linked case-study libraries" for item in items)
    assert all(item["case_place"] and item["case_state"] and item["case_year"] for item in items)
    assert all(item["case_place_type"] in {"town_or_city", "county_or_region", "tribal_community", "statewide_or_multi_community"} for item in items)
    assert all(item["project_stage"] in {"Planning", "Implementation", "Cleanup"} for item in items)
    serialized = json.dumps(payload, ensure_ascii=False).lower()
    assert not re.search(r"[a-z]:\\|protos|private_internal|needs_image_review|todo|lorem ipsum", serialized)
    manifest = {
        "release_id": f"rerc-independent-community-precedents-{payload['generated_at']}",
        "status": "PASS",
        "scope": "Curated, detailed public precedents not duplicated in the linked source libraries.",
        "privacy": {"private_source_records_modified": False, "local_paths_included": False, "admin_fields_included": False, "images_included": False},
        "count": len(items),
        "program_counts": dict(sorted(Counter(item["case_program"] for item in items).items())),
        "source_host_counts": dict(sorted(Counter(urlparse(item["source_url"]).hostname for item in items).items())),
        "checks": ["unique IDs", "official HTTPS sources", "no linked-library duplication", "bounded summaries", "no private paths"],
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(manifest, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
