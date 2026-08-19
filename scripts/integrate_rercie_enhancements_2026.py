#!/usr/bin/env python3
"""Apply the reviewed RERC-e 0.5.1 quality and mascot enhancements."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    if text.count(old) != 1:
        raise ValueError(f"Expected one {label} block, found {text.count(old)}")
    return text.replace(old, new, 1)


def update_core() -> None:
    path = ROOT / "rercie" / "rercie_core.py"
    text = path.read_text(encoding="utf-8")
    text = replace_once(text, "import zipfile\n", "import zipfile\nimport xml.etree.ElementTree as ET\n", "ElementTree import")

    old_lookup = '''    try:
        profile = fetch_public_community_profile(community, state)
    except Exception:
        if not key_provided:
            return {
                "profile": {},
                "message": "No public profile match was available. Add a Census API key for this lookup, or check the spelling and state for your community.",
                "status": "key_required",
            }
        profile = {}
'''
    new_lookup = '''    public_profile_unavailable = False
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
'''
    text = replace_once(text, old_lookup, new_lookup, "community lookup exception")

    old_funding = '''    fields = (
        ("Program", record.get("title") or record.get("program")),
        ("Organization", record.get("organization") or record.get("agency")),
        ("Description", record.get("description")),
        ("Best for", record.get("best_for") or record.get("bestFor")),
        ("Official page", record.get("url") or record.get("source_url")),
    )
'''
    new_funding = '''    fields = (
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
'''
    text = replace_once(text, old_funding, new_funding, "funding record fields")

    build_anchor = "def build_draft(payload: dict[str, Any]) -> dict[str, Any]:\n"
    validation = '''DRAFT_FIELD_LIMITS = {
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


''' + build_anchor
    text = replace_once(text, build_anchor, validation, "draft validation function")
    text = replace_once(
        text,
        build_anchor + "    if payload.get(\"usePublicData\"):\n",
        build_anchor + "    validate_draft_context(payload)\n    if payload.get(\"usePublicData\"):\n",
        "draft validation call",
    )

    old_xml = '''def _paragraph_xml(text: str, style: str | None = None) -> str:
    properties = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    safe = escape(text)
    return f'<w:p>{properties}<w:r><w:t xml:space="preserve">{safe}</w:t></w:r></w:p>'
'''
    new_xml = '''XML_FORBIDDEN_CONTROLS = re.compile(r"[\\x00-\\x08\\x0B\\x0C\\x0E-\\x1F]")


def _xml_text(value: Any) -> str:
    return XML_FORBIDDEN_CONTROLS.sub("", str(value or ""))


def _paragraph_xml(text: str, style: str | None = None) -> str:
    properties = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    safe = escape(_xml_text(text))
    return f'<w:p>{properties}<w:r><w:t xml:space="preserve">{safe}</w:t></w:r></w:p>'
'''
    text = replace_once(text, old_xml, new_xml, "DOCX XML sanitizer")
    text = text.replace("<dc:title>{escape(title)}</dc:title>", "<dc:title>{escape(_xml_text(title))}</dc:title>")

    text = replace_once(
        text,
        "    header .mascot { width:120px; height:168px; object-fit:contain; border:4px solid rgba(255,255,255,.82); border-radius:6px; background:#fff; }\n",
        '''    header .mascot-stage { position:relative; width:120px; height:168px; justify-self:end; transform-origin:50% 90%; animation:rercie-bob 4s ease-in-out infinite; }
    header .mascot { display:block; width:100%; height:100%; object-fit:contain; border:4px solid rgba(255,255,255,.82); border-radius:6px; background:#fff; }
    header .mascot-wing { position:absolute; z-index:2; top:39px; right:-9px; width:42px; height:58px; transform-origin:20% 82%; animation:rercie-wave 2.4s ease-in-out infinite; border:2px solid #4e3927; border-radius:75% 20% 70% 30%; background:#7a5738; box-shadow:inset -8px -6px 0 rgba(48,31,20,.18); }
    header .mascot-wing::before,header .mascot-wing::after { content:""; position:absolute; right:3px; width:28px; height:11px; border-radius:70% 30% 70% 30%; background:#9a7049; transform:rotate(16deg); }
    header .mascot-wing::before { top:12px; } header .mascot-wing::after { top:29px; right:1px; }
    @keyframes rercie-bob { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-4px)} }
    @keyframes rercie-wave { 0%,100%{transform:rotate(7deg)} 18%{transform:rotate(-24deg)} 34%{transform:rotate(12deg)} 50%{transform:rotate(-18deg)} 68%{transform:rotate(7deg)} }
''',
        "embedded mascot animation CSS",
    )
    text = text.replace(
        "header .welcome { grid-template-columns:minmax(0,1fr) 88px; gap:12px; } header .mascot { width:88px; height:124px; }",
        "header .welcome { grid-template-columns:minmax(0,1fr) 88px; gap:12px; } header .mascot-stage { width:88px; height:124px; }",
    )
    text = replace_once(
        text,
        "    @media (max-width:560px) { header .brand,.engine { grid-template-columns:1fr; display:grid; }",
        "    @media (prefers-reduced-motion:reduce) { header .mascot-stage,header .mascot-wing { animation:none !important; } }\n    @media (max-width:560px) { header .brand,.engine { grid-template-columns:1fr; display:grid; }",
        "embedded reduced motion",
    )
    text = replace_once(
        text,
        '<img class="mascot" src="/assets/rerc-e-eagle.jpg" alt="RERC-e, a bald eagle field guide holding a notebook">',
        '<div class="mascot-stage"><img class="mascot" src="/assets/rerc-e-eagle.jpg" alt="RERC-e, a bald eagle field guide holding a notebook"><span class="mascot-wing" aria-hidden="true"></span></div>',
        "embedded mascot markup",
    )
    text = text.replace('<input id="community" placeholder="Example: Taos">', '<input id="community" required aria-required="true" maxlength="200" placeholder="Example: Taos">')
    text = text.replace('<select id="state"></select>', '<select id="state" required aria-required="true"></select>')
    text = text.replace('<input id="projectTitle" placeholder="Example: Downtown trail connection">', '<input id="projectTitle" required aria-required="true" maxlength="300" placeholder="Example: Downtown trail connection">')
    text = text.replace('<textarea id="projectSummary" class="small"></textarea>', '<textarea id="projectSummary" class="small" maxlength="5000"></textarea>')

    text = text.replace('if(!profile[key])return;', 'if(profile[key]===undefined||profile[key]===null||String(profile[key]).trim()==="")return;')
    collect_anchor = '    function collectPayload(){ return {community:document.getElementById("community").value,state:stateSelect.value,projectTitle:document.getElementById("projectTitle").value,projectSummary:document.getElementById("projectSummary").value,selectedGrant:document.getElementById("selectedGrant").value,matchCapacity:document.getElementById("matchCapacity").value,sourceNotes:document.getElementById("sourceNotes").value,projectNotes:document.getElementById("projectNotes").value,usePublicData:document.getElementById("usePublicData").checked,provider:document.getElementById("provider").value,model:"gemma-3-1b-it-Q4_K_M.gguf",censusApiKey:document.getElementById("censusApiKey").value}; }\n'
    validation_js = collect_anchor + '''    function validateDraftInputs(){ const required=[["community","community"],["state","state or territory"],["projectTitle","project title"]]; for(const [id,label] of required){ const control=document.getElementById(id); if(!control.value.trim()){ setStatus(`Add the ${label} before creating a draft.`,true); control.focus(); return false; } } const hasContext=["projectSummary","projectNotes","selectedGrant"].some((id)=>document.getElementById(id).value.trim()); if(!hasContext){ setStatus("Add a project summary, imported project notes, or funding details before creating a draft.",true); document.getElementById("projectSummary").focus(); return false; } return true; }
'''
    text = replace_once(text, collect_anchor, validation_js, "client draft validation")

    old_load = '    async function loadGrants(){ setStatus("Loading the public funding list..."); const response=await apiFetch("/api/grants"); if(!response.ok) throw new Error((await response.json()).error||"The list could not be loaded."); const data=await response.json(); const select=document.getElementById("grantSelect"); select.innerHTML=\'<option value="">Choose a funding match</option>\'; data.grants.forEach((grant,index)=>{ const option=document.createElement("option"); option.value=String(index); option.textContent=`${grant.title||grant.program||"Untitled"} - ${grant.organization||grant.agency||"Organization not listed"}`; option.dataset.grant=JSON.stringify(grant,null,2); select.appendChild(option); }); setStatus(`Loaded ${data.grants.length} funding options. Updated ${data.updated||"date not listed"}.`); }\n'
    new_load = '''    async function loadGrants(){ const button=document.getElementById("loadGrants"); button.disabled=true; setStatus("Loading the public funding list..."); try{ const response=await apiFetch("/api/grants"); const data=await response.json(); if(!response.ok) throw new Error(data.error||"The list could not be loaded."); const select=document.getElementById("grantSelect"); select.replaceChildren(); const placeholder=document.createElement("option"); placeholder.value=""; placeholder.textContent="Choose a funding match"; select.appendChild(placeholder); data.grants.forEach((grant,index)=>{ const option=document.createElement("option"); option.value=String(index); option.textContent=`${grant.title||grant.program||"Untitled"} - ${grant.organization||grant.agency||"Organization not listed"}`; option.dataset.grant=JSON.stringify(grant,null,2); select.appendChild(option); }); setStatus(`Loaded ${data.grants.length} funding options. Updated ${data.updated||"date not listed"}.`); }finally{ button.disabled=false; } }
'''
    text = replace_once(text, old_load, new_load, "funding list loading")
    text = text.replace(
        'document.getElementById("draftButton").addEventListener("click",async()=>{ const button=document.getElementById("draftButton"); button.disabled=true;',
        'document.getElementById("draftButton").addEventListener("click",async()=>{ if(!validateDraftInputs())return; const button=document.getElementById("draftButton"); button.disabled=true;',
    )
    old_docx = '    document.getElementById("downloadDocx").addEventListener("click",async()=>{ if(!lastDraft){setStatus("Create a draft first.",true);return;} setStatus("Building the Word file..."); const response=await apiFetch("/api/export-docx",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({draft:lastDraft,title:document.getElementById("projectTitle").value||"RERC-e Draft"})}); if(!response.ok){setStatus("The Word file could not be created.",true);return;} downloadBlob(await response.blob(),draftFilename("docx")); setStatus("Word file ready."); });\n'
    new_docx = '''    document.getElementById("downloadDocx").addEventListener("click",async()=>{ if(!lastDraft){setStatus("Create a draft first.",true);return;} const button=document.getElementById("downloadDocx"); button.disabled=true; setStatus("Building the Word file..."); try{ const response=await apiFetch("/api/export-docx",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({draft:lastDraft,title:document.getElementById("projectTitle").value||"RERC-e Draft"})}); if(!response.ok){ const data=await response.json().catch(()=>({})); throw new Error(data.error||"The Word file could not be created."); } downloadBlob(await response.blob(),draftFilename("docx")); setStatus("Word file ready."); }catch(error){setStatus("Word export failed: "+error.message,true);}finally{button.disabled=false;} });
'''
    text = replace_once(text, old_docx, new_docx, "Word export handling")
    old_copy = '    document.getElementById("copyDraft").addEventListener("click",async()=>{ if(!lastDraft){setStatus("Create a draft first.",true);return;} await navigator.clipboard.writeText(lastDraft); setStatus("Draft copied."); });\n'
    new_copy = '''    document.getElementById("copyDraft").addEventListener("click",async()=>{ if(!lastDraft){setStatus("Create a draft first.",true);return;} try{ if(!navigator.clipboard||!navigator.clipboard.writeText)throw new Error("Clipboard access is unavailable"); await navigator.clipboard.writeText(lastDraft); setStatus("Draft copied."); }catch{ setStatus("Copy is unavailable in this browser. Select the draft text and copy it manually.",true); output.focus(); const selection=window.getSelection(); const range=document.createRange(); range.selectNodeContents(output); selection.removeAllRanges(); selection.addRange(range); } });
'''
    text = replace_once(text, old_copy, new_copy, "copy handling")

    text = text.replace('        malformed_no_key = lookup_community_profile("Damascus", "Virginia", "")\n        assert malformed_no_key["status"] == "key_required"', '        malformed_no_key = lookup_community_profile("Damascus", "Virginia", "")\n        assert malformed_no_key["status"] == "unavailable"')
    smoke_anchor = '    sample = {"community":"Damascus","state":"Virginia","projectTitle":"Trailhead Wayfinding","projectSummary":"Improve access from downtown to nearby trails.","selectedGrant":"Sample funding record","usePublicData":False,"provider":"fallback"}\n'
    smoke_add = '''    rich_funding = _funding_record_text(json.dumps({
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
''' + smoke_anchor
    text = replace_once(text, smoke_anchor, smoke_add, "new smoke checks")
    text = text.replace('    docx = build_docx(result["draft"], "Smoke Test")', '    docx = build_docx(result["draft"] + "\\x01", "Smoke Test\\x02")')
    text = text.replace('        assert "word/document.xml" in package.namelist()', '        assert "word/document.xml" in package.namelist()\n        document_xml = package.read("word/document.xml")\n        ET.fromstring(document_xml)\n        assert b"\\x01" not in document_xml and b"\\x02" not in package.read("docProps/core.xml")')

    path.write_text(text, encoding="utf-8", newline="\n")


def update_public_mascot() -> None:
    index = ROOT / "index.html"
    text = index.read_text(encoding="utf-8")
    text = replace_once(
        text,
        '    <img class="rercie-mascot" src="assets/rerc-e-eagle.jpg" alt="RERC-e, a bald eagle field guide holding a notebook at a rural trailhead">',
        '    <div class="rercie-mascot-stage"><img class="rercie-mascot" src="assets/rerc-e-eagle.jpg" alt="RERC-e, a bald eagle field guide holding a notebook at a rural trailhead"><span class="rercie-wave-wing" aria-hidden="true"></span></div>',
        "public mascot markup",
    )
    index.write_text(text, encoding="utf-8", newline="\n")

    css = ROOT / "rercie.css"
    styles = css.read_text(encoding="utf-8")
    animation = '''

.rercie-mascot-stage {
  position: relative;
  width: min(280px, 100%);
  aspect-ratio: 16 / 9;
  align-self: center;
  justify-self: center;
  transform-origin: 50% 90%;
  animation: rercie-bob 4s ease-in-out infinite;
}

.rercie-mascot-stage .rercie-mascot { width: 100%; height: 100%; aspect-ratio: 16 / 9; }
.rercie-wave-wing {
  position: absolute;
  z-index: 2;
  top: 24%;
  right: -8px;
  width: 52px;
  height: 72px;
  transform-origin: 20% 82%;
  animation: rercie-wave 2.4s ease-in-out infinite;
  border: 2px solid #4e3927;
  border-radius: 75% 20% 70% 30%;
  background: #7a5738;
  box-shadow: inset -10px -8px 0 rgba(48,31,20,.18);
}
.rercie-wave-wing::before,.rercie-wave-wing::after { content:""; position:absolute; right:4px; width:36px; height:13px; border-radius:70% 30% 70% 30%; background:#9a7049; transform:rotate(16deg); }
.rercie-wave-wing::before { top:16px; }
.rercie-wave-wing::after { top:38px; right:1px; }
@keyframes rercie-bob { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-5px)} }
@keyframes rercie-wave { 0%,100%{transform:rotate(7deg)} 18%{transform:rotate(-24deg)} 34%{transform:rotate(12deg)} 50%{transform:rotate(-18deg)} 68%{transform:rotate(7deg)} }
@media (prefers-reduced-motion:reduce) { .rercie-mascot-stage,.rercie-wave-wing { animation:none !important; } }
@media (max-width:980px) { .rercie-mascot-stage { width:145px; } .rercie-wave-wing { width:42px; height:58px; } }
@media (max-width:680px) { .rercie-mascot-stage { width:138px; } }
'''
    if ".rercie-mascot-stage {" not in styles:
        styles += animation
    css.write_text(styles, encoding="utf-8", newline="\n")


def update_launcher() -> None:
    path = ROOT / "rercie" / "packaging" / "RERCieLauncher.cs"
    text = path.read_text(encoding="utf-8")
    old = '''        private async void StopClicked(object sender, EventArgs args)
        {
            busy = true;
            RefreshButtons();
            int failures = 0;
            int stopped = await Task.Run(() => Runtime.StopOwnedProcesses(out failures));
            statusLabel.Text = failures > 0 ? "RERC-e could not stop every local process. Close RERC-e and try again." : stopped > 0 ? "RERC-e stopped." : "RERC-e was already stopped.";
            progressBar.Value = 0;
            busy = false;
            RefreshButtons();
        }
'''
    new = '''        private async void StopClicked(object sender, EventArgs args)
        {
            busy = true;
            statusLabel.ForeColor = Color.FromArgb(70, 80, 75);
            RefreshButtons();
            try
            {
                int failures = 0;
                int stopped = await Task.Run(() => Runtime.StopOwnedProcesses(out failures));
                statusLabel.Text = failures > 0 ? "RERC-e could not stop every local process. Close RERC-e and try again." : stopped > 0 ? "RERC-e stopped." : "RERC-e was already stopped.";
                if (failures > 0) statusLabel.ForeColor = Color.FromArgb(139, 30, 30);
            }
            catch (Exception error)
            {
                statusLabel.Text = "RERC-e could not stop: " + error.Message;
                statusLabel.ForeColor = Color.FromArgb(139, 30, 30);
            }
            finally
            {
                progressBar.Value = 0;
                busy = false;
                RefreshButtons();
            }
        }
'''
    text = replace_once(text, old, new, "launcher stop recovery")
    path.write_text(text, encoding="utf-8", newline="\n")


def update_versions() -> None:
    replacements = {
        "rercie/rercie_core.py": [("APP_VERSION = \"0.5.0\"", "APP_VERSION = \"0.5.1\"")],
        "rercie/rercie.py": [("app.APP_VERSION = \"0.5.0\"", "app.APP_VERSION = \"0.5.1\"")],
        "rercie/rercie_quality.py": [("app.APP_VERSION = \"0.5.0\"", "app.APP_VERSION = \"0.5.1\"")],
        "rercie/build_installer.ps1": [("$Version = \"0.5.0\"", "$Version = \"0.5.1\"")],
        "rercie/packaging/RERCieLauncher.cs": [("Version = \"0.5.0\"", "Version = \"0.5.1\"")],
        "rercie/packaging/RERCie.iss": [("AppVersion \"0.5.0\"", "AppVersion \"0.5.1\"")],
        "rercie/README.md": [("Current source version: `0.5.0`", "Current source version: `0.5.1`"), ("RERC-e 0.5.0", "RERC-e 0.5.1")],
        "rercie/RERC-e-LICENSE.txt": [("Version 0.5.0", "Version 0.5.1"), ("TIMBERWING-RERC-E-0.5.0-20260719", "TIMBERWING-RERC-E-0.5.1-20260819")],
        "scripts/qa_release.py": [("EXPECTED_RERCIE_VERSION = \"0.5.0\"", "EXPECTED_RERCIE_VERSION = \"0.5.1\""), ('#define AppVersion "0.5.0"', '#define AppVersion "0.5.1"'), ('$Version = "0.5.0"', '$Version = "0.5.1"'), ("rerc_e_0.5.0", "rerc_e_0.5.1")],
        "scripts/generate_source_qa_evidence.py": [("0.5.0", "0.5.1")],
    }
    for relative, pairs in replacements.items():
        path = ROOT / relative
        text = path.read_text(encoding="utf-8")
        for old, new in pairs:
            text = text.replace(old, new)
        path.write_text(text, encoding="utf-8", newline="\n")

    for relative in ("rercie/packaging/installer_manifest.json", "rercie/packaging/RERC-e-LICENSE-MANIFEST.json"):
        path = ROOT / relative
        data = json.loads(path.read_text(encoding="utf-8"))
        if relative.endswith("installer_manifest.json"):
            data["package"]["version"] = "0.5.1"
        else:
            import hashlib
            data["version"] = "0.5.1"
            data["license_identifier"] = "TIMBERWING-RERC-E-0.5.1-20260819"
            data["issued_date"] = "2026-08-19"
            data["license_sha256"] = hashlib.sha256((ROOT / "rercie" / "RERC-e-LICENSE.txt").read_bytes()).hexdigest()
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    update_core()
    update_public_mascot()
    update_launcher()
    update_versions()
    print("Applied RERC-e 0.5.1 enhancements.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
