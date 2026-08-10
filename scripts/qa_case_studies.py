from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "case_studies.js"
MANIFEST = ROOT / "case_studies.public_manifest.json"
HEALTH = ROOT / "case_studies.source_health.json"
PREFIX = "window.RERC_CASE_STUDIES="
PUBLIC_HOSTS = {"www.epa.gov", "toolkit.climate.gov", "www.rd.usda.gov"}
FORBIDDEN = (
    "protos treats",
    "protos indexes",
    "record remains flagged",
    "image rights",
    "internal source",
    "local source",
    "needs review",
    "source manifest",
    ".pptx",
    ".docx",
    ".xlsx",
)


def main() -> int:
    raw = DATA.read_text(encoding="utf-8").strip()
    assert raw.startswith(PREFIX) and raw.endswith(";")
    payload = json.loads(raw[len(PREFIX) : -1])
    items = payload["items"]
    assert len(items) == payload["count"]
    assert len({item["item_id"] for item in items}) == len(items)
    assert all(item["item_type"] == "Case Study" for item in items)
    assert all(55 <= len(item["summary"]) <= 560 for item in items)
    assert all(item["case_place"] and item["case_state"] for item in items)
    assert all(item["case_state"] != "Unknown" for item in items)
    assert all(urlparse(item["source_url"]).hostname in PUBLIC_HOSTS for item in items)

    serialized = json.dumps(payload, ensure_ascii=False).lower()
    assert not re.search(r"[a-z]:\\", serialized)
    assert not any(marker in serialized for marker in FORBIDDEN)
    assert not any(marker in serialized for marker in ("Ã", "Â", "â", "Æ", "ï¿½", "\ufffd"))
    assert not any("$" in item["case_place"] or len(item["case_place"]) > 72 for item in items)
    assert not any(re.search(r"epa grant recipients?|site description|photo courtesy|pictured here|supporting environmental excellence", item["summary"], re.I) for item in items)
    assert all(item["summary"][-1] in ".!?" for item in items)
    assert len({item["summary"] for item in items}) == len(items)
    assert not any(re.search(r"helps communities compare approaches|official example from|is an EPA RERC|used Local Foods, Local Places technical assistance", item["summary"], re.I) for item in items)
    assert not any(re.search(r"\b(un-\s+derutilized|fabrica\u019fion)", item["summary"] + " " + item["topic_tags"], re.I) for item in items)
    assert not any(re.search(r"\.\s+(and|or|provide|enhance|help|explore)\b|residents walk through a greenhouse|\bSt\.$", item["summary"], re.I) for item in items)
    assert not any(re.search(r"appears in the official|case record for|is an official|an USDA", item["summary"], re.I) for item in items)
    assert not any(any(len(sentence.split()) > 49 for sentence in re.split(r"(?<=[.!?])\s+", item["summary"])) for item in items)
    assert not any(item["case_place"] == item["case_state"] for item in items)
    assert all(item["case_place_type"] in {"town_or_city", "county_or_region", "tribal_community", "statewide_or_multi_community"} for item in items)
    assert Counter(item["case_place_type"] for item in items) == {
        "town_or_city": 359,
        "county_or_region": 48,
        "statewide_or_multi_community": 56,
        "tribal_community": 14,
    }
    assert sum(item["case_place_type"] == "tribal_community" for item in items) >= 10
    expected_place_types = {
        "A Successful Transformation: From Wasted Lot to Reading Hot\u2010Spot": "town_or_city",
        "Richmond Creamery, Richmond, Vt.": "town_or_city",
        "South Dakota Governor's House Program - Providing Affordable Housing for 30 Years": "statewide_or_multi_community",
        "Lapwai, Idaho Local Foods, Local Places Summary Report": "tribal_community",
        "Mission, South Dakota Local Foods, Local Places Summary Report": "tribal_community",
        "Akwesasne, New York (2022)": "tribal_community",
        "Buffelgrass Removal, Fire, and Climate Adaptation": "county_or_region",
        "Forest Thinning to Restore Fire Resilience at Lassen Volcanic National Park": "county_or_region",
        "Great Lakes Restoration Initiative Pollinator Task Force": "county_or_region",
        "Alligator River National Wildlife Refuge / Albemarle-Pamlico Peninsula Climate Adaptation Project": "county_or_region",
        "Expanding an Indigenous Environmental Monitoring Network: Community-driven Stewardship of Land and Water": "tribal_community",
    }
    place_types_by_title = {item["title"]: item["case_place_type"] for item in items}
    assert all(place_types_by_title.get(title) == expected for title, expected in expected_place_types.items())
    assert all(item["project_stage"] in {"Planning", "Implementation", "Cleanup"} for item in items)
    assert all(item["project_stage"] == "Cleanup" for item in items if item["case_program"] == "EPA Brownfields Success Stories")
    assert not any(item["case_year"] == "2026" for item in items if item["case_program"] == "EPA Examples of Smart Growth Communities and Projects")

    debris = re.compile(r"image lessons learned|figure\s+\d|courtesy|years awarded|site descrip|grant types?:|grants and resources:|\u019f|\(pdf\)|\b\d+(?:\.\d+)?\s*MB\b|proposed site plan|R1 Success Story:|Brownfields Success Story|Job Placement Rate:|Current Uses?:|Year Awarded:|Residents walk through a greenhouse|twoand|Industriallumber|Fish and Wildlife Service \(USFWS\) to evaluate", re.I)
    suspicious_place = re.compile(r"\b(plan|action|company|industrial development|successful transformation|workers in|brownfield to)\b", re.I)
    assert not any(debris.search(item["summary"]) or item["summary"][:1].islower() for item in items)
    assert not any(":" in item["case_place"] or suspicious_place.search(item["case_place"]) for item in items)
    assert not any(re.match(r"^(of|the|a|an)\b", item["case_place"], re.I) for item in items)
    by_title = {item["title"]: item for item in items}
    expected_geography = {
        "WaterFire Arts Center, Providence, R.I.": ("Providence", "Rhode Island", "town_or_city"),
        "Hillsboro, OR: Navigating a New River Launch": ("Hillsboro", "Oregon", "town_or_city"),
        "Ambler, PA: Repowering a Historic Landmark": ("Ambler", "Pennsylvania", "town_or_city"),
        "Richmond, VA: Cheers to a Revitalized Neighborhood": ("Richmond", "Virginia", "town_or_city"),
        "Wood for Life, a Collaborative Partnership to Provide Wood to the Navajo Nation and Hopi Tribe": ("Navajo Nation and Hopi Tribe", "Arizona", "tribal_community"),
        "Alligator River National Wildlife Refuge / Albemarle-Pamlico Peninsula Climate Adaptation Project": ("Albemarle-Pamlico Peninsula", "North Carolina", "county_or_region"),
    }
    assert all((by_title[title]["case_place"], by_title[title]["case_state"], by_title[title]["case_place_type"]) == expected for title, expected in expected_geography.items())
    assert "two- and three-bedroom homes" in by_title["South Dakota Governor's House Program - Providing Affordable Housing for 30 Years"]["summary"]
    assert "restored its floodplain" in by_title["250 Birge St., Brattleboro, Vt."]["summary"]
    assert by_title["250 Birge St., Brattleboro, Vt."]["topic_tags"] == "Brownfields; Land Revitalization; Public Park; Floodplain Restoration; Flood Resilience"
    assert "Dare and Hyde Counties" in by_title["Alligator River National Wildlife Refuge / Albemarle-Pamlico Peninsula Climate Adaptation Project"]["summary"]
    st_paul = by_title["Expanding an Indigenous Environmental Monitoring Network: Community-driven Stewardship of Land and Water"]["summary"]
    assert "St. Paul Island" in st_paul and "[E]mpowering" not in st_paul and "ISN History" not in st_paul
    great_lakes = by_title["Great Lakes Restoration Initiative Pollinator Task Force"]["summary"]
    assert not great_lakes.endswith('".') and '".' not in great_lakes
    planning = [item for item in items if item["case_program"] in {"Recreation Economy for Rural Communities", "Local Foods, Local Places"}]
    assert len({item["summary"] for item in planning}) == len(planning)
    assert all(item["case_place"].lower() in item["summary"].lower() or item["case_place"] == "Multiple communities" for item in planning)
    assert all(
        item["case_place"] == "Forest County" or item["case_place_type"] in {"town_or_city", "tribal_community"}
        for item in items if item["case_program"] == "Local Foods, Local Places"
    )

    health = json.loads(HEALTH.read_text(encoding="utf-8"))
    unique_urls = len({item["source_url"] for item in items})
    assert health["unique_urls"] == unique_urls
    assert health["counts"]["hard_failure"] == 0
    assert health["counts"]["manual_review"] == 0
    assert sum(health["counts"].values()) == unique_urls

    programs = Counter(item["case_program"] for item in items)
    hosts = Counter(urlparse(item["source_url"]).hostname for item in items)
    manifest = {
        "release_id": f"rerc-public-community-examples-{payload['generated_at']}",
        "status": "PASS",
        "scope": "Text-only community examples derived from official federal public web records.",
        "approval_basis": "Public RERC community-example integration approved on 2026-07-17.",
        "privacy": {
            "private_source_records_modified": False,
            "local_paths_included": False,
            "admin_fields_included": False,
            "images_included": False,
        },
        "rights_note": "Official links and short source-derived descriptions are attributed. Images are excluded. This release check is not a legal opinion.",
        "count": len(items),
        "program_counts": dict(sorted(programs.items())),
        "source_host_counts": dict(sorted(hosts.items())),
        "source_health": {
            "unique_urls": health["unique_urls"],
            **health["counts"],
        },
        "checks": [
            "unique IDs",
            "official HTTPS hosts only",
            "bounded summaries",
            "known geography",
            "no private paths",
            "no internal workflow language",
            "no source filenames",
            "no common mojibake",
            "no images",
            "no extraction debris",
            "specific community names",
            "normalized community types",
            "distinct planning-assistance summaries",
        ],
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
