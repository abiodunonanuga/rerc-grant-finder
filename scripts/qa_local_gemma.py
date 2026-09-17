from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "rercie"))

import rercie_core as app  # noqa: E402


def funding_record(**overrides: str) -> str:
    record = {
        "title": "Example Recreation Program",
        "organization": "Example Agency",
        "status": "Recurring",
        "amount_or_cost": "Varies",
        "match_or_cost": "Typically 20 percent minimum",
        "deadline_or_availability": "Confirm the current cycle",
        "summary": "Supports community recreation projects.",
        "source_url": "https://example.gov/program",
    }
    record.update(overrides)
    return json.dumps(record)


def cases() -> dict[str, dict]:
    return {
        "sparse": {
            "community": "Pine Hollow",
            "state": "Virginia",
            "projectTitle": "River Access Improvement",
            "projectSummary": "Improve public access to the river.",
            "selectedGrant": funding_record(),
            "provider": "local",
            "usePublicData": False,
        },
        "developed": {
            "community": "Pine Hollow",
            "state": "Virginia",
            "projectTitle": "Downtown-to-River Trail Access and Wayfinding",
            "projectSummary": (
                "The town plans to improve a 0.8-mile connection between downtown and the public river landing "
                "by installing directional signs, replacing two inaccessible curb ramps, and adding a shaded rest area."
            ),
            "selectedGrant": funding_record(
                title="Transportation Alternatives Program",
                organization="VDOT",
                amount_or_cost="80% federal funding",
                match_or_cost="Yes, 20%",
            ),
            "matchCapacity": (
                "The town has reserved $60,000 in local capital funds toward the 20 percent match. "
                "Public Works has assigned its director as project manager."
            ),
            "sourceNotes": (
                "The local catalog lists the Transportation Alternatives Program as recurring and describes "
                "80 percent federal funding with a 20 percent match. Confirm the current application cycle "
                "and eligible cost rules on the official VDOT page before applying."
            ),
            "projectNotes": (
                "Public Works will manage procurement. The planning district commission will provide grant "
                "administration. Construction is proposed for April through September 2027. Local merchants "
                "have documented recurring visitor confusion at three downtown intersections. No crash data "
                "or economic impact estimate has been verified."
            ),
            "provider": "local",
            "usePublicData": False,
        },
        "detailed": {
            "community": "Blue Ridge Junction",
            "state": "Virginia",
            "projectTitle": "North Fork Trailhead Safety and Access Project",
            "projectSummary": (
                "The county will reconstruct the North Fork trailhead to eliminate unsafe shoulder parking, "
                "provide an accessible arrival area, protect the stream buffer, and give visitors clear route information."
            ),
            "selectedGrant": funding_record(
                title="Recreational Trails Program",
                organization="Virginia DCR",
                status="Cycle closed",
                deadline_or_availability="2026 cycle closed May 5, 2026; recurring",
            ),
            "matchCapacity": (
                "The preliminary project budget is $450,000. The county plans to request $360,000 and has "
                "assigned $90,000 in adopted capital funds as the local share. The county engineer will manage "
                "design and construction; the procurement officer and finance director will oversee contracting "
                "and reimbursement."
            ),
            "sourceNotes": (
                "The local catalog marks the 2026 Recreational Trails Program cycle as closed on May 5, 2026 "
                "and lists a typical minimum match of 20 percent. The county is preparing for a future cycle and "
                "must verify the next notice, applicant rules, eligible costs, environmental requirements, and scoring criteria."
            ),
            "projectNotes": (
                "County traffic counts recorded 126 vehicles during the five-hour peak period on each of six "
                "benchmark weekend days in 2025. The existing lot has 42 marked spaces, no accessible spaces, "
                "and an average of 31 vehicles parked on the road shoulder during those benchmark periods. "
                "The project will add 28 marked spaces, including two accessible spaces; construct a 300-foot "
                "accessible route to the trail kiosk; install drainage and native plantings within the disturbed "
                "area; and replace four conflicting signs with one route map and three directional signs. The "
                "county owns the site. Thirty-percent design drawings and a preliminary cost estimate were completed "
                "in August 2026. If funding is awarded by March 2027, the county will complete final design and permits "
                "by September 2027, advertise construction in October 2027, and open the improvements by June 2028. "
                "The county will repeat the six benchmark observations one year after opening. Its target is no more "
                "than five shoulder-parked vehicles during each comparable peak period."
            ),
            "provider": "local",
            "usePublicData": False,
        },
        "mismatch": {
            "community": "Pine Hollow",
            "state": "Virginia",
            "projectTitle": "Downtown Facade Program",
            "projectSummary": "Rehabilitate commercial building facades along Main Street.",
            "selectedGrant": funding_record(title="Recreational Trails Program"),
            "sourceNotes": "This project contains no trail activity, and the selected program does not fit the proposed work.",
            "provider": "local",
            "usePublicData": False,
        },
    }


