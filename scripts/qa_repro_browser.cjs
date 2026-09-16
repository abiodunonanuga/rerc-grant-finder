const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const { spawn, execFileSync } = require("child_process");
const { chromium } = require("playwright");

const root = path.resolve(__dirname, "..");
const artifacts = path.resolve(process.argv[2] || path.join(root, "output", "playwright"));
const staticPort = 8877;
const localPort = 8907;
const token = crypto.randomBytes(32).toString("hex");
const checks = {};
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function ready(url) {
  for (let attempt = 0; attempt < 80; attempt++) {
    try {
      if ((await fetch(url)).ok) return;
    } catch {}
    await sleep(250);
  }
  throw new Error(`Timed out waiting for ${url}`);
}

async function saveDownload(page, selector, fileName) {
  const pending = page.waitForEvent("download", { timeout: 10000 });
  await page.locator(selector).click();
  const download = await pending;
  const destination = path.join(artifacts, fileName);
  await download.saveAs(destination);
  return destination;
}

async function run() {
  fs.mkdirSync(artifacts, { recursive: true });
  const staticServer = spawn("python", ["-m", "http.server", String(staticPort), "--bind", "127.0.0.1"], {
    cwd: root, stdio: "ignore", windowsHide: true
  });
  const localServer = spawn("python", [path.join(root, "rercie", "rercie_core.py"), "--serve", "--host", "127.0.0.1", "--port", String(localPort)], {
    cwd: root, env: { ...process.env, RERCIE_SESSION_TOKEN: token }, stdio: "ignore", windowsHide: true
  });
  let browser;
  try {
    await ready(`http://127.0.0.1:${staticPort}/`);
    await ready(`http://127.0.0.1:${localPort}/`);
    const chromePath = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
    browser = await chromium.launch(fs.existsSync(chromePath)
      ? { executablePath: chromePath, headless: true }
      : { headless: true });
    const context = await browser.newContext({ viewport: { width: 1360, height: 900 }, acceptDownloads: true });
    const explorer = await context.newPage();
    const explorerErrors = [];
    explorer.on("pageerror", (error) => explorerErrors.push(error.message));
    await explorer.goto(`http://127.0.0.1:${staticPort}/`, { waitUntil: "networkidle" });
    await explorer.locator("html.rerc-planner-ready").waitFor();
    await explorer.locator("#stateSelect").selectOption("Virginia");
    await explorer.locator("#limitSelect").selectOption("30");
    await explorer.locator(".result-card").first().locator('[data-action="planner-save"]').click();
    await explorer.waitForTimeout(500);
    checks.saveAttempt = {
      count: await explorer.locator("#savedCountBadge").innerText(),
      status: await explorer.locator("#plannerStatus").innerText(),
      firstCard: await explorer.locator(".result-card").first().innerText()
    };
    if (checks.saveAttempt.count !== "1") throw new Error("Save did not take effect: " + JSON.stringify(checks.saveAttempt));
    await explorer.reload({ waitUntil: "networkidle" });
    await explorer.locator("html.rerc-planner-ready").waitFor();
    checks.restoredState = {
      field: await explorer.locator("#stateSelect").inputValue(),
      count: await explorer.locator("#matchCount").innerText(),
      heading: await explorer.locator("#communityTitle").innerText(),
      validation: await explorer.locator("#profileStatus").innerText()
    };
    if (checks.restoredState.field !== "Virginia" || checks.restoredState.count !== "240" ||
        !checks.restoredState.heading.includes("Virginia") ||
        checks.restoredState.validation.includes("Choose a state")) {
      throw new Error("Explorer restored state and results disagree.");
    }
    await explorer.locator("#showSavedOnly").click();
    checks.savedView = {
      count: await explorer.locator("#matchCount").innerText(),
      announcement: await explorer.locator("#matchAnnouncement").innerText()
    };
    if (checks.savedView.count !== "1" || !checks.savedView.announcement.includes("1 saved")) {
      throw new Error("Saved-only result count is stale.");
    }
    const savedCsv = await saveDownload(explorer, "#exportCsv", "saved-view.csv");
    const csvRows = fs.readFileSync(savedCsv, "utf8").trim().split(/\r?\n/).length - 1;
    checks.savedCsvRows = csvRows;
    if (csvRows !== 1) throw new Error(`Saved-only CSV exported ${csvRows} data rows.`);

    await explorer.locator('[data-wizard-step="2"]').click();
    const applicant = explorer.locator('#applicantOptions input[type="checkbox"]').first();
    const applicantValue = await applicant.inputValue();
    await applicant.check();
    await explorer.locator("#keywordSearch").fill("Trail");
    await explorer.locator("#includeClosed").check();
    let workspace;
    try {
      workspace = await saveDownload(explorer, "#exportWorkspaceFile", "filtered-workspace.rerc-workspace");
    } catch (error) {
      const choices = await explorer.evaluate(() => Object.fromEntries(["applicantOptions", "topicOptions", "fundingTypeOptions", "resourceTypeOptions", "caseStudyPhaseOptions"].map((id) => {
        const root = document.getElementById(id);
        return [id, { selected: [...root.querySelectorAll("input:checked")].map((input) => input.value), all: [...root.querySelectorAll("input")].map((input) => input.value) }];
      })));
      throw new Error(`Workspace export failed: ${error.message}; page errors: ${JSON.stringify(explorerErrors)}; status: ${await explorer.locator("#shareStatus").innerText()}; choices: ${JSON.stringify(choices)}`);
    }
    const workspaceData = JSON.parse(fs.readFileSync(workspace, "utf8"));
    checks.workspaceFilters = workspaceData.filters;
    if (workspaceData.filters.keywordSearch !== "Trail" ||
        !workspaceData.filters.applicantOptions.includes(applicantValue) ||
        !workspaceData.filters.includeClosed) {
      throw new Error("Saved workspace omitted the active filters.");
    }
    await explorer.reload({ waitUntil: "networkidle" });
    await explorer.locator("html.rerc-planner-ready").waitFor();
    checks.reloadedFilters = {
      keyword: await explorer.locator("#keywordSearch").inputValue(),
      applicant: await explorer.locator(`#applicantOptions input[value="${applicantValue}"]`).isChecked(),
      includeClosed: await explorer.locator("#includeClosed").isChecked()
    };
    if (checks.reloadedFilters.keyword !== "Trail" || !checks.reloadedFilters.applicant ||
        !checks.reloadedFilters.includeClosed) throw new Error("Workspace filters were lost on refresh.");
    await explorer.locator('[data-wizard-step="2"]').click();
    await explorer.locator("#keywordSearch").fill("Forest");
    await explorer.locator("#importWorkspaceFile").setInputFiles(workspace);
    await explorer.waitForTimeout(350);
    if (await explorer.locator("#keywordSearch").inputValue() !== "Trail") {
      throw new Error("Importing a workspace did not restore its filters.");
    }
    await explorer.locator('[data-wizard-step="3"]').click();
    await explorer.locator("#showSavedOnly").click();
    if (!await explorer.locator("#nextDeadlinePanel").isHidden() ||
        !await explorer.locator('#resultsToolbar label[for="sortSelect"]').isHidden()) {
      throw new Error("Saved view still displays controls for the full result list.");
    }

    await explorer.locator("#projectCommunity").fill("St. Paul");
    await explorer.locator("#projectTitle").fill("QA TEST Riverfront trail access");
    await explorer.locator("#projectNotes").fill("Synthetic QA notes. Budget and partners are unconfirmed.");
    await explorer.locator("#includeHandoffNotes").check();
    const versionNote = await explorer.locator(".handoff-compatibility").innerText();
    if (!versionNote.includes("0.4.0 installer cannot import")) throw new Error("Handoff hides the current installer incompatibility.");
    let handoffDialogs = 0;
    explorer.on("dialog", async (dialog) => { handoffDialogs += 1; await dialog.dismiss(); });
    const handoff = await saveDownload(explorer, "#exportRercE", "community-plan.rerc-e");
    if (handoffDialogs) throw new Error("Handoff still requires a native Firefox/JavaScript dialog.");
    const pythonCheck = "import json,sys;sys.path.insert(0,sys.argv[1]);from rercie_core import validate_handoff_text;from pathlib import Path;p=validate_handoff_text(Path(sys.argv[2]).read_bytes());print(json.dumps({'community':p['community'],'state':p['state'],'notes':p['projectNotes'],'records':len(p['selectedRecords'])}))";
    checks.handoff = JSON.parse(execFileSync("python", ["-c", pythonCheck, path.join(root, "rercie"), handoff], { encoding: "utf8" }));
    if (checks.handoff.community !== "St. Paul" || checks.handoff.state !== "Virginia" ||
        checks.handoff.records !== 1 || !checks.handoff.notes.includes("unconfirmed")) {
      throw new Error("Exporter produced a plan the current RERC-e importer cannot use.");
    }
    const wordPlan = await saveDownload(explorer, "#exportPlanWord", "community-plan.docx");
    checks.wordPlanBytes = fs.statSync(wordPlan).size;
    await explorer.screenshot({ path: path.join(artifacts, "saved-explorer.png"), fullPage: true });

    const local = await context.newPage();
    await local.route("**/api/grants", (route) => route.fulfill({
      status: 200, contentType: "application/json",
      body: JSON.stringify({ grants: [
        { item_id: "QA-GRANT", title: "Synthetic Trail Grant", organization: "QA agency", source_url: "https://example.org/grant" },
        ...Array.from({ length: 828 }, (_, index) => ({ item_id: `QA-${index}`, title: `Sample option ${index}`, organization: "QA agency" }))
      ], updated: "QA" })
    }));
    await local.goto(`http://127.0.0.1:${localPort}/#token=${token}`, { waitUntil: "domcontentloaded" });
    await local.locator("#planInput").setInputFiles(handoff);
    await local.locator("#planImportStatus").filter({ hasText: "St. Paul" }).waitFor();
    checks.importedCommunity = await local.locator("#community").inputValue();
    if (checks.importedCommunity !== "St. Paul") throw new Error("RERC-e did not import the Explorer community.");
    await local.locator("#nextFunding").click();
    await local.locator("#grantSearchStatus").filter({ hasText: "829" }).waitFor();
    checks.fundingInitialOptions = await local.locator("#grantSelect option").count();
    if (checks.fundingInitialOptions > 62) throw new Error("The unsearched funding dropdown still shows hundreds of options.");
    await local.locator("#grantSearch").fill("Synthetic Trail Grant");
    await local.locator("#grantSelect").selectOption("0");
    checks.fundingSummary = await local.locator("#fundingSummary").innerText();
    if (!checks.fundingSummary.includes("Synthetic Trail Grant")) throw new Error("Selected funding record has no readable summary.");
    await local.locator("#grantSearch").fill("no matching program");
    if (await local.locator("#grantSelect").inputValue() !== "0" ||
        !await local.locator("#fundingSummary").getByText("Synthetic Trail Grant").isVisible()) {
      throw new Error("Searching funding removed the current selection.");
    }
    await local.locator("#loadGrants").click();
    await local.locator("#status").filter({ hasText: "Loaded 829" }).waitFor();
    if (await local.locator("#grantSelect").inputValue() !== "0") throw new Error("Funding list refresh lost the current selection.");
    await local.locator("#usePublicData").uncheck();
    await local.locator('[data-step="project"]').click();
    await local.locator("#projectSummary").fill("Synthetic accessible river trailhead and connection.");
    await local.locator('[data-step="draft"]').click();
    await local.locator("#provider").selectOption("fallback");
    await local.locator("#draftButton").click();
    await local.locator("#status").filter({ hasText: "Draft ready" }).waitFor({ timeout: 30000 });
    checks.generatedDraft = (await local.locator("#output").innerText()).includes("Riverfront trail access");
    if (!checks.generatedDraft) throw new Error("RERC-e did not generate a draft from the imported plan.");
    await local.locator('[data-step="funding"]').click();
    await local.locator("#fundingDetailsPanel summary").click();
    await local.locator("#selectedGrant").fill("Changed synthetic funding record after drafting.");
    await local.locator('[data-step="draft"]').click();
    await local.locator("#downloadMd").click();
    checks.fundingStaleWarning = await local.locator("#status").innerText();
    if (!checks.fundingStaleWarning.includes("Inputs changed")) throw new Error("Funding change did not invalidate the draft.");
    await local.locator('[data-step="project"]').click();
    await local.locator("#projectSummary").fill("Changed synthetic project scope after drafting.");
    await local.locator('[data-step="draft"]').click();
    await local.locator("#downloadMd").click();
    checks.staleWarning = await local.locator("#status").innerText();
    if (!checks.staleWarning.includes("Inputs changed")) throw new Error("Outdated draft export was not blocked.");
    await local.reload({ waitUntil: "domcontentloaded" });
    checks.reloadedProject = await local.locator("#projectSummary").inputValue();
    checks.reloadedDraft = (await local.locator("#output").innerText()).includes("Riverfront trail access");
    const health = await local.evaluate(() => fetch("/health", { headers: { "X-RERC-e-Token": sessionStorage.getItem("rercie.tabSessionToken.v1") || "" } }).then((response) => response.status));
    checks.reloadedHealthStatus = health;
    if (health !== 200 || !checks.reloadedDraft ||
        checks.reloadedProject !== "Changed synthetic project scope after drafting.") {
      throw new Error("RERC-e refresh failed to retain session, inputs, or draft.");
    }
    await local.screenshot({ path: path.join(artifacts, "recovered-rercie.png"), fullPage: true });
    await context.close();
    console.log(JSON.stringify({ status: "PASS", checks }, null, 2));
  } finally {
    if (browser) await browser.close();
    localServer.kill();
    staticServer.kill();
  }
}

run().catch((error) => {
  console.error(error.stack || String(error));
  process.exitCode = 1;
});
