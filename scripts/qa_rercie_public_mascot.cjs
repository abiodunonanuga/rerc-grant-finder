const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const url = process.argv[2] || "http://127.0.0.1:8877/";
const outDir = process.argv[3] || "browser-qa-rercie-mascot";
const chromePath = "C:\\\\Program Files\\\\Google\\\\Chrome\\\\Application\\\\chrome.exe";

function assert(value, message) { if (!value) throw new Error(message); }

async function inspect(page) {
  await page.goto(url, { waitUntil: "networkidle", timeout: 60000 });
  return page.locator(".rercie-mascot-stage").evaluate((stage) => ({
    stageAnimation: getComputedStyle(stage).animationName,
    wingAnimation: getComputedStyle(stage.querySelector(".rercie-wave-wing")).animationName,
    loaded: stage.querySelector("img").complete && stage.querySelector("img").naturalWidth > 0,
    noOverflow: document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1,
    catalogBusy: document.querySelector(".scene-catalog").getAttribute("aria-busy"),
  }));
}

async function main() {
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch(fs.existsSync(chromePath)
    ? { executablePath: chromePath, headless: true }
    : { headless: true });
  try {
    const desktop = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
    const desktopPage = await desktop.newPage();
    const errors = [];
    desktopPage.on("pageerror", (error) => errors.push(error.message));
    const active = await inspect(desktopPage);
    assert(active.stageAnimation === "rercie-bob" && active.wingAnimation === "rercie-wave", "Public RERC-e mascot is not waving");
    assert(active.loaded && active.noOverflow && active.catalogBusy === "false", "Public mascot image, layout, or catalog loading state failed");
    await desktopPage.locator("#rercie").screenshot({ path: path.join(outDir, "public-rercie-waving.png") });

    const reduced = await browser.newContext({ viewport: { width: 390, height: 844 }, reducedMotion: "reduce" });
    const reducedPage = await reduced.newPage();
    const quiet = await inspect(reducedPage);
    assert(quiet.stageAnimation === "none" && quiet.wingAnimation === "none", "Public mascot ignores reduced motion");
    assert(quiet.noOverflow, "Public RERC-e section overflows on mobile");
    await reducedPage.locator("#rercie").screenshot({ path: path.join(outDir, "public-rercie-mobile-static.png") });
    assert(errors.length === 0, `Browser errors: ${errors.join(" | ")}`);
    const report = { status: "PASS", active, reduced: quiet, errors };
    fs.writeFileSync(path.join(outDir, "qa_rercie_public_mascot.json"), JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report, null, 2));
  } finally {
    await browser.close();
  }
}

main().catch((error) => { console.error(error.stack || error.message); process.exit(1); });
