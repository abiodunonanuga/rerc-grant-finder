from __future__ import annotations

import argparse
import concurrent.futures
import csv
from datetime import datetime
import hashlib
import io
import ipaddress
import json
import os
from pathlib import Path
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
DATA_PREFIX = "window.RERC_CATALOG = "
CASE_PREFIX = "window.RERC_CASE_STUDIES="
EASTERN = ZoneInfo("America/New_York")
TARGET_HOUR = 3
TARGET_MINUTE = 33
MAX_ROWS_PER_SHEET = 250
MAX_PROBE_WORKERS = 12
CONTACT_HEADER_TERMS = ("email", "e mail", "phone", "telephone", "contact person", "contact information")
CONTACT_HEADERS = {"name", "your name", "contact name", "submitted by", "submitter name"}
ITEM_TYPES = {
    "funding": "Funding",
    "grant": "Funding",
    "loan": "Funding",
    "resource": "Resource",
    "tool": "Resource",
    "case study": "Case Study",
    "case studies": "Case Study",
    "example": "Case Study",
}
ITEM_ALIASES = {
    "submission_type": ("type", "item type", "submission type", "what are you submitting"),
    "title": ("title", "name", "program name", "resource name", "item name"),
    "organization": ("organization", "agency", "provider", "sponsor"),
    "source_url": ("url", "website", "official url", "source url", "program website"),
    "geography": ("geography", "state", "states", "service area", "coverage area"),
    "eligible_users": ("eligible users", "who can apply", "eligibility", "best for"),
    "deadline": ("deadline", "next deadline", "availability", "deadline or availability"),
    "amount": ("amount", "funding amount", "award amount", "cost"),
    "match": ("match", "matching requirement", "cost share"),
    "summary": ("summary", "description", "about", "details"),
    "notes": ("notes", "additional information", "why should this be added"),
}
ISSUE_ALIASES = {
    "issue_type": ("issue type", "type", "category", "what is wrong"),
    "description": ("description", "problem", "what happened", "details"),
    "target_url": ("page url", "url", "link", "program website", "where did this happen"),
    "item_id": ("item id", "record id", "program id"),
    "expected": ("expected", "what should happen", "suggested correction"),
    "device": ("device", "browser", "phone or computer"),
}


def normalize_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def value_for(row: dict[str, str], aliases: tuple[str, ...]) -> str:
    normalized = {normalize_header(key): clean(value) for key, value in row.items()}
    wanted = [normalize_header(alias) for alias in aliases]
    for alias in wanted:
        if normalized.get(alias):
            return normalized[alias]
    for key, value in normalized.items():
        if value and any(alias in key or key in alias for alias in wanted):
            return value
    return ""


