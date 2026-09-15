from __future__ import annotations

import argparse
import html
import io
import json
import os
import re
import secrets
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
import zipfile
import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape


APP_VERSION = "0.5.1"
APP_DIR = Path(os.environ.get("RERCIE_APP_ROOT") or (Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent))
ASSET_DIR = APP_DIR / "assets"
if not ASSET_DIR.is_dir() and not getattr(sys, "frozen", False):
    ASSET_DIR = Path(__file__).resolve().parent.parent / "assets"
LOCAL_KNOWLEDGE_DIR = APP_DIR / "local_knowledge"
PUBLIC_CATALOG_URL = "https://henkelpress.github.io/rerc-grant-finder/data.js"
PUBLIC_COMMUNITY_PROFILE_URL = "https://henkelpress.github.io/rerc-grant-finder/community_profiles.js"
COMMUNITY_PROFILE_PREFIX = "window.RERC_COMMUNITY_PROFILES="
MAX_COMMUNITY_PROFILE_BYTES = 16 * 1024 * 1024
MAX_COMMUNITY_PROFILE_RECORDS = 50000
CATALOG_PREFIXES = ("window.RERC_CATALOG = ", "window.GRANT_EXPLORER_DATA = ")
DEFAULT_MODEL = "gemma-3-1b-it-Q4_K_M.gguf"
LOCAL_CHAT_URL = os.environ.get("RERCIE_LOCAL_CHAT_URL", "http://127.0.0.1:8788/v1/chat/completions")
LOCAL_HEALTH_URL = os.environ.get("RERCIE_LOCAL_HEALTH_URL", "http://127.0.0.1:8788/health")
LOCAL_MODELS_URL = os.environ.get("RERCIE_LOCAL_MODELS_URL", "http://127.0.0.1:8788/v1/models")
SESSION_TOKEN = os.environ.get("RERCIE_SESSION_TOKEN", "")
EXPECTED_HOST = os.environ.get("RERCIE_EXPECTED_HOST", "127.0.0.1:8789").lower()
EXPECTED_ORIGIN = f"http://{EXPECTED_HOST}"


def _require_loopback_runtime_url(name: str, value: str) -> str:
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise RuntimeError(f"{name} must use a loopback-only http URL.")
    return value


for _runtime_name, _runtime_url in (
    ("RERCIE_LOCAL_CHAT_URL", LOCAL_CHAT_URL),
    ("RERCIE_LOCAL_HEALTH_URL", LOCAL_HEALTH_URL),
    ("RERCIE_LOCAL_MODELS_URL", LOCAL_MODELS_URL),
):
    _require_loopback_runtime_url(_runtime_name, _runtime_url)
CENSUS_YEAR = "2024"
CENSUS_ISLAND_YEAR = "2020"
MAX_REQUEST_BYTES = 6 * 1024 * 1024
HANDOFF_SCHEMA = "rerc-e-handoff"
LEGACY_HANDOFF_SCHEMA = "rercie-handoff"
HANDOFF_VERSION = 1
MAX_HANDOFF_BYTES = 256 * 1024
MAX_HANDOFF_RECORDS = 100
MAX_HANDOFF_ROADMAP_ITEMS = 50
STARTUP_HANDOFF_PATH = APP_DIR / "runtime" / "handoff" / "pending.rercie"

STATE_FIPS = {
    "Alabama": "01", "Alaska": "02", "Arizona": "04", "Arkansas": "05", "California": "06",
    "Colorado": "08", "Connecticut": "09", "Delaware": "10", "District of Columbia": "11",
    "Florida": "12", "Georgia": "13", "Hawaii": "15", "Idaho": "16", "Illinois": "17",
    "Indiana": "18", "Iowa": "19", "Kansas": "20", "Kentucky": "21", "Louisiana": "22",
    "Maine": "23", "Maryland": "24", "Massachusetts": "25", "Michigan": "26", "Minnesota": "27",
    "Mississippi": "28", "Missouri": "29", "Montana": "30", "Nebraska": "31", "Nevada": "32",
    "New Hampshire": "33", "New Jersey": "34", "New Mexico": "35", "New York": "36",
    "North Carolina": "37", "North Dakota": "38", "Ohio": "39", "Oklahoma": "40", "Oregon": "41",
    "Pennsylvania": "42", "Rhode Island": "44", "South Carolina": "45", "South Dakota": "46",
    "Tennessee": "47", "Texas": "48", "Utah": "49", "Vermont": "50", "Virginia": "51",
    "Washington": "53", "West Virginia": "54", "Wisconsin": "55", "Wyoming": "56",
    "American Samoa": "60", "Guam": "66", "Northern Mariana Islands": "69", "Puerto Rico": "72",
    "U.S. Virgin Islands": "78",
}

ISLAND_AREA_DATASETS = {
    "American Samoa": "dhcas",
    "Guam": "dhcgu",
    "Northern Mariana Islands": "dhcmp",
    "U.S. Virgin Islands": "dhcvi",
}

HANDOFF_TOP_LEVEL_FIELDS = {
    "schema", "version", "community", "state", "projectTitle", "projectNotes",
    "profile", "roadmap", "selectedRecords",
}
HANDOFF_PROFILE_FIELD_LIMITS = {
    "geoid": 32,
    "place": 300,
    "geography_type": 80,
    "population": 40,
    "median_age": 40,
    "median_household_income": 40,
    "poverty_rate_percent": 40,
    "source": 500,
    "source_url": 2048,
    "year": 20,
    "coverage_note": 2000,
    "margin_of_error_note": 2000,
    "suppressed": 20,
}
HANDOFF_ROADMAP_FIELD_LIMITS = {
    "id": 200,
    "stage": 100,
    "title": 500,
    "description": 4000,
    "status": 100,
    "dueDate": 40,
    "owner": 300,
    "notes": 4000,
    "sourceUrl": 2048,
}
HANDOFF_RECORD_FIELD_LIMITS = {
    "item_id": 200,
    "item_type": 40,
    "title": 500,
    "organization": 500,
    "status": 200,
    "last_checked": 40,
    "geography": 500,
    "eligible_users": 3000,
    "project_stage": 500,
    "topic_tags": 3000,
    "support_type": 200,
    "amount_or_cost": 2000,
    "match_or_cost": 2000,
    "deadline_or_availability": 2000,
    "summary": 5000,
    "why_it_matters": 5000,
    "source_url": 2048,
    "case_place": 300,
    "case_state": 100,
    "case_place_type": 100,
    "case_program": 500,
    "case_year": 40,
    "case_partners": 2000,
}
HTML_MARKUP_PATTERN = re.compile(r"<\s*/?\s*[A-Za-z!][^>]*>")

SYSTEM_PROMPT = """You are an evidence-extraction assistant. Return JSON only.

Select up to six useful excerpts copied exactly from the supplied evidence. Do not
paraphrase, summarize, correct, combine, or add text. Each excerpt must be a
complete sentence or a short self-contained phrase. Return this shape:
{"excerpts":[{"text":"exact copied text"}]}
If there is no useful evidence, return {"excerpts":[]}."""


