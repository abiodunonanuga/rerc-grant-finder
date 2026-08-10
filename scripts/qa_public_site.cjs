const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");
const { execFileSync } = require("child_process");

const expectedDeadlineReport = JSON.parse(execFileSync(
  process.execPath, [path.join(__dirname, "qa_deadline_parity.cjs"), "--json"], { encoding: "utf8" }
));

const baseUrl = process.argv[2] || "http://127.0.0.1:8877/";
const outDir = process.argv[3] || "browser-qa";
const chromePath = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const checks = {};
const downloads = {};
const errors = [];
const failures = [];
const check = (name, ok) => { if (!ok) failures.push(name); };
const overflow = (page) => page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1);
const hasSensitiveKey = (value) => {
  if (!value || typeof value !== "object") return false;
  if (Array.isArray(value)) return value.some(hasSensitiveKey);
  return Object.entries(value).some(([key, nested]) => /^(token|api[_-]?key|secret)$/i.test(key) || hasSensitiveKey(nested));
};

async function selectState(page, state) {
  await page.locator("#stateSelect").selectOption({ label: state });
  await page.waitForTimeout(100);
}

async function selectStateFromAnyPhase(page, state) {
  await page.evaluate((value) => {
    const select = document.getElementById("stateSelect");
    select.value = value;
    select.dispatchEvent(new Event("change", { bubbles: true }));
  }, state);
  await page.waitForTimeout(100);
}

async function resultIds(page) {
  return page.evaluate(() => window.RERCExplorer.getMatches().map((item) => item.item_id));
}

async function download(page, selector, filename) {
  const event = page.waitForEvent("download");
  await page.locator(selector).click();
  const item = await event;
  const file = path.join(outDir, filename);
  await item.saveAs(file);
  return { file, name: item.suggestedFilename(), bytes: fs.statSync(file).size };
}

