# RERC Intake Watcher

The `Daily RERC Maintenance Watcher` runs at 3:33 a.m. Eastern every day. It reads the two Google Forms response sheets, checks submitted official links, detects likely duplicates, verifies reproducible broken-link reports, checks every existing funding/resource source, audits every funding timing field, and checks every community-example source.

## Activation

1. In each Google Form, open **Responses** and link the form to a Google Sheet.
2. Create a response-only view that excludes email addresses, names, phone numbers, and internal notes. Do not make the original response workbook public if it contains contact information.
3. Set the response-only sheet to **Anyone with the link can view**.
4. In the GitHub repository, open **Settings > Secrets and variables > Actions > Variables**.
5. Add `RERC_NEW_ITEMS_SHEET_URL` and `RERC_ISSUES_SHEET_URL` using the two Google Sheet links.
6. Run **Daily RERC Maintenance Watcher** manually once and inspect its summary and `RERC intake watcher review queue` issue.

The watcher accepts normal Google Sheet URLs and converts them to CSV export URLs. It never writes to Google Drive.

## Safety Boundary

- Contact columns are removed before reports are written.
- Submitted records are never published directly.
- Reachable links and complete fields make a submission ready for human review; they do not prove eligibility or program status.
- Reproducible `404` and `410` reports are marked verified. Other issue reports remain queued for human reproduction.
- Any catalog change must pass the existing catalog, geography, deadline, release, browser, mobile, and Quintesson QA before publication.
- The GitHub Action uses two UTC schedules and an Eastern-time guard so daylight saving time does not move the local run time.

## Local Test

```powershell
python -m unittest tests/test_rerc_intake_watcher.py
python scripts/rerc_intake_watcher.py --force --skip-network
```

The second command is expected to report `CONFIGURATION_REQUIRED` until the two sheet URLs are supplied.
