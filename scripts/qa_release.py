from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import sys
import zipfile
from html.parser import HTMLParser
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATE_TAG = date.today().isoformat()
PREFIX = "window.RERC_CATALOG = "
EXPECTED_RERCIE_VERSION = "0.5.0"
EXPECTED_REFERRER_POLICY = "strict-origin-when-cross-origin"
EXPECTED_CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self'; "
    "img-src 'self' data:; "
    "connect-src 'self'; "
    "frame-src https://docs.google.com; "
    "font-src 'self'; object-src 'none'; base-uri 'self'; "
    "form-action 'self'; upgrade-insecure-requests"
)

def git_blob_sha256(commit: str, name: str) -> str:
    blob = subprocess.run(["git", "show", f"{commit}:{name}"], cwd=ROOT, check=True, capture_output=True).stdout
    return hashlib.sha256(blob).hexdigest()


def canonical_text_sha256(path: Path) -> str:
    with path.open("r", encoding="utf-8", newline=None) as handle:
        normalized = handle.read()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

class SiteContractParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.elements: list[tuple[str, dict[str, str]]] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        self.elements.append(
            (tag, {name: value or "" for name, value in attrs})
        )


def parse_site_contract(html: str) -> SiteContractParser:
    parser = SiteContractParser()
    parser.feed(html)
    parser.close()
    return parser


def parse_javascript_assignment(path: Path, prefix: str) -> object:
    raw = path.read_text(encoding="utf-8").strip()
    assert raw.startswith(prefix) and raw.endswith(";")
    return json.loads(raw[len(prefix):-1])


def run(*args: str) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


