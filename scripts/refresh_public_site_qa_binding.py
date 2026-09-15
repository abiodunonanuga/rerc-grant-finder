"""Rebind the current site UI after browser QA without rebuilding static catalog files."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOWNLOADS = ROOT / "downloads"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def committed_sha256(commit: str, path: str) -> str:
    return sha256(subprocess.check_output(["git", "cat-file", "blob", f"{commit}:{path}"], cwd=ROOT))


def main() -> None:
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    files = re.findall(r'href="downloads/([^\"]+)"', index)
    if len(files) != 3 or {Path(name).suffix for name in files} != {".csv", ".docx", ".xlsx"}:
        raise ValueError("The public page must link one CSV, Word, and Excel catalog file.")
    package_date = re.search(r"_(\d{4}-\d{2}-\d{2})\.docx$", next(name for name in files if name.endswith(".docx")))
    if not package_date:
        raise ValueError("The linked Word package does not carry a date.")
    report_path = DOWNLOADS / f"RERC_Community_Explorer_QA_{package_date.group(1)}.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("status") != "PASS":
        raise ValueError("The linked static catalog package has no PASS report.")
    for extension in ("csv", "docx", "xlsx"):
        file_name = next(name for name in files if name.endswith("." + extension))
        evidence = report[extension]
        file_path = DOWNLOADS / file_name
        if evidence["file"] != file_name or evidence["sha256"] != sha256(file_path.read_bytes()) or evidence["bytes"] != file_path.stat().st_size:
            raise ValueError(f"The linked {extension} package no longer matches its QA report.")
    browser = json.loads((ROOT / "browser-qa" / "playwright_qa.json").read_text(encoding="utf-8"))
    if browser.get("status") != "PASS" or browser.get("errors") or browser.get("failures"):
        raise ValueError("Current public-site browser QA must pass before rebinding the site.")
    if browser["checks"]["counts"] != [report["funding"], report["resources"], report["community_examples"]]:
        raise ValueError("Browser catalog counts disagree with the linked static package.")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    for path, expected in report["source_sha256"].items():
        if committed_sha256(commit, path) != expected:
            raise ValueError(f"Catalog source changed after the static {package_date.group(1)} package was built: {path}")
    report["site_sha256"] = {path: committed_sha256(commit, path) for path in report["site_sha256"]}
    report["site_validation"] = {
        "status": "PASS",
        "checked_on": date.today().isoformat(),
        "site_commit": commit,
        "browser_report_sha256": sha256((ROOT / "browser-qa" / "playwright_qa.json").read_bytes()),
        "note": "Site interface source and browser QA refreshed; the linked static catalog files and their original package source remain unchanged.",
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "report": str(report_path), "site_commit": commit, "package_date": package_date.group(1)}, indent=2))


if __name__ == "__main__":
    main()