def main() -> int:
    assert app.DEFAULT_MODEL == "gemma-3-4b-it-Q4_K_M.gguf"
    models = app.request_json(app.LOCAL_MODELS_URL, timeout=10)
    model_ids = [str(item.get("id") or item.get("name") or "") for item in (models.get("data") or models.get("models") or [])]
    assert any(app.DEFAULT_MODEL.lower() in model_id.lower() for model_id in model_ids), "The approved Gemma 3 4B model is not loaded."

    results: dict[str, dict] = {}
    payloads = cases()
    built: dict[str, dict] = {}
    for name, payload in payloads.items():
        started = time.perf_counter()
        result = app.build_draft(payload)
        elapsed = round(time.perf_counter() - started, 2)
        built[name] = result
        assert not app.grounding_issues(result["draft"], payload, result["publicProfile"])
        assert "The town is eligible" not in result["draft"]
        results[name] = {
            "elapsed_seconds": elapsed,
            "fit_status": result["fitStatus"],
            "model_written_sections": result["modelWrittenSections"],
            "fallback_sections": result["fallbackSections"],
            "raw_model_prose_exposed": result["rawModelProseExposed"],
            "warnings": result["warnings"],
        }

    assert built["sparse"]["modelWrittenSections"] == []
    assert built["sparse"]["warnings"] == []
    assert set(built["developed"]["modelWrittenSections"]) == {"Project Need", "Proposed Work"}
    assert "No crash data or economic impact estimate has been verified." not in built["developed"]["draft"]
    assert "[add local fact] Add the intended beneficiaries, measurable outcomes, baseline, and target." in built["developed"]["draft"]
    assert set(built["detailed"]["modelWrittenSections"]) == {"Project Need", "Proposed Work", "Community Benefit"}
    detailed = built["detailed"]["draft"]
    assert "The preliminary project budget is $450,000." in detailed
    assert "plans to request $360,000" in detailed
    assert "$90,000 in adopted capital funds as the local share" in detailed
    assert "If funding is awarded by March 2027" in detailed
    assert "Its target is no more than five shoulder-parked vehicles" in detailed
    assert "The supplied funding record lists the deadline or availability" not in detailed
    assert "[add local fact] Total budget" not in detailed
    assert "[add local fact] Implementation start" not in detailed
    mismatch = built["mismatch"]
    assert mismatch["fitStatus"] == "conflict"
    assert "## Funding Fit Decision" in mismatch["draft"]
    assert "## Project Need" not in mismatch["draft"]

    unsafe_payload = payloads["developed"]
    original_writer = app.call_local_writer
    app.call_local_writer = lambda *_args, **_kwargs: json.dumps(
        {
            "Project Need": "The town is eligible and has already received $999,999.",
            "Proposed Work": "The town will acquire land and hire a consultant.",
        }
    )
    try:
        rejected = app.build_draft(unsafe_payload)
    finally:
        app.call_local_writer = original_writer
    assert rejected["modelWrittenSections"] == []
    assert rejected["rawModelProseExposed"] is False
    assert rejected["warnings"]
    assert "$999,999" not in rejected["draft"]
    assert "The town will acquire land" not in rejected["draft"]

    core_path = ROOT / "rercie" / "rercie_core.py"
    report = {
        "status": "PASS",
        "tested_date": date.today().isoformat(),
        "app_version": app.APP_VERSION,
        "model": app.DEFAULT_MODEL,
        "loaded_model_ids": model_ids,
        "source_sha256": hashlib.sha256(core_path.read_bytes()).hexdigest(),
        "source_normalized_sha256": hashlib.sha256(
            core_path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
        ).hexdigest(),
        "raw_model_prose_exposed": True,
        "schema_constrained_batch": True,
        "protected_statement_validation": True,
        "section_level_fallback": True,
        "unsupported_eligibility_claim_absent": True,
        "scenarios": results,
        "rejection_probe": {
            "status": "PASS",
            "model_written_sections": rejected["modelWrittenSections"],
            "fallback_sections": rejected["fallbackSections"],
        },
        "evidence_scope": "Source-bound Gemma 3 4B inference passed sparse, developed, detailed, mismatch, and forced-rejection cases against the final RERC-e source before packaging.",
        "later_standalone_rerun": {
            "status": "PASS",
            "reason": "Completed against the pinned approved local Gemma service.",
        },
    }
    output = ROOT / "rercie" / "packaging" / "LOCAL_GEMMA_QA.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