def row_key(kind: str, row: dict[str, str]) -> str:
    payload = json.dumps(
        {normalize_header(key): clean(value) for key, value in sorted(row.items())},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(f"{kind}|{payload}".encode("utf-8")).hexdigest()[:20]


def scheduled_now(now: datetime | None = None) -> bool:
    current = now or datetime.now(EASTERN)
    if current.tzinfo is None:
        current = current.replace(tzinfo=EASTERN)
    else:
        current = current.astimezone(EASTERN)
    return current.hour == TARGET_HOUR and current.minute == TARGET_MINUTE


def is_public_https_url(value: str) -> bool:
    if any(character in value for character in ("<", ">", "\\", "\t", "\r", "\n")):
        return False
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return False
    host = parsed.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        return False
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return True
    return not (address.is_private or address.is_loopback or address.is_link_local or address.is_reserved)


def distinct_rows(kind: str, rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen = set()
    result = []
    for row in rows[-MAX_ROWS_PER_SHEET:]:
        key = row_key(kind, row)
        if key not in seen and any(clean(value) for value in row.values()):
            seen.add(key)
            result.append(row)
    return result


def markdown_text(value: str) -> str:
    text = clean(value)
    for character in ("\\", "`", "*", "_", "[", "]", "<", ">", "#", "|"):
        text = text.replace(character, "\\" + character)
    return text

def google_csv_url(value: str) -> str:
    url = clean(value)
    match = re.search(r"docs\.google\.com/spreadsheets/d/([A-Za-z0-9_-]+)", url)
    if not match:
        return url
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query)
    fragment = urllib.parse.parse_qs(parsed.fragment)
    gid = (query.get("gid") or fragment.get("gid") or ["0"])[0]
    return f"https://docs.google.com/spreadsheets/d/{match.group(1)}/export?format=csv&gid={gid}"


def read_csv_source(value: str, timeout: int = 30) -> list[dict[str, str]]:
    source = google_csv_url(value)
    if source.startswith("file://"):
        text = Path(urllib.request.url2pathname(urllib.parse.urlparse(source).path)).read_text(encoding="utf-8-sig")
    else:
        request = urllib.request.Request(
            source,
            headers={"User-Agent": "RERC-Intake-Watcher/1.0", "Accept": "text/csv,text/plain,*/*"},
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout, context=ssl.create_default_context()) as response:
                text = response.read().decode("utf-8-sig")
        except urllib.error.HTTPError as exc:
            if exc.code in {401, 403}:
                raise RuntimeError(
                    "The response sheet is not readable. Share a response-only sheet as Anyone with the link can view."
                ) from exc
            raise
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("The response sheet has no header row")
    return [{str(key): clean(value) for key, value in row.items() if key is not None} for row in reader]


def load_js_payload(path: Path, prefix: str) -> dict:
    raw = path.read_text(encoding="utf-8").strip()
    if not raw.startswith(prefix) or not raw.endswith(";"):
        raise ValueError(f"{path.name} has an unexpected format")
    return json.loads(raw[len(prefix) : -1])


def catalog_index() -> dict[str, set[str]]:
    catalog = load_js_payload(ROOT / "data.js", DATA_PREFIX)
    cases = load_js_payload(ROOT / "case_studies.js", CASE_PREFIX)
    items = list(catalog.get("items", [])) + list(cases.get("items", []))
    return {
        "ids": {clean(item.get("item_id")) for item in items if clean(item.get("item_id"))},
        "urls": {clean(item.get("source_url")).rstrip("/").lower() for item in items if clean(item.get("source_url"))},
        "titles": {normalize_text(clean(item.get("title"))) for item in items if clean(item.get("title"))},
    }


def probe_url(url: str, timeout: int = 20) -> dict:
    result = {"reachable": False, "status": None, "final_url": url, "manual_review": False, "error": ""}
    if not is_public_https_url(url):
        result["error"] = "An official HTTPS URL is required"
        return result
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36",
        "Accept": "text/html,application/pdf,*/*",
    }
    for method in ("HEAD", "GET"):
        try:
            request = urllib.request.Request(url, method=method, headers=headers)
            with urllib.request.urlopen(request, timeout=timeout, context=ssl.create_default_context()) as response:
                status = getattr(response, "status", 200)
                result.update(reachable=status < 400, status=status, final_url=response.geturl())
                return result
        except urllib.error.HTTPError as exc:
            if method == "HEAD":
                continue
            result.update(status=exc.code, error=str(exc), manual_review=exc.code in {401, 403, 429})
        except Exception as exc:  # noqa: BLE001 - every provider failure is preserved in the queue.
            if method == "HEAD":
                continue
            result.update(error=f"{type(exc).__name__}: {exc}", manual_review=True)
    return result


def classify_item(row: dict[str, str], index: dict[str, set[str]], check_network: bool) -> dict:
    item = {key: value_for(row, aliases) for key, aliases in ITEM_ALIASES.items()}
    raw_type = normalize_text(item["submission_type"])
    item_type = next((mapped for key, mapped in ITEM_TYPES.items() if key == raw_type or key in raw_type), "")
    source_url = item["source_url"]
    normalized_url = source_url.rstrip("/").lower()
    errors = []
    if not item_type:
        errors.append("Choose Funding, Resource, or Case Study")
    if not item["title"]:
        errors.append("A title is required")
    if not source_url:
        errors.append("An official URL is required")
    elif not is_public_https_url(source_url):
        errors.append("The official URL must use HTTPS")
    duplicate = ""
    if normalized_url and normalized_url in index["urls"]:
        duplicate = "official URL already exists"
    elif normalize_text(item["title"]) and normalize_text(item["title"]) in index["titles"]:
        duplicate = "title already exists"
    probe = probe_url(source_url) if check_network and is_public_https_url(source_url) else None
    if probe and not probe["reachable"] and not probe["manual_review"]:
        errors.append(f"Official URL failed with {probe['status'] or probe['error']}")
    if duplicate:
        disposition = "possible_update_to_existing"
    elif errors:
        disposition = "rejected_or_incomplete"
    elif probe and probe["manual_review"]:
        disposition = "manual_source_review"
    elif check_network and probe and probe["reachable"]:
        disposition = "ready_for_human_review"
    else:
        disposition = "source_check_pending"
    return {
        "submission_id": row_key("new_item", row),
        "disposition": disposition,
        "item_type": item_type or item["submission_type"],
        "title": item["title"],
        "organization": item["organization"],
        "source_url": source_url,
        "geography": item["geography"],
        "eligible_users": item["eligible_users"],
        "deadline_or_availability": item["deadline"],
        "amount_or_cost": item["amount"],
        "match_or_cost": item["match"],
        "summary": item["summary"],
        "notes": item["notes"],
        "duplicate_note": duplicate,
        "validation_errors": errors,
        "source_check": probe,
    }


def classify_issue(row: dict[str, str], index: dict[str, set[str]], check_network: bool) -> dict:
    issue = {key: value_for(row, aliases) for key, aliases in ISSUE_ALIASES.items()}
    errors = []
    if not issue["description"]:
        errors.append("An issue description is required")
    target = issue["target_url"]
    item_id = issue["item_id"]
    probe = probe_url(target) if check_network and is_public_https_url(target) else None
    evidence = []
    if item_id:
        evidence.append("catalog item found" if item_id in index["ids"] else "catalog item ID not found")
    if probe:
        if probe["status"] in {404, 410}:
            evidence.append(f"broken link reproduced ({probe['status']})")
        elif probe["reachable"]:
            evidence.append("reported page is reachable; behavior still needs reproduction")
        elif probe["manual_review"]:
            evidence.append("automated access was blocked; manual reproduction required")
    reproduced = bool(probe and probe["status"] in {404, 410})
    if errors:
        disposition = "rejected_or_incomplete"
    elif reproduced:
        disposition = "verified_issue"
    else:
        disposition = "needs_human_reproduction"
    return {
        "submission_id": row_key("issue", row),
        "disposition": disposition,
        "issue_type": issue["issue_type"] or "Other",
        "description": issue["description"],
        "target_url": target,
        "item_id": item_id,
        "expected": issue["expected"],
        "device": issue["device"],
        "validation_errors": errors,
        "verification_evidence": evidence,
        "target_check": probe,
    }