def main() -> int:
    run(sys.executable, "-m", "py_compile", "rercie/rercie_core.py", "rercie/rercie_quality.py", "rercie/rercie.py")
    run(sys.executable, "rercie/rercie.py", "--smoke")
    sys.path.insert(0, str(ROOT / "rercie"))
    import rercie as app
    expected_app_version = app.app.APP_VERSION
    assert expected_app_version == EXPECTED_RERCIE_VERSION
    run("node", "--check", "app.js")
    run("node", "--check", "planner.js")
    run("node", "--check", "ui-i18n.js")
    run(sys.executable, "scripts/qa_case_studies.py")
    run(sys.executable, "scripts/qa_funding_deadlines.py")
    run(sys.executable, "scripts/qa_geography_coverage.py")

    raw = (ROOT / "data.js").read_text(encoding="utf-8").strip()
    assert raw.startswith(PREFIX) and raw.endswith(";")
    payload = json.loads(raw[len(PREFIX):-1])
    items = payload["items"]
    counts = payload["counts"]
    assert counts == {
        "combined": len(items),
        "funding": sum(item["item_type"] == "Funding" for item in items),
        "resources": sum(item["item_type"] == "Resource" for item in items),
    }
    by_id = {item["item_id"]: item for item in items}
    for item_id in ("RERC-RES-0014", "RERC-RES-0066", "RERC-RES-0068", "RERC-RES-0076"):
        assert by_id[item_id]["item_type"] == "Funding"
    assert all(item["item_type"] in {"Funding", "Resource"} for item in items)
    funding_items = [item for item in items if item["item_type"] == "Funding"]
    assert len(funding_items) == counts["funding"]
    assert all((item.get("deadline_or_availability") or "").strip() for item in funding_items)
    assert all(re.fullmatch(r"20\d{2}-\d{2}-\d{2}", item.get("last_checked", "")) for item in funding_items)
    assert all((item.get("source_url") or "").startswith("https://") for item in funding_items)
    assert not any(re.search(r"potential rerc fit|purpose tags", item.get("why_it_matters", ""), re.I) for item in items)
    assert not any((item.get("summary") or "").strip() in {"", "-"} for item in items)
    reviewed_resources = [item for item in items if item["item_id"].startswith(("RERC-RES-R2-", "RERC-RES-NEW-2026-"))]
    assert len(reviewed_resources) == 106
    assert all(len(item["summary"].strip()) >= 55 for item in reviewed_resources)
    assert not any(
        item["summary"].strip(". ").lower()
        in {item["title"].strip(". ").lower(), item["organization"].strip(". ").lower()}
        for item in reviewed_resources
    )
    assert not any(re.fullmatch(r".*\(?(?:19|20)\d{2}\)?\.?", item["summary"]) for item in reviewed_resources)

    index = (ROOT / "index.html").read_text(encoding="utf-8")
    site_contract = parse_site_contract(index)
    elements_by_id: dict[str, tuple[str, dict[str, str]]] = {}
    for tag, attrs in site_contract.elements:
        element_id = attrs.get("id")
        if element_id:
            assert element_id not in elements_by_id
            elements_by_id[element_id] = (tag, attrs)
    required_v2_elements = {
        "matchesWorkspace": "section",
        "showFunding": "button",
        "showResources": "button",
        "showCases": "button",
        "matchCount": "strong",
        "fundingMatchCount": "strong",
        "resourceMatchCount": "strong",
        "caseStudyMatchCount": "strong",
        "planWorkspace": "aside",
        "shareWorkspace": "button",
    }
    assert required_v2_elements.keys() <= elements_by_id.keys()
    assert all(
        elements_by_id[element_id][0] == expected_tag
        for element_id, expected_tag in required_v2_elements.items()
    )
    mode_elements = [
        (tag, attrs)
        for tag, attrs in site_contract.elements
        if attrs.get("data-mode")
    ]
    assert len(mode_elements) == 4
    mode_controls = {
        attrs.get("data-mode"): (tag, attrs)
        for tag, attrs in mode_elements
    }
    assert set(mode_controls) == {"All", "Funding", "Resource", "Case Study"}
    assert mode_controls["All"][0] == "button"
    assert mode_controls["All"][1].get("aria-pressed") == "true"
    assert {
        mode: mode_controls[mode][1].get("id")
        for mode in ("Funding", "Resource", "Case Study")
    } == {
        "Funding": "showFunding",
        "Resource": "showResources",
        "Case Study": "showCases",
    }
    assert all(
        mode_controls[mode][0] == "button"
        and mode_controls[mode][1].get("type") == "button"
        and mode_controls[mode][1].get("aria-pressed") == "false"
        for mode in ("Funding", "Resource", "Case Study")
    )
    script_sources = {
        attrs.get("src", "").split("?", 1)[0]
        for tag, attrs in site_contract.elements
        if tag == "script" and attrs.get("src")
    }
    assert {"site-config.js", "ui-i18n.js", "app.js", "planner.js"} <= script_sources
    rercie_download = next(
        (
            attrs.get("href", "")
            for tag, attrs in site_contract.elements
            if tag == "a" and attrs.get("id") == "rercieDownload"
        ),
        "",
    )
    assert rercie_download == "https://github.com/henkelpress/rerc-grant-finder/releases/latest/download/RERCie-Setup.exe"

    meta_by_name = {
        attrs.get("name", "").lower(): attrs.get("content", "")
        for tag, attrs in site_contract.elements
        if tag == "meta" and attrs.get("name")
    }
    meta_by_http_equiv = {
        attrs.get("http-equiv", "").lower(): attrs.get("content", "")
        for tag, attrs in site_contract.elements
        if tag == "meta" and attrs.get("http-equiv")
    }
    assert meta_by_name.get("referrer") == EXPECTED_REFERRER_POLICY
    assert meta_by_http_equiv.get("content-security-policy") == EXPECTED_CSP

    planner = (ROOT / "planner.js").read_text(encoding="utf-8")
    assert not any(value in planner for value in (
        "nominatim.openstreetmap.org", "OpenStreetMap", "communityMap", "loadProjectedProfile",
        "locateCommunity", "Why it matches", "Why it fits",
    ))
    assert "profileRows(model.profile)" in planner

    app_js = (ROOT / "app.js").read_text(encoding="utf-8")
    config_js = (ROOT / "site-config.js").read_text(encoding="utf-8")
    assert "function coveredStates(item)" in app_js
    assert "function matchesGeography(item, selectedPlace)" in app_js
    assert 'geography.toLowerCase().includes("multi-state")' in app_js
    assert "regionalCoverage.includes(selectedPlace)" in app_js
    assert "Program Website" in app_js and "<strong>Who:</strong>" in app_js
    who_position = app_js.index("<strong>Who:</strong>")
    assert who_position < app_js.index("<details class=\"card-details\">", who_position)
    assert "Why it fits" not in app_js and "Why it matches" not in app_js
    assert "coverage_note" in app_js and "covered_states" in app_js
    assert all(value in config_js for value in ("filters", "ranking", "thresholds", "weights", "failClosedWithoutRegionalCoverage"))

    assert 'id="stateSelect"' in index and 'required' in index
    assert 'id="placeTypeSelect"' not in index and 'id="communityName"' not in index and 'id="communityMap"' not in index
    assert "Choose one state, D.C., or U.S. territory." in index
    assert "Regional programs appear only in the states and territories they serve." in index
    assert "source-backed examples from Protos" not in index and "community profile" not in index.lower()
    assert "why it fits" not in index.lower()
    assert all(value not in index for value in ("fundingViewSwitch", "showFundingCalendar", "calendarGrid", "calendarAgenda", "exportCalendar"))
    assert all(value in index for value in ("fundingTypeOptions", "caseStudyPhaseOptions", "Reset roadmap", "contribute", "openIssueReport", "openCatalogSubmission", "issueReportDialog", "catalogSubmissionDialog"))
    assert "github.com/henkelpress/rerc-grant-finder/issues/new" not in index
    contributions = (ROOT / "contributions.js").read_text(encoding="utf-8")
    assert all(value in contributions for value in ("issueReportUrl", "catalogSubmissionUrl", "embedded", "docs.google.com"))
    assert 'src="deadline-utils.js?v=20260805-2"' in index
    deadline_utils = (ROOT / "deadline-utils.js").read_text(encoding="utf-8")
    assert all(value in deadline_utils for value in ("parseDeadline", "fundingTiming", "RERCDeadlineUtils"))
    assert all(value in app_js for value in ("fundingFilterLabels", "caseStudyPhase", "fundingTiming", "fundingTimingCounts", "wordPageBreakXml"))
    assert all(value in planner for value in (
        "deadline-status", "stateChanged", "docxPageBreak", "rerc.activeWorkspaceId.v2",
        "WORKSPACE_ID_PREFIX", "createWorkspaceId", "phaseChanged"
    ))
    assert "renderCardActions" not in app_js and "planner-card-actions" in planner
    assert "window.RERC_CASE_STUDIES" in app_js and "Read the example" in app_js
    assert "topicCorpus(item)" in app_js and "broadFundingStage" in app_js
    assert "selectedStage !== \"Any step\"" in app_js
    assert "<${headingTag}>${escapeHtml(item.title)}</${headingTag}>" in app_js

    ui_i18n = (ROOT / "ui-i18n.js").read_text(encoding="utf-8")
    assert all(value in ui_i18n for value in (
        "Application timing", "Last checked", "Check current availability",
        "Check the official program page.", "No upcoming dated funding deadline found.",
        "Program Website", "Coverage note:",
    ))
    assert "Why it fits" not in ui_i18n and "Community profile" not in ui_i18n
    assert all(value in ui_i18n for value in (
        "Funding details", "Case study phase", "Reset roadmap", "Report an issue",
        "Submit a grant, resource, or case study",
    ))
    assert (ROOT / ".github" / "ISSUE_TEMPLATE" / "feedback.yml").is_file()
    assert (ROOT / ".github" / "ISSUE_TEMPLATE" / "catalog-submission.yml").is_file()

    manifest = json.loads((ROOT / "maintenance" / "multistate_coverage.json").read_text(encoding="utf-8"))
    regional = [item for item in items if item.get("geography", "").strip().lower() == "multi-state"]
    assert len(regional) == len(manifest["records"])
    assert {item["item_id"] for item in regional} == {row["item_id"] for row in manifest["records"]}
    assert all(item.get("covered_states") and item.get("coverage_note") and item.get("coverage_source_url", "").startswith("https://") for item in regional)

    assert "later standalone retest could not run" not in index.lower()
    styles = (ROOT / "styles.css").read_text(encoding="utf-8")
    assert "outline: 3px solid var(--gold)" in styles
    assert "object-fit: contain" in styles and "object-position: center" in styles
    assert (ROOT / ".gitattributes").read_text(encoding="utf-8").count("eol=lf") >= 8
    assert (ROOT / "scripts" / "qa_public_site.cjs").is_file()
    assert not (ROOT / "scripts" / "qa_public_site_cases.cjs").exists()
    assert not (ROOT / "scripts" / "qa_public_site_final.cjs").exists()
    qa_workflow = (ROOT / ".github" / "workflows" / "qa.yml").read_text(encoding="utf-8")
    assert "qa_public_site.cjs" in qa_workflow and "qa_geography_coverage.py" in qa_workflow
    assert not (ROOT / ".github" / "workflows" / "deploy-pages.yml").exists()
    source_health = (ROOT / ".github" / "workflows" / "source-health.yml").read_text(encoding="utf-8")
    discovery = (ROOT / ".github" / "workflows" / "discover-federal-opportunities.yml").read_text(encoding="utf-8")
    assert "17 10 * * *" in source_health and "actions/cache/restore@v5" in source_health
    assert "23 11 * * *" in discovery
    assert ".source-monitor/" in (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert 'id="nextDeadlinePanel"' in index and "renderNextDeadline" in app_js
    case_raw = (ROOT / "case_studies.js").read_text(encoding="utf-8").strip()
    case_prefix = "window.RERC_CASE_STUDIES="
    assert case_raw.startswith(case_prefix) and case_raw.endswith(";")
    case_payload = json.loads(case_raw[len(case_prefix):-1])
    cases = case_payload["items"]
    assert len(cases) == case_payload["count"]
    assert all(case["source_url"].startswith(("https://www.epa.gov/", "https://toolkit.climate.gov/", "https://www.rd.usda.gov/")) for case in cases)
    assert not any(re.search(r"[A-Za-z]:\\\\|protos|private_internal|needs_image_review", json.dumps(case), re.I) for case in cases)
    case_by_id = {case["item_id"]: case for case in cases}
    assert case_by_id["RERC-CASE-BROWNFIELDS-SUCCESS-STORIES-WEIRTON-WV-FROM-ABANDONED-SCHOOL-TO-MAIN-EVENT-WV-2017"]["summary"].startswith("Weirton used EPA brownfields")
    assert case_by_id["RERC-CASE-BROWNFIELDS-SUCCESS-STORIES-WELLSBURG-WV-A-LOCAL-MANUFACTURING-EXPANSION-TAKES-FLIGHT-WV-2017"]["summary"].startswith("Wellsburg and regional partners")

    downloads = ROOT / "downloads"
    public_downloads = re.findall(r'href="downloads/([^\"]+)"', index)
    assert len(public_downloads) == 3
    static_docx = downloads / next(name for name in public_downloads if name.endswith(".docx"))
    static_xlsx = downloads / next(name for name in public_downloads if name.endswith(".xlsx"))
    static_csv = downloads / next(name for name in public_downloads if name.endswith(".csv"))
    package_date = re.search(r"_(\d{4}-\d{2}-\d{2})\.docx$", static_docx.name).group(1)
    assert static_docx.stat().st_size > 100_000
    assert static_xlsx.stat().st_size > 100_000
    assert static_csv.stat().st_size > 100_000
    with static_csv.open("r", encoding="utf-8-sig", newline="") as handle:
        csv_rows = list(csv.DictReader(handle))
    csv_row_count = len(csv_rows)
    assert csv_row_count == len(items) + len(cases)
    assert {"Covered States", "Coverage Note", "Coverage Source URL", "Type of Help", "Official URL"} <= set(csv_rows[0])
    assert "Why It May Help" not in csv_rows[0]
    assert sum(bool(row["Covered States"]) for row in csv_rows) == len(regional)
    assert sum(bool(row["Coverage Source URL"]) for row in csv_rows) == len(regional)
    assert not any(re.search(r"[A-Za-z]:\\|private_internal|needs_image_review|lorem ipsum|TODO", json.dumps(row), re.I) for row in csv_rows)
    with zipfile.ZipFile(static_docx) as package:
        names = set(package.namelist())
        assert "word/comments.xml" not in names
        document_xml = package.read("word/document.xml").decode("utf-8")
        assert "<w:ins" not in document_xml and "<w:del" not in document_xml
        assert "Why it may help" not in document_xml
        assert not re.search(r"[A-Za-z]:\\\\|private_internal|needs_image_review|lorem ipsum|TODO", document_xml, re.I)
        assert document_xml.count("<w:hyperlink") == csv_row_count + len(regional)
        assert document_xml.count("<w:cantSplit") > 4000
        assert document_xml.count("<w:keepNext") > 4000
        app_xml = package.read("docProps/app.xml").decode("utf-8")
        core_xml = package.read("docProps/core.xml").decode("utf-8")
        assert "Microsoft Office Word" in app_xml and "Macintosh" not in app_xml
        assert "<ns0:Pages>" not in app_xml and "<Pages>" not in app_xml
        assert f"{package_date}T00:00:00Z" in core_xml
        assert "Timberwing Systems, an EPR, P.C. initiative" in core_xml
        assert "not an EPA grant program" in document_xml
    with zipfile.ZipFile(static_xlsx) as package:
        names = set(package.namelist())
        assert not any(name.startswith("xl/comments") for name in names)
        assert not any(b"<f" in package.read(name) for name in names if name.startswith("xl/worksheets/sheet") and name.endswith(".xml"))
        workbook_xml = package.read("xl/workbook.xml").decode("utf-8")
        assert all(name in workbook_xml for name in ("Funding", "Resources", "Community Examples"))
        core_xml = package.read("docProps/core.xml").decode("utf-8")
        assert "Timberwing Systems, an EPR, P.C. initiative" in core_xml
    sha256 = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    package_report = json.loads((downloads / f"RERC_Community_Explorer_QA_{package_date}.json").read_text(encoding="utf-8"))
    assert csv_row_count == package_report["records"]
    head_commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    assert package_report["status"] == "PASS"
    assert package_report["source_sha256"] == {
        "data.js": git_blob_sha256(head_commit, "data.js"),
        "case_studies.js": git_blob_sha256(head_commit, "case_studies.js"),
    }
    assert re.fullmatch(r"[0-9a-f]{40}", package_report["catalog_source_commit"])
    assert "source commit used to generate" in package_report["release_binding_note"]
    assert package_report["site_sha256"] == {
        name: git_blob_sha256(head_commit, name)
        for name in ("index.html", "styles.css", "rercie.css", "app.js", "planner.js", "ui-i18n.js", "deadline-utils.js", "site-config.js", "data.js", "case_studies.js", "maintenance/multistate_coverage.json", "favicon.svg", "vendor/jszip.min.js", "vendor/lucide.min.js", "assets/hero-outdoor.jpg", "assets/rerc-e-eagle.jpg", "README.md")
    }
    assert package_report["docx"]["sha256"] == sha256(static_docx)
    assert package_report["xlsx"]["sha256"] == sha256(static_xlsx)
    assert package_report["csv"]["sha256"] == sha256(static_csv)

    source_health = json.loads((ROOT / "case_studies.source_health.json").read_text(encoding="utf-8"))
    assert source_health["status"] == "PASS"
    assert source_health["unique_urls"] == len({case["source_url"] for case in cases})
    assert source_health["counts"]["hard_failure"] == 0
    assert source_health["counts"]["manual_review"] == 0
    assert sum(source_health["counts"].values()) == source_health["unique_urls"]
    assert source_health["counts"]["hard_failure"] == 0
    assert source_health["case_studies_sha256"] == canonical_text_sha256(ROOT / "case_studies.js")

    core = (ROOT / "rercie" / "rercie_core.py").read_text(encoding="utf-8")
    assert "call_openai_compatible" not in core
    assert "apiEndpoint" not in core and "apiModel" not in core
    assert "RERC-e is reviewing your notes with local Gemma" in core
    assert "rawModelProseExposed" in core
    assert "parse_verified_excerpts" in core
    launcher = (ROOT / "rercie" / "packaging" / "RERCieLauncher.cs").read_text(encoding="utf-8")
    assert "Read the Gemma Terms" in launcher
    assert "Apache License 2.0" not in launcher
    installer_script = (ROOT / "rercie" / "packaging" / "RERCie.iss").read_text(encoding="utf-8")
    assert '[InstallDelete]' not in installer_script
    assert 'Name: "{app}\\models"' in installer_script  # Uninstall cleanup remains intentional.
    assert '#define AppVersion "0.5.0"' in installer_script
    build_script = (ROOT / "rercie" / "build_installer.ps1").read_text(encoding="utf-8")
    assert '$Version = "0.5.0"' in build_script
    installer_manifest = json.loads(
        (ROOT / "rercie" / "packaging" / "installer_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert installer_manifest["package"]["version"] == EXPECTED_RERCIE_VERSION
    source_qa = json.loads((ROOT / "rercie" / "packaging" / "QA_EVIDENCE.json").read_text(encoding="utf-8"))
    assert source_qa["status"] == "SOURCE_PASS" and source_qa["evidence_stage"] == "source"
    assert source_qa["app_version"] == EXPECTED_RERCIE_VERSION
    assert source_qa["app_version"] == expected_app_version
    assert source_qa.get("historical") is not True
    assert source_qa["checks"]["package_integrity"]["status"] == "PENDING_BUILD"
    assert source_qa["release_binding"]["status"] == "PENDING_BUILD"
    live_catalog_qa = source_qa["checks"]["live_catalog"]
    assert live_catalog_qa["total_items"] == len(items) + len(cases)
    assert live_catalog_qa["funding_items"] == counts["funding"]
    assert live_catalog_qa["resource_items"] == counts["resources"]
    assert live_catalog_qa["case_study_items"] == len(cases)
    assert live_catalog_qa["case_study_unique_urls_checked"] == source_health["unique_urls"]
    assert live_catalog_qa["case_study_hard_failed_urls"] == source_health["counts"]["hard_failure"]
    assert live_catalog_qa["case_study_reachable_urls"] == source_health["counts"]["reachable"]
    assert live_catalog_qa["case_study_restricted_urls"] == source_health["counts"]["restricted_but_present"]
    assert live_catalog_qa["case_study_manual_review_urls"] == source_health["counts"]["manual_review"]
    local_report = json.loads((ROOT / "rercie" / "packaging" / "LOCAL_GEMMA_QA.json").read_text(encoding="utf-8"))
    assert local_report["status"] == "PASS"
    assert local_report["app_version"] == EXPECTED_RERCIE_VERSION
    assert local_report["app_version"] == expected_app_version
    assert local_report.get("historical") is not True
    assert local_report["model"] == "gemma-3-1b-it-Q4_K_M.gguf"
    assert local_report['source_normalized_sha256'] == git_blob_sha256(
        head_commit, 'rercie/rercie_core.py'
    )
    assert local_report["raw_model_prose_exposed"] is False
    assert local_report["evidence_scope"].startswith(("Package-bound", "Source-bound"))
    assert local_report["later_standalone_rerun"]["status"] == "PASS"
    assert source_qa["checks"]["local_generation"]["later_standalone_rerun_status"] == "PASS"
    assert not any("later standalone Gemma inference rerun was not" in item.lower() for item in source_qa["disclosed_limits"])

    captured_urls = []
    original_request_json = app.app.request_json
    original_env_value = app.app._local_env_value
    app.app._local_env_value = lambda _name: ""
    app.app.request_json = lambda url, **_kwargs: (
        captured_urls.append(url)
        or [
            ["NAME", "DP05_0001E", "DP03_0062E", "DP03_0128PE", "DP05_0018E", "state", "place"],
            ["Taos town, New Mexico", "6458", "47304", "13.7", "53.7", "35", "76200"],
        ]
    )
    try:
        try:
            app.app.fetch_census_community_profile("Taos", "New Mexico", "")
            raise AssertionError("Direct Census lookup accepted a missing API key.")
        except PermissionError:
            pass
        assert captured_urls == []
        keyed_profile = app.app.fetch_census_community_profile("Taos", "New Mexico", "CENSUS_QA_KEY")
    finally:
        app.app.request_json = original_request_json
        app.app._local_env_value = original_env_value
    assert keyed_profile["place"] == "Taos town, New Mexico"
    assert captured_urls and "key=CENSUS_QA_KEY" in captured_urls[0]
    profile = {"population": "1046", "source": "Test source"}
    draft_payload = {
        "community": "Test",
        "state": "Virginia",
        "projectTitle": "Trail",
        "projectSummary": "Improve a trail connection between the park and downtown.",
        "provider": "local",
        "usePublicData": False,
    }
    unsafe = "The town is eligible and will acquire land, hire a consultant, and secure every approval."
    assert app.app.grounding_issues(unsafe, draft_payload, profile)
    exact = "Improve a trail connection between the park and downtown."
    evidence = app.app.evidence_text(draft_payload, profile, "")
    verified = app.app.parse_verified_excerpts(json.dumps({"excerpts": [{"text": exact}]}), evidence)
    assert verified == [exact]
    paraphrased = app.app.parse_verified_excerpts(
        json.dumps({"excerpts": [{"text": "Build a trail from downtown to the park."}]}),
        evidence,
    )
    whitespace_changed = app.app.parse_verified_excerpts(
        json.dumps({"excerpts": [{"text": "Improve  a trail connection between the park and downtown."}]}),
        evidence,
    )
    assert paraphrased == []
    assert whitespace_changed == []
    scaffold = app.app.deterministic_scaffold(draft_payload, profile, verified)
    assert not app.app.grounding_issues(scaffold, draft_payload, profile, verified)
    original_selector = app.app.select_evidence_excerpts
    app.app.select_evidence_excerpts = lambda *_args, **_kwargs: [exact]
    try:
        built = app.app.build_draft(draft_payload)
    finally:
        app.app.select_evidence_excerpts = original_selector
    assert built["rawModelProseExposed"] is False
    assert built["evidenceExcerpts"] == [exact]
    assert exact in built["draft"]
    assert unsafe not in built["draft"]

    result = {
        "status": "PASS",
        "version": app.app.APP_VERSION,
        "counts": {**counts, "case_studies": len(cases), "public_total": len(items) + len(cases)},
        "check_groups": [
            "source_syntax",
            "catalog_integrity",
            "v2_site_contract",
            "planner_security_contract",
            "state_only_geography",
            "regional_coverage",
            "case_studies",
            "downloads",
            "rerc_e_0.5.0",
            "privacy_and_grounding",
        ],
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
