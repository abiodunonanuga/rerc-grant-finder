const fs = require("fs");
const http = require("http");
const path = require("path");
const { spawn } = require("child_process");
const { chromium } = require("playwright");
const axe = require("axe-core");

const root = path.resolve(__dirname, "..");
const outDir = path.resolve(process.argv[2] || path.join(root, "browser-qa", "accessibility"));
const explorerPort = Number(process.env.RERC_A11Y_EXPLORER_PORT || 8892);
const guidePort = Number(process.env.RERC_A11Y_GUIDE_PORT || 8893);
const guideToken = "rerc-e-accessibility-qa-token";
const chromePath = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const liveUrl = process.env.RERC_A11Y_LIVE_URL || "";

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function relativeLuminance(hex) {
  const components = [1, 3, 5].map((index) => Number.parseInt(hex.slice(index, index + 2), 16) / 255)
    .map((value) => value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4);
  return 0.2126 * components[0] + 0.7152 * components[1] + 0.0722 * components[2];
}

function contrastRatio(foreground, background) {
  const first = relativeLuminance(foreground);
  const second = relativeLuminance(background);
  return (Math.max(first, second) + 0.05) / (Math.min(first, second) + 0.05);
}

function composite(foreground, background, opacity) {
  const foregroundChannels = [1, 3, 5].map((index) => Number.parseInt(foreground.slice(index, index + 2), 16));
  const backgroundChannels = [1, 3, 5].map((index) => Number.parseInt(background.slice(index, index + 2), 16));
  return `#${foregroundChannels.map((value, index) => Math.round(value * opacity + backgroundChannels[index] * (1 - opacity)).toString(16).padStart(2, "0")).join("")}`;
}

function contrastEvidence() {
  const lightestHeroPixelAfterOverlay = composite("#072a1f", "#ffffff", 0.72);
  const pairs = {
    explorerHeroEyebrowWorstCase: ["#cce9d9", lightestHeroPixelAfterOverlay],
    explorerHeroBodyWorstCase: ["#ffffff", lightestHeroPixelAfterOverlay],
    explorerPrimaryAction: ["#17251f", "#f2c14e"],
    explorerMutedOnWhite: ["#52615b", "#ffffff"],
    explorerRiverLinkOnWhite: ["#1b6a8f", "#ffffff"],
    guideWhiteOnForest: ["#ffffff", "#173f35"],
    guideWhiteOnGreen: ["#ffffff", "#00573f"],
    guideHeaderCopyOnGreen: ["#e4f1eb", "#00573f"],
    guideMutedOnWhite: ["#5d6b66", "#ffffff"],
  };
  return Object.fromEntries(Object.entries(pairs).map(([name, colors]) => [name, {
    foreground: colors[0],
    background: colors[1],
    ratio: Math.round(contrastRatio(colors[0], colors[1]) * 100) / 100,
    required: 4.5,
  }]));
}

function contentType(file) {
  const extension = path.extname(file).toLowerCase();
  return ({
    ".css": "text/css; charset=utf-8",
    ".csv": "text/csv; charset=utf-8",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".html": "text/html; charset=utf-8",
    ".ico": "image/x-icon",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  })[extension] || "application/octet-stream";
}

function startStaticServer() {
  const server = http.createServer((request, response) => {
    try {
      const requestUrl = new URL(request.url, `http://127.0.0.1:${explorerPort}`);
      const relative = decodeURIComponent(requestUrl.pathname === "/" ? "/index.html" : requestUrl.pathname);
      const file = path.resolve(root, `.${relative}`);
      if (file !== root && !file.startsWith(`${root}${path.sep}`)) {
        response.writeHead(403).end("Forbidden");
        return;
      }
      if (!fs.existsSync(file) || !fs.statSync(file).isFile()) {
        response.writeHead(404).end("Not found");
        return;
      }
      response.writeHead(200, { "Content-Type": contentType(file), "Cache-Control": "no-store" });
      fs.createReadStream(file).pipe(response);
    } catch (error) {
      response.writeHead(500).end(error.message);
    }
  });
  return new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(explorerPort, "127.0.0.1", () => resolve(server));
  });
}