def redact_text(value: str) -> str:
    text = re.sub(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", "[redacted email]", value, flags=re.IGNORECASE)
    return re.sub(r"(?<!\d)(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}(?!\d)", "[redacted phone]", text)


def redact_row(row: dict[str, str]) -> dict[str, str]:
    return {
        key: redact_text(value)
        for key, value in row.items()
        if normalize_header(key) not in CONTACT_HEADERS
        and not any(term in normalize_header(key) for term in CONTACT_HEADER_TERMS)
    }

def render_markdown(report: dict) -> str:
    lines = [
        "# RERC Intake Watcher Review Queue",
        "",
        f"Generated: {report['generated_at']}",
        f"Status: {report['status']}",
        f"New-item submissions checked: {len(report['new_items'])}",
        f"Issue reports checked: {len(report['issues'])}",
        "",
        "This queue contains no contact fields. Public catalog changes still require review and the normal release QA.",
        "",
    ]
    if report.get("configuration_errors"):
        lines.extend(["## Configuration Hold", "", *[f"- {markdown_text(item)}" for item in report["configuration_errors"]], ""])
    if report["new_items"]:
        lines.extend(["## New Items", ""])
        for item in report["new_items"]:
            lines.append(
                f"- **{item['disposition']}**: {markdown_text(item['title'] or 'Untitled submission')} "
                f"({markdown_text(item['item_type'] or 'type missing')}) - "
                f"{markdown_text(item['source_url'])} - `{item['submission_id']}`"
            )
        lines.append("")
    if report["issues"]:
        lines.extend(["## Reported Issues", ""])
        for item in report["issues"]:
            lines.append(
                f"- **{item['disposition']}**: {markdown_text(item['issue_type'])} - "
                f"{markdown_text(item['description'][:240])} `{item['submission_id']}`"
            )
        lines.append("")
    return "\n".join(lines)

def run(args: argparse.Namespace) -> dict:
    now = datetime.now(EASTERN)
    if args.scheduled and not args.force and not scheduled_now(now):
        return {
            "status": "SKIPPED_OUTSIDE_0333_EASTERN",
            "generated_at": now.isoformat(),
            "new_items": [],
            "issues": [],
            "configuration_errors": [],
        }
    new_items_url = clean(args.new_items_url or os.environ.get("RERC_NEW_ITEMS_SHEET_URL"))
    issues_url = clean(args.issues_url or os.environ.get("RERC_ISSUES_SHEET_URL"))
    configuration_errors = []
    if not new_items_url:
        configuration_errors.append("RERC_NEW_ITEMS_SHEET_URL is not configured")
    if not issues_url:
        configuration_errors.append("RERC_ISSUES_SHEET_URL is not configured")
    index = catalog_index()
    new_rows = []
    issue_rows = []
    if new_items_url:
        try:
            new_rows = read_csv_source(new_items_url)
        except Exception as exc:  # noqa: BLE001 - configuration failures must be visible in the queue.
            configuration_errors.append(f"New-item sheet: {type(exc).__name__}: {exc}")
    if issues_url:
        try:
            issue_rows = read_csv_source(issues_url)
        except Exception as exc:  # noqa: BLE001 - configuration failures must be visible in the queue.
            configuration_errors.append(f"Issue sheet: {type(exc).__name__}: {exc}")
    new_rows = distinct_rows("new_item", new_rows)
    issue_rows = distinct_rows("issue", issue_rows)
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_PROBE_WORKERS) as pool:
        new_items = list(pool.map(lambda row: classify_item(redact_row(row), index, not args.skip_network), new_rows))
        issues = list(pool.map(lambda row: classify_issue(redact_row(row), index, not args.skip_network), issue_rows))
    report = {
        "status": "CONFIGURATION_REQUIRED" if configuration_errors else "REVIEW_READY",
        "generated_at": now.isoformat(),
        "schedule": "03:33 America/New_York",
        "new_items": new_items,
        "issues": issues,
        "configuration_errors": configuration_errors,
        "privacy": "Contact fields are removed before reports are written.",
        "publication_boundary": "No submission is published automatically. Validated rows enter human review and existing release QA.",
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Read RERC Google Sheets response queues and verify public submissions.")
    parser.add_argument("--new-items-url", default="")
    parser.add_argument("--issues-url", default="")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "intake-review")
    parser.add_argument("--scheduled", action="store_true", help="Run only at 03:33 America/New_York")
    parser.add_argument("--force", action="store_true", help="Bypass the local-time gate for manual runs")
    parser.add_argument("--skip-network", action="store_true", help="Parse and validate without probing submitted URLs")
    parser.add_argument("--gate-only", action="store_true", help="Return only the 03:33 Eastern schedule decision")
    args = parser.parse_args()
    if args.gate_only:
        allowed = args.force or scheduled_now()
        print(json.dumps({"run": allowed, "schedule": "03:33 America/New_York"}))
        return 0 if allowed else 78
    report = run(args)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "intake-review-queue.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (args.output_dir / "intake-review-queue.md").write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "new_items": len(report["new_items"]),
        "issues": len(report["issues"]),
        "configuration_errors": report["configuration_errors"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
