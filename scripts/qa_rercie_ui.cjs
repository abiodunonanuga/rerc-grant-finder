const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const baseUrl = process.argv[2] || "http://127.0.0.1:8791/";
const token = process.argv[3] || "rercie-qa-token";
const outDir = process.argv[4] || "browser-qa-rercie";
const chromePath = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function openPage(context) {
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });
  await page.route("**/api/grants", (route) => route.fulfill({
    status: 200, contentType: "application/json",
    body: JSON.stringify({ grants: [
      { item_id: "QA-GRANT", title: "Synthetic Trail Grant", organization: "QA agency", source_url: "https://example.org/grant" }
    ], updated: "Synthetic UI QA" })
  }));
  await page.goto(`${baseUrl}#token=${encodeURIComponent(token)}`, { waitUntil: "networkidle", timeout: 60000 });
  return { page, errors };
}

async function main() {
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch(fs.existsSync(chromePath)
    ? { executablePath: chromePath, headless: true }
    : { headless: true });
  try {
    const desktopContext = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
    const { page, errors } = await openPage(desktopContext);
    assert(await page.title() === "RERC-e Local Grant-Writing Guide", "Wrong RERC-e page title");
    assert(await page.locator("h1").innerText() === "Meet RERC-e", "RERC-e first screen is blank or wrong");
    const animation = await page.locator(".mascot-stage").evaluate((stage) => ({
      stage: getComputedStyle(stage).animationName,
      imageLoaded: stage.querySelector(".mascot").naturalWidth > 0,
      timerHidden: document.getElementById("workingTime").getAttribute("aria-hidden"),
    }));
    assert(animation.stage === "rercie-bob" && animation.imageLoaded, "RERC-e header image is not displayed");
    assert(animation.timerHidden === "true", "Generation timer is exposed through the live region");
    assert(await page.locator("#projectStep").isVisible() && !await page.locator("#fundingStep").isVisible(), "First screen does not focus on the project");
    await page.screenshot({ path: path.join(outDir, "rerc-e-project-step.png"), fullPage: true });

    await page.locator('[data-step="draft"]').click();
    await page.locator("#draftButton").click();
    assert(/Add the community/i.test(await page.locator("#status").innerText()), "Empty draft did not explain the first missing field");
    assert(await page.locator("#community").evaluate((node) => document.activeElement === node), "Missing community field was not focused");
    assert(await page.locator("#projectStep").isVisible(), "Input error did not return to the project step");

    await page.locator("#community").fill("St. Paul");
    await page.locator("#state").selectOption("Virginia");
    await page.locator("#projectTitle").fill("Downtown trail connection");
    await page.locator("#projectSummary").fill("Connect downtown businesses to the regional trail with safer wayfinding.");
    await page.locator("#nextFunding").click();
    await page.locator("#usePublicData").uncheck();
    await page.locator("#grantSelect").selectOption("0");
    assert(/Synthetic Trail Grant/.test(await page.locator("#fundingSummary").innerText()), "Funding step did not show the selected match");
    await page.screenshot({ path: path.join(outDir, "rerc-e-funding-step.png"), fullPage: true });
    await page.locator('[data-step="draft"]').click();
    await page.locator("#provider").selectOption("fallback");
    await page.locator("#draftButton").click();
    await page.waitForFunction(() => document.getElementById("output").textContent.includes("## Fit Summary"), null, { timeout: 30000 });
    assert(/Draft ready/i.test(await page.locator("#status").innerText()), "Fallback draft did not complete");

    const importedProfile = await page.evaluate(async ({ token }) => {
      const response = await fetch("/api/draft", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-RERCie-Token": token },
        body: JSON.stringify({
          community: "St. Paul", state: "Virginia", projectTitle: "Trail", projectNotes: "Connect the trail.",
          publicProfile: { place: "St. Paul town, Virginia", population: "0", source: "Imported profile", source_url: "https://data.census.gov/" },
          usePublicData: false, provider: "fallback"
        })
      });
      return response.json();
    }, { token });
    assert(importedProfile.profileStatus === "imported" && importedProfile.draft.includes("Population: 0"), "Imported profile facts did not reach drafting");

    await page.locator('[data-step="funding"]').click();
    await page.locator("#fileInput").setInputFiles({
      name: "too-large.txt", mimeType: "text/plain", buffer: Buffer.alloc(513 * 1024, "a")
    });
    assert(/under 512 KB/i.test(await page.locator("#status").innerText()), "Oversized file did not produce the bounded recovery message");
    await page.locator('[data-step="draft"]').click();
    await page.screenshot({ path: path.join(outDir, "rercie-desktop.png"), fullPage: true });

    const reducedContext = await browser.newContext({ viewport: { width: 390, height: 844 }, reducedMotion: "reduce" });
    const reduced = await openPage(reducedContext);
    const reducedAnimation = await reduced.page.locator(".mascot-stage").evaluate((stage) => ({
      stage: getComputedStyle(stage).animationName,
      imageLoaded: stage.querySelector(".mascot").naturalWidth > 0,
      overflow: document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1,
    }));
    assert(reducedAnimation.stage === "none" && reducedAnimation.imageLoaded, "Reduced-motion preference did not stop mascot animation");
    assert(reducedAnimation.overflow, "RERC-e mobile interface has horizontal overflow");
    await reduced.page.screenshot({ path: path.join(outDir, "rercie-mobile-reduced-motion.png"), fullPage: true });
    assert(errors.length === 0 && reduced.errors.length === 0, `Browser errors: ${[...errors, ...reduced.errors].join(" | ")}`);

    const report = { status: "PASS", animation, importedProfile: { status: importedProfile.profileStatus }, reducedAnimation, errors };
    fs.writeFileSync(path.join(outDir, "qa_rercie_ui.json"), JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report, null, 2));
  } finally {
    await browser.close();
  }
}

main().catch((error) => { console.error(error.stack || error.message); process.exit(1); });
