# RERC Community Explorer

Public GitHub Pages site for exploring funding, technical resources, and official community examples relevant to Recreation Economy *for* Rural Communities work.

Live site: <https://henkelpress.github.io/rerc-grant-finder/>

## Current Catalog

- 1,031 public records
- 829 funding options
- 192 guides, tools, data sources, training programs, and other resources
- 10 curated, detailed public precedents outside the linked case-study libraries

Resource results can be filtered by type. Case-study browsing starts with 24 ranked examples and links to the complete official source libraries.
- Coverage for all 50 states, the District of Columbia, Puerto Rico, American Samoa, Guam, the Northern Mariana Islands, and the U.S. Virgin Islands

People choose a state or territory, select All, Funding, Resources, or Case studies, and answer a few project questions. Saved funding is organized into a chronological Plan, Design, Build, and Operate sequence with application timing, useful phase outputs, and later saved targets that the current step can help prepare. This planning sequence does not promise an award. Users can export the roadmap and funding sequence as a real Word DOCX or CSV. Regional programs appear only when their reviewed service area includes the selected state or territory. The full Word appendix, Excel workbook, and CSV include all three content types and their official URLs.

## Public Site Files

- `index.html`
- `styles.css`
- `rercie.css`
- `app.js`
- `deadline-utils.js`
- `site-config.js`
- `data.js`
- `maintenance/catalog.csv` and `scripts/catalog_maintenance.py`
- `case_studies.js`
- `assets/`
- `downloads/`

Maintenance instructions: [`MAINTENANCE.md`](MAINTENANCE.md)


## Case Studies

The community-example layer contains 10 curated, detailed public precedents that are not repeated in the four linked source libraries. The records draw on direct official pages and reports from the National Park Service, Natural Resources Conservation Service, Federal Highway Administration, Forest Service, and a Climate Resilience Toolkit action-plan page. Private records, local paths, administrative notes, and images are excluded. The 2026-08-20 source-health check reached all nine unique official source URLs with no hard failures.

## Meet RERC-e

RERC-e Local Grant-Writing Guide is an optional Windows app. It helps people review likely funding matches and turn project notes into a structured first draft. Local Gemma may select exact excerpts from supplied evidence; RERC-e verifies them and places them in a fixed outline. Raw model prose is not shown.

- Friendly Windows setup wizard
- No command-line setup for the person installing it
- Start Menu shortcut and optional desktop shortcut
- No account or API key required for local writing
- First use downloads a verified Google Gemma 3 1B model, about 0.81 GB
- Real Word `.docx` and Markdown export

[Download RERC-e for Windows](https://github.com/henkelpress/rerc-grant-finder/releases/latest/download/RERCie-Setup.exe)

The current public installer is RERC-e 0.4.0. It passed installer QA and uses Google Gemma 3 1B. The installer is not code-signed, so Windows may show a safety notice. RERC-e 0.5.1 has passed source, local-generation, browser, animation, and launcher compilation QA but is not the public installer yet. Its unsigned package was blocked by Windows security and is held for authorized publisher signing and clean-machine testing. RERC-e is a community-built tool. It is not an EPA grant program, does not decide eligibility, and does not submit applications.

The reviewed source and Timberwing Systems license are in `rercie/`. Model weights are not stored in this repository or installer.

## Release QA

- `python scripts/catalog_maintenance.py check`
- `python scripts/qa_release.py`
- `python scripts/qa_case_studies.py`
- `python scripts/qa_geography_coverage.py`
- `python scripts/check_case_sources.py`
- `node scripts/qa_public_site.cjs <site-url> <output-folder>`

## Automated Checks

The `Daily RERC Maintenance Watcher` runs at 3:33 a.m. Eastern. It reads the public response-only Google Sheets configured for the two site forms, removes contact fields, checks submitted links and duplicates, verifies reproducible broken-link reports, checks every catalog source and regional coverage source, audits every funding timing field, and checks every community-example source. It updates a sanitized maintainer issue and uploads the complete QA reports. See [`maintenance/INTAKE_WATCHER.md`](maintenance/INTAKE_WATCHER.md).

The `Daily Federal Opportunity Discovery` workflow searches the public Grants.gov API each day and uploads a review queue of posted and forecasted opportunities related to rural development, outdoor recreation, trails, tourism, community development, economic development, and technical assistance.

New opportunities, changed source signals, and status changes require human review before they enter the public catalog. The monitoring workflows do not publish unreviewed records.

## Publication Boundary

Do not add raw working files, source-audit tables, private records, private notes, email chains, private reference files, model weights, generated logs, PID files, or draft QA material to this public repository.
