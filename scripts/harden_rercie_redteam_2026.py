#!/usr/bin/env python3
"""Apply independent red-team fixes to RERC-e 0.5.1."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    if text.count(old) != 1:
        raise ValueError(f"Expected one {label}, found {text.count(old)}")
    return text.replace(old, new, 1)


def update_core() -> None:
    path = ROOT / "rercie" / "rercie_core.py"
    text = path.read_text(encoding="utf-8")

    runtime_anchor = 'EXPECTED_ORIGIN = f"http://{EXPECTED_HOST}"\n'
    runtime_validation = runtime_anchor + '''

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
'''
    text = replace_once(text, runtime_anchor, runtime_validation, "loopback URL validation")

    old_selected = '''        ("Eligible users", record.get("eligible_users")),
        ("Project stage", record.get("project_stage")),
        ("Amount or support", record.get("amount_or_cost")),
        ("Match or cost", record.get("match_or_cost")),
        ("Deadline or availability", record.get("deadline_or_availability")),
        ("Summary", record.get("summary")),
        ("Official page", record.get("source_url")),
'''
    new_selected = '''        ("Eligible users", record.get("eligible_users")),
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
'''
    text = replace_once(text, old_selected, new_selected, "imported funding fields")

    old_roadmap = '''            if item.get("status"):
                line += f" (Status: {item['status']})"
            roadmap_lines.append(line)
'''
    new_roadmap = '''            if item.get("status"):
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
'''
    text = replace_once(text, old_roadmap, new_roadmap, "roadmap import details")

    old_consume = '''    try:
        size = STARTUP_HANDOFF_PATH.stat().st_size
        if size <= 0 or size > MAX_HANDOFF_BYTES:
            raise ValueError(f"The launcher plan must be no larger than {MAX_HANDOFF_BYTES // 1024} KB.")
        return handoff_to_form(validate_handoff_text(STARTUP_HANDOFF_PATH.read_bytes()))
    finally:
        try:
            STARTUP_HANDOFF_PATH.unlink()
        except OSError:
            pass
'''
    new_consume = '''    try:
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
'''
    text = replace_once(text, old_consume, new_consume, "startup handoff preservation")

    old_profile_url = '                "source_url": "https://henkelpress.github.io/rerc-grant-finder/",\n'
    new_profile_url = '''                "source_url": str(record.get("source_url") or (
                    "https://api.census.gov/data/2024/acs/acs5/profile.html"
                    if "ACS" in source else
                    "https://www.census.gov/data/datasets/2020/dec/2020-island-areas.html"
                )),
'''
    text = replace_once(text, old_profile_url, new_profile_url, "record-specific profile source")

    build_anchor = "def build_draft(payload: dict[str, Any]) -> dict[str, Any]:\n"
    profile_validator = '''def validate_supplied_profile(value: Any) -> dict[str, str]:
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


''' + build_anchor
    text = replace_once(text, build_anchor, profile_validator, "supplied profile validator")
    old_build_lookup = '''    validate_draft_context(payload)
    if payload.get("usePublicData"):
        profile_lookup = lookup_community_profile(
            str(payload.get("community") or ""),
            str(payload.get("state") or ""),
            str(payload.get("censusApiKey") or ""),
        )
    else:
        profile_lookup = {"profile": {}, "message": "Community lookup was turned off.", "status": "skipped"}
'''
    new_build_lookup = '''    validate_draft_context(payload)
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
'''
    text = replace_once(text, old_build_lookup, new_build_lookup, "imported profile drafting")

    text = text.replace("Verified excerpts selected from the supplied material:", "Exact excerpts selected from the supplied material (the underlying claims still require human review):")
    text = text.replace(
        'f"Gemma selected {len(excerpts)} exact evidence excerpt"',
        'f"Gemma selected {len(excerpts)} exact supplied excerpt"',
    )
    text = text.replace(
        'f"{\'s\' if len(excerpts) != 1 else \'\'}; RERC-e verified and placed them in a fixed outline."',
        'f"{\'s\' if len(excerpts) != 1 else \'\'}; RERC-e checked that they were copied exactly and placed them in a fixed outline. Review the underlying claims."',
    )

    text = text.replace('    let lastDraft="";\n', '    let lastDraft=""; let activePublicProfile={};\n')
    text = text.replace(
        'function renderProfile(profile,message,lookupStatus){ const box=',
        'function renderProfile(profile,message,lookupStatus){ activePublicProfile=profile&&typeof profile==="object"?profile:{}; const box=',
    )
    text = text.replace(
        'projectNotes:document.getElementById("projectNotes").value,usePublicData:',
        'projectNotes:document.getElementById("projectNotes").value,publicProfile:activePublicProfile,usePublicData:',
    )
    text = text.replace('<textarea id="projectNotes"></textarea>', '<textarea id="projectNotes" maxlength="100000"></textarea>')
    text = text.replace('<span id="workingTime">0 seconds</span>', '<span id="workingTime" aria-hidden="true">0 seconds</span>')

    old_files = '    document.getElementById("fileInput").addEventListener("change",async(event)=>{ const parts=[]; for(const file of event.target.files){ if(file.size>2000000){ setStatus(`${file.name} is too large. Use a text file under 2 MB.`,true); continue; } parts.push(`\\n--- File: ${file.name} ---\\n${await file.text()}`); } const notes=document.getElementById("projectNotes"); notes.value=`${notes.value}\\n${parts.join("\\n")}`.trim(); if(parts.length) setStatus(`Read ${parts.length} file(s).`); });\n'
    new_files = '''    document.getElementById("fileInput").addEventListener("change",async(event)=>{ const files=[...event.target.files]; const parts=[]; let total=0; if(files.length>10){setStatus("Add no more than 10 text files at a time.",true);event.target.value="";return;} for(const file of files){ if(file.size>512*1024){ setStatus(`${file.name} is too large. Use a text file under 512 KB.`,true); continue; } total+=file.size; if(total>2*1024*1024){setStatus("The selected files exceed the 2 MB combined limit.",true);break;} parts.push(`\\n--- File: ${file.name} ---\\n${await file.text()}`); } const notes=document.getElementById("projectNotes"); const combined=`${notes.value}\\n${parts.join("\\n")}`.trim(); if(combined.length>100000){setStatus("The notes and file text exceed the 100,000-character drafting limit. Use shorter excerpts.",true);return;} notes.value=combined; if(parts.length) setStatus(`Read ${parts.length} file(s).`); });
'''
    text = replace_once(text, old_files, new_files, "aligned file upload limits")

    old_runtime = '    async function checkRuntime(){ const badge=document.getElementById("runtime"); try{ const response=await apiFetch("/api/runtime"); const data=await response.json(); badge.textContent=data.ready?"Local model ready":"Local model is starting"; badge.className=data.ready?"runtime":"runtime offline"; }catch{ badge.textContent="Could not check local writer"; badge.className="runtime offline"; } }\n'
    new_runtime = '''    let runtimePoll=0;
    async function checkRuntime(){ const badge=document.getElementById("runtime"); try{ const response=await apiFetch("/api/runtime"); const data=await response.json(); badge.textContent=data.ready?"Local model ready":"Local model is starting"; badge.className=data.ready?"runtime":"runtime offline"; if(data.ready&&runtimePoll){clearInterval(runtimePoll);runtimePoll=0;} }catch{ badge.textContent="Could not check local writer"; badge.className="runtime offline"; } }
'''
    text = replace_once(text, old_runtime, new_runtime, "runtime polling")
    text = text.replace('    checkRuntime(); checkStartupPlan(); loadGrants()', '    checkRuntime(); runtimePoll=window.setInterval(checkRuntime,5000); checkStartupPlan(); loadGrants()')

    old_serve = '''def serve(host: str, port: int) -> int:
    if host not in {"127.0.0.1", "localhost"}:
        raise ValueError("RERC-e can run only on this computer.")
    if not SESSION_TOKEN:
'''
    new_serve = '''def serve(host: str, port: int) -> int:
    global EXPECTED_HOST, EXPECTED_ORIGIN
    if host not in {"127.0.0.1", "localhost"}:
        raise ValueError("RERC-e can run only on this computer.")
    browser_host = "127.0.0.1" if host == "localhost" else host
    EXPECTED_HOST = f"{browser_host}:{port}"
    EXPECTED_ORIGIN = f"http://{EXPECTED_HOST}"
    if not SESSION_TOKEN:
'''
    text = replace_once(text, old_serve, new_serve, "custom host authorization")

    smoke_anchor = '    no_leak_prompt = compose_prompt({"projectTitle": "Test", "censusApiKey": "CENSUS_API_KEY_SENTINEL"}, sample_profile, "")\n'
    smoke = '''    imported_profile_payload = {
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
''' + smoke_anchor
    text = replace_once(text, smoke_anchor, smoke, "red-team smoke checks")

    path.write_text(text, encoding="utf-8", newline="\n")


def update_public_site() -> None:
    path = ROOT / "index.html"
    text = path.read_text(encoding="utf-8")
    text = text.replace('<div class="scene-catalog" aria-label="Explorer catalog summary">', '<div class="scene-catalog" aria-label="Explorer catalog summary" aria-busy="true">')
    text = text.replace('<strong id="fundingCount">0</strong>', '<strong id="fundingCount">...</strong>')
    text = text.replace('<strong id="resourceCount">0</strong>', '<strong id="resourceCount">...</strong>')
    text = text.replace('<strong id="caseStudyCount">0</strong>', '<strong id="caseStudyCount">...</strong>')
    text = text.replace('Download RERC-e</a>', 'Download RERC-e for Windows</a>')
    path.write_text(text, encoding="utf-8", newline="\n")

    app = ROOT / "app.js"
    source = app.read_text(encoding="utf-8")
    source = replace_once(
        source,
        '  elements.caseStudyCount.textContent = caseStudies.length.toLocaleString();\n',
        '  elements.caseStudyCount.textContent = caseStudies.length.toLocaleString();\n  document.querySelector(".scene-catalog")?.setAttribute("aria-busy", "false");\n',
        "catalog loading completion",
    )
    app.write_text(source, encoding="utf-8", newline="\n")

    css = ROOT / "styles.css"
    styles = css.read_text(encoding="utf-8")
    marker = "@media (max-width: 680px) {"
    if "scroll-padding-top: 124px" not in styles:
        styles = styles.replace(marker, marker + "\n  html { scroll-padding-top: 124px; }", 1)
    css.write_text(styles, encoding="utf-8", newline="\n")


def main() -> int:
    update_core()
    update_public_site()
    print("Applied RERC-e independent red-team fixes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