async function waitFor(url, headers = {}) {
  let lastError;
  for (let attempt = 0; attempt < 80; attempt += 1) {
    try {
      const response = await fetch(url, { headers });
      if (response.ok) return;
      lastError = new Error(`${url} returned ${response.status}`);
    } catch (error) {
      lastError = error;
    }
    await new Promise((resolve) => setTimeout(resolve, 125));
  }
  throw lastError || new Error(`${url} did not become ready`);
}

function startGuideService() {
  const environment = {
    ...process.env,
    RERCIE_SESSION_TOKEN: guideToken,
    RERCIE_EXPECTED_HOST: `127.0.0.1:${guidePort}`,
    RERCIE_APP_ROOT: path.join(root, "rercie"),
    PYTHONDONTWRITEBYTECODE: "1",
  };
  return spawn("python", ["rercie.py", "--serve", "--host", "127.0.0.1", "--port", String(guidePort)], {
    cwd: path.join(root, "rercie"),
    env: environment,
    stdio: ["ignore", "ignore", "pipe"],
    windowsHide: true,
  });
}

function delay(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

async function stopChild(child) {
  if (!child || child.exitCode !== null) return;
  const exited = new Promise((resolve) => child.once("exit", resolve));
  child.kill();
  await Promise.race([exited, delay(3000)]);
  if (child.exitCode === null) {
    child.kill("SIGKILL");
    await Promise.race([exited, delay(2000)]);
  }
  child.stderr?.destroy();
  child.unref();
}

function simplifyAxe(result) {
  return {
    id: result.id,
    impact: result.impact,
    help: result.help,
    helpUrl: result.helpUrl,
    tags: result.tags,
    nodes: result.nodes.map((node) => ({
      target: node.target,
      html: node.html,
      failureSummary: node.failureSummary,
    })),
  };
}

async function axeAudit(page, name) {
  await page.waitForFunction(() => Boolean(window.axe), null, { timeout: 10000 });
  const results = await page.evaluate(async () => window.axe.run(document, {
    runOnly: {
      type: "tag",
      values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"],
    },
    resultTypes: ["violations", "incomplete", "passes"],
  }));
  return {
    name,
    url: page.url(),
    violations: results.violations.map(simplifyAxe),
    incomplete: results.incomplete.map(simplifyAxe),
    passRuleCount: results.passes.length,
  };
}

async function keyboardSample(page, maximum = 45) {
  await page.evaluate(() => {
    const active = document.activeElement;
    if (active && typeof active.blur === "function") active.blur();
    window.scrollTo(0, 0);
  });
  const sample = [];
  const seen = new Map();
  for (let index = 0; index < maximum; index += 1) {
    await page.keyboard.press("Tab");
    const focused = await page.evaluate(() => {
      const node = document.activeElement;
      if (!node || node === document.body) return null;
      const rect = node.getBoundingClientRect();
      const style = getComputedStyle(node);
      const text = (node.getAttribute("aria-label") || node.innerText || node.value || node.getAttribute("title") || "").trim().replace(/\s+/g, " ").slice(0, 120);
      return {
        tag: node.tagName.toLowerCase(),
        id: node.id || "",
        text,
        visible: rect.width > 0 && rect.height > 0 && style.visibility !== "hidden" && style.display !== "none",
        rect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
        outlineStyle: style.outlineStyle,
        outlineWidth: style.outlineWidth,
        boxShadow: style.boxShadow,
      };
    });
    if (!focused) continue;
    const key = `${focused.tag}#${focused.id}:${focused.text}`;
    if (seen.has(key)) break;
    seen.set(key, true);
    sample.push(focused);
  }
  return sample;
}

async function skipLinkCheck(page, expectedTarget) {
  await page.evaluate(() => {
    const active = document.activeElement;
    if (active && typeof active.blur === "function") active.blur();
    history.replaceState(null, "", location.pathname + location.search);
    window.scrollTo(0, 0);
  });
  await page.keyboard.press("Tab");
  const first = await page.evaluate(() => ({
    text: (document.activeElement?.innerText || "").trim(),
    href: document.activeElement?.getAttribute?.("href") || "",
  }));
  await page.keyboard.press("Enter");
  await page.waitForTimeout(50);
  const result = await page.evaluate(() => ({
    activeId: document.activeElement?.id || "",
    hash: location.hash,
  }));
  return { first, ...result, passed: first.href === `#${expectedTarget}` && result.activeId === expectedTarget };
}

async function optionalSkipLinkCheck(page) {
  await page.evaluate(() => {
    const active = document.activeElement;
    if (active && typeof active.blur === "function") active.blur();
    history.replaceState(null, "", location.pathname + location.search);
    window.scrollTo(0, 0);
  });
  await page.keyboard.press("Tab");
  const first = await page.evaluate(() => ({
    text: (document.activeElement?.innerText || "").trim(),
    href: document.activeElement?.getAttribute?.("href") || "",
  }));
  if (!first.href.startsWith("#") || first.href.length < 2) return { first, activeId: "", hash: "", passed: false };
  const target = first.href.slice(1);
  const exists = await page.evaluate((id) => Boolean(document.getElementById(id)), target);
  if (!exists) return { first, activeId: "", hash: "", passed: false };
  await page.keyboard.press("Enter");
  await page.waitForTimeout(50);
  const result = await page.evaluate(() => ({ activeId: document.activeElement?.id || "", hash: location.hash }));
  return { first, ...result, passed: result.activeId === target };
}

async function layoutChecks(page) {
  return page.evaluate(() => {
    const visible = (node) => {
      const style = getComputedStyle(node);
      const rect = node.getBoundingClientRect();
      return rect.width > 0 && rect.height > 0 && style.visibility !== "hidden" && style.display !== "none";
    };
    const targets = [...document.querySelectorAll("a[href],button,input,select,textarea,summary,[tabindex]")]
      .filter(visible)
      .map((node) => {
        const rect = node.getBoundingClientRect();
        return {
          selector: node.id ? `#${node.id}` : `${node.tagName.toLowerCase()}.${[...node.classList].slice(0, 2).join(".")}`,
          name: (node.getAttribute("aria-label") || node.innerText || node.value || "").trim().replace(/\s+/g, " ").slice(0, 80),
          width: Math.round(rect.width * 10) / 10,
          height: Math.round(rect.height * 10) / 10,
        };
      });
    return {
      viewport: { width: innerWidth, height: innerHeight },
      document: { width: document.documentElement.scrollWidth, height: document.documentElement.scrollHeight },
      horizontalPageOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
      tinyTargets: targets.filter((item) => item.width < 24 || item.height < 24),
      smallTargets: targets.filter((item) => item.width < 44 || item.height < 44),
      landmarks: {
        header: document.querySelectorAll("header").length,
        nav: document.querySelectorAll("nav").length,
        main: document.querySelectorAll("main").length,
        aside: document.querySelectorAll("aside").length,
        footer: document.querySelectorAll("footer").length,
      },
      headings: [...document.querySelectorAll("h1,h2,h3,h4,h5,h6")].filter(visible).map((node) => ({
        level: Number(node.tagName.slice(1)),
        text: node.textContent.trim().replace(/\s+/g, " ").slice(0, 120),
      })),
    };
  });
}

async function textSpacingCheck(page) {
  await page.evaluate(() => {
    for (const node of document.querySelectorAll("*")) {
      node.style.setProperty("line-height", "1.5", "important");
      node.style.setProperty("letter-spacing", ".12em", "important");
      node.style.setProperty("word-spacing", ".16em", "important");
    }
    for (const paragraph of document.querySelectorAll("p")) paragraph.style.setProperty("margin-bottom", "2em", "important");
  });
  return page.evaluate(() => ({
    horizontalPageOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
    clippedText: [...document.querySelectorAll("p,li,label,button,a,h1,h2,h3,h4,h5,h6,summary")].filter((node) => {
      const style = getComputedStyle(node);
      const rect = node.getBoundingClientRect();
      if (!rect.width || !rect.height || style.display === "none" || style.visibility === "hidden") return false;
      return node.scrollHeight > node.clientHeight + 1 && !["auto", "scroll"].includes(style.overflowY);
    }).slice(0, 30).map((node) => ({ tag: node.tagName.toLowerCase(), id: node.id, text: node.textContent.trim().replace(/\s+/g, " ").slice(0, 100) })),
  }));
}

async function auditExplorer(browser, baseUrl, prefix) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, reducedMotion: "no-preference" });
  await context.addInitScript({ content: axe.source });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });
  await page.goto(baseUrl, { waitUntil: "networkidle", timeout: 60000 });
  await page.waitForSelector("html.rerc-planner-ready", { timeout: 60000 });
  const initial = await axeAudit(page, `${prefix}: initial location step`);
  const keyboard = await keyboardSample(page);
  const firstTab = keyboard[0] || null;
  await page.reload({ waitUntil: "networkidle", timeout: 60000 });
  await page.waitForSelector("html.rerc-planner-ready", { timeout: 60000 });
  const skipLink = await skipLinkCheck(page, "finder");
  await page.locator("#stateSelect").selectOption({ label: "Virginia" });
  await page.locator('#workflowSteps [data-wizard-step="2"]').click();
  const priorities = await axeAudit(page, `${prefix}: priorities step`);
  await page.locator('#workflowSteps [data-wizard-step="3"]').click();
  await page.waitForSelector(".result-card", { timeout: 60000 });
  const matches = await axeAudit(page, `${prefix}: matches and plan workspace`);
  const desktopLayout = await layoutChecks(page);
  await page.screenshot({ path: path.join(outDir, `${prefix}-desktop.png`), fullPage: true });
  const languageButton = page.locator("#openLanguage");
  if (await languageButton.count()) {
    await languageButton.click();
    await page.locator("#languageDialog").waitFor({ state: "visible" });
  }
  const dialog = await axeAudit(page, `${prefix}: language dialog`);
  if (await page.locator("#languageDialog").isVisible()) await page.keyboard.press("Escape");
  await context.close();

  const narrowContext = await browser.newContext({ viewport: { width: 320, height: 800 }, reducedMotion: "reduce" });
  await narrowContext.addInitScript({ content: axe.source });
  const narrow = await narrowContext.newPage();
  await narrow.goto(baseUrl, { waitUntil: "networkidle", timeout: 60000 });
  await narrow.waitForSelector("html.rerc-planner-ready", { timeout: 60000 });
  const narrowLayout = await layoutChecks(narrow);
  const narrowAxe = await axeAudit(narrow, `${prefix}: 320 CSS pixel reflow and reduced motion`);
  const reducedMotion = await narrow.evaluate(() => ({
    requested: matchMedia("(prefers-reduced-motion: reduce)").matches,
    animatedElements: [...document.querySelectorAll("*")].filter((node) => {
      const style = getComputedStyle(node);
      return style.animationName !== "none" && style.animationDuration !== "0s";
    }).slice(0, 20).map((node) => ({ tag: node.tagName.toLowerCase(), id: node.id, className: node.className })),
  }));
  const textSpacing = await textSpacingCheck(narrow);
  await narrow.screenshot({ path: path.join(outDir, `${prefix}-320px-text-spacing.png`), fullPage: true });
  await narrowContext.close();
  return { initial, priorities, matches, dialog, narrowAxe, skipLink, keyboard, firstTab, desktopLayout, narrowLayout, reducedMotion, textSpacing, errors };
}

async function auditLiveExplorer(browser, baseUrl) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, reducedMotion: "no-preference" });
  await context.addInitScript({ content: axe.source });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });
  await page.goto(baseUrl, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForSelector("body", { timeout: 10000 });
  await page.waitForTimeout(3000);
  const readiness = await page.evaluate(() => ({
    plannerReady: document.documentElement.classList.contains("rerc-planner-ready"),
    title: document.title,
    interactiveCount: document.querySelectorAll("a[href],button,input,select,textarea,summary,[tabindex]").length,
  }));
  const initial = await axeAudit(page, "public RERC Explorer: rendered page");
  const keyboard = await keyboardSample(page);
  await page.reload({ waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForTimeout(1500);
  const skipLink = await optionalSkipLinkCheck(page);
  const desktopLayout = await layoutChecks(page);
  await page.screenshot({ path: path.join(outDir, "rerc-explorer-live-desktop.png"), fullPage: true });
  await context.close();

  const narrowContext = await browser.newContext({ viewport: { width: 320, height: 800 }, reducedMotion: "reduce" });
  await narrowContext.addInitScript({ content: axe.source });
  const narrow = await narrowContext.newPage();
  await narrow.goto(baseUrl, { waitUntil: "domcontentloaded", timeout: 60000 });
  await narrow.waitForSelector("body", { timeout: 10000 });
  await narrow.waitForTimeout(1500);
  const narrowLayout = await layoutChecks(narrow);
  const narrowAxe = await axeAudit(narrow, "public RERC Explorer: 320 CSS pixel reflow and reduced motion");
  const reducedMotion = await narrow.evaluate(() => ({
    requested: matchMedia("(prefers-reduced-motion: reduce)").matches,
    animatedElements: [...document.querySelectorAll("*")].filter((node) => {
      const style = getComputedStyle(node);
      return style.animationName !== "none" && style.animationDuration !== "0s";
    }).slice(0, 20).map((node) => ({ tag: node.tagName.toLowerCase(), id: node.id, className: node.className })),
  }));
  const textSpacing = await textSpacingCheck(narrow);
  await narrow.screenshot({ path: path.join(outDir, "rerc-explorer-live-320px-text-spacing.png"), fullPage: true });
  await narrowContext.close();
  return { readiness, initial, narrowAxe, skipLink, keyboard, desktopLayout, narrowLayout, reducedMotion, textSpacing, errors };
}

async function mockGuideApi(page) {
  await page.route("**/api/runtime", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ ready: true }) }));
  await page.route("**/api/grants", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      grants: [{ item_id: "A11Y-GRANT", title: "Accessibility Test Grant", organization: "QA agency", source_url: "https://example.org/grant" }],
      updated: "Synthetic accessibility QA",
    }),
  }));
}

async function auditGuide(browser, baseUrl) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, reducedMotion: "no-preference" });
  await context.addInitScript({ content: axe.source });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });
  await mockGuideApi(page);
  await page.goto(`${baseUrl}#token=${encodeURIComponent(guideToken)}`, { waitUntil: "networkidle", timeout: 60000 });
  const project = await axeAudit(page, "RERC-e: project step");
  const keyboard = await keyboardSample(page);
  await page.reload({ waitUntil: "networkidle", timeout: 60000 });
  const skipLink = await skipLinkCheck(page, "mainContent");
  await page.locator('[data-step="funding"]').click();
  const funding = await axeAudit(page, "RERC-e: funding and notes step");
  await page.locator('[data-step="draft"]').click();
  const draft = await axeAudit(page, "RERC-e: draft and export step");
  const desktopLayout = await layoutChecks(page);
  await page.screenshot({ path: path.join(outDir, "rerc-e-desktop.png"), fullPage: true });
  await context.close();

  const narrowContext = await browser.newContext({ viewport: { width: 320, height: 800 }, reducedMotion: "reduce" });
  await narrowContext.addInitScript({ content: axe.source });
  const narrow = await narrowContext.newPage();
  await mockGuideApi(narrow);
  await narrow.goto(`${baseUrl}#token=${encodeURIComponent(guideToken)}`, { waitUntil: "networkidle", timeout: 60000 });
  const narrowLayout = await layoutChecks(narrow);
  const narrowAxe = await axeAudit(narrow, "RERC-e: 320 CSS pixel reflow and reduced motion");
  const reducedMotion = await narrow.evaluate(() => ({
    requested: matchMedia("(prefers-reduced-motion: reduce)").matches,
    mascotAnimation: getComputedStyle(document.querySelector(".mascot-stage")).animationName,
  }));
  const textSpacing = await textSpacingCheck(narrow);
  await narrow.screenshot({ path: path.join(outDir, "rerc-e-320px-text-spacing.png"), fullPage: true });
  await narrowContext.close();
  return { project, funding, draft, narrowAxe, skipLink, keyboard, desktopLayout, narrowLayout, reducedMotion, textSpacing, errors };
}

function allViolations(report) {
  const results = [];
  const walk = (value) => {
    if (!value || typeof value !== "object") return;
    if (Array.isArray(value.violations)) results.push(...value.violations.map((violation) => ({ audit: value.name, ...violation })));
    Object.values(value).forEach(walk);
  };
  walk(report);
  return results;
}

async function main() {
  fs.mkdirSync(outDir, { recursive: true });
  const staticServer = await startStaticServer();
  const guideService = startGuideService();
  let guideStderr = "";
  guideService.stderr.on("data", (chunk) => { guideStderr += chunk.toString(); });
  let browser;
  try {
    await waitFor(`http://127.0.0.1:${explorerPort}/`);
    await waitFor(`http://127.0.0.1:${guidePort}/health`, { "X-RERC-e-Token": guideToken, Host: `127.0.0.1:${guidePort}` });
    browser = await chromium.launch(fs.existsSync(chromePath) ? { executablePath: chromePath, headless: true } : { headless: true });
    const report = {
      standard: "WCAG 2.2 Level AA",
      testedAt: new Date().toISOString(),
      scope: ["local RERC Explorer source", "local RERC-e source", ...(liveUrl ? [liveUrl] : [])],
      explorer: await auditExplorer(browser, `http://127.0.0.1:${explorerPort}/`, "rerc-explorer-local"),
      guide: await auditGuide(browser, `http://127.0.0.1:${guidePort}/`),
      manualContrast: contrastEvidence(),
    };
    if (liveUrl) report.live = await auditLiveExplorer(browser, liveUrl);
    report.automatedViolations = allViolations(report);
    report.summary = {
      automatedViolationRuleCount: new Set(report.automatedViolations.map((item) => item.id)).size,
      automatedViolationInstanceCount: report.automatedViolations.reduce((sum, item) => sum + item.nodes.length, 0),
      localExplorerFirstTabIsSkipLink: report.explorer.firstTab?.text?.toLowerCase().includes("skip") || false,
      localExplorerReflowsAt320: !report.explorer.narrowLayout.horizontalPageOverflow,
      guideReflowsAt320: !report.guide.narrowLayout.horizontalPageOverflow,
      reducedMotionExplorer: report.explorer.reducedMotion.requested && report.explorer.reducedMotion.animatedElements.length === 0,
      reducedMotionGuide: report.guide.reducedMotion.requested && report.guide.reducedMotion.mascotAnimation === "none",
      explorerSkipLinkWorks: report.explorer.skipLink.passed,
      guideSkipLinkWorks: report.guide.skipLink.passed,
      manualContrastPairsPass: Object.values(report.manualContrast).every((pair) => pair.ratio >= pair.required),
      liveExplorerPlannerReady: report.live ? report.live.readiness.plannerReady : null,
      liveExplorerReflowsAt320: report.live ? !report.live.narrowLayout.horizontalPageOverflow : null,
      liveExplorerSkipLinkWorks: report.live ? report.live.skipLink.passed : null,
      reducedMotionLiveExplorer: report.live ? report.live.reducedMotion.requested && report.live.reducedMotion.animatedElements.length === 0 : null,
    };
    fs.writeFileSync(path.join(outDir, "accessibility-audit.json"), JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report.summary, null, 2));
    if (report.automatedViolations.length) {
      console.error(JSON.stringify(report.automatedViolations, null, 2));
      process.exitCode = 2;
    }
    assert(report.summary.localExplorerFirstTabIsSkipLink, "The Explorer skip link is not first in keyboard order");
    assert(report.summary.localExplorerReflowsAt320, "The Explorer has page-level horizontal overflow at 320 CSS pixels");
    assert(report.summary.guideReflowsAt320, "RERC-e has page-level horizontal overflow at 320 CSS pixels");
    assert(report.summary.reducedMotionExplorer, "The Explorer still animates when reduced motion is requested");
    assert(report.summary.reducedMotionGuide, "RERC-e still animates when reduced motion is requested");
    assert(report.summary.explorerSkipLinkWorks, "The Explorer skip link does not move keyboard focus to the main content");
    assert(report.summary.guideSkipLinkWorks, "The RERC-e skip link does not move keyboard focus to the main content");
    assert(report.summary.manualContrastPairsPass, "A manually evaluated foreground/background color pair does not meet 4.5:1 contrast");
  } finally {
    if (browser) await Promise.race([browser.close(), delay(10000)]);
    if (typeof staticServer.closeAllConnections === "function") staticServer.closeAllConnections();
    await Promise.race([new Promise((resolve) => staticServer.close(resolve)), delay(3000)]);
    await stopChild(guideService);
    if (guideStderr.trim()) fs.writeFileSync(path.join(outDir, "rerc-e-service-stderr.log"), guideStderr);
  }
}

main().then(
  () => process.exit(process.exitCode || 0),
  (error) => {
    console.error(error.stack || error.message);
    process.exit(1);
  },
);
