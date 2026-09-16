# RERC-e Local Grant-Writing Guide

RERC-e Local Grant-Writing Guide is an optional app for the Recreation Economy *for* Rural Communities funding and resource explorer.

Current source version: `0.5.1`.

The Windows installer includes the RERC-e app and the pinned `llama.cpp` runtime. The local Gemma writer does not require a command line, an account, or an API key. The Gemma model is downloaded only when the person selects **Download and start**.

## Install RERC-e on Windows

1. Check the latest GitHub release and its publisher-signature status. The current public 0.4.0 installer is unsigned.
2. Open the installer and follow the setup screens.
3. Keep the Start Menu shortcut. You can also choose a desktop shortcut.
4. Select **Meet RERC-e** on the last screen.
5. Select **Download and start**. RERC-e downloads the local model and checks it before opening.

The first model download is about 0.81 GB. RERC-e checks the model before using it. Later starts use the model already on the computer.

Upgrades keep a verified local Gemma model, so people do not have to download it again.

No command line is needed. Open RERC-e from the Start Menu. The launcher opens the guide in a dedicated Microsoft Edge app window with no browser address bar or visible local link. The lightweight native window handles first-run download and startup, then stays hidden while the guide is open. Closing the app window stops the local services RERC-e started. Official funding and publisher pages still expose their real web addresses for verification.

RERC-e source can also open a Community Explorer plan. Use **Open Community Explorer plan** inside RERC-e, or open an installed `.rerc-e` file from Windows. RERC-e checks the file before filling any fields and shows what it imported. Older plan files remain readable.

RERC-e 0.5.1 source now includes a three-step interface, a complete first-run **Download and start** button, a dedicated Edge app window, Per-Monitor V2 scaling, and RERC-e-branded new plan files. The app-window handoff uses a one-time 60-second code, exchanges it for an HttpOnly same-site cookie, and never places the full local service token in the Edge command line. The public 0.4.0 installer does not include these changes. The source-built native setup window passed on Windows 10 at the computer's actual 150% display scale, with additional 100%, 150%, and 200% geometry checks. A signed-package and clean-machine Windows 10/11 test is still required before release. No authorized RERC-e code-signing identity was available on this computer, so verified-publisher distribution remains on hold.

## What RERC-e Does

- Loads the current public RERC funding list.
- Accepts project notes and selected text files.
- Opens a checked Community Explorer plan with its community, state or territory, project title, project notes, profile, roadmap, and selected public records.
- Looks up community profiles from the public prebuilt `community_profiles.js` dataset by exact community + state/territory match first, then by a unique town/city/village name in that state. If no unambiguous match is present, RERC-e can use a provided Census API key to query the Census API for fallback place/county matching (including territory-level context for American Samoa, Guam, Northern Mariana Islands, and U.S. Virgin Islands).
- Creates a first-draft grant narrative with clear fact-check markers.
- Exports a real Word `.docx` file or Markdown.
- Includes all 50 states, the District of Columbia, and five U.S. territories.

## Privacy

Gemma writing and files in `local_knowledge` stay on this computer. RERC-e first uses the public prebuilt `community_profiles.js` dataset for exact community + state or territory matches, then a unique town/city/village name within that state. The HTTPS response is bounded to 16 MiB and 50,000 records so the shipped 14.4 MB profile bundle can load; invalid, oversized, or malformed profile files are rejected without using their contents. If no unambiguous profile match is available, RERC-e falls back to a direct Census API lookup only when a `CENSUS_API_KEY` is available (environment or session field). Without a key, it returns `key_required` and makes no direct Census call. The Census key is not sent to Gemma, saved by RERC-e, or included in generated output.

Do not add private files to a public copy of this project. Local reference files belong in `local_knowledge`.

Imported plans stay on this computer. The `.rerc-e` handoff is a local file export. RERC-e processes it through its authenticated loopback service only after you open or import it. RERC-e does not put plan notes in a web address or send them to the public explorer. A launcher-opened plan is copied into RERC-e's local runtime folder, checked once, and removed after the local service reads it.

## Community Explorer Plan Format

A plan is UTF-8 JSON saved with the `.rerc-e` extension. The in-app picker also accepts `.json` and older plan files. The maximum file size is 256 KB.

The top-level object must contain exactly these fields:

```json
{
  "schema": "rerc-e-handoff",
  "version": 1,
  "community": "St. Paul",
  "state": "Virginia",
  "projectTitle": "Downtown Trail Connection",
  "projectNotes": "Confirmed project notes.",
  "profile": {},
  "roadmap": [],
  "selectedRecords": []
}
```

`community` is limited to 200 characters, `state` to 100, `projectTitle` to 300, and `projectNotes` to 20,000. A plan can include up to 50 roadmap items and 100 selected records. Each selected record must contain `item_id`, `item_type`, `title`, and `source_url`; `item_type` must be `Funding`, `Resource`, or `Case Study`. Source URLs must use `http` or `https`. Unknown fields, unsupported versions, duplicate record IDs, HTML markup, malformed JSON, and over-limit content are rejected.

Profile fields supported in version 1 are `geoid`, `place`, `geography_type`, `population`, `median_age`, `median_household_income`, `poverty_rate_percent`, `source`, `source_url`, `year`, `coverage_note`, `margin_of_error_note`, and `suppressed`. Roadmap items support `id`, `stage`, `title`, `description`, `status`, `dueDate`, `owner`, `notes`, and `sourceUrl`; `stage` and `title` are required.

Imported content is applied only as plain text. RERC-e never renders imported HTML. Funding records fill the funding-details field. Roadmap items and selected resources or community examples are added to the project notes so they are available to the evidence-based draft.

## Human Review Required

RERC-e is a community-built tool. It is not an EPA grant program. It does not decide final eligibility or submit an application. Before using a draft:

1. Open the official funding page.
2. Confirm the deadline, applicant rules, match, award size, and allowed work.
3. Replace every bracketed note with a checked local fact.
4. Have a person review the full application.

## Build the Installer: Developers Only

Most people should use a signed `RERC-e-Setup.exe` from this repository's release page. The steps below are only for developers who are building the installer.

The source tree does not contain generated executables, the `llama.cpp` runtime, or model weights. `build_installer.ps1` runs the source smoke test, builds the hidden Python service with PyInstaller, compiles the native Windows launcher, verifies the pinned runtime archive, writes the integrity manifest, and creates `RERC-e-Setup.exe` with Inno Setup.

Release evidence is version-bound. The build refuses QA evidence from another RERC-e version or evidence labeled historical. `scripts/qa_local_gemma.py` regenerates the current `LOCAL_GEMMA_QA.json`; reviewers must complete and approve the current `QA_EVIDENCE.json` before its status can become `SOURCE_PASS`. Do not change a version number on old evidence and treat it as a new test.

The build does not regenerate source QA evidence. It generates `file_integrity.json` and `RERC-e-Release-QA.json`, generates the packaged `installer_manifest.json` from the reviewed source manifest plus the current version and source commit, and copies then enriches the package copy of `QA_EVIDENCE.json`. Files ending in `_HISTORICAL.json` are retained for provenance and are never release inputs.

```powershell
python -m pip install -r .\requirements-build.txt
python ..\scripts\qa_local_gemma.py
python ..\scripts\qa_release.py
& ..\scripts\qa_native_windows.ps1
$publisherThumbprint = "<authorized-publisher-certificate-thumbprint>"
.\build_installer.ps1 -AcceptRuntimeDownload -CodeSigningThumbprint $publisherThumbprint -RequireCodeSignature
```

The local Gemma service must be running for `qa_local_gemma.py`. A pending or failed QA result is a release hold, not a reason to edit the evidence to `PASS`.

The build requires a trusted, identity-matched publisher signature by default and signs the launcher, service, and installer with a SHA-256 timestamp. It supports either a local organization-validation certificate by thumbprint or Azure Artifact Signing with `-ArtifactSigningDlib`, `-ArtifactSigningMetadata`, and `-PublisherLegalName`. See [packaging/PUBLISHER_SIGNING.md](packaging/PUBLISHER_SIGNING.md) for the identity decision, enrollment steps, prerequisites, and verification commands. For isolated QA only, use `-AllowUnsignedQaBuild`; that path labels its result `QA_ONLY_UNSIGNED` and does not authorize a public release. A valid signature identifies the publisher but does not guarantee that a new download has enough Windows SmartScreen reputation to suppress its initial warning.

## Help

If RERC-e does not open, start it again from the Start Menu. If an installed file fails its safety check, run the installer again. Report repeat problems at [henkelpress/rerc-grant-finder](https://github.com/henkelpress/rerc-grant-finder/issues).