async function main() {
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch(fs.existsSync(chromePath)
    ? { executablePath: chromePath, headless: true }
    : { headless: true });
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, acceptDownloads: true });
    const page = await context.newPage();
    const isBenignGoogleFormsConsoleError = (message) => (
      /filesystem:https:\/\/docs\.google\.com\/persistent\/docs\/fonts\/.*\.woff2/i.test(message)
      && /net::ERR_FILE_NOT_FOUND/i.test(message)
    ) || (
      /Framing 'https:\/\/docs\.google\.com\/' violates the following report-only Content Security Policy directive/i.test(message)
      && /frame-ancestors 'self'/i.test(message)
    );
    page.on("pageerror", (error) => errors.push(`pageerror:${error.message}`));
    page.on("console", (message) => {
      if (message.type() === "error") {
        const where = message.location();
        const detail = `console:${where.url}:${where.lineNumber}:${where.columnNumber}:${message.text()}`;
        if (!isBenignGoogleFormsConsoleError(detail)) errors.push(detail);
      }
    });
    await page.goto(baseUrl, { waitUntil: "networkidle", timeout: 60000 });
    await page.waitForSelector("html.rerc-planner-ready");
    await page.waitForSelector("#stateSelect", { state: "visible" });

    checks.initial = await page.evaluate(() => ({
      formVisible: document.getElementById("communityFilters").getBoundingClientRect().height > 0,
      stateRequired: document.getElementById("stateSelect").required,
      stateEnabled: !document.getElementById("stateSelect").disabled,
      stateOptions: document.getElementById("stateSelect").options.length,
      obsoleteLocalityControls: ["placeTypeSelect", "communityName", "communityMap"].filter((id) => document.getElementById(id)),
      futureLocked: [...document.querySelectorAll('#workflowSteps [data-wizard-step="2"], #workflowSteps [data-wizard-step="3"], #workflowSteps [data-wizard-step="4"]')].every((node) => node.disabled),
      resultsHidden: document.getElementById("matchesWorkspace").hidden
    }));
    checks.blankBlocked = checks.initial.futureLocked
      && /required/i.test(await page.locator("#communityRequirement").innerText());
    await selectState(page, "Virginia");
    checks.unlocked = await page.locator('#workflowSteps [data-wizard-step="2"], #workflowSteps [data-wizard-step="3"], #workflowSteps [data-wizard-step="4"]').evaluateAll((nodes) => nodes.every((node) => !node.disabled));
    await page.locator('#workflowSteps [data-wizard-step="2"]').click();
    checks.phase2 = await page.locator('[data-wizard-panel="2"]').isVisible();
    const applicantChoices = page.locator("#applicantOptions > label");
    checks.priorityPager = {
      firstPage: await applicantChoices.evaluateAll((nodes) => nodes.filter((node) => !node.hidden).map((node) => node.textContent.trim())),
      nextEnabled: await page.locator('[data-choice-next="applicantOptions"]').isEnabled()
    };
    await page.locator('[data-choice-next="applicantOptions"]').click();
    checks.priorityPager.secondPage = await applicantChoices.evaluateAll((nodes) => nodes.filter((node) => !node.hidden).map((node) => node.textContent.trim()));
    await page.locator('#workflowSteps [data-wizard-step="3"]').click();
    await page.waitForSelector(".result-card");
    checks.phase3 = await page.locator("#matchesWorkspace").isVisible();
    check("state_gate", checks.initial.formVisible && checks.initial.stateRequired && checks.initial.stateEnabled
      && checks.initial.stateOptions === 57 && checks.initial.obsoleteLocalityControls.length === 0
      && checks.initial.futureLocked && checks.initial.resultsHidden && checks.blankBlocked && checks.unlocked
      && checks.phase2 && checks.phase3 && checks.priorityPager.firstPage.length <= 6
      && checks.priorityPager.nextEnabled && checks.priorityPager.secondPage.join("|") !== checks.priorityPager.firstPage.join("|"));

    checks.counts = await page.evaluate(() => ["fundingCount", "resourceCount", "caseStudyCount"].map((id) => Number(document.getElementById(id).textContent)));
    check("catalog_counts", checks.counts.join(",") === "659,167,476" && checks.counts.reduce((sum, value) => sum + value, 0) === 1302);

    const windowIds = await resultIds(page);
    checks.virginiaRegional = {
      opportunityAppalachia: windowIds.includes("RERC-FND-0271"),
      craft3Excluded: !windowIds.includes("RERC-FND-0255"),
      psegExcluded: !windowIds.includes("RERC-FND-0269")
    };
    await selectStateFromAnyPhase(page, "Oregon");
    const oregonIds = await resultIds(page);
    checks.oregonRegional = {
      craft3: oregonIds.includes("RERC-FND-0255"),
      opportunityAppalachiaExcluded: !oregonIds.includes("RERC-FND-0271"),
      psegExcluded: !oregonIds.includes("RERC-FND-0269")
    };
    await selectStateFromAnyPhase(page, "New Jersey");
    checks.newJerseyRegional = await page.evaluate(() => {
      const byId = new Map(window.RERCExplorer.catalog.map((item) => [item.item_id, item]));
      return {
        pseg: window.RERCExplorer.matchesGeography(byId.get("RERC-FND-0269"), "New Jersey"),
        craft3Excluded: !window.RERCExplorer.matchesGeography(byId.get("RERC-FND-0255"), "New Jersey")
      };
    });
    await selectStateFromAnyPhase(page, "Puerto Rico");
    const puertoRicoIds = await resultIds(page);
    checks.territoryRegional = {
      coralFund: puertoRicoIds.includes("RERC-FND-0261"),
      insularOiaExcluded: !["RERC-FND-0257", "RERC-FND-0262", "RERC-FND-0265", "RERC-FND-0267", "RERC-FND-0648"].some((id) => puertoRicoIds.includes(id))
    };
    checks.runtimeGeography = await page.evaluate(() => {
      const byId = new Map(window.RERCExplorer.catalog.map((item) => [item.item_id, item]));
      const territories = ["American Samoa", "Guam", "Northern Mariana Islands", "Puerto Rico", "U.S. Virgin Islands"];
      const territoryNationalIds = ["RERC-FND-0288", "RERC-FND-0287", "RERC-FND-0273", "RERC-RES-0037", "RERC-RES-0045"];
      const reachableIds = ["RERC-RES-NEW-2026-015", "RERC-RES-NEW-2026-018", "RERC-RES-NEW-2026-020", "RERC-RES-NEW-2026-031"];
      return {
        territoryNational: territoryNationalIds.every((id) => territories.every((place) => window.RERCExplorer.matchesGeography(byId.get(id), place))),
        formerlyUnreachable: reachableIds.every((id) => ["Virginia", "Alaska", "Hawaii", "Puerto Rico"].some((place) => window.RERCExplorer.matchesGeography(byId.get(id), place))),
        fiveStarBounded: window.RERCExplorer.matchesGeography(byId.get("RERC-FND-0476"), "Puerto Rico")
          && window.RERCExplorer.matchesGeography(byId.get("RERC-FND-0476"), "U.S. Virgin Islands")
          && !window.RERCExplorer.matchesGeography(byId.get("RERC-FND-0476"), "Guam"),
        stages: window.RERCExplorer.matchesStage(byId.get("RERC-FND-0282"), "Early Design")
          && window.RERCExplorer.matchesStage(byId.get("RERC-FND-0282"), "Construction"),
        otherApplicant: !window.RERCExplorer.matchesApplicants(byId.get("RERC-FND-0007").eligible_users.toLowerCase(), ["__other__"])
      };
    });
    check("regional_coverage", Object.values(checks.virginiaRegional).every(Boolean)
      && Object.values(checks.oregonRegional).every(Boolean)
      && Object.values(checks.newJerseyRegional).every(Boolean)
      && Object.values(checks.territoryRegional).every(Boolean)
      && Object.values(checks.runtimeGeography).every(Boolean));

    await selectStateFromAnyPhase(page, "Virginia");
    await page.evaluate(() => window.RERCExplorer.chooseMode("Funding"));
    await page.waitForTimeout(100);
    const appalachiaCard = page.locator('article[data-item-id="RERC-FND-0271"]');
    checks.card = await appalachiaCard.evaluate((card) => {
      const who = card.querySelector(".eligibility");
      const details = card.querySelector("details");
      const link = [...card.querySelectorAll("a")].find((anchor) => anchor.textContent.trim() === "Program Website");
      return {
        who: who?.textContent.trim() || "",
        whoBeforeDetails: !!who && !!details && !!(who.compareDocumentPosition(details) & Node.DOCUMENT_POSITION_FOLLOWING),
        link: link?.href || "",
        coverage: card.textContent.includes("Coverage note:"),
        noWhy: !/why it (fits|matches)/i.test(card.textContent),
        score: card.querySelector(".score strong")?.textContent.trim() || ""
      };
    });
    check("public_card_contract", /^Who:/.test(checks.card.who) && checks.card.whoBeforeDetails
      && /^https:\/\//.test(checks.card.link) && checks.card.coverage && checks.card.noWhy && checks.card.score.length > 0);

    checks.fundingTiming = await page.evaluate(() => window.RERCExplorer.fundingTimingCounts(window.RERCExplorer.catalog.filter((item) => item.item_type === "Funding")));
    const browserDeadlineRecords = await page.evaluate(() => Object.fromEntries(
      window.RERCExplorer.catalog.filter((item) => item.item_type === "Funding")
        .map((item) => [item.item_id, window.RERCExplorer.fundingTiming(item).type])
    ));
    const deadlineMismatches = Object.entries(expectedDeadlineReport.records)
      .filter(([itemId, type]) => browserDeadlineRecords[itemId] !== type)
      .map(([itemId, type]) => ({ itemId, expected: type, actual: browserDeadlineRecords[itemId] || null }));
    checks.fundingTimingParity = {
      expected: expectedDeadlineReport.counts,
      actual: checks.fundingTiming,
      recordsChecked: Object.keys(expectedDeadlineReport.records).length,
      mismatches: deadlineMismatches
    };
    check("funding_timing_coverage", Object.values(checks.fundingTiming).reduce((sum, value) => sum + value, 0) === 659
      && checks.fundingTiming.dated > 0 && checks.fundingTiming.rolling > 0 && checks.fundingTiming.date_pending > 0);
    check("funding_timing_parity", expectedDeadlineReport.status === "PASS"
      && JSON.stringify(checks.fundingTiming) === JSON.stringify(expectedDeadlineReport.counts)
      && checks.fundingTimingParity.recordsChecked === 659 && deadlineMismatches.length === 0);
    checks.nextDeadline = await page.locator("#nextDeadlinePanel").evaluate((node) => ({
      visible: node.getBoundingClientRect().height > 0,
      date: node.querySelector("#nextDeadlineDate")?.textContent.trim() || "",
      program: node.querySelector("#nextDeadlineMeta")?.textContent.trim() || "",
      link: node.querySelector("#nextDeadlineLink")?.getAttribute("href") || ""
    }));
    check("next_deadline", checks.nextDeadline.visible && /\b20\d{2}\b/.test(checks.nextDeadline.date)
      && checks.nextDeadline.program.length > 5 && /^https:\/\//.test(checks.nextDeadline.link));

    checks.eagle = await page.locator(".rercie-mascot").evaluate((image) => {
      const style = getComputedStyle(image); const box = image.getBoundingClientRect();
      return { loaded: image.complete && image.naturalWidth > 0, objectFit: style.objectFit, objectPosition: style.objectPosition, ratio: box.width / box.height };
    });
    check("eagle_centered", checks.eagle.loaded && checks.eagle.objectFit === "contain"
      && /50%|center/.test(checks.eagle.objectPosition) && Math.abs(checks.eagle.ratio - (16 / 9)) < 0.03);
    check("desktop_overflow", await overflow(page));

    checks.modes = {};
    for (const [name, selector] of Object.entries({ all: '[data-mode="All"]', funding: "#showFunding", resources: "#showResources", cases: "#showCases" })) {
      await page.locator(selector).click();
      checks.modes[name] = await page.locator(selector).getAttribute("aria-pressed") === "true";
    }
    check("mode_buttons", Object.values(checks.modes).every(Boolean));
    await page.locator("#showFunding").click();
    checks.allResultsDefault = await page.locator("#limitSelect").inputValue() === "all";
    await page.locator('#workflowSteps [data-wizard-step="2"]').click();
    await page.locator('#funding-filter-0').check();
    await page.locator('#workflowSteps [data-wizard-step="3"]').click();
    checks.fundingFilter = await page.evaluate(() => window.RERCExplorer.getMatches().every((item) => item.item_type !== "Funding" || /\bgrant\b/i.test(`${item.title} ${item.support_type} ${item.amount_or_cost} ${item.match_or_cost}`)));
    await page.locator('#workflowSteps [data-wizard-step="2"]').click();
    await page.locator('#funding-filter-0').uncheck();
    await page.locator('#showCases').click();
    await page.locator('#case-study-phase-1').check();
    await page.locator('#workflowSteps [data-wizard-step="3"]').click();
    checks.caseStudyFilter = await page.evaluate(() => window.RERCExplorer.getMatches().every((item) => item.item_type !== "Case Study" || /design|engineer|predevelopment/i.test(`${item.project_stage} ${item.topic_tags}`)));
    await page.locator('#workflowSteps [data-wizard-step="2"]').click();
    await page.locator('#case-study-phase-1').uncheck();
    await page.locator('#workflowSteps [data-wizard-step="3"]').click();
    await page.locator('#showFunding').click();
    check("result_filters", checks.allResultsDefault && checks.fundingFilter && checks.caseStudyFilter);
    checks.cardActions = await page.locator(".result-card").first().evaluate((card) => ({
      planner: card.querySelectorAll(".planner-card-actions [data-action]").length,
      duplicateBase: card.querySelectorAll(".card-actions [data-action]").length
    }));
    check("single_card_actions", checks.cardActions.planner === 2 && checks.cardActions.duplicateBase === 0);

    checks.calendarRemoved = await page.evaluate(() => !document.getElementById("showFundingCalendar")
      && !document.getElementById("fundingCalendar") && !document.getElementById("exportCalendar"));
    checks.intakeForms = await page.evaluate(() => ({
      githubLinks: [...document.querySelectorAll("#contribute a")].some((link) => link.href.includes("github.com")),
      issueButton: Boolean(document.getElementById("openIssueReport")),
      submissionButton: Boolean(document.getElementById("openCatalogSubmission"))
    }));
    await page.locator("#openIssueReport").click();
    checks.issueForm = await page.evaluate(() => ({
      open: document.getElementById("issueReportDialog").open,
      frame: document.getElementById("issueReportFrame").src,
      external: document.getElementById("issueReportExternal").href
    }));
    await page.locator("#issueReportDialog [data-close-contribution]").first().click();
    await page.locator("#openCatalogSubmission").click();
    checks.submissionForm = await page.evaluate(() => ({
      open: document.getElementById("catalogSubmissionDialog").open,
      frame: document.getElementById("catalogSubmissionFrame").src,
      external: document.getElementById("catalogSubmissionExternal").href
    }));
    await page.locator("#catalogSubmissionDialog [data-close-contribution]").first().click();
    check("public_intake_and_deadline_boundary", checks.calendarRemoved
      && !checks.intakeForms.githubLinks && checks.intakeForms.issueButton && checks.intakeForms.submissionButton
      && checks.issueForm.open && checks.issueForm.frame.includes("1FAIpQLScBYulkwgoEVhLKftiGBm81LZxPdhojZVQtUT8ZQjWj4Sit6g")
      && checks.issueForm.frame.includes("embedded=true") && checks.issueForm.external.includes("usp=header")
      && checks.submissionForm.open && checks.submissionForm.frame.includes("1FAIpQLSdL4GfgKT_ub6I8zd0d7vXXszwZG498b81XR12L-ZCYiUvqfQ")
      && checks.submissionForm.frame.includes("embedded=true") && checks.submissionForm.external.includes("usp=header"));

    const save = page.locator('[data-action="planner-save"]').first();
    await save.click(); await page.waitForTimeout(300);
    checks.savedBeforeReload = Number(await page.evaluate(() => document.querySelector("#savedCountBadge, #savedTrayCount, #mobileSavedCount")?.textContent || 0));
    await page.reload({ waitUntil: "networkidle" }); await page.waitForSelector("html.rerc-planner-ready");
    checks.savedAfterReload = Number(await page.evaluate(() => document.querySelector("#savedCountBadge, #savedTrayCount, #mobileSavedCount")?.textContent || 0));
    check("saved_persists", checks.savedBeforeReload === 1 && checks.savedAfterReload === 1);

    checks.workspace = await page.evaluate(() => ({
      id: localStorage.getItem("rerc.activeWorkspaceId.v2"),
      legacyId: localStorage.getItem("rerc.lastWorkspaceId")
    }));
    check("private_browser_workspace", /^browser-/.test(checks.workspace.id || ""));

    const roadmapPhase = page.locator("#roadmap select").first();
    const currentPhase = await roadmapPhase.inputValue();
    const nextPhase = currentPhase === "Build" ? "Plan" : "Build";
    await roadmapPhase.selectOption(nextPhase); await page.waitForTimeout(300);
    checks.roadmapPhaseChange = {
      selected: await page.locator("#roadmap select").first().inputValue(),
      message: await page.locator("#plannerStatus").innerText()
    };
    check("roadmap_phase_editable", checks.roadmapPhaseChange.selected === nextPhase
      && new RegExp(`Moved to ${nextPhase}`).test(checks.roadmapPhaseChange.message));

    const previousWorkspaceId = checks.workspace.id;
    page.once("dialog", (dialog) => dialog.accept());
    await page.locator("#deleteLocalData").click(); await page.waitForTimeout(300);
    checks.resetRoadmap = await page.evaluate(() => ({
      count: Number(document.querySelector("#savedCountBadge, #savedTrayCount, #mobileSavedCount")?.textContent || 0),
      id: localStorage.getItem("rerc.activeWorkspaceId.v2")
    }));
    check("roadmap_reset", checks.resetRoadmap.count === 0 && checks.resetRoadmap.id !== previousWorkspaceId && /^browser-/.test(checks.resetRoadmap.id || ""));

    await page.evaluate(() => window.RERCExplorer.chooseMode("Funding"));
    await page.locator('[data-action="planner-save"]').first().click(); await page.waitForTimeout(300);
    await selectStateFromAnyPhase(page, "New York");
    checks.stateSwitchClearsSaved = Number(await page.evaluate(() => document.querySelector("#savedCountBadge, #savedTrayCount, #mobileSavedCount")?.textContent || 0)) === 0;
    check("state_switch_clears_saved", checks.stateSwitchClearsSaved);
    await selectStateFromAnyPhase(page, "Virginia");
    await page.evaluate(() => window.RERCExplorer.chooseMode("Funding"));
    await page.locator('[data-action="planner-save"]').first().click();

    await page.locator("#openLanguage").click(); await page.locator("#languageDialog").waitFor({ state: "visible" });
    const spanishOption = page.locator('#languageDialog input[value="es"]');
    await spanishOption.click(); await page.locator("#languageDialog").waitFor({ state: "hidden" }); await page.waitForTimeout(100);
    await page.evaluate(() => window.RERCExplorer.chooseMode("Funding"));
    await page.waitForTimeout(150);
    const spanishCard = page.locator(".result-card").first();
    await spanishCard.locator("details").evaluate((node) => { node.open = true; });
    const spanishDeadlineText = await page.locator("#nextDeadlineMeta").innerText();
    const spanishMobileStartText = await page.locator('[data-mobile-action="filters"]').innerText();
    checks.spanish = {
      deadlineText: spanishDeadlineText,
      mobileStartText: spanishMobileStartText,
      lang: await page.locator("html").getAttribute("lang") === "es",
      stateIntro: /Primero, elija/.test(await page.locator("#communityFilters").innerText()),
      resources: /Recursos/.test(await page.locator("#showResources").innerText()),
      download: /Descargar RERC-e/.test(await page.locator("#rercieDownload").innerText()),
      website: /Sitio web del programa/.test(await spanishCard.innerText()),
      who: /Qui[eé]n:/.test(await spanishCard.innerText()),
      coverage: !/Coverage note:/.test(await page.locator("body").innerText()),
      deadline: /Quedan \d+ d.as|Vence hoy/u.test(spanishDeadlineText),
      mobileStart: /Inicio/.test(spanishMobileStartText),
      title: /Financiamiento para Virginia/.test(await page.locator("#communityTitle").innerText()),
      noEnglishDynamic: !/days? left|Due today/.test(await page.locator("body").innerText())
    };
    check("spanish_applied", Object.entries(checks.spanish).filter(([key]) => !key.endsWith("Text")).every(([, value]) => Boolean(value)));
    await page.locator("#openLanguage").click(); await page.locator('#languageDialog input[value="en"]').click();
    await page.locator("#languageDialog").waitFor({ state: "hidden" });
    checks.englishRestored = await page.locator("html").getAttribute("lang") === "en";
    check("english_restored", checks.englishRestored);

    downloads.csv = await download(page, "#exportPlanCsv", "plan.csv");
    downloads.docx = await download(page, "#exportPlanWord", "plan.docx");
    downloads.workspace = await download(page, "#exportWorkspaceFile", "plan.rerc-workspace");
    page.once("dialog", (dialog) => dialog.accept());
    downloads.rercie = await download(page, "#exportRercie", "plan.rercie");
    checks.rercie = JSON.parse(fs.readFileSync(downloads.rercie.file, "utf8"));
    check("download_events", Object.values(downloads).every((item) => item.bytes > 0));
    check("rercie_schema", checks.rercie.schema === "rercie-handoff" && checks.rercie.version === 1
      && !hasSensitiveKey(checks.rercie) && !/sk-[A-Za-z0-9]{12,}/.test(JSON.stringify(checks.rercie)));
    await page.screenshot({ path: path.join(outDir, "desktop.png"), fullPage: true });
    await context.close();

    checks.mobile = {};
    for (const width of [320, 390]) {
      const mobile = await browser.newContext({ viewport: { width, height: 844 } });
      const mobilePage = await mobile.newPage();
      mobilePage.on("pageerror", (error) => errors.push(`mobile:${width}:${error.message}`));
      await mobilePage.goto(baseUrl, { waitUntil: "networkidle", timeout: 60000 });
      await mobilePage.waitForSelector("html.rerc-planner-ready"); await mobilePage.waitForSelector("#stateSelect", { state: "visible" });
      const locked = await mobilePage.locator('#workflowSteps [data-wizard-step="2"], #workflowSteps [data-wizard-step="3"], #workflowSteps [data-wizard-step="4"]').evaluateAll((nodes) => nodes.every((node) => node.disabled));
      await selectState(mobilePage, "New Mexico");
      await mobilePage.locator('#workflowSteps [data-wizard-step="3"]').click(); await mobilePage.waitForSelector(".result-card");
      const controls = await mobilePage.locator("button, a, input, select").evaluateAll((nodes) => nodes.filter((node) => {
        const style = getComputedStyle(node); const box = node.getBoundingClientRect();
        return !node.matches('input[type="file"]') && style.display !== "none" && style.visibility !== "hidden" && box.width > 0 && box.height > 0;
      }).map((node) => Math.min(node.getBoundingClientRect().width, node.getBoundingClientRect().height)));
      checks.mobile[width] = {
        overflow: await overflow(mobilePage),
        bottomNav: await mobilePage.locator(".mobile-nav").isVisible(),
        controls44: controls.every((value) => value >= 44),
        lockedInitially: locked,
        stateSelected: await mobilePage.locator("#stateSelect").inputValue() === "New Mexico",
        results: await mobilePage.locator(".result-card").count() > 0
      };
      check(`mobile_${width}`, Object.values(checks.mobile[width]).every(Boolean));
      await mobilePage.screenshot({ path: path.join(outDir, `mobile-${width}.png`), fullPage: true });
      await mobile.close();
    }
    check("browser_errors", errors.length === 0);
  } finally {
    await browser.close();
  }

  const report = {
    status: failures.length ? "FAIL" : "PASS",
    baseUrl,
    checks,
    downloads: Object.fromEntries(Object.entries(downloads).map(([name, item]) => [name, { name: item.name, bytes: item.bytes }])),
    errors,
    failures
  };
  fs.writeFileSync(path.join(outDir, "playwright_qa.json"), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
  process.exitCode = failures.length ? 1 : 0;
}

main().catch((error) => { console.error(error.stack || String(error)); process.exitCode = 1; });