def _plain_object(value: Any, label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError(f"{label} must be a plain JSON object.")
    return value


def _bounded_handoff_string(value: Any, label: str, limit: int, required: bool = False) -> str:
    if type(value) is not str:
        raise ValueError(f"{label} must be text.")
    text = unicodedata.normalize("NFC", value)
    if len(text) > limit:
        raise ValueError(f"{label} is too long.")
    if required and not text.strip():
        raise ValueError(f"{label} is required.")
    if HTML_MARKUP_PATTERN.search(text):
        raise ValueError(f"{label} contains HTML markup. Use plain text only.")
    return text


def _validated_http_url(value: Any, label: str, limit: int = 2048) -> str:
    url = _bounded_handoff_string(value, label, limit)
    if not url:
        return ""
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError(f"{label} must be a public http or https URL.")
    return url


def _reject_json_constant(value: str) -> Any:
    raise ValueError(f"Unsupported JSON value: {value}.")


def validate_handoff_package(package: Any) -> dict[str, Any]:
    handoff = _plain_object(package, "The plan")
    keys = set(handoff)
    if keys != HANDOFF_TOP_LEVEL_FIELDS:
        missing = sorted(HANDOFF_TOP_LEVEL_FIELDS - keys)
        unexpected = sorted(keys - HANDOFF_TOP_LEVEL_FIELDS)
        details = []
        if missing:
            details.append("missing " + ", ".join(missing))
        if unexpected:
            details.append("unexpected " + ", ".join(unexpected))
        raise ValueError("The plan fields are not valid" + (": " + "; ".join(details) if details else "."))
    if type(handoff.get("schema")) is not str or handoff.get("schema") not in {HANDOFF_SCHEMA, LEGACY_HANDOFF_SCHEMA}:
        raise ValueError(f"The plan schema must be {HANDOFF_SCHEMA}.")
    if type(handoff.get("version")) is not int or handoff.get("version") != HANDOFF_VERSION:
        raise ValueError(f"The plan version must be {HANDOFF_VERSION}.")

    community = _bounded_handoff_string(handoff.get("community"), "community", 200, required=True)
    state = _bounded_handoff_string(handoff.get("state"), "state", 100, required=True)
    if state not in STATE_FIPS:
        raise ValueError("state must be a supported U.S. state or territory.")
    project_title = _bounded_handoff_string(handoff.get("projectTitle"), "projectTitle", 300, required=True)
    project_notes = _bounded_handoff_string(handoff.get("projectNotes"), "projectNotes", 20000)

    raw_profile = _plain_object(handoff.get("profile"), "profile")
    unexpected_profile = set(raw_profile) - set(HANDOFF_PROFILE_FIELD_LIMITS)
    if unexpected_profile:
        raise ValueError("profile contains unsupported fields: " + ", ".join(sorted(unexpected_profile)))
    profile: dict[str, Any] = {}
    for key, value in raw_profile.items():
        if type(value) not in {str, int, float, bool}:
            raise ValueError(f"profile.{key} must be a text, number, or true/false value.")
        text = _bounded_handoff_string(str(value), f"profile.{key}", HANDOFF_PROFILE_FIELD_LIMITS[key])
        profile[key] = text
    if "source_url" in profile:
        profile["source_url"] = _validated_http_url(profile["source_url"], "profile.source_url")

    raw_roadmap = handoff.get("roadmap")
    if type(raw_roadmap) is not list:
        raise ValueError("roadmap must be a JSON array.")
    if len(raw_roadmap) > MAX_HANDOFF_ROADMAP_ITEMS:
        raise ValueError(f"roadmap can contain no more than {MAX_HANDOFF_ROADMAP_ITEMS} items.")
    roadmap: list[dict[str, str]] = []
    for index, raw_item in enumerate(raw_roadmap):
        item = _plain_object(raw_item, f"roadmap[{index}]")
        unexpected_fields = set(item) - set(HANDOFF_ROADMAP_FIELD_LIMITS)
        if unexpected_fields:
            raise ValueError(f"roadmap[{index}] contains unsupported fields: " + ", ".join(sorted(unexpected_fields)))
        if "stage" not in item or "title" not in item:
            raise ValueError(f"roadmap[{index}] must include stage and title.")
        normalized_item: dict[str, str] = {}
        for key, value in item.items():
            normalized_item[key] = _bounded_handoff_string(
                value,
                f"roadmap[{index}].{key}",
                HANDOFF_ROADMAP_FIELD_LIMITS[key],
                required=key in {"stage", "title"},
            )
        if normalized_item.get("sourceUrl"):
            normalized_item["sourceUrl"] = _validated_http_url(
                normalized_item["sourceUrl"], f"roadmap[{index}].sourceUrl"
            )
        roadmap.append(normalized_item)

    raw_records = handoff.get("selectedRecords")
    if type(raw_records) is not list:
        raise ValueError("selectedRecords must be a JSON array.")
    if len(raw_records) > MAX_HANDOFF_RECORDS:
        raise ValueError(f"selectedRecords can contain no more than {MAX_HANDOFF_RECORDS} records.")
    selected_records: list[dict[str, str]] = []
    record_ids: set[str] = set()
    for index, raw_record in enumerate(raw_records):
        record = _plain_object(raw_record, f"selectedRecords[{index}]")
        unexpected_fields = set(record) - set(HANDOFF_RECORD_FIELD_LIMITS)
        if unexpected_fields:
            raise ValueError(
                f"selectedRecords[{index}] contains unsupported fields: " + ", ".join(sorted(unexpected_fields))
            )
        required_fields = {"item_id", "item_type", "title", "source_url"}
        if not required_fields.issubset(record):
            raise ValueError(f"selectedRecords[{index}] must include item_id, item_type, title, and source_url.")
        normalized_record: dict[str, str] = {}
        for key, value in record.items():
            normalized_record[key] = _bounded_handoff_string(
                value,
                f"selectedRecords[{index}].{key}",
                HANDOFF_RECORD_FIELD_LIMITS[key],
                required=key in required_fields,
            )
        item_type = normalized_record["item_type"].lower()
        if item_type not in {"funding", "resource", "case study"}:
            raise ValueError(f"selectedRecords[{index}].item_type is not supported.")
        normalized_record["source_url"] = _validated_http_url(
            normalized_record["source_url"], f"selectedRecords[{index}].source_url"
        )
        item_id = normalized_record["item_id"]
        if item_id in record_ids:
            raise ValueError(f"selectedRecords contains a duplicate item_id: {item_id}.")
        record_ids.add(item_id)
        selected_records.append(normalized_record)

    return {
        "schema": HANDOFF_SCHEMA,
        "version": HANDOFF_VERSION,
        "community": community,
        "state": state,
        "projectTitle": project_title,
        "projectNotes": project_notes,
        "profile": profile,
        "roadmap": roadmap,
        "selectedRecords": selected_records,
    }


def validate_handoff_text(raw: str | bytes) -> dict[str, Any]:
    if isinstance(raw, bytes):
        encoded = raw
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError("The plan must be UTF-8 JSON text.") from exc
    elif type(raw) is str:
        text = raw
        encoded = raw.encode("utf-8")
    else:
        raise ValueError("The plan must be JSON text.")
    if not encoded or len(encoded) > MAX_HANDOFF_BYTES:
        raise ValueError(f"The plan must be no larger than {MAX_HANDOFF_BYTES // 1024} KB.")
    try:
        package = json.loads(text, parse_constant=_reject_json_constant)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("The plan is not valid JSON.") from exc
    return validate_handoff_package(package)


def _selected_record_summary(record: dict[str, str]) -> str:
    fields = (
        ("Program", record.get("title")),
        ("Organization", record.get("organization")),
        ("Status", record.get("status")),
        ("Eligible users", record.get("eligible_users")),
        ("Geography", record.get("geography")),
        ("Project stage", record.get("project_stage")),
        ("Topics", record.get("topic_tags")),
        ("Support type", record.get("support_type")),
        ("Amount or support", record.get("amount_or_cost")),
        ("Match or cost", record.get("match_or_cost")),
        ("Deadline or availability", record.get("deadline_or_availability")),
        ("Last checked", record.get("last_checked")),
        ("Summary", record.get("summary") or record.get("why_it_matters")),
        ("Official page", record.get("source_url")),
    )
    return "\n".join(f"{label}: {value}" for label, value in fields if value)


def handoff_to_form(handoff: dict[str, Any]) -> dict[str, Any]:
    funding_records = [
        record for record in handoff["selectedRecords"]
        if record.get("item_type", "").lower() == "funding"
    ]
    reference_records = [
        record for record in handoff["selectedRecords"]
        if record.get("item_type", "").lower() != "funding"
    ]
    selected_funding_details = "\n\n---\n\n".join(_selected_record_summary(record) for record in funding_records)
    notes_parts = [handoff["projectNotes"].strip()] if handoff["projectNotes"].strip() else []
    if handoff["roadmap"]:
        roadmap_lines = ["Community Explorer roadmap:"]
        for item in handoff["roadmap"]:
            line = f"- {item.get('stage')}: {item.get('title')}"
            if item.get("description"):
                line += f" - {item['description']}"
            if item.get("status"):
                line += f" (Status: {item['status']})"
            details = []
            if item.get("owner"):
                details.append(f"Owner: {item['owner']}")
            if item.get("dueDate"):
                details.append(f"Due: {item['dueDate']}")
            if item.get("notes"):
                details.append(f"Notes: {item['notes']}")
            if item.get("sourceUrl"):
                details.append(f"Source: {item['sourceUrl']}")
            if details:
                line += " | " + " | ".join(details)
            roadmap_lines.append(line)
        notes_parts.append("\n".join(roadmap_lines))
    if reference_records:
        reference_lines = ["Selected public resources and community examples:"]
        for record in reference_records:
            reference_lines.append(
                f"- {record.get('title')} ({record.get('item_type')}): {record.get('source_url')}"
            )
        notes_parts.append("\n".join(reference_lines))
    return {
        "status": "imported",
        "message": (
            f"Opened the Community Explorer plan for {handoff['community']}. "
            f"Imported {len(funding_records)} funding record"
            f"{'' if len(funding_records) == 1 else 's'} and "
            f"{len(reference_records)} resource or community example"
            f"{'' if len(reference_records) == 1 else 's'}."
        ),
        "community": handoff["community"],
        "state": handoff["state"],
        "projectTitle": handoff["projectTitle"],
        "projectNotes": "\n\n".join(notes_parts),
        "profile": handoff["profile"],
        "roadmap": handoff["roadmap"],
        "selectedRecords": handoff["selectedRecords"],
        "selectedFundingDetails": selected_funding_details,
    }


def consume_startup_handoff() -> dict[str, Any] | None:
    if not STARTUP_HANDOFF_PATH.is_file():
        return None
    try:
        size = STARTUP_HANDOFF_PATH.stat().st_size
        if size <= 0 or size > MAX_HANDOFF_BYTES:
            raise ValueError(f"The launcher plan must be no larger than {MAX_HANDOFF_BYTES // 1024} KB.")
        imported = handoff_to_form(validate_handoff_text(STARTUP_HANDOFF_PATH.read_bytes()))
    except Exception as exc:
        rejected = STARTUP_HANDOFF_PATH.with_name(f"rejected-{int(time.time())}.rercie")
        try:
            STARTUP_HANDOFF_PATH.replace(rejected)
            raise ValueError(f"The startup plan was rejected and preserved as {rejected.name}: {exc}") from exc
        except OSError:
            raise
    STARTUP_HANDOFF_PATH.unlink(missing_ok=True)
    return imported


def request_json(url: str, payload: dict[str, Any] | None = None, headers: dict[str, str] | None = None, timeout: int = 30) -> Any:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request_headers = {"Accept": "application/json", "User-Agent": f"RERC-e/{APP_VERSION}"}
    if body is not None:
        request_headers["Content-Type"] = "application/json"
    if headers:
        request_headers.update(headers)
    request = urllib.request.Request(url, data=body, headers=request_headers)
    opener = urllib.request.build_opener(_HttpsOnlyRedirectHandler())
    with opener.open(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def parse_public_catalog(raw: str) -> dict[str, Any]:
    raw = raw.strip()
    prefix = next((item for item in CATALOG_PREFIXES if raw.startswith(item)), None)
    if not prefix or not raw.endswith(";"):
        raise ValueError("The public funding file was not in the expected format.")
    catalog = json.loads(raw[len(prefix):-1])
    if "items" in catalog:
        items = catalog.get("items") or []
        return {
            "grants": [item for item in items if str(item.get("item_type", "")).lower() == "funding"],
            "resources": [item for item in items if str(item.get("item_type", "")).lower() == "resource"],
            "counts": catalog.get("counts") or {},
            "updated": catalog.get("updated") or "",
        }
    if "grants" in catalog:
        return catalog
    raise ValueError("The public funding file did not contain funding records.")


class _HttpsOnlyRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> Any:
        if urllib.parse.urlsplit(newurl).scheme.lower() != "https":
            raise ValueError("The public resource redirected away from HTTPS.")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _request_text(url: str, *, timeout: int = 30, max_bytes: int = MAX_REQUEST_BYTES) -> str:
    if not url.lower().startswith("https://"):
        raise ValueError("RERC-e can only fetch public HTTPS resources.")
    if max_bytes <= 0:
        raise ValueError("The public payload size limit must be positive.")
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/javascript,text/plain,*/*", "User-Agent": f"RERC-e/{APP_VERSION}"},
    )
    opener = urllib.request.build_opener(_HttpsOnlyRedirectHandler())
    with opener.open(request, timeout=timeout) as response:
        final_url = response.geturl()
        if not final_url.lower().startswith("https://"):
            raise ValueError("The public resource redirected away from HTTPS.")
        content_length = response.headers.get("Content-Length", "").strip()
        if content_length:
            try:
                content_length_value = int(content_length)
            except ValueError as exc:
                raise ValueError("The public payload had an invalid size header.") from exc
            if content_length_value < 0 or content_length_value > max_bytes:
                raise ValueError("The public payload exceeded the size limit.")
        payload = response.read(max_bytes + 1)
    if len(payload) > max_bytes:
        raise ValueError("The public payload exceeded the size limit.")
    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("The public payload was not valid UTF-8.") from exc


def fetch_public_catalog() -> dict[str, Any]:
    return parse_public_catalog(_request_text(PUBLIC_CATALOG_URL))


def parse_public_community_profiles(raw: str) -> list[dict[str, Any]]:
    try:
        raw_bytes = raw.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError("The public community profile file was not valid UTF-8.") from exc
    if len(raw_bytes) > MAX_COMMUNITY_PROFILE_BYTES:
        raise ValueError("The public community profile file exceeded the size limit.")
    match = re.fullmatch(
        r"window\.RERC_COMMUNITY_PROFILES\s*=\s*(\[.*\])\s*;\s*",
        raw.strip(),
        flags=re.DOTALL,
    )
    if not match:
        raise ValueError("The public community profile file was not in the expected format.")
    try:
        records = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise ValueError("The public community profile file contained invalid JSON.") from exc
    if not isinstance(records, list):
        raise ValueError("The public community profile file was not a list.")
    if len(records) > MAX_COMMUNITY_PROFILE_RECORDS:
        raise ValueError("The public community profile file contained too many records.")
    if any(not isinstance(record, dict) for record in records):
        raise ValueError("The public community profile file contained an invalid record.")
    return records


def _coerce_profile_number(raw: Any) -> str:
    value = str(raw or "").strip()
    if value and value.lower() == "nan":
        return ""
    return value


def _normalize_lookup_name(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def fetch_public_community_profile(community: str, state: str) -> dict[str, str]:
    records = parse_public_community_profiles(
        _request_text(PUBLIC_COMMUNITY_PROFILE_URL, max_bytes=MAX_COMMUNITY_PROFILE_BYTES)
    )
    target_name = _normalize_lookup_name((community or "").split(",", 1)[0])
    target_state = _normalize_lookup_name(state or "")
    exact_matches: list[dict[str, Any]] = []
    alias_matches: list[dict[str, Any]] = []
    for record in records:
        candidate_name = _normalize_lookup_name(
            (str(record.get("community", "")) or str(record.get("name", ""))).split(",", 1)[0]
        )
        candidate_state = _normalize_lookup_name(str(record.get("state", "")))
        if candidate_state != target_state:
            continue
        if candidate_name == target_name:
            exact_matches.append(record)
        elif re.sub(r"\s+(?:town|city|village)$", "", candidate_name) == target_name:
            alias_matches.append(record)
    matching_records = exact_matches or alias_matches
    if len(matching_records) == 1:
        record = matching_records[0]
        if record:
            source = str(record.get("source") or "RERC Community Explorer profile bundle").strip()
            profile: dict[str, str] = {
                "source": source,
                "source_url": str(record.get("source_url") or (
                    "https://api.census.gov/data/2024/acs/acs5/profile.html"
                    if "ACS" in source else
                    "https://www.census.gov/data/datasets/2020/dec/2020-island-areas.html"
                )),
                "year": str(record.get("vintage") or ""),
                "geography_type": str(record.get("placeType") or "community").replace("_", " ").strip(),
                "place": str(record.get("name") or record.get("community") or ""),
                "population": _coerce_profile_number(record.get("population")),
                "median_household_income": _coerce_profile_number(record.get("medianHouseholdIncome")),
                "poverty_rate_percent": _coerce_profile_number(record.get("povertyRate")),
                "coverage_note": str(record.get("coverageNote") or "").strip(),
            }
            if record.get("geoid"):
                profile["geoid"] = str(record.get("geoid") or "").strip()
            if record.get("broadbandRate") is not None:
                profile["broadband_rate"] = _coerce_profile_number(record.get("broadbandRate"))
            return profile
    return {}

def _local_env_value(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if value:
        return value
    env_path = Path.home() / ".env"
    try:
        for raw_line in env_path.read_text(encoding="utf-8-sig", errors="ignore").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, candidate = line.split("=", 1)
            if key.strip() == name:
                return candidate.strip().strip('"').strip("'")
    except OSError:
        pass
    return ""


def _normalize_geography_name(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii").lower()
    text = re.sub(r"\bst[.]?\b", "saint", text)
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()
    suffixes = {
        "city", "town", "village", "borough", "municipality", "municipio", "cdp",
        "county", "parish", "census area", "city and borough",
    }
    for suffix in sorted(suffixes, key=len, reverse=True):
        if text.endswith(" " + suffix):
            text = text[: -(len(suffix) + 1)].strip()
            break
    return text


def _best_geography_record(rows: Any, community: str) -> dict[str, str]:
    if not isinstance(rows, list) or len(rows) < 2:
        return {}
    headers = rows[0]
    target = _normalize_geography_name((community or "").split(",", 1)[0])
    if not target:
        return {}
    scored: list[tuple[int, int, dict[str, str]]] = []
    for row in rows[1:]:
        record = dict(zip(headers, row, strict=False))
        candidate = _normalize_geography_name(record.get("NAME", "").split(",", 1)[0])
        if candidate == target:
            score = 4
        elif candidate.startswith(target + " ") or target.startswith(candidate + " "):
            score = 3
        elif target in candidate or candidate in target:
            score = 2
        else:
            continue
        scored.append((score, -abs(len(candidate) - len(target)), record))
    if not scored:
        return {}
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    if len(scored) > 1 and scored[0][:2] == scored[1][:2]:
        return {}
    return scored[0][2]


def _census_api_key(census_api_key: str = "") -> str:
    return (census_api_key or _local_env_value("CENSUS_API_KEY")).strip()


def _census_url(path: str, params: dict[str, str]) -> str:
    return f"https://api.census.gov/data/{path}?{urllib.parse.urlencode(params)}"


def fetch_census_community_profile(community: str, state: str, census_api_key: str = "") -> dict[str, str]:
    community = (community or "").split(",", 1)[0].strip()
    state = (state or "").strip()
    fips = STATE_FIPS.get(state)
    if not community or not fips:
        return {}
    api_key = _census_api_key(census_api_key)
    if not api_key:
        raise PermissionError("A Census API key is required for direct lookup.")

    if state in ISLAND_AREA_DATASETS:
        dataset = ISLAND_AREA_DATASETS[state]
        params = {"get": "NAME,P1_001N", "for": f"state:{fips}", "key": api_key}
        rows = request_json(_census_url(f"{CENSUS_ISLAND_YEAR}/dec/{dataset}", params), timeout=30)
        record = dict(zip(rows[0], rows[1], strict=False)) if isinstance(rows, list) and len(rows) > 1 else {}
        if not record:
            return {}
        return {
            "source": f"U.S. Census Bureau {CENSUS_ISLAND_YEAR} Island Areas Census",
            "source_url": "https://www.census.gov/data/developers/data-sets/decennial-census.html",
            "year": CENSUS_ISLAND_YEAR,
            "geography_type": "territory",
            "place": record.get("NAME", state),
            "population": record.get("P1_001N", ""),
            "coverage_note": f"Community-level ACS profiles are not available through this endpoint, so RERC-e used territory-level context for {state}.",
        }

    fields = "NAME,DP05_0001E,DP03_0062E,DP03_0128PE,DP05_0018E"
    explicit_county = bool(re.search(r"\b(county|parish|census area)\b", community, re.IGNORECASE))
    geography_types = ("county", "place") if explicit_county else ("place", "county")
    for geography_type in geography_types:
        params = {"get": fields, "for": f"{geography_type}:*", "in": f"state:{fips}", "key": api_key}
        rows = request_json(_census_url(f"{CENSUS_YEAR}/acs/acs5/profile", params), timeout=30)
        record = _best_geography_record(rows, community)
        if not record:
            continue
        geoid = fips + record.get(geography_type, "")
        summary_level = "160" if geography_type == "place" else "050"
        return {
            "source": f"U.S. Census Bureau ACS {CENSUS_YEAR} 5-year profile",
            "source_url": f"https://data.census.gov/profile?g={summary_level}XX00US{geoid}",
            "year": CENSUS_YEAR,
            "geography_type": geography_type,
            "place": record.get("NAME", ""),
            "population": record.get("DP05_0001E", ""),
            "median_age": record.get("DP05_0018E", ""),
            "median_household_income": record.get("DP03_0062E", ""),
            "poverty_rate_percent": record.get("DP03_0128PE", ""),
        }
    return {}

def lookup_community_profile(community: str, state: str, census_api_key: str = "") -> dict[str, Any]:
    if not (community or "").strip() or not (state or "").strip():
        return {"profile": {}, "message": "Enter a community and choose a state or territory first.", "status": "missing_input"}

    api_key = _census_api_key(census_api_key)
    key_provided = bool(api_key)
    public_profile_unavailable = False
    try:
        profile = fetch_public_community_profile(community, state)
    except Exception:
        public_profile_unavailable = True
        profile = {}
        if not key_provided:
            return {
                "profile": {},
                "message": "The prebuilt community facts could not be reached right now. Retry, add a Census API key for fallback lookup, or continue with checked local facts.",
                "status": "unavailable",
            }

    if profile:
        return {
            "profile": profile,
            "message": f"Community facts found for {profile.get('place', community)}.",
            "status": "found",
        }

    if not key_provided:
        return {
            "profile": {},
            "message": "A matching public community profile was not found. Add a Census API key for this lookup, or check the spelling and state for your community.",
            "status": "key_required",
        }

    try:
        profile = fetch_census_community_profile(community, state, api_key)
    except PermissionError as exc:
        return {"profile": {}, "message": str(exc), "status": "key_required"}
    except Exception:
        return {
            "profile": {},
            "message": "Community facts could not be reached right now. The draft will mark local facts that still need to be added.",
            "status": "unavailable",
        }

    if not profile:
        return {
            "profile": {},
            "message": "No exact Census place or county match was found. Check the community name or add local facts in the notes.",
            "status": "not_found",
        }

    return {"profile": profile, "message": f"Community facts found for {profile.get('place', community)}.", "status": "found"}


def load_local_knowledge(max_total_chars: int = 32000, max_file_chars: int = 9000) -> str:
    LOCAL_KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    chunks: list[str] = []
    total = 0
    for path in sorted(LOCAL_KNOWLEDGE_DIR.iterdir()):
        if path.name.lower() == "readme.md" or path.suffix.lower() not in {".md", ".txt", ".csv", ".json"} or not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            continue
        if not content:
            continue
        block = f"\n--- Local reference: {path.name} ---\n{content[:max_file_chars]}\n"
        if total + len(block) > max_total_chars:
            break
        chunks.append(block)
        total += len(block)
    return "\n".join(chunks).strip()


def format_public_profile(public_profile: dict[str, str]) -> str:
    if not public_profile:
        return "[No verified public community profile was found. Do not guess local statistics.]"
    lines = [
        f"Verified geography: {public_profile.get('place', '[not listed]')}",
        f"Geography type: {public_profile.get('geography_type', '[not listed]')}",
    ]
    population = str(public_profile.get("population") or "").strip()
    income = str(public_profile.get("median_household_income") or "").strip()
    median_age = str(public_profile.get("median_age") or "").strip()
    poverty = str(public_profile.get("poverty_rate_percent") or "").strip()
    if population.lstrip("-").isdigit():
        lines.append(f"Population: {int(population):,}")
    if median_age:
        lines.append(f"Median age: {median_age} years")
    if income.lstrip("-").isdigit():
        lines.append("Median household income: $" + f"{int(income):,}")
    if poverty:
        lines.append(f"People below the poverty line: {poverty}%")
    if public_profile.get("coverage_note"):
        lines.append(f"Coverage note: {public_profile['coverage_note']}")
    lines.append(f"Source: {public_profile.get('source', 'U.S. Census Bureau')}")
    if public_profile.get("source_url"):
        lines.append(f"Official profile: {public_profile['source_url']}")
    return "\n".join(f"- {line}" for line in lines)


def compose_prompt(payload: dict[str, Any], public_profile: dict[str, str], local_knowledge: str) -> str:
    profile_text = format_public_profile(public_profile)
    return f"""Write a useful first-draft grant narrative for a community team to edit.

Community: {payload.get('community') or '[add community]'}, {payload.get('state') or '[add state or territory]'}
Project title: {payload.get('projectTitle') or '[add project title]'}
Project summary: {payload.get('projectSummary') or '[add project summary]'}

Selected funding record:
{payload.get('selectedGrant') or '[select a funding source]'}

Match, staff, and partner capacity:
{payload.get('matchCapacity') or '[add match and capacity facts]'}

Verified public community context:
{profile_text}

Project notes and uploaded text:
{payload.get('projectNotes') or '[add project notes]'}

Facts to check on the official funding page:
{payload.get('sourceNotes') or '[add source notes]'}

Local reference files:
{local_knowledge or '[no local reference files loaded]'}

Write Markdown with these level-two sections in this order: Fit Summary; Project Need; Community Context; Proposed Work; Community Benefit; Work Plan; Budget and Match Notes; Source and Eligibility Checks; Missing Details.

Writing requirements:
- Write cohesive short paragraphs, not a template conversation or a list of generic claims.
- Use the verified public facts exactly and name their source in Community Context.
- Connect only the stated project actions and verified facts; do not invent local conditions, outcomes, eligibility, deadlines, award amounts, match rules, partners, budgets, or commitments.
- Do not repeat the same caution in every section.
- Put unknown local facts in Missing Details as [add local fact].
- Put each unconfirmed funding rule in Source and Eligibility Checks as [check official source].
- Make the draft specific enough that a community can improve it, while preserving uncertainty.
- Do not include any number unless that exact number appears in the supplied evidence above.
- Do not create a study, survey, traffic condition, economic effect, budget, match amount, timeline, required partner, or eligibility rule.
- When the evidence does not support a claim, omit it and add the missing item under Missing Details.
""".strip()


def call_local_writer(prompt: str, model: str, system_prompt: str = SYSTEM_PROMPT) -> str:
    payload = {
        "model": model or DEFAULT_MODEL,
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
        "temperature": 0.0,
        "top_p": 0.9,
        "repeat_penalty": 1.08,
        "max_tokens": 900,
        "stream": False,
    }
    data = request_json(LOCAL_CHAT_URL, payload=payload, timeout=300)
    choices = data.get("choices") or []
    return choices[0].get("message", {}).get("content", "").strip() if choices else ""


def _normalized_text(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value or "")).strip()


def evidence_text(payload: dict[str, Any], public_profile: dict[str, str], local_knowledge: str) -> str:
    fields = (
        ("Community", payload.get("community")),
        ("State or territory", payload.get("state")),
        ("Project title", payload.get("projectTitle")),
        ("Project summary", payload.get("projectSummary")),
        ("Selected funding record", _funding_record_text(payload.get("selectedGrant"))),
        ("Match, staff, and partner capacity", payload.get("matchCapacity")),
        ("Official-source notes", payload.get("sourceNotes")),
        ("Project notes and uploaded text", payload.get("projectNotes")),
        ("Verified public community profile", format_public_profile(public_profile)),
        ("Local reference files", local_knowledge),
    )
    return "\n\n".join(
        f"[{label}]\n{str(value).strip()}" for label, value in fields if str(value or "").strip()
    )


def parse_verified_excerpts(raw: str, evidence: str, limit: int = 6) -> list[str]:
    candidate = (raw or "").strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json)?\s*", "", candidate, flags=re.IGNORECASE)
        candidate = re.sub(r"\s*```$", "", candidate)
    try:
        parsed = json.loads(candidate)
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    entries = parsed.get("excerpts", []) if isinstance(parsed, dict) else []
    if not isinstance(entries, list):
        return []
    verified: list[str] = []
    for entry in entries:
        excerpt = entry.get("text", "") if isinstance(entry, dict) else ""
        excerpt = str(excerpt).strip()
        if len(excerpt) < 18 or len(excerpt) > 500:
            continue
        if excerpt not in evidence or excerpt in verified:
            continue
        verified.append(excerpt)
        if len(verified) >= limit:
            break
    return verified


def select_evidence_excerpts(
    payload: dict[str, Any],
    public_profile: dict[str, str],
    local_knowledge: str,
    model: str,
) -> list[str]:
    evidence = evidence_text(payload, public_profile, local_knowledge)
    if not evidence:
        return []
    prompt = (
        "Select the most useful evidence for a grant-writing outline. "
        "Copy every excerpt exactly. Return JSON only.\n\nEVIDENCE:\n" + evidence
    )
    raw = call_local_writer(prompt, model, SYSTEM_PROMPT)
    return parse_verified_excerpts(raw, evidence)


def _funding_record_text(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "[select a funding source]"
    try:
        record = json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        return raw[:5000]
    if not isinstance(record, dict):
        return raw[:5000]
    fields = (
        ("Program", record.get("title") or record.get("program")),
        ("Organization", record.get("organization") or record.get("agency")),
        ("Status", record.get("status")),
        ("Eligible applicants", record.get("eligible_users") or record.get("best_for") or record.get("bestFor")),
        ("Project stage", record.get("project_stage")),
        ("Description", record.get("summary") or record.get("description") or record.get("why_it_matters")),
        ("Amount or support", record.get("amount_or_cost")),
        ("Match or cost share", record.get("match_or_cost")),
        ("Deadline or availability", record.get("deadline_or_availability")),
        ("Official page", record.get("url") or record.get("source_url")),
    )
    return "\n".join(f"- {label}: {value}" for label, value in fields if value) or raw[:5000]


def _as_sentence(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return text
    text = text[0].upper() + text[1:]
    return text if text.endswith((".", "!", "?")) else text + "."


def deterministic_scaffold(payload: dict[str, Any], public_profile: dict[str, str], excerpts: list[str] | None = None) -> str:
    community = str(payload.get("community") or "[add community]").strip()
    state = str(payload.get("state") or "[add state or territory]").strip()
    title = str(payload.get("projectTitle") or "[add project title]").strip()
    summary = _as_sentence(str(payload.get("projectSummary") or "[add project summary]"))
    project_notes = str(payload.get("projectNotes") or "").strip()[:1800]
    grant = _funding_record_text(payload.get("selectedGrant"))
    match = str(payload.get("matchCapacity") or "[add match, staff, and partner capacity facts]").strip()
    source = str(payload.get("sourceNotes") or "[add the official source link and current funding details]").strip()
    profile = format_public_profile(public_profile)
    verified_excerpts = [item for item in (excerpts or []) if item]
    evidence_block = ""
    if verified_excerpts:
        evidence_block = (
            "\n\nExact excerpts selected from the supplied material (the underlying claims still require human review):\n\n"
            + "\n".join(f"- \"{item}\"" for item in verified_excerpts)
        )
    notes_block = (
        f"\n\nProject notes supplied by the community:\n\n{project_notes}"
        if project_notes
        else "\n\n[add local fact] Add confirmed project tasks, locations, partners, and expected results."
    )
    return f"""# {title}

## Fit Summary

{community}, {state}, is considering the {title} project. The community describes the project as follows: {summary}

The funding record supplied below may be worth screening for this project. [check official source] Confirm that the applicant, location, proposed work, costs, schedule, and attachments meet the current rules.

{grant}

## Project Need

The community has identified the following need: {summary}

Use the final application to explain the size and effect of this need with checked local evidence. [add local fact]

## Community Context

{profile}

## Proposed Work

The current concept is based on the project summary and the community-supplied notes below.{notes_block}{evidence_block}

Before submission, turn this concept into a confirmed scope with clear tasks, locations, responsible parties, approvals, deliverables, and measures of success.

## Community Benefit

If completed as described, {title} is intended to help {community} advance the purpose stated in the project summary. The final application should identify who would benefit, explain how they would benefit, and support those statements with local plans, records, or partner documentation. [add local fact]

## Work Plan

1. Confirm the project scope, location, applicant, and responsible staff.
2. Check the funding program's current eligibility and application requirements.
3. Define the tasks, approvals, partners, deliverables, and measures that apply to this project.
4. Build a supported budget, schedule, and match plan.
5. Complete the application and establish a practical method for tracking results.

## Budget and Match Notes

{match}

[check official source] Confirm allowed costs, award limits, match rules, and required budget documentation before finalizing the budget.

## Source and Eligibility Checks

Community notes about the official source:

{source}

- [check official source] Confirm eligible applicants, locations, activities, and costs.
- [check official source] Confirm the current deadline, award range, match, and required attachments.

## Missing Details

- [add local fact] Applicant legal name and confirmed project location.
- [add local fact] Checked evidence showing the need and people served.
- [add local fact] Confirmed scope, schedule, staff, partners, and expected results.
- [add local fact] Total budget and committed match.
- [check official source] Current funding rules and application instructions.
"""


_NUMBER_WORDS = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
    "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10", "eleven": "11",
    "twelve": "12", "thirteen": "13", "fourteen": "14", "fifteen": "15", "sixteen": "16",
    "seventeen": "17", "eighteen": "18", "nineteen": "19", "twenty": "20",
}


def _number_tokens(text: str) -> set[str]:
    tokens = set()
    for raw in re.findall(r"(?<![A-Za-z0-9])[$]?(\d[\d,]*(?:\.\d+)?)%?", text or ""):
        normalized = raw.replace(",", "").lstrip("0") or "0"
        tokens.add(normalized)
    lowered = (text or "").lower()
    for word, number in _NUMBER_WORDS.items():
        if re.search(rf"\b{word}\b", lowered):
            tokens.add(number)
    return tokens


def _word_tokens(text: str) -> set[str]:
    return {token.lower() for token in re.findall(r"[A-Za-z][A-Za-z'-]{2,}", text or "")}


def grounding_issues(
    draft: str,
    payload: dict[str, Any],
    public_profile: dict[str, str],
    excerpts: list[str] | None = None,
) -> list[str]:
    expected = deterministic_scaffold(payload, public_profile, excerpts)
    if _normalized_text(draft) == _normalized_text(expected):
        return []
    return ["draft differs from the deterministic evidence scaffold"]


DRAFT_FIELD_LIMITS = {
    "community": 200,
    "state": 100,
    "projectTitle": 300,
    "projectSummary": 5000,
    "selectedGrant": 20000,
    "matchCapacity": 10000,
    "sourceNotes": 10000,
    "projectNotes": 100000,
}


def validate_draft_context(payload: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ValueError("The draft request must be a JSON object.")
    for field, limit in DRAFT_FIELD_LIMITS.items():
        value = str(payload.get(field) or "")
        if len(value) > limit:
            raise ValueError(f"{field} is too long. Keep it under {limit:,} characters.")
    missing = [
        label for field, label in (
            ("community", "community"),
            ("state", "state or territory"),
            ("projectTitle", "project title"),
        ) if not str(payload.get(field) or "").strip()
    ]
    if missing:
        raise ValueError("Add the " + ", ".join(missing) + " before creating a draft.")
    if not any(str(payload.get(field) or "").strip() for field in ("projectSummary", "projectNotes", "selectedGrant")):
        raise ValueError("Add a project summary, imported project notes, or funding details before creating a draft.")


def validate_supplied_profile(value: Any) -> dict[str, str]:
    if value in (None, {}):
        return {}
    raw = _plain_object(value, "publicProfile")
    unexpected = set(raw) - set(HANDOFF_PROFILE_FIELD_LIMITS)
    if unexpected:
        raise ValueError("publicProfile contains unsupported fields: " + ", ".join(sorted(unexpected)))
    profile: dict[str, str] = {}
    for key, item in raw.items():
        if type(item) not in {str, int, float, bool}:
            raise ValueError(f"publicProfile.{key} must be text, a number, or true/false.")
        profile[key] = _bounded_handoff_string(str(item), f"publicProfile.{key}", HANDOFF_PROFILE_FIELD_LIMITS[key])
    if profile.get("source_url"):
        profile["source_url"] = _validated_http_url(profile["source_url"], "publicProfile.source_url")
    return profile


def build_draft(payload: dict[str, Any]) -> dict[str, Any]:
    validate_draft_context(payload)
    supplied_profile = validate_supplied_profile(payload.get("publicProfile"))
    if supplied_profile:
        profile_lookup = {"profile": supplied_profile, "message": "Community facts imported from the Community Explorer plan.", "status": "imported"}
    elif payload.get("usePublicData"):
        profile_lookup = lookup_community_profile(
            str(payload.get("community") or ""),
            str(payload.get("state") or ""),
            str(payload.get("censusApiKey") or ""),
        )
    else:
        profile_lookup = {"profile": {}, "message": "Community lookup was turned off.", "status": "skipped"}
    public_profile = profile_lookup["profile"]
    provider = str(payload.get("provider") or "local").lower()
    if provider not in {"local", "fallback"}:
        provider = "local"
    local_knowledge = load_local_knowledge()
    model = DEFAULT_MODEL
    warnings: list[str] = []
    excerpts: list[str] = []
    if provider == "local":
        try:
            excerpts = select_evidence_excerpts(payload, public_profile, local_knowledge, model)
        except Exception:
            warnings.append(
                "The local Gemma evidence review could not finish. "
                "RERC-e still made a structured outline from the supplied facts."
            )
    draft = deterministic_scaffold(payload, public_profile, excerpts)
    issues = grounding_issues(draft, payload, public_profile, excerpts)
    if issues:
        excerpts = []
        draft = deterministic_scaffold(payload, public_profile)
        warnings.append("RERC-e removed an unverified evidence selection.")
    safety_notice = (
        f"Gemma selected {len(excerpts)} exact supplied excerpt"
        f"{'s' if len(excerpts) != 1 else ''}; RERC-e checked that they were copied exactly and placed them in a fixed outline. Review the underlying claims."
        if excerpts
        else "RERC-e used a fixed evidence-based outline. Add and verify the marked details before submission."
    )
    return {
        "draft": draft,
        "provider": provider,
        "model": model,
        "publicProfile": public_profile,
        "profileMessage": profile_lookup["message"],
        "profileStatus": profile_lookup["status"],
        "localKnowledgeChars": len(local_knowledge),
        "warnings": warnings,
        "safetyNotice": safety_notice,
        "evidenceExcerpts": excerpts,
        "rawModelProseExposed": False,
        "generatedAt": int(time.time()),
    }

XML_FORBIDDEN_CONTROLS = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")


def _xml_text(value: Any) -> str:
    return XML_FORBIDDEN_CONTROLS.sub("", str(value or ""))


def _paragraph_xml(text: str, style: str | None = None) -> str:
    properties = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    safe = escape(_xml_text(text))
    return f'<w:p>{properties}<w:r><w:t xml:space="preserve">{safe}</w:t></w:r></w:p>'


def build_docx(draft: str, title: str = "RERC-e Draft") -> bytes:
    paragraphs: list[str] = []
    for raw_line in (draft or "").replace("\r\n", "\n").split("\n"):
        line = raw_line.strip()
        if not line:
            paragraphs.append("<w:p/>")
        elif line.startswith("### "):
            paragraphs.append(_paragraph_xml(line[4:], "Heading3"))
        elif line.startswith("## "):
            paragraphs.append(_paragraph_xml(line[3:], "Heading2"))
        elif line.startswith("# "):
            paragraphs.append(_paragraph_xml(line[2:], "Title"))
        elif re.match(r"^[-*]\s+", line):
            paragraphs.append(_paragraph_xml("- " + re.sub(r"^[-*]\s+", "", line)))
        else:
            paragraphs.append(_paragraph_xml(line))
    document_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>{''.join(paragraphs)}<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1080" w:right="1080" w:bottom="1080" w:left="1080"/></w:sectPr></w:body></w:document>'''
    styles_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:rPr><w:sz w:val="22"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:rPr><w:b/><w:color w:val="00573F"/><w:sz w:val="34"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:rPr><w:b/><w:color w:val="173F35"/><w:sz w:val="28"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/><w:basedOn w:val="Normal"/><w:rPr><w:b/><w:sz w:val="24"/></w:rPr></w:style></w:styles>'''
    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/><Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/><Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/></Types>'''
    root_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/></Relationships>'''
    document_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>'''
    core_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>{escape(_xml_text(title))}</dc:title><dc:creator>RERC-e</dc:creator></cp:coreProperties>'''
    app_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"><Application>RERC-e</Application></Properties>'''
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as package:
        package.writestr("[Content_Types].xml", content_types)
        package.writestr("_rels/.rels", root_rels)
        package.writestr("word/document.xml", document_xml)
        package.writestr("word/styles.xml", styles_xml)
        package.writestr("word/_rels/document.xml.rels", document_rels)
        package.writestr("docProps/core.xml", core_xml)
        package.writestr("docProps/app.xml", app_xml)
    return output.getvalue()


HTML_PAGE = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>RERC-e Local Grant-Writing Guide</title>
  <link rel="icon" type="image/jpeg" href="/assets/rerc-e-eagle.jpg">
  <style>
    :root { --green:#00573f; --forest:#173f35; --leaf:#3e7c59; --river:#1b6a8f; --sky:#dceef5; --sun:#f2c14e; --ink:#20312b; --muted:#5d6b66; --line:#d8e0dc; --paper:#fff; --mist:#f3f7f4; --danger:#8b1e1e; }
    * { box-sizing:border-box; }
    body { margin:0; color:var(--ink); background:var(--mist); font-family:Arial,Helvetica,sans-serif; line-height:1.5; letter-spacing:0; }
    a { color:var(--river); }
    header { padding:24px max(20px,calc((100vw - 1280px)/2)); color:#fff; background:var(--green); border-bottom:5px solid var(--sun); }
    header .brand { display:flex; justify-content:space-between; gap:20px; align-items:center; }
    header .welcome { display:grid; grid-template-columns:minmax(0,1fr) 120px; gap:24px; align-items:center; }
    header .mascot-stage { position:relative; width:120px; height:168px; justify-self:end; transform-origin:50% 90%; animation:rercie-bob 4s ease-in-out infinite; }
    header .mascot { display:block; width:100%; height:100%; object-fit:contain; border:4px solid rgba(255,255,255,.82); border-radius:6px; background:#fff; }
    @keyframes rercie-bob { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-4px)} }
    header h1 { margin:12px 0 6px; font-size:2.25rem; line-height:1.05; }
    header p { max-width:760px; margin:0; color:#e4f1eb; }
    header a { color:#fff; font-weight:700; }
    .privacy { padding:10px max(20px,calc((100vw - 1280px)/2)); color:var(--forest); background:var(--sky); font-size:1rem; }
    .notice { padding:10px max(20px,calc((100vw - 1280px)/2)); color:var(--ink); background:#fff8df; border-bottom:1px solid #e6cf82; font-size:1rem; }
    main { display:grid; grid-template-columns:minmax(300px,430px) minmax(0,1fr); gap:16px; width:min(1320px,100%); margin:0 auto; padding:16px; }
    .panel { padding:18px; border:1px solid var(--line); background:var(--paper); }
    h2 { margin:0 0 8px; font-size:1.12rem; }
    .section-note { margin:0 0 12px; color:var(--muted); font-size:1rem; }
    label { display:block; margin:12px 0 5px; color:var(--forest); font-size:1rem; font-weight:700; }
    input, select, textarea { width:100%; min-height:42px; padding:9px 10px; border:1px solid #aebdb5; border-radius:4px; color:var(--ink); background:#fff; font:inherit; letter-spacing:0; }
    textarea { min-height:96px; resize:vertical; }
    .small { min-height:72px; }
    .check { display:flex; gap:8px; align-items:flex-start; font-weight:400; }
    .check input { width:auto; min-height:0; margin-top:4px; }
    .actions { display:flex; flex-wrap:wrap; gap:9px; margin-top:14px; }
    button { min-height:43px; padding:0 14px; border:2px solid var(--green); border-radius:5px; color:#fff; background:var(--green); font:inherit; font-weight:800; cursor:pointer; }
    button.secondary { border-color:var(--sun); color:#17251f; background:var(--sun); }
    button.quiet { color:var(--green); background:#fff; }
    button:disabled { cursor:wait; opacity:.7; }
    .engine { display:grid; grid-template-columns:minmax(220px,1fr) auto; gap:12px; align-items:end; padding:12px; border-left:5px solid var(--leaf); background:var(--mist); }
    .engine label { margin-top:0; }
    .runtime { align-self:center; padding:7px 10px; border-radius:4px; color:var(--forest); background:#e1eee5; font-size:1rem; font-weight:700; }
    .runtime.offline { color:var(--danger); background:#fdeaea; }
    .advanced { display:none; margin-top:10px; padding:12px; border:1px solid var(--line); background:#fafcfb; }
    .advanced.visible { display:block; }
    .status { margin:12px 0; color:var(--muted); font-size:1rem; }
    .status.warning { color:var(--danger); }
    .lookup-help { margin-top:10px; padding:10px 12px; border:1px solid var(--line); background:#fafcfb; }
    .lookup-help summary { color:var(--forest); font-weight:800; cursor:pointer; }
    .funding-summary { margin:8px 0; padding:10px 12px; border-left:4px solid var(--leaf); background:var(--mist); color:var(--ink); font-size:.9rem; overflow-wrap:anywhere; }
    .funding-summary strong { display:block; margin-bottom:3px; }
    .funding-summary span { display:block; }
    .funding-summary a { display:inline-block; margin-top:5px; color:var(--green); font-weight:700; }
    .funding-details { margin-top:10px; padding:10px 12px; border:1px solid var(--line); background:#fafcfb; }
    .funding-details summary { color:var(--forest); font-weight:800; cursor:pointer; }
    .funding-details label { margin-top:9px; }
    #grantSearchStatus { margin:5px 0; font-size:.85rem; }
    .community-profile { margin-top:10px; padding:12px; border-left:5px solid var(--river); background:var(--sky); }
    .community-profile strong { display:block; margin-bottom:4px; }
    .community-profile ul { margin:6px 0; padding-left:20px; }
    .plan-import { margin-bottom:18px; padding:12px; border-left:5px solid var(--sun); background:#fff8df; }
    .plan-import label { margin-top:0; }
    .plan-import .status { margin-bottom:0; }
    .working { margin:12px 0; padding:12px; border:1px solid #b8d6c5; background:#eef7f1; }
    .working-row { display:flex; justify-content:space-between; gap:12px; color:var(--forest); font-weight:800; }
    .working progress { display:block; width:100%; height:14px; margin-top:8px; accent-color:var(--green); }
    .output { min-height:570px; padding:18px; border:1px solid var(--line); white-space:pre-wrap; background:#fff; font-family:Consolas,"Courier New",monospace; font-size:1rem; overflow-wrap:anywhere; }
    @media (max-width:900px) { main { grid-template-columns:1fr; } .output { min-height:420px; } }
    @media (prefers-reduced-motion:reduce) { header .mascot-stage { animation:none !important; } }
    @media (max-width:560px) { header .brand,.engine { grid-template-columns:1fr; display:grid; } header .welcome { grid-template-columns:minmax(0,1fr) 88px; gap:12px; } header .mascot-stage { width:88px; height:124px; } main { padding:10px; } .panel { padding:14px; } .actions button { flex:1 1 145px; } }
    /* RERC site's forest, river and gold palette, with one task in view. */
    body { background:#edf3ef; font-family:"Segoe UI",Arial,sans-serif; }
    header { padding:22px max(20px,calc((100vw - 1080px)/2)) 28px; background:linear-gradient(130deg,#173f35,#00573f 70%); border-bottom:4px solid var(--sun); }
    header .brand { font-size:.88rem; letter-spacing:.02em; }
    header .brand a { font-size:.88rem; }
    header .welcome { grid-template-columns:minmax(0,1fr) 240px; }
    header h1 { margin-top:22px; font-size:clamp(2rem,4vw,3rem); letter-spacing:-.035em; }
    header p { max-width:620px; font-size:1.08rem; }
    header .mascot-stage { width:240px; height:135px; }
    header .mascot { object-fit:cover; border:3px solid rgba(255,255,255,.85); border-radius:12px; }
    .assurance { width:min(1080px,calc(100% - 32px)); margin:14px auto 0; padding:9px 14px; border:1px solid #d3e2d8; border-radius:10px; background:#fff; font-size:.88rem; }
    .assurance summary { color:var(--forest); font-weight:800; cursor:pointer; }
    .assurance .privacy,.assurance .notice { margin-top:10px; padding:8px 10px; border-radius:8px; font-size:.88rem; }
    .journey { display:flex; gap:10px; width:min(1080px,100%); margin:20px auto 0; padding:0 16px; }
    .journey button { flex:1; min-height:62px; padding:9px 15px; border:1px solid #cbd9d0; border-radius:12px; color:var(--forest); background:#fff; font-size:.95rem; font-weight:700; text-align:left; box-shadow:0 3px 12px rgba(23,63,53,.05); }
    .journey button[aria-current="step"] { color:#fff; background:var(--forest); border-color:var(--forest); }
    .journey .step-number { display:inline-grid; place-items:center; width:28px; height:28px; margin-right:8px; border-radius:50%; color:var(--forest); background:var(--sun); }
    .global-status { width:min(1048px,calc(100% - 32px)); margin:10px auto 0; padding:8px 12px; border-radius:8px; background:#e1eee5; font-size:.88rem; }
    .global-status.warning { background:#fdeaea; }
    main { display:block; width:min(1080px,100%); padding:16px 16px 48px; }
    .step-panel[hidden] { display:none !important; }
    .panel { padding:clamp(18px,3vw,34px); border:1px solid #d7e3da; border-radius:18px; box-shadow:0 12px 34px rgba(23,63,53,.07); }
    h2 { font-size:clamp(1.4rem,2.5vw,1.85rem); letter-spacing:-.025em; }
    .step-eyebrow { margin:0 0 6px; color:var(--river); font-size:.78rem; font-weight:800; letter-spacing:.11em; text-transform:uppercase; }
    .step-intro { max-width:720px; margin:0 0 20px; color:var(--muted); }
    .field-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); column-gap:18px; }
    .field-grid .full { grid-column:1/-1; }
    label { font-size:.94rem; }
    input,select,textarea { min-height:46px; padding:11px 12px; border-radius:9px; }
    textarea { min-height:105px; }
    input:focus-visible,select:focus-visible,textarea:focus-visible,button:focus-visible,summary:focus-visible { outline:3px solid var(--sun); outline-offset:2px; }
    .plan-import { padding:16px 18px; border:1px solid #ead590; border-radius:12px; background:#fffaf0; }
    .plan-import h2 { font-size:1.05rem; }
    .plan-import input { max-width:600px; }
    .actions { margin-top:20px; }
    button { min-height:48px; padding:8px 18px; border-radius:10px; }
    .actions .next { margin-left:auto; }
    .funding-summary,.community-profile,.engine,.working,.funding-details,.lookup-help { border-radius:10px; }
    .funding-summary { padding:15px; }
    .output { min-height:360px; margin-top:18px; padding:24px; border-radius:12px; line-height:1.6; font-family:"Segoe UI",Arial,sans-serif; }
    .draft-exports { margin-top:10px; }
    .draft-exports button:disabled { cursor:not-allowed; opacity:.45; }
    @media (max-width:600px) { header { padding-bottom:18px; } header h1 { margin-top:12px; } header p { font-size:.94rem; } .journey { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:6px; } .journey button { min-height:69px; padding:7px 8px; font-size:.78rem; text-align:center; line-height:1.2; } .journey .step-number { display:grid; width:23px; height:23px; margin:0 auto 3px; } .field-grid { grid-template-columns:1fr; } .actions .next { margin-left:0; } .panel { padding:18px; } header .welcome { grid-template-columns:minmax(0,1fr) 116px; } header .mascot-stage { width:116px; height:72px; } }
  </style>
</head>
<body>
  <header>
    <div class="brand"><strong>Recreation Economy <em>for</em> Rural Communities</strong><a href="https://henkelpress.github.io/rerc-grant-finder/" target="_blank" rel="noopener">Open the public explorer</a></div>
    <div class="welcome"><div><h1>Meet RERC-e</h1><p>Use a funding match and your project notes to create a first draft. Check every fact before you apply.</p></div><div class="mascot-stage"><img class="mascot" src="/assets/rerc-e-eagle.jpg" alt="RERC-e, a bald eagle field guide holding a notebook"></div></div>

  </header>
  <details class="assurance"><summary>Privacy and limits</summary>
    <div class="privacy"><strong>Private by default:</strong> Gemma writing and local reference files stay on this computer. Census and catalog lookups use public websites.</div>
    <div class="notice"><strong>Keep in mind:</strong> RERC-e is a community-built grant-writing guide. It is not an EPA grant program. It does not decide who can apply or submit an application for you.</div>
  </details>
  <nav class="journey" aria-label="RERC-e steps">
    <button type="button" data-step="project" aria-current="step"><span class="step-number">1</span> Project</button>
    <button type="button" data-step="funding"><span class="step-number">2</span> Funding and notes</button>
    <button type="button" data-step="draft"><span class="step-number">3</span> Draft and export</button>
  </nav>
  <p id="status" class="status global-status" aria-live="polite">Ready.</p>
  <main>
    <section class="panel step-panel" id="projectStep" data-panel="project" aria-labelledby="projectStepTitle">
      <p class="step-eyebrow">Step 1 of 3</p>
      <h2 id="projectStepTitle">Tell RERC-e about your project</h2>
      <p class="step-intro">Open a plan from the Community Explorer or enter the basic facts here. You can change them at any time.</p>
      <div class="plan-import">
        <h2>Have a Community Explorer plan?</h2>
        <label for="planInput">Open Community Explorer plan</label>
        <input id="planInput" type="file" accept=".rerc-e,.rercie,.json,application/json">
        <p id="planImportStatus" class="status" aria-live="polite">Choose a RERC-e plan file exported by the public explorer.</p>
      </div>
      <p class="section-note">Start with the facts you know. The draft will mark anything that is missing.</p>
      <div class="field-grid">
        <div><label for="community">Community</label><input id="community" required aria-required="true" maxlength="200" placeholder="Example: Taos"></div>
        <div><label for="state">State or territory</label><select id="state" required aria-required="true"></select></div>
        <div class="full"><label for="projectTitle">Project title</label><input id="projectTitle" required aria-required="true" maxlength="300" placeholder="Example: Downtown trail connection"></div>
      </div>
      <label for="projectSummary">What do you want to do?</label><textarea id="projectSummary" class="small" maxlength="5000"></textarea>
      <div class="actions"><button id="nextFunding" class="next" type="button">Continue to funding and notes</button></div>
    </section>
    <section class="panel step-panel" id="fundingStep" data-panel="funding" aria-labelledby="fundingStepTitle" hidden>
      <p class="step-eyebrow">Step 2 of 3</p>
      <h2 id="fundingStepTitle">Review funding and add context</h2>
      <p class="step-intro">Choose a match, then add what your community can contribute and what you still need to verify.</p>
      <label for="grantSearch">Search funding list</label><input id="grantSearch" type="search" maxlength="100" placeholder="Program or organization">
      <label for="grantSelect">Funding match</label><select id="grantSelect"><option value="">Load the public list</option></select>
      <p id="grantSearchStatus" class="section-note" aria-live="polite">Search after loading the public funding list.</p>
      <div id="fundingSummary" class="funding-summary" aria-live="polite">Choose a funding match or paste checked details.</div>
      <div class="actions"><button id="loadGrants" class="quiet" type="button">Load funding list</button></div>
      <details id="fundingDetailsPanel" class="funding-details"><summary>Review or paste funding details</summary><label for="selectedGrant">Funding details</label><textarea id="selectedGrant" placeholder="Choose a funding match above, or paste the current details here."></textarea></details>
      <label for="matchCapacity">Match, staff, and partners</label><textarea id="matchCapacity" class="small"></textarea>
      <label for="sourceNotes">Facts to check on the official page</label><textarea id="sourceNotes" class="small" placeholder="Deadline, eligibility, match, award size, and source link"></textarea>
      <label for="fileInput">Add text files</label><input id="fileInput" type="file" multiple accept=".txt,.md,.csv,.json">
      <label for="projectNotes">Notes and file text</label><textarea id="projectNotes" maxlength="100000"></textarea>
      <label class="check" for="usePublicData"><input id="usePublicData" type="checkbox" checked><span>Look up prebuilt community facts and local Census fallback if needed.</span></label>
      <div class="actions"><button id="lookupCommunity" class="quiet" type="button">Look up community facts</button></div>
      <details class="lookup-help"><summary>Community lookup help</summary><p class="section-note">RERC-e first checks the public prebuilt <code>community_profiles.js</code> dataset for an exact community + state/territory match. Use a free Census API key only when that match is not found.</p><label for="censusApiKey">Census API key</label><input id="censusApiKey" type="password" autocomplete="off" placeholder="Optional Census API key for fallback lookup"><p class="section-note"><a href="https://api.census.gov/data/key_signup.html" target="_blank" rel="noopener">Get a free Census API key</a></p></details>
      <div id="communityProfile" class="community-profile" hidden aria-live="polite"></div>
      <div class="actions"><button class="quiet" type="button" data-go="project">Back to project</button><button class="next" type="button" data-go="draft">Continue to draft</button></div>
    </section>
    <section class="panel step-panel" id="draftStep" data-panel="draft" aria-labelledby="draftStepTitle" hidden>
      <p class="step-eyebrow">Step 3 of 3</p>
      <h2 id="draftStepTitle">Create and review your first draft</h2>
      <p class="step-intro">RERC-e writes a starting point. Review every statement and check current rules on official funding pages before using it.</p>
      <div class="engine">
        <div><label for="provider">Writing method</label><select id="provider"><option value="local">Local Gemma writer</option><option value="fallback">Structured outline only</option></select></div>
        <span id="runtime" class="runtime">Checking local writer...</span>
      </div>
      <div class="actions">
        <button id="draftButton" class="secondary" type="button">Create first draft</button>
      </div>
      <div class="actions draft-exports" aria-label="Draft exports">
        <button id="downloadDocx" class="quiet" type="button">Export Word</button>
        <button id="downloadMd" class="quiet" type="button">Export Markdown</button>
        <button id="copyDraft" class="quiet" type="button">Copy</button>
      </div>
      <div id="working" class="working" hidden aria-live="polite">
        <div class="working-row"><span id="workingLabel">RERC-e is working...</span><span id="workingTime" aria-hidden="true">0 seconds</span></div>
        <progress aria-label="RERC-e is generating the draft"></progress>
      </div>
      <p id="saveStatus" class="section-note" aria-live="polite">Work in this tab is saved locally for refresh recovery.</p>
      <div id="output" class="output" role="region" aria-label="Draft output" tabindex="0">Your first draft will appear here.</div>
      <div class="actions"><button class="quiet" type="button" data-go="funding">Back to funding and notes</button></div>
    </section>
  </main>
  <script>
    const states = __STATE_OPTIONS__;
    const stateSelect = document.getElementById("state");
    states.forEach((state) => { const option=document.createElement("option"); option.value=state; option.textContent=state||"Choose a state or territory"; stateSelect.appendChild(option); });
    const MAX_PLAN_BYTES=256*1024;
    let lastDraft=""; let activePublicProfile={};
    const status=document.getElementById("status"); const output=document.getElementById("output");
    let currentStep="project";
    function showStep(step,focusHeading=false){
      if(!["project","funding","draft"].includes(step))return;
      currentStep=step;
      document.querySelectorAll(".step-panel").forEach((panel)=>{panel.hidden=panel.dataset.panel!==step;});
      document.querySelectorAll(".journey button").forEach((button)=>{
        if(button.dataset.step===step)button.setAttribute("aria-current","step");
        else button.removeAttribute("aria-current");
      });
      if(step==="funding"&&grantCatalog.length&&status.textContent==="Ready.")setStatus(`${grantCatalog.length} funding options available. Choose a match or add checked details.`);
      if(focusHeading){const heading=document.querySelector(`[data-panel="${step}"] h2`);heading.tabIndex=-1;heading.focus();window.scrollTo(0,0);}
      scheduleProjectSave();
    }
    document.querySelectorAll(".journey button").forEach((button)=>button.addEventListener("click",()=>showStep(button.dataset.step,true)));
    document.querySelectorAll("[data-go]").forEach((button)=>button.addEventListener("click",()=>showStep(button.dataset.go,true)));
    document.getElementById("nextFunding").addEventListener("click",()=>showStep("funding",true));
    const TOKEN_STORAGE_KEY="rercie.tabSessionToken.v1";
    const launchToken=new URLSearchParams(location.hash.slice(1)).get("token")||"";
    let sessionToken=launchToken;
    try{ if(launchToken)sessionStorage.setItem(TOKEN_STORAGE_KEY,launchToken); else sessionToken=sessionStorage.getItem(TOKEN_STORAGE_KEY)||""; }catch{}
    if(location.hash)history.replaceState(null,"",location.pathname+location.search);
    async function apiFetch(url,options={}){ if(!sessionToken)throw new Error("Open RERC-e from its Start Menu shortcut to connect this tab."); const headers=new Headers(options.headers||{}); headers.set("X-RERCie-Token",sessionToken); const response=await fetch(url,{...options,headers}); if(response.status===403){sessionToken=""; try{sessionStorage.removeItem(TOKEN_STORAGE_KEY);}catch{} throw new Error("The local session expired. Reopen RERC-e from its Start Menu shortcut. Your work in this tab is still saved.");} return response; }
    function setStatus(message,warning=false){ status.textContent=message; status.className=warning?"status global-status warning":"status global-status"; }
    const PROJECT_STORAGE_KEY="rercie.tabProject.v1";
    const PROJECT_FIELDS=["community","state","projectTitle","projectSummary","selectedGrant","matchCapacity","sourceNotes","projectNotes","provider","usePublicData"];
    let inputVersion=0, draftInputVersion=-1, saveTimer=0;
    function draftIsStale(){return Boolean(lastDraft)&&inputVersion!==draftInputVersion;}
    function updateSaveStatus(){const note=document.getElementById("saveStatus"); note.textContent=draftIsStale()?"Inputs changed since this draft. Create a new draft before exporting or copying.":"Work in this tab is saved locally for refresh recovery."; note.className=draftIsStale()?"status warning":"section-note";}
    function saveProjectState(){if(saveTimer){clearTimeout(saveTimer);saveTimer=0;} const fields={}; PROJECT_FIELDS.forEach((id)=>{const control=document.getElementById(id);fields[id]=control.type==="checkbox"?control.checked:control.value;}); try{sessionStorage.setItem(PROJECT_STORAGE_KEY,JSON.stringify({schema:1,fields,lastDraft,publicProfile:activePublicProfile,inputVersion,draftInputVersion,step:currentStep}));updateSaveStatus();}catch{const note=document.getElementById("saveStatus");note.textContent="This app could not save the project for refresh recovery. Export your draft before closing.";note.className="status warning";} }
    function scheduleProjectSave(){if(saveTimer)clearTimeout(saveTimer);saveTimer=setTimeout(saveProjectState,250);}
    function markInputsChanged(){inputVersion++;if(status.classList.contains("warning")&&/^Add (the |a project)/.test(status.textContent))setStatus("Project details updated. Continue when you are ready.");updateSaveStatus();scheduleProjectSave();}
    function restoreProjectState(){try{const saved=JSON.parse(sessionStorage.getItem(PROJECT_STORAGE_KEY)||"null");if(!saved||saved.schema!==1||!saved.fields||typeof saved.fields!=="object")return;PROJECT_FIELDS.forEach((id)=>{const control=document.getElementById(id);const value=saved.fields[id];if(control.type==="checkbox")control.checked=Boolean(value);else if(typeof value==="string")control.value=value.slice(0,Number(control.maxLength)>0?control.maxLength:100000);});lastDraft=typeof saved.lastDraft==="string"?saved.lastDraft.slice(0,150000):"";activePublicProfile=saved.publicProfile&&typeof saved.publicProfile==="object"&&!Array.isArray(saved.publicProfile)?saved.publicProfile:{};inputVersion=Number.isSafeInteger(saved.inputVersion)?saved.inputVersion:0;draftInputVersion=Number.isSafeInteger(saved.draftInputVersion)?saved.draftInputVersion:-1;if(lastDraft)output.textContent=lastDraft;if(Object.keys(activePublicProfile).length)renderProfile(activePublicProfile,"Community facts restored from this app.","found");renderFundingSummary();showStep(saved.step||"project");updateSaveStatus();}catch{} }
    function canUseDraft(){if(!lastDraft){setStatus("Create a draft first.",true);return false;}if(draftIsStale()){setStatus("Inputs changed since this draft. Create a new draft before exporting or copying.",true);return false;}return true;}
    let workingTimer=0;
    function startWorking(){ const box=document.getElementById("working"); const label=document.getElementById("workingLabel"); const clock=document.getElementById("workingTime"); const provider=document.getElementById("provider").value; const started=Date.now(); box.hidden=false; label.textContent=provider==="local"?"RERC-e is reviewing your notes with local Gemma...":"RERC-e is building a structured outline..."; const tick=()=>{ const elapsed=Math.floor((Date.now()-started)/1000); clock.textContent=elapsed+" seconds"; }; tick(); workingTimer=window.setInterval(tick,1000); }
    function stopWorking(){ document.getElementById("working").hidden=true; if(workingTimer){window.clearInterval(workingTimer);workingTimer=0;} }
    function formatProfileValue(key,value){ if((key==="population"||key==="median_household_income")&&/^\d+$/.test(String(value))){ const number=Number(value).toLocaleString(); return key==="median_household_income"?"$"+number:number; } return String(value); }
    function renderProfile(profile,message,lookupStatus){ activePublicProfile=profile&&typeof profile==="object"?profile:{}; const box=document.getElementById("communityProfile"); box.replaceChildren(); box.hidden=false; const heading=document.createElement("strong"); heading.textContent=profile&&profile.place?profile.place:"Community facts"; box.appendChild(heading); if(!profile||!Object.keys(profile).length){ const note=document.createElement("span"); note.textContent=message||"No community facts were found."; box.appendChild(note); if(lookupStatus==="key_required"){document.querySelector(".lookup-help").open=true;} return; } const labels={population:"Population",median_age:"Median age",median_household_income:"Median household income",poverty_rate_percent:"People below the poverty line",geography_type:"Geography used"}; const list=document.createElement("ul"); Object.keys(labels).forEach((key)=>{ if(profile[key]===undefined||profile[key]===null||String(profile[key]).trim()==="")return; const item=document.createElement("li"); let value=formatProfileValue(key,profile[key]); if(key==="median_age")value+=" years"; if(key==="poverty_rate_percent")value+="%"; item.textContent=labels[key]+": "+value; list.appendChild(item); }); box.appendChild(list); const source=document.createElement(profile.source_url?"a":"span"); source.textContent=profile.source||"U.S. Census Bureau"; if(profile.source_url){source.href=profile.source_url;source.target="_blank";source.rel="noopener";} box.appendChild(source); if(profile.coverage_note){ const coverage=document.createElement("p"); coverage.textContent=profile.coverage_note; box.appendChild(coverage); } }
    function applyImportedPlan(data){ document.getElementById("community").value=data.community||""; stateSelect.value=data.state||""; document.getElementById("projectTitle").value=data.projectTitle||""; document.getElementById("projectNotes").value=data.projectNotes||""; document.getElementById("selectedGrant").value=data.selectedFundingDetails||""; lastDraft="";draftInputVersion=-1;output.textContent="Create a first draft from the imported plan."; if(data.profile&&Object.keys(data.profile).length){renderProfile(data.profile,"Community facts imported from the plan.","found");}else{activePublicProfile={};document.getElementById("communityProfile").hidden=true;} renderFundingSummary();markInputsChanged();saveProjectState(); const message=(data.message||"Community Explorer plan opened.")+" Review the imported facts and official funding pages before drafting."; const importStatus=document.getElementById("planImportStatus"); importStatus.textContent=message; importStatus.className="status"; setStatus(message); }
    async function importPlanText(text){ const response=await apiFetch("/api/import-plan",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({packageText:text})}); const data=await response.json(); if(!response.ok)throw new Error(data.error||"The plan could not be opened."); applyImportedPlan(data); }
    async function openPlanFile(file){ if(!file)return; const importStatus=document.getElementById("planImportStatus"); if(!/\.(rerc-e|rercie|json)$/i.test(file.name)){throw new Error("Choose a RERC-e Community Explorer plan file.");} if(file.size<=0||file.size>MAX_PLAN_BYTES){throw new Error("The plan must be a non-empty file no larger than 256 KB.");} importStatus.textContent="Checking the Community Explorer plan..."; const text=await file.text(); if(new TextEncoder().encode(text).length>MAX_PLAN_BYTES)throw new Error("The plan must be no larger than 256 KB."); let parsed; try{parsed=JSON.parse(text);}catch{throw new Error("The plan is not valid JSON.");} if(!parsed||Array.isArray(parsed)||typeof parsed!=="object"||!(["rerc-e-handoff","rercie-handoff"].includes(parsed.schema))||parsed.version!==1){throw new Error("This is not a supported RERC-e Community Explorer plan.");} await importPlanText(text); }
    async function checkStartupPlan(){ if(!sessionToken){setStatus("Open RERC-e from its Start Menu shortcut to connect this tab.",true);return;} try{ const response=await apiFetch("/api/startup-plan"); const data=await response.json(); if(data.status==="none")return; if(!response.ok)throw new Error(data.error||"The plan could not be opened."); applyImportedPlan(data); }catch(error){ const importStatus=document.getElementById("planImportStatus"); importStatus.textContent=error.message.includes("session")?error.message:"The plan passed from Windows could not be opened: "+error.message; importStatus.className="status warning"; setStatus(importStatus.textContent,true); } }
    async function lookupCommunityFacts(){ const button=document.getElementById("lookupCommunity"); button.disabled=true; setStatus("Looking up community facts..."); try{ const body={community:document.getElementById("community").value,state:stateSelect.value,censusApiKey:document.getElementById("censusApiKey").value}; const response=await apiFetch("/api/community-profile",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)}); const data=await response.json(); if(!response.ok)throw new Error(data.error||"Lookup failed."); renderProfile(data.profile,data.message,data.status); markInputsChanged();setStatus(data.message,data.status!=="found"); }catch(error){renderProfile({},"Community facts could not be reached right now.","unavailable");markInputsChanged();setStatus("Community lookup failed: "+error.message,true);}finally{button.disabled=false;} }
    function collectPayload(){ return {community:document.getElementById("community").value,state:stateSelect.value,projectTitle:document.getElementById("projectTitle").value,projectSummary:document.getElementById("projectSummary").value,selectedGrant:document.getElementById("selectedGrant").value,matchCapacity:document.getElementById("matchCapacity").value,sourceNotes:document.getElementById("sourceNotes").value,projectNotes:document.getElementById("projectNotes").value,publicProfile:activePublicProfile,usePublicData:document.getElementById("usePublicData").checked,provider:document.getElementById("provider").value,model:"gemma-3-1b-it-Q4_K_M.gguf",censusApiKey:document.getElementById("censusApiKey").value}; }
    function validateDraftInputs(){ const required=[["community","community"],["state","state or territory"],["projectTitle","project title"]]; for(const [id,label] of required){ const control=document.getElementById(id); if(!control.value.trim()){ setStatus(`Add the ${label} before creating a draft.`,true); showStep("project"); control.focus(); return false; } } const hasContext=["projectSummary","projectNotes","selectedGrant"].some((id)=>document.getElementById(id).value.trim()); if(!hasContext){ setStatus("Add a project summary, imported project notes, or funding details before creating a draft.",true); showStep("project"); document.getElementById("projectSummary").focus(); return false; } return true; }
    let runtimePoll=0;
    async function checkRuntime(){ const badge=document.getElementById("runtime"); try{ const response=await apiFetch("/api/runtime"); const data=await response.json(); badge.textContent=data.ready?"Local model ready":"Local model is starting"; badge.className=data.ready?"runtime":"runtime offline"; if(data.ready&&runtimePoll){clearInterval(runtimePoll);runtimePoll=0;} }catch{ badge.textContent="Could not check local writer"; badge.className="runtime offline"; } }
    let grantCatalog=[];
    function fundingDetailRecord(){const details=document.getElementById("selectedGrant").value.trim();try{return JSON.parse(details);}catch{return null;}}
    function renderFundingSummary(){
      const box=document.getElementById("fundingSummary");box.replaceChildren();
      const details=document.getElementById("selectedGrant").value.trim();
      if(!details){box.textContent="Choose a funding match or paste checked details.";return;}
      const record=fundingDetailRecord();
      const field=(label)=>details.match(new RegExp(`^(?:- )?${label}:\\s*(.+)$`,"m"))?.[1]||"";
      const heading=document.createElement("strong");heading.textContent=record?.title||record?.program||field("Program")||"Using pasted funding details";box.appendChild(heading);
      const organization=record?.organization||record?.agency||field("Organization");
      if(organization){const note=document.createElement("span");note.textContent=organization;box.appendChild(note);}
      const source=record?.url||record?.source_url||field("Official page");
      try{const url=new URL(source);if(["http:","https:"].includes(url.protocol)&&!url.username&&!url.password){const link=document.createElement("a");link.href=url.href;link.target="_blank";link.rel="noopener";link.textContent="Check official program page";box.appendChild(link);}}catch{}
    }
    function renderGrantOptions(){
      const select=document.getElementById("grantSelect");
      const query=document.getElementById("grantSearch").value.trim().toLowerCase();
      const previous=document.getElementById("selectedGrant").value.trim();
      const previousId=fundingDetailRecord()?.item_id||"";
      const matches=grantCatalog.filter((grant)=>[grant.title,grant.program,grant.organization,grant.agency,grant.geography].some((value)=>String(value||"").toLowerCase().includes(query)));
      select.replaceChildren();
      const placeholder=document.createElement("option");placeholder.value="";placeholder.textContent="Choose a funding match";select.appendChild(placeholder);
      const previousRecord=previousId?grantCatalog.find((grant)=>grant.item_id===previousId):null;
      const shown=matches.slice(0,60);
      if(previousRecord&&!shown.includes(previousRecord))shown.unshift(previousRecord);
      let selected="";
      shown.forEach((grant)=>{const option=document.createElement("option");option.value=String(grantCatalog.indexOf(grant));option.textContent=`${grant.title||grant.program||"Untitled"} - ${grant.organization||grant.agency||"Organization not listed"}`;option.dataset.grant=JSON.stringify(grant);select.appendChild(option);if(previousId&&grant.item_id===previousId)selected=option.value;});
      if(selected)select.value=selected;
      else if(previous){const manual=document.createElement("option");manual.value="manual";manual.textContent="Using pasted funding details";select.appendChild(manual);select.value="manual";}
      document.getElementById("grantSearchStatus").textContent=`${matches.length} of ${grantCatalog.length} funding options match. ${Math.min(matches.length,60)} shown; search by program or organization to narrow the list${previousRecord&&!matches.includes(previousRecord)?". Current selection kept above":""}.`;
      renderFundingSummary();
    }
    async function loadGrants(){ const button=document.getElementById("loadGrants"); button.disabled=true; if(currentStep==="funding")setStatus("Loading the public funding list..."); try{ const response=await apiFetch("/api/grants"); const data=await response.json(); if(!response.ok) throw new Error(data.error||"The list could not be loaded."); grantCatalog=Array.isArray(data.grants)?data.grants:[];renderGrantOptions();if(currentStep==="funding")setStatus(`Loaded ${grantCatalog.length} funding options. Updated ${data.updated||"date not listed"}.`); }finally{ button.disabled=false; } }
    document.getElementById("loadGrants").addEventListener("click",()=>loadGrants().catch((error)=>setStatus(`Could not load funding: ${error.message}`,true)));
    document.getElementById("grantSearch").addEventListener("input",renderGrantOptions);
    document.getElementById("grantSelect").addEventListener("change",(event)=>{ if(event.target.value!=="manual")document.getElementById("selectedGrant").value=event.target.selectedOptions[0]?.dataset?.grant||"";renderFundingSummary();markInputsChanged(); });
    document.getElementById("fileInput").addEventListener("change",async(event)=>{ const files=[...event.target.files]; const parts=[]; let total=0; if(files.length>10){setStatus("Add no more than 10 text files at a time.",true);event.target.value="";return;} for(const file of files){ if(file.size>512*1024){ setStatus(`${file.name} is too large. Use a text file under 512 KB.`,true); continue; } total+=file.size; if(total>2*1024*1024){setStatus("The selected files exceed the 2 MB combined limit.",true);break;} parts.push(`\n--- File: ${file.name} ---\n${await file.text()}`); } const notes=document.getElementById("projectNotes"); const combined=`${notes.value}\n${parts.join("\n")}`.trim(); if(combined.length>100000){setStatus("The notes and file text exceed the 100,000-character drafting limit. Use shorter excerpts.",true);return;} notes.value=combined; if(parts.length){markInputsChanged();setStatus(`Read ${parts.length} file(s).`);} });
    document.getElementById("planInput").addEventListener("change",(event)=>{ openPlanFile(event.target.files[0]).catch((error)=>{ const importStatus=document.getElementById("planImportStatus"); importStatus.textContent="Could not open the plan: "+error.message; importStatus.className="status warning"; setStatus(importStatus.textContent,true); }).finally(()=>{event.target.value="";}); });
    document.getElementById("lookupCommunity").addEventListener("click",lookupCommunityFacts);
    document.getElementById("draftButton").addEventListener("click",async()=>{ if(!validateDraftInputs())return; const button=document.getElementById("draftButton"); const versionAtStart=inputVersion; button.disabled=true; startWorking(); setStatus("RERC-e is preparing the draft..."); try{ const response=await apiFetch("/api/draft",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(collectPayload())}); const data=await response.json(); if(!response.ok) throw new Error(data.error||"Draft failed."); lastDraft=data.draft; draftInputVersion=versionAtStart; output.textContent=data.draft; renderProfile(data.publicProfile,data.profileMessage,data.profileStatus); saveProjectState(); const readyMessage=data.localKnowledgeChars?"Draft ready. Local reference files were used.":"Draft ready."; setStatus(data.warnings?.length?data.warnings.join(" "):readyMessage+" "+(data.safetyNotice||"")+" "+(data.profileMessage||""),Boolean(data.warnings?.length)); }catch(error){ setStatus("Draft failed: "+error.message,true); }finally{ stopWorking(); button.disabled=false; } });
    function downloadBlob(blob,filename){ const link=document.createElement("a"); link.href=URL.createObjectURL(blob); link.download=filename; link.click(); setTimeout(()=>URL.revokeObjectURL(link.href),1000); }
    function draftFilename(extension){ const raw=document.getElementById("projectTitle").value||"Project"; const safe=raw.normalize("NFKD").replace(/[^\w -]/g,"").trim().replace(/\s+/g,"_").slice(0,60)||"Project"; const now=new Date(); const date=[now.getFullYear(),String(now.getMonth()+1).padStart(2,"0"),String(now.getDate()).padStart(2,"0")].join("-"); return `RERC-e_${safe}_Draft_${date}.${extension}`; }
    document.getElementById("downloadMd").addEventListener("click",()=>{ if(!canUseDraft())return; downloadBlob(new Blob([lastDraft],{type:"text/markdown"}),draftFilename("md")); });
    document.getElementById("downloadDocx").addEventListener("click",async()=>{ if(!canUseDraft())return; const button=document.getElementById("downloadDocx"); button.disabled=true; setStatus("Building the Word file..."); try{ const response=await apiFetch("/api/export-docx",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({draft:lastDraft,title:document.getElementById("projectTitle").value||"RERC-e Draft"})}); if(!response.ok){ const data=await response.json().catch(()=>({})); throw new Error(data.error||"The Word file could not be created."); } downloadBlob(await response.blob(),draftFilename("docx")); setStatus("Word file ready."); }catch(error){setStatus("Word export failed: "+error.message,true);}finally{button.disabled=false;} });
    document.getElementById("copyDraft").addEventListener("click",async()=>{ if(!canUseDraft())return; try{ if(!navigator.clipboard||!navigator.clipboard.writeText)throw new Error("Clipboard access is unavailable"); await navigator.clipboard.writeText(lastDraft); setStatus("Draft copied."); }catch{ setStatus("Copy is unavailable in this browser. Select the draft text and copy it manually.",true); output.focus(); const selection=window.getSelection(); const range=document.createRange(); range.selectNodeContents(output); selection.removeAllRanges(); selection.addRange(range); } });
    PROJECT_FIELDS.filter((id)=>id!=="selectedGrant").forEach((id)=>{const control=document.getElementById(id);control.addEventListener(control.tagName==="SELECT"||control.type==="checkbox"?"change":"input",markInputsChanged);});
    document.getElementById("selectedGrant").addEventListener("input",()=>{const select=document.getElementById("grantSelect");if(select.value!=="manual"){let manual=[...select.options].find((option)=>option.value==="manual");if(!manual){manual=document.createElement("option");manual.value="manual";manual.textContent="Using pasted funding details";select.appendChild(manual);}select.value="manual";}renderFundingSummary();markInputsChanged();});
    window.addEventListener("pagehide",saveProjectState);
    restoreProjectState();
    if(sessionToken){checkRuntime(); runtimePoll=window.setInterval(checkRuntime,5000); checkStartupPlan(); loadGrants().catch((error)=>setStatus(error.message.includes("session")?error.message:"The public funding list is not available right now. You can paste funding details instead.",true));}
    else setStatus("Open RERC-e from its Start Menu shortcut to connect this tab. Your saved work in this tab is available below.",true);
  </script>
</body>
</html>'''.replace("__STATE_OPTIONS__", json.dumps([""] + list(STATE_FIPS.keys())))


class RERCieHandler(BaseHTTPRequestHandler):
    server_version = f"RERC-e/{APP_VERSION}"

    def log_message(self, format: str, *args: Any) -> None:
        stream = getattr(sys, "stderr", None)
        if stream and hasattr(stream, "write"):
            try:
                stream.write("%s - - [%s] %s\n" % (self.client_address[0], self.log_date_time_string(), format % args))
            except (OSError, ValueError):
                pass

    def _authorize(self, require_token: bool = False) -> bool:
        if self.headers.get("Host", "").lower() != EXPECTED_HOST:
            self.send_json({"error": "Local request rejected."}, status=421)
            return False
        if require_token:
            origin = self.headers.get("Origin", "")
            if origin and origin.lower() != EXPECTED_ORIGIN:
                self.send_json({"error": "Local request rejected."}, status=403)
                return False
            provided = self.headers.get("X-RERCie-Token", "")
            if not SESSION_TOKEN or not secrets.compare_digest(provided, SESSION_TOKEN):
                self.send_json({"error": "Local session not authorized."}, status=403)
                return False
        return True

    def _headers(self, status: int, content_type: str, length: int, disposition: str | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; font-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'")
        if disposition:
            self.send_header("Content-Disposition", disposition)
        self.end_headers()

    def send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self._headers(status, "application/json; charset=utf-8", len(body))
        self.wfile.write(body)

    def send_bytes(self, body: bytes, content_type: str, filename: str) -> None:
        self._headers(200, content_type, len(body), f'attachment; filename="{filename}"')
        self.wfile.write(body)

    def send_text(self, body: str, status: int = 200) -> None:
        encoded = body.encode("utf-8")
        self._headers(status, "text/html; charset=utf-8", len(encoded))
        self.wfile.write(encoded)

    def read_payload(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > MAX_REQUEST_BYTES:
            raise ValueError("The request was empty or too large.")
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("The request must be a JSON object.")
        return payload

    def do_GET(self) -> None:
        require_token = self.path == "/health" or self.path.startswith("/api/")
        if not self._authorize(require_token=require_token):
            return
        if self.path in {"/", "/index.html"}:
            self.send_text(HTML_PAGE)
        elif self.path == "/assets/rerc-e-eagle.jpg":
            asset_path = ASSET_DIR / "rerc-e-eagle.jpg"
            if not asset_path.is_file():
                self.send_json({"error": "Not found"}, status=404)
                return
            body = asset_path.read_bytes()
            self._headers(200, "image/jpeg", len(body))
            self.wfile.write(body)
        elif self.path == "/health":
            self.send_json({"status": "ok", "app": "RERC-e", "version": APP_VERSION})
        elif self.path == "/api/runtime":
            try:
                health = request_json(LOCAL_HEALTH_URL, timeout=3)
                models = request_json(LOCAL_MODELS_URL, timeout=3)
                model_ids = [str(item.get("id") or "") for item in models.get("data", []) if isinstance(item, dict)]
                ready = str(health.get("status", "")).lower() in {"ok", "ready"} and any(DEFAULT_MODEL in model_id for model_id in model_ids)
                self.send_json({"ready": ready})
            except Exception:
                self.send_json({"ready": False})
        elif self.path == "/api/grants":
            try:
                self.send_json(fetch_public_catalog())
            except Exception as exc:
                self.send_json({"error": html.escape(str(exc))}, status=502)
        elif self.path == "/api/startup-plan":
            try:
                imported = consume_startup_handoff()
                self.send_json(imported or {"status": "none"})
            except Exception as exc:
                self.send_json({"error": str(exc)}, status=400)
        else:
            self.send_json({"error": "Not found"}, status=404)

    def do_POST(self) -> None:
        if not self._authorize(require_token=True):
            return
        if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
            self.send_json({"error": "Use application/json for local requests."}, status=415)
            return
        try:
            payload = self.read_payload()
            if self.path == "/api/community-profile":
                self.send_json(lookup_community_profile(
                    str(payload.get("community") or ""),
                    str(payload.get("state") or ""),
                    str(payload.get("censusApiKey") or ""),
                ))
            elif self.path == "/api/draft":
                self.send_json(build_draft(payload))
            elif self.path == "/api/export-docx":
                document = build_docx(str(payload.get("draft") or ""), str(payload.get("title") or "RERC-e Draft"))
                self.send_bytes(document, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "RERC-e_Draft.docx")
            elif self.path == "/api/import-plan":
                package_text = payload.get("packageText")
                if type(package_text) is not str:
                    raise ValueError("packageText must be JSON text.")
                self.send_json(handoff_to_form(validate_handoff_text(package_text)))
            else:
                self.send_json({"error": "Not found"}, status=404)
        except Exception as exc:
            self.send_json({"error": str(exc)}, status=400)


def serve(host: str, port: int) -> int:
    global EXPECTED_HOST, EXPECTED_ORIGIN
    if host not in {"127.0.0.1", "localhost"}:
        raise ValueError("RERC-e can run only on this computer.")
    browser_host = "127.0.0.1" if host == "localhost" else host
    EXPECTED_HOST = f"{browser_host}:{port}"
    EXPECTED_ORIGIN = f"http://{EXPECTED_HOST}"
    if not SESSION_TOKEN:
        raise RuntimeError("RERC-e needs a local session token.")
    server = ThreadingHTTPServer((host, port), RERCieHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def smoke() -> int:
    current = parse_public_catalog('window.RERC_CATALOG = {"items":[{"item_type":"Funding","title":"One"},{"item_type":"Resource","title":"Two"}]};')
    assert len(current["grants"]) == 1 and len(current["resources"]) == 1
    legacy = parse_public_catalog('window.GRANT_EXPLORER_DATA = {"grants":[{"title":"Legacy"}]};')
    assert len(legacy["grants"]) == 1
    sample_rows = [
        ["NAME", "state", "place"],
        ["St. Paul town, Virginia", "51", "71616"],
        ["Damascus town, Virginia", "51", "21000"],
    ]
    assert _best_geography_record(sample_rows, "St Paul").get("place") == "71616"
    sample_profile = {"place": "St. Paul town, Virginia", "population": "1046", "median_household_income": "29554", "source": "Test source"}
    profile_text = format_public_profile(sample_profile)
    assert "Population: 1,046" in profile_text and "Median household income: $29,554" in profile_text
    assert "CENSUS_KEY_SENTINEL" not in compose_prompt({"projectTitle": "Test"}, sample_profile, "")
    assert DEFAULT_MODEL == "gemma-3-1b-it-Q4_K_M.gguf"
    valid_handoff = {
        "schema": HANDOFF_SCHEMA,
        "version": HANDOFF_VERSION,
        "community": "St. Paul",
        "state": "Virginia",
        "projectTitle": "Downtown Trail Connection",
        "projectNotes": "Connect downtown businesses to the regional trail.",
        "profile": {
            "place": "St. Paul town, Virginia",
            "population": "1046",
            "source": "U.S. Census Bureau",
            "source_url": "https://data.census.gov/",
        },
        "roadmap": [
            {"stage": "Plan", "title": "Confirm the project scope", "status": "Next"},
        ],
        "selectedRecords": [
            {
                "item_id": "RERC-FND-TEST",
                "item_type": "Funding",
                "title": "Sample Trail Grant",
                "organization": "Sample Agency",
                "summary": "Supports eligible trail connections.",
                "source_url": "https://example.gov/trail-grant",
            },
        ],
    }
    imported = handoff_to_form(validate_handoff_text(json.dumps(valid_handoff)))
    assert imported["community"] == "St. Paul"
    assert "Sample Trail Grant" in imported["selectedFundingDetails"]
    assert "Community Explorer roadmap" in imported["projectNotes"]
    assert validate_handoff_text(json.dumps(dict(valid_handoff, schema=LEGACY_HANDOFF_SCHEMA)))["schema"] == HANDOFF_SCHEMA
    invalid_handoff = dict(valid_handoff, schema="wrong-schema")
    try:
        validate_handoff_text(json.dumps(invalid_handoff))
        raise AssertionError("Invalid handoff schema was accepted.")
    except ValueError:
        pass
    try:
        validate_handoff_text("x" * (MAX_HANDOFF_BYTES + 1))
        raise AssertionError("Oversized handoff was accepted.")
    except ValueError:
        pass
    unsafe_url_handoff = json.loads(json.dumps(valid_handoff))
    unsafe_url_handoff["selectedRecords"][0]["source_url"] = "javascript:alert(1)"
    try:
        validate_handoff_text(json.dumps(unsafe_url_handoff))
        raise AssertionError("Unsafe source URL was accepted.")
    except ValueError:
        pass
    markup_handoff = dict(valid_handoff, projectNotes="<img src=x onerror=alert(1)>")
    try:
        validate_handoff_text(json.dumps(markup_handoff))
        raise AssertionError("HTML markup was accepted.")
    except ValueError:
        pass
    try:
        parse_public_community_profiles("window.RERC_COMMUNITY_PROFILES = {\"bad\": true}")
        assert False, "Malformed community profile payload should be rejected."
    except ValueError:
        pass
    try:
        parse_public_community_profiles("window.RERC_COMMUNITY_PROFILES = [\"not a record\"];" )
        assert False, "Invalid community profile records should be rejected."
    except ValueError:
        pass
    try:
        parse_public_community_profiles("window.RERC_COMMUNITY_PROFILES=[];" + (" " * MAX_COMMUNITY_PROFILE_BYTES))
        assert False, "Oversize community profile payload should be rejected."
    except ValueError:
        pass
    try:
        _request_text("http://example.test/community_profiles.js", max_bytes=1024)
        raise AssertionError("Non-HTTPS community profile URL was accepted.")
    except ValueError:
        pass

    lookup_globals = globals()
    backup_public_lookup = lookup_globals["fetch_public_community_profile"]
    backup_census_lookup = lookup_globals["fetch_census_community_profile"]
    backup_key_lookup = lookup_globals["_census_api_key"]
    backup_request_text = lookup_globals["_request_text"]
    try:
        profile_bundle = "window.RERC_COMMUNITY_PROFILES = " + json.dumps([
            {"community": "Damascus", "state": "Virginia", "name": "Damascus town, Virginia", "population": 21000},
            {"community": "Damascus", "state": "Tennessee", "name": "Damascus, Tennessee", "population": 800},
        ]) + ";"
        lookup_globals["_request_text"] = lambda url, **kwargs: profile_bundle
        exact_public_profile = fetch_public_community_profile("Damascus", "Virginia")
        assert exact_public_profile.get("place") == "Damascus town, Virginia"
        assert exact_public_profile.get("population") == "21000"
        assert not fetch_public_community_profile("Damascus", "West Virginia")
        lookup_globals["_request_text"] = backup_request_text

        lookup_globals["fetch_public_community_profile"] = lambda community, state: {
            "place": "Damascus town, Virginia",
            "geography_type": "place",
            "population": "21000",
            "median_household_income": "30000",
            "source": "prebuilt profile",
            "source_url": "https://henkelpress.github.io/rerc-grant-finder/",
        }
        projected = lookup_community_profile("Damascus", "Virginia", "")
        assert projected["status"] == "found"
        assert projected["profile"].get("place") == "Damascus town, Virginia"

        lookup_globals["fetch_public_community_profile"] = lambda community, state: {}
        lookup_globals["_census_api_key"] = lambda census_api_key="": ""
        lookup_globals["fetch_census_community_profile"] = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("Keyless lookup must not call Census."))
        no_match_no_key = lookup_community_profile("Unknownville", "Virginia", "")
        assert no_match_no_key["status"] == "key_required"
        assert "Add a Census API key" in no_match_no_key["message"]

        lookup_globals["fetch_public_community_profile"] = lambda community, state: (_ for _ in ()).throw(ValueError("malformed payload"))
        malformed_no_key = lookup_community_profile("Damascus", "Virginia", "")
        assert malformed_no_key["status"] == "unavailable"

        lookup_globals["fetch_public_community_profile"] = lambda community, state: {}
        lookup_globals["fetch_census_community_profile"] = lambda community, state, census_api_key="": {"place": "Damascus town, Virginia", "source": "census fallback", "geography_type": "place"}
        lookup_globals["_census_api_key"] = lambda census_api_key="": census_api_key.strip()
        with_key_fallback = lookup_community_profile("Damascus", "Virginia", "CENSUS_API_KEY_SENTINEL")
        assert with_key_fallback["status"] == "found"
        assert with_key_fallback["profile"].get("source") == "census fallback"
    finally:
        lookup_globals["fetch_public_community_profile"] = backup_public_lookup
        lookup_globals["fetch_census_community_profile"] = backup_census_lookup
        lookup_globals["_census_api_key"] = backup_key_lookup

    imported_profile_payload = {
        "community": "St. Paul", "state": "Virginia", "projectTitle": "Trail",
        "projectNotes": "Connect the trail.", "publicProfile": sample_profile,
        "usePublicData": False, "provider": "fallback",
    }
    imported_profile_result = build_draft(imported_profile_payload)
    assert imported_profile_result["profileStatus"] == "imported"
    assert "Population: 1,046" in imported_profile_result["draft"]
    try:
        _require_loopback_runtime_url("test", "https://example.com/v1/chat")
        raise AssertionError("A non-loopback writer URL was accepted.")
    except RuntimeError:
        pass
    no_leak_prompt = compose_prompt({"projectTitle": "Test", "censusApiKey": "CENSUS_API_KEY_SENTINEL"}, sample_profile, "")
    assert "CENSUS_API_KEY_SENTINEL" not in no_leak_prompt
    unsafe_draft = "A survey found 70% support and an $85,000 budget."
    assert grounding_issues(unsafe_draft, {"projectSummary": "Improve a trail."}, sample_profile)
    unsafe_qualitative = "The town will acquire land, hire a consultant, obtain approvals, and has strong community support."
    assert grounding_issues(unsafe_qualitative, {"projectSummary": "Improve a trail."}, sample_profile)
    safe_scaffold = deterministic_scaffold({"community": "Test", "state": "Virginia", "projectTitle": "Trail", "projectSummary": "Improve a trail."}, sample_profile)
    assert not grounding_issues(safe_scaffold, {"community": "Test", "state": "Virginia", "projectTitle": "Trail", "projectSummary": "Improve a trail."}, sample_profile)
    rich_funding = _funding_record_text(json.dumps({
        "title": "Trail Grant", "organization": "Example Agency", "status": "Recurring",
        "eligible_users": "Local governments", "summary": "Supports trail connections.",
        "amount_or_cost": "$100,000", "match_or_cost": "20%", "deadline_or_availability": "Annual",
        "source_url": "https://example.gov/trail",
    }))
    assert all(label in rich_funding for label in ("Status", "Eligible applicants", "Amount or support", "Match or cost share", "Deadline or availability"))
    try:
        validate_draft_context({"community": "Damascus", "state": "Virginia", "projectTitle": "Trail"})
        raise AssertionError("Drafting accepted no project summary, notes, or funding details.")
    except ValueError:
        pass
    sample = {"community":"Damascus","state":"Virginia","projectTitle":"Trailhead Wayfinding","projectSummary":"Improve access from downtown to nearby trails.","selectedGrant":"Sample funding record","usePublicData":False,"provider":"fallback"}
    result = build_draft(sample)
    assert "Fit Summary" in result["draft"]
    docx = build_docx(result["draft"] + "\x01", "Smoke Test\x02")
    assert docx.startswith(b"PK")
    with zipfile.ZipFile(io.BytesIO(docx)) as package:
        assert "word/document.xml" in package.namelist()
        document_xml = package.read("word/document.xml")
        ET.fromstring(document_xml)
        assert b"\x01" not in document_xml and b"\x02" not in package.read("docProps/core.xml")
    print(json.dumps({
        "status": "PASS",
        "version": APP_VERSION,
        "catalog_formats": 2,
        "territories": 5,
        "docx_bytes": len(docx),
        "handoff_schema": HANDOFF_SCHEMA,
        "handoff_version": HANDOFF_VERSION,
        "handoff_max_bytes": MAX_HANDOFF_BYTES,
        "handoff_checks": ["valid", "invalid_schema", "oversize", "unsafe_url", "html_markup"],
        "profile_checks": [
            "https_only_bounded",
            "exact_community_state",
            "no_match_no_key",
            "malformed_no_key",
            "key_direct_fallback",
            "no_key_to_gemma",
        ],
        "model": DEFAULT_MODEL,
    }, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="RERC-e Local Grant-Writing Guide")
    parser.add_argument("--serve", action="store_true", help="start the local web interface")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8789)
    parser.add_argument("--smoke", action="store_true", help="run offline checks")
    args = parser.parse_args()
    if args.smoke:
        return smoke()
    if args.serve:
        return serve(args.host, args.port)
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
