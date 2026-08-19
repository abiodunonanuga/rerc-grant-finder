const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");
const { chromium } = require("playwright");

const baseUrl = process.argv[2] || "http://127.0.0.1:8877/";
const outDir = process.argv[3] || "browser-qa-usability-feedback";
const chromePath = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function prepare(page, state = "Virginia") {
  await page.goto(baseUrl, { waitUntil: "networkidle", timeout: 60000 });
  await page.waitForSelector("html.rerc-planner-ready");
  await page.locator("#stateSelect").selectOption({ label: state });
  await page.locator('#workflowSteps [data-wizard-step="3"]').click();
  await page.waitForSelector(".result-card");
}

async function main() {
  fs.mkdirSync(outDir, { recursive: true });
  const errors = [];
  const browser = await chromium.launch(fs.existsSync(chromePath)
    ? { executablePath: chromePath, headless: true }
    : { headless: true });
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, acceptDownloads: true });
    const page = await context.newPage();
    page.on("pageerror", (error) => errors.push(error.message));
    await prepare(page);

    await page.evaluate(() => window.RERCExplorer.chooseMode("Resource"));
    const resourceBefore = await page.evaluate(() => window.RERCExplorer.getMatches().length);
    const dataFiltered = await page.evaluate(() => {
      const input = document.querySelector('#resourceTypeOptions input[value="data"]');
      input.checked = true;
      input.dispatchEvent(new Event("change", { bubbles: true }));
      const matches = window.RERCExplorer.getMatches();
      return {
        count: matches.length,
        valid: matches.every((item) => item.item_type === "Resource" && window.RERCExplorer.resourceTypeLabels(item).includes("data")),
      };
    });
    assert(resourceBefore > dataFiltered.count && dataFiltered.count > 0, "Resource type filter did not narrow the list");
    assert(dataFiltered.valid, "Resource type filter returned an incorrectly classified item");

    await page.evaluate(() => {
      document.querySelectorAll("#resourceTypeOptions input").forEach((input) => { input.checked = false; });
      window.RERCExplorer.chooseMode("Case Study");
    });
    await page.waitForTimeout(150);
    const featured = await page.evaluate(() => ({
      total: window.RERCExplorer.getMatches().length,
      cards: document.querySelectorAll("#results .result-card.case-study").length,
      controlVisible: !document.getElementById("caseStudyViewControl").hidden,
      collectionsVisible: !document.getElementById("caseStudyCollections").hidden,
      collectionLinks: [...document.querySelectorAll("#caseStudyCollections a")].map((link) => link.href),
    }));
    assert(featured.total > 24 && featured.cards === 24, "Case-study featured view is not capped at 24 ranked examples");
    assert(featured.controlVisible && featured.collectionsVisible, "Case-study controls or source collections are hidden");
    assert(featured.collectionLinks.length === 4 && featured.collectionLinks.every((url) => /^https:\/\//.test(url)), "Case-study parent links are incomplete");

    await page.locator("#caseStudyViewSelect").selectOption("all");
    await page.waitForTimeout(100);
    const allCards = await page.locator("#results .result-card.case-study").count();
    assert(allCards === featured.total, "All case studies option does not reveal the full filtered set");

    await page.locator('#results .result-card.case-study [data-action="planner-save"]').nth(0).click();
    await page.locator('#results .result-card.case-study [data-action="planner-save"]').nth(1).click();
    const downloadEvent = page.waitForEvent("download");
    await page.locator("#exportPlanWord").click();
    const download = await downloadEvent;
    const docxPath = path.join(outDir, "saved-plan.docx");
    await download.saveAs(docxPath);
    const inspectCode = [
      "import json,sys,zipfile",
      "z=zipfile.ZipFile(sys.argv[1])",
      "doc=z.read('word/document.xml').decode('utf-8')",
      "styles=z.read('word/styles.xml').decode('utf-8')",
      "print(json.dumps({'page_breaks':doc.count('w:type=\\\"page\\\"'),'category_refs':doc.count('w:val=\\\"Category\\\"'),'keyvalue_refs':doc.count('w:val=\\\"KeyValue\\\"'),'green':'175641' in styles,'category_style':'w:styleId=\\\"Category\\\"' in styles,'keyvalue_style':'w:styleId=\\\"KeyValue\\\"' in styles}))",
    ].join(";");
    const docx = JSON.parse(execFileSync("python", ["-c", inspectCode, docxPath], { encoding: "utf8" }));
    assert(docx.page_breaks === 2, "Saved-plan Word export does not place each selected item on its own page");
    assert(docx.category_refs === 2 && docx.keyvalue_refs > 2, "Saved-plan Word export lacks category or labeled metadata formatting");
    assert(docx.green && docx.category_style && docx.keyvalue_style, "Saved-plan Word styles are incomplete");

    const mobile = await context.newPage();
    await mobile.setViewportSize({ width: 390, height: 844 });
    await prepare(mobile);
    await mobile.evaluate(() => window.RERCExplorer.chooseMode("Case Study"));
    await mobile.waitForTimeout(100);
    const mobileChecks = await mobile.evaluate(() => ({
      noOverflow: document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1,
      resourceOptions: document.querySelectorAll("#resourceTypeOptions input").length,
      collectionColumns: getComputedStyle(document.querySelector("#caseStudyCollections ul")).gridTemplateColumns.split(" ").length,
      caseCards: document.querySelectorAll("#results .result-card.case-study").length,
    }));
    assert(mobileChecks.noOverflow, "Mobile page has horizontal overflow");
    assert(mobileChecks.resourceOptions === 6, "Mobile resource type controls are incomplete");
    assert(mobileChecks.collectionColumns === 1 && mobileChecks.caseCards === 24, "Mobile case-study layout is not compact and single-column");
    assert(errors.length === 0, `Browser errors: ${errors.join(" | ")}`);

    const report = { status: "PASS", resourceBefore, dataFiltered, featured, docx, mobileChecks, errors };
    fs.writeFileSync(path.join(outDir, "qa_usability_feedback.json"), JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report, null, 2));
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error.stack || error.message);
  process.exit(1);
});
