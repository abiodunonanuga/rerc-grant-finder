from __future__ import annotations

import argparse
import csv
import io
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data.js"
CSV_PATH = ROOT / "maintenance" / "catalog.csv"
PREFIX = "window.RERC_CATALOG = "
FIELDS = [
    "item_id", "item_type", "title", "organization", "status", "last_checked", "geography",
    "covered_states", "coverage_note", "coverage_source_url", "eligible_users", "project_stage",
    "topic_tags", "support_type", "amount_or_cost", "match_or_cost", "deadline_or_availability",
    "summary", "why_it_matters", "source_url",
]
OPTIONAL_FIELDS = {"covered_states", "coverage_note", "coverage_source_url"}


def load_catalog() -> dict:
    raw = DATA_PATH.read_text(encoding="utf-8").strip()
    if not raw.startswith(PREFIX) or not raw.endswith(";"):
        raise ValueError("data.js is not in the RERC catalog format")
    return json.loads(raw[len(PREFIX):-1])


def render_csv(catalog: dict) -> str:
    handle = io.StringIO(newline="")
    writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    for item in catalog["items"]:
        row = {field: item.get(field, "") for field in FIELDS}
        row["covered_states"] = "|".join(item.get("covered_states") or [])
        writer.writerow(row)
    return handle.getvalue()


def export_catalog(catalog: dict) -> None:
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    CSV_PATH.write_text(render_csv(catalog), encoding="utf-8-sig", newline="")


def import_catalog(catalog: dict) -> dict:
    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != FIELDS:
            raise ValueError("maintenance/catalog.csv headers changed; restore the documented field order")
        rows = list(reader)
    ids = [row["item_id"].strip() for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("maintenance/catalog.csv contains duplicate item_id values")
    current = {item["item_id"]: item for item in catalog["items"]}
    if set(ids) != set(current):
        missing = sorted(set(current) - set(ids))
        extra = sorted(set(ids) - set(current))
        raise ValueError(f"Catalog IDs changed unexpectedly. Missing={missing[:5]} Extra={extra[:5]}")
    rebuilt = []
    for row in rows:
        item = dict(current[row["item_id"].strip()])
        for field in FIELDS:
            value = row[field].strip()
            if field == "covered_states":
                states = [part.strip() for part in value.split("|") if part.strip()]
                if states:
                    item[field] = states
                else:
                    item.pop(field, None)
            elif field in OPTIONAL_FIELDS:
                if value:
                    item[field] = value
                else:
                    item.pop(field, None)
            else:
                item[field] = value
        rebuilt.append(item)
    catalog["items"] = rebuilt
    catalog["updated"] = date.today().isoformat()
    catalog["counts"] = {
        "combined": len(rebuilt),
        "funding": sum(item["item_type"] == "Funding" for item in rebuilt),
        "resources": sum(item["item_type"] == "Resource" for item in rebuilt),
    }
    DATA_PATH.write_text(PREFIX + json.dumps(catalog, separators=(",", ":"), ensure_ascii=False) + ";\n", encoding="utf-8", newline="\n")
    export_catalog(catalog)
    return catalog


def check_catalog(catalog: dict) -> None:
    expected = render_csv(catalog)
    actual = CSV_PATH.read_text(encoding="utf-8-sig")
    if actual.replace("\r\n", "\n") != expected:
        raise SystemExit("maintenance/catalog.csv differs from data.js. Run: python scripts/catalog_maintenance.py export")
    items = catalog["items"]
    expected_counts = {
        "combined": len(items),
        "funding": sum(item.get("item_type") == "Funding" for item in items),
        "resources": sum(item.get("item_type") == "Resource" for item in items),
    }
    if catalog.get("counts") != expected_counts:
        raise SystemExit(f"Catalog counts do not match item records: {catalog.get('counts')} != {expected_counts}")
    print(json.dumps({"status": "PASS", "records": len(catalog["items"]), "catalog_csv": str(CSV_PATH.relative_to(ROOT))}))


def main() -> int:
    parser = argparse.ArgumentParser(description="Export, import, or verify the human-editable RERC funding/resource catalog.")
    parser.add_argument("command", choices=("export", "import", "check"))
    args = parser.parse_args()
    catalog = load_catalog()
    if args.command == "export":
        export_catalog(catalog)
        print(f"Wrote {CSV_PATH}")
    elif args.command == "import":
        import_catalog(catalog)
        print(f"Updated {DATA_PATH} and normalized {CSV_PATH}")
    else:
        check_catalog(catalog)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())