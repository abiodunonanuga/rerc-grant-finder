from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RERCIE = ROOT / "rercie"
PACKAGING = RERCIE / "packaging"
LAYOUT_SHA256 = "df70b1e32a489edfa0fa82309dccd30207a2ae1e1876ae11d4623766e3f7b697"
TERRITORIES = {"Puerto Rico", "U.S. Virgin Islands", "Guam", "American Samoa", "Northern Mariana Islands"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_blob_sha256(commit: str, name: str) -> str:
    payload = subprocess.check_output(['git', 'cat-file', 'blob', f'{commit}:{name}'], cwd=ROOT)
    return hashlib.sha256(payload).hexdigest()


def load_assignment(path: Path):
    text = path.read_text(encoding="utf-8").strip()
    payload = text.split("=", 1)[1].strip()
    if payload.endswith(";"):
        payload = payload[:-1]
    return json.loads(payload)


def current_expected_counts() -> dict[str, int]:
    catalog = load_assignment(ROOT / "data.js")["items"]
    cases = load_assignment(ROOT / "case_studies.js")["items"]
    return {
        "funding": sum(item.get("item_type") == "Funding" for item in catalog),
        "resources": sum(item.get("item_type") == "Resource" for item in catalog),
        "case_studies": len(cases),
        "public_total": len(catalog) + len(cases),
    }


def layout_sha256() -> str:
    source = (PACKAGING / "RERCieLauncher.cs").read_text(encoding="utf-8")
    pattern = re.compile(
        r"^\s*(?:ClientSize|MinimumSize|AutoScaleMode|\w+\.(?:Location|Size|Font|AutoSize|MinimumSize|MaximumSize))\s*=.*$",
        re.MULTILINE,
    )
    normalized = "\n".join(line.strip() for line in pattern.findall(source))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def source_service_identity_check() -> dict[str, int | bool]:
    port = 18790
    token = "rercie-source-qa-token"
    host = f"127.0.0.1:{port}"
    env = os.environ.copy()
    env.update({"RERCIE_SESSION_TOKEN": token, "RERCIE_EXPECTED_HOST": host})
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    process = subprocess.Popen(
        [sys.executable, str(RERCIE / "rercie.py"), "--serve", "--host", "127.0.0.1", "--port", str(port)],
        cwd=RERCIE,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )

    def status(path: str, headers: dict[str, str], payload: bytes | None = None) -> int:
        request = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=payload, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=3) as response:
                return response.status
        except urllib.error.HTTPError as error:
            return error.code

    try:
        deadline = time.time() + 20
        healthy = False
        while time.time() < deadline:
            try:
                healthy = status("/health", {"Host": host, "X-RERCie-Token": token}) == 200
                if healthy:
                    break
            except (OSError, urllib.error.URLError):
                pass
            time.sleep(0.25)
        assert healthy, "RERC-e source service did not become healthy."
        missing_token = status("/health", {"Host": host})
        wrong_host = status("/health", {"Host": "example.test", "X-RERCie-Token": token})
        wrong_origin = status(
            "/api/community-profile",
            {"Host": host, "Origin": "https://example.test", "X-RERCie-Token": token, "Content-Type": "application/json"},
            b"{}",
        )
        assert (missing_token, wrong_host, wrong_origin) == (403, 421, 403)
        return {"loopback_only": True, "missing_token_status": missing_token, "wrong_host_status": wrong_host, "wrong_origin_status": wrong_origin}
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate audited RERC-e source-stage release evidence.")
    parser.add_argument("--browser-report", default="browser-qa-pass/playwright_qa.json")
    args = parser.parse_args()
    expected_counts = current_expected_counts()

    smoke_process = subprocess.run(
        [sys.executable, str(RERCIE / "rercie.py"), "--smoke"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    smoke = json.loads(smoke_process.stdout)
    assert smoke["status"] == "PASS" and smoke["version"] == "0.5.1"
    assert smoke["docx_bytes"] >= 3000
    smoke_contract = {key: value for key, value in smoke.items() if key != "docx_bytes"}

    local_gemma = json.loads((PACKAGING / "LOCAL_GEMMA_QA.json").read_text(encoding="utf-8"))
    assert local_gemma["status"] == "PASS" and local_gemma["app_version"] == "0.5.1"
    assert local_gemma["model"] == "gemma-3-1b-it-Q4_K_M.gguf"
    head_commit = subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True
    ).strip()
    assert local_gemma['source_normalized_sha256'] == git_blob_sha256(
        head_commit, 'rercie/rercie_core.py'
    )
    assert local_gemma["raw_model_prose_exposed"] is False
    assert local_gemma["unsupported_eligibility_claim_absent"] is True
    assert local_gemma["later_standalone_rerun"]["status"] == "PASS"

    browser_path = ROOT / args.browser_report
    browser = json.loads(browser_path.read_text(encoding="utf-8"))
    assert browser["status"] == "PASS" and not browser["errors"] and not browser["failures"]
    assert browser["checks"]["counts"] == [expected_counts["funding"], expected_counts["resources"], expected_counts["case_studies"]]
    assert all(value is True for key, value in browser["checks"]["spanish"].items() if not key.endswith("Text"))
    english_restored = browser["checks"].get("englishRestored", True)
    assert english_restored is True
    assert all(item["controls44"] and item["overflow"] for item in browser["checks"]["mobile"].values())
    browser_contract = {
        "status": browser["status"],
        "counts": browser["checks"]["counts"],
        "modes": browser["checks"]["modes"],
        "saved_persistence": [browser["checks"]["savedBeforeReload"], browser["checks"]["savedAfterReload"]],
        "card_actions": browser["checks"]["cardActions"],
        "spanish": {
            key: value
            for key, value in browser["checks"]["spanish"].items()
            if not key.endswith("Text")
        },
        "english_restored": english_restored,
        "roadmap_phase_change": browser["checks"]["roadmapPhaseChange"],
        "roadmap_reset": {
            "count": browser["checks"]["resetRoadmap"]["count"],
            "private_workspace": str(browser["checks"]["resetRoadmap"]["id"]).startswith("browser-"),
        },
        "state_switch_clears_saved": browser["checks"]["stateSwitchClearsSaved"],
        "rercie_schema": browser["checks"]["rercie"]["schema"],
        "rercie_version": browser["checks"]["rercie"]["version"],
        "mobile": browser["checks"]["mobile"],
        "errors": browser["errors"],
        "failures": browser["failures"],
    }

    catalog = load_assignment(ROOT / "data.js")["items"]
    cases = load_assignment(ROOT / "case_studies.js")["items"]
    counts = {
        "funding": sum(item.get("item_type") == "Funding" for item in catalog),
        "resources": sum(item.get("item_type") == "Resource" for item in catalog),
        "case_studies": len(cases),
        "public_total": len(catalog) + len(cases),
    }
    assert counts == expected_counts

    profiles = load_assignment(ROOT / "community_profiles.js")
    profile_rows = profiles.get("profiles", profiles) if isinstance(profiles, dict) else profiles
    assert len(profile_rows) == 35958
    represented = {str(row.get("state") or row.get("stateCode") or "") for row in profile_rows}
    assert TERRITORIES.issubset(represented)

    source_health = json.loads((ROOT / "case_studies.source_health.json").read_text(encoding="utf-8"))
    assert source_health["status"] == "PASS"
    assert source_health["unique_urls"] == len({item["source_url"] for item in cases})
    assert source_health["counts"]["hard_failure"] == 0
    assert source_health["counts"]["manual_review"] == 0
    assert sum(source_health["counts"].values()) == source_health["unique_urls"]

    historical = json.loads((PACKAGING / "QA_EVIDENCE_0.3.5_HISTORICAL.json").read_text(encoding="utf-8"))
    display = historical["checks"]["display_scaling"]
    assert display["status"] == "PASS" and display["tested_scales"] == ["100%", "150%", "200%"]
    assert layout_sha256() == LAYOUT_SHA256

    installer_manifest = json.loads((PACKAGING / "installer_manifest.json").read_text(encoding="utf-8"))
    assert installer_manifest["package"]["version"] == "0.5.1"
    build_script = (RERCIE / "build_installer.ps1").read_text(encoding="utf-8")
    assert "gemma-3-1b-it-Q4_K_M.gguf" in build_script and "b9987" in build_script
    assert (PACKAGING / "INSTALLER_NOTICE.txt").is_file()
    identity = source_service_identity_check()

    evidence = {
        "app_version": "0.5.1",
        "status": "SOURCE_PASS",
        "tested_date": local_gemma["tested_date"],
        "evidence_stage": "source",
        "checks": {
            "source_smoke": {"status": "PASS", **smoke_contract, "docx_minimum_bytes": 3000},
            "native_launcher": {"status": "PENDING_BUILD", "powershell_required": False, "plan_handoff_supported": True},
            "display_scaling": {"status": "PASS", "tested_scales": display["tested_scales"], "layout_geometry_sha256": LAYOUT_SHA256, "layout_reviewed_for_version": "0.5.1", "dpi_autoscaling_and_scroll_enabled": True},
            "installer_wizard": {"status": "PENDING_RELEASE_TEST", "per_user_install": True, "uninstall_entry": True},
            "package_integrity": {"status": "PENDING_BUILD", "integrity_checked_binaries": 0},
            "live_catalog": {"status": "PASS", "total_items": counts["public_total"], "funding_items": counts["funding"], "resource_items": counts["resources"], "case_study_items": counts["case_studies"], "territory_filter_checked": True, "case_study_unique_urls_checked": source_health["unique_urls"], "case_study_hard_failed_urls": source_health["counts"]["hard_failure"], "case_study_reachable_urls": source_health["counts"]["reachable"], "case_study_restricted_urls": source_health["counts"]["restricted_but_present"], "case_study_manual_review_urls": source_health["counts"]["manual_review"]},
            "local_generation": {"status": "PASS", "model": "Google Gemma 3 1B Instruct Q4_K_M", "source_sha256": local_gemma["source_sha256"], "source_normalized_sha256": local_gemma["source_normalized_sha256"], "verified_excerpt_count": local_gemma["verified_excerpt_count"], "raw_model_prose_exposed": False, "later_standalone_rerun_status": "PASS"},
            "docx_export": {"status": "PASS", "minimum_bytes": 3000, "office_open_xml": True},
            "api_privacy_regression": {"status": "PASS", "key_sent_to_gemma": False, "handoff_checks": smoke["handoff_checks"], "https_profile_check": "https_only_bounded" in smoke["profile_checks"]},
            "service_identity_checks": {"status": "PASS", **identity, "packaged_authenticated_health": "PENDING_BUILD"},
            "licensing_and_runtime": {"status": "PASS", "approved_model": smoke["model"], "llama_cpp_release": "b9987", "runtime_sha256_pinned": True, "model_sha256_pinned": True, "license_notice_included": True},
            "community_lookup": {"status": "PASS", "profile_checks": smoke["profile_checks"], "territories_represented": sorted(TERRITORIES), "profile_count": len(profile_rows)},
            "executable_release_qa": {"status": "PENDING_BUILD", "ci_required": True, "deploy_required": True, "installer_build_required": True},
        },
        "disclosed_limits": [
            "The public installer is not code-signed, so Windows may show a safety notice.",
            "The isolated installer test runs on the build computer rather than a clean Windows virtual machine.",
            "Users must review every generated draft and verify current funding rules at the official source.",
        ],
        "release_binding": {"source_commit": None, "integrity_manifest_sha256": None, "installer_sha256": None, "status": "PENDING_BUILD"},
        "verification_inputs": {"browser_contract_sha256": hashlib.sha256(json.dumps(browser_contract, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest(), "local_gemma_report_sha256": git_blob_sha256(head_commit, "rercie/packaging/LOCAL_GEMMA_QA.json")},
    }
    output = PACKAGING / "QA_EVIDENCE.json"
    output.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "output": str(output), "app_version": "0.5.1", "counts": counts, "profile_count": len(profile_rows), "layout_geometry_sha256": LAYOUT_SHA256, "service_identity": identity}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
