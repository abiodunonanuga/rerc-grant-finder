from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).absolute().parents[1]
PREFIX = "window.RERC_CATALOG = "
MAX_REVIEW_AGE_DAYS = 60
EXPECTED_CLASSES = {"dated", "rolling", "closed", "variable", "active_period", "recurring", "date_pending"}


def load_catalog(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8").strip()
    if not raw.startswith(PREFIX) or not raw.endswith(";"):
        raise ValueError("data.js is not in the RERC catalog format")
    return json.loads(raw[len(PREFIX) : -1])


def browser_classifications(path: Path) -> dict:
    result = subprocess.run(
        ["node", str(ROOT / "scripts" / "qa_deadline_parity.cjs"), "--json", str(path)],
        cwd=ROOT, check=True, capture_output=True, text=True,
    )
    report = json.loads(result.stdout)
    if report.get("status") != "PASS" or report.get("funding_records") != 659:
        raise ValueError("Shared browser deadline classifier failed its coverage gate")
    records = report.get("records", {})
    if len(records) != 659 or set(records.values()) - EXPECTED_CLASSES:
        raise ValueError("Shared browser deadline classifier returned invalid record classes")
    return report


def audit(path: Path) -> dict:
    payload = load_catalog(path)
    funding = [item for item in payload.get("items", []) if item.get("item_type") == "Funding"]
    shared = browser_classifications(path)
    classifications = shared["records"]
    rows = []
    issues = []
    counts: Counter[str] = Counter()
    today = date.today()
    for item in funding:
        item_id = str(item.get("item_id") or "")
        timing = str(item.get("deadline_or_availability") or "").strip()
        checked = str(item.get("last_checked") or "").strip()
        source = str(item.get("source_url") or "").strip()
        category = classifications.get(item_id)
        if category not in EXPECTED_CLASSES:
            issues.append({"item_id": item_id, "issue": "missing shared browser timing class"})
            category = "date_pending"
        counts[category] += 1
        checked_date = date.fromisoformat(checked) if re.fullmatch(r"20\d{2}-\d{2}-\d{2}", checked) else None
        row = {
            "item_id": item_id,
            "title": item.get("title"),
            "status": item.get("status"),
            "timing_class": category,
            "deadline_or_availability": timing,
            "last_checked": checked,
            "review_age_days": (today - checked_date).days if checked_date else None,
            "source_url": source,
        }
        rows.append(row)
        if not timing:
            issues.append({"item_id": item_id, "issue": "blank timing"})
        if not re.fullmatch(r"20\d{2}-\d{2}-\d{2}", checked):
            issues.append({"item_id": item_id, "issue": "missing review date"})
        if not source.startswith("https://"):
            issues.append({"item_id": item_id, "issue": "missing HTTPS source"})
    stale = [row for row in rows if row["review_age_days"] is not None and row["review_age_days"] > MAX_REVIEW_AGE_DAYS]
    parity = dict(sorted(counts.items())) == dict(sorted(shared["counts"].items()))
    if not parity:
        issues.append({"issue": "browser/Python deadline class mismatch"})
    structural_ok = not issues and len(funding) == 659 and parity
    return {
        "status": "FAIL" if not structural_ok else ("REVIEW" if stale else "PASS"),
        "coverage_status": "PASS" if not issues and len(funding) == 659 else "FAIL",
        "freshness_status": "REVIEW" if stale else "CURRENT",
        "deadline_parity_status": "PASS" if parity else "FAIL",
        "checked_on": today.isoformat(),
        "funding_records": len(funding),
        "counts": dict(sorted(counts.items())),
        "records_with_timing": sum(bool(row["deadline_or_availability"]) for row in rows),
        "records_with_review_date": sum(bool(re.fullmatch(r"20\d{2}-\d{2}-\d{2}", row["last_checked"])) for row in rows),
        "records_with_https_source": sum(row["source_url"].startswith("https://") for row in rows),
        "freshness_policy_days": MAX_REVIEW_AGE_DAYS,
        "stale_over_policy_days": len(stale),
        "oldest_review_date": min((row["last_checked"] for row in rows if row["last_checked"]), default=""),
        "stale_review_queue": stale,
        "review_queue": [row for row in rows if row["timing_class"] in {"variable", "recurring", "active_period", "date_pending"}],
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit deadline coverage and browser-classification parity for every funding record.")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()
    data_path = ROOT / "data.js"
    if not data_path.exists():
        data_path = ROOT / "site-src" / "data.js"
    report = audit(data_path)
    if args.write_report:
        (ROOT / "funding-deadline-audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        lines = [
            "# Funding Deadline Audit", "", f"Status: {report['status']}",
            f"Funding records: {report['funding_records']}",
            f"Timing fields present: {report['records_with_timing']}",
            f"Review dates present: {report['records_with_review_date']}",
            f"HTTPS sources present: {report['records_with_https_source']}",
            f"Browser/Python deadline parity: {report['deadline_parity_status']}",
            f"Freshness status: {report['freshness_status']}",
            f"Freshness policy: review source content at least every {report['freshness_policy_days']} days",
            f"Reviews beyond policy: {report['stale_over_policy_days']}",
            f"Oldest review date: {report['oldest_review_date']}", "",
            "Coverage confirms that every record has timing text, a review date, an HTTPS source, and the same deadline class used by the public browser.", "",
            "## Timing Classes",
        ]
        lines.extend(f"- {name}: {count}" for name, count in report["counts"].items())
        lines.extend(["", f"Records queued for a future date check: {len(report['review_queue'])}"])
        (ROOT / "funding-deadline-audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    keys = ("status", "coverage_status", "freshness_status", "deadline_parity_status", "funding_records", "counts", "records_with_timing", "records_with_review_date", "records_with_https_source", "freshness_policy_days", "stale_over_policy_days", "oldest_review_date", "issues")
    print(json.dumps({key: report[key] for key in keys}, indent=2))
    return 0 if report["status"] in {"PASS", "REVIEW"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
