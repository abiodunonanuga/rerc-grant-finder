"use strict";

const fundingResources = Array.isArray(window.RERC_CATALOG?.items) ? window.RERC_CATALOG.items : [];
const caseStudies = Array.isArray(window.RERC_CASE_STUDIES?.items) ? window.RERC_CASE_STUDIES.items : [];
const catalog = [...fundingResources, ...caseStudies];

const places = [
  "Alabama","Alaska","Arizona","Arkansas","California","Colorado","Connecticut","Delaware","District of Columbia",
  "Florida","Georgia","Hawaii","Idaho","Illinois","Indiana","Iowa","Kansas","Kentucky","Louisiana","Maine",
  "Maryland","Massachusetts","Michigan","Minnesota","Mississippi","Missouri","Montana","Nebraska","Nevada",
  "New Hampshire","New Jersey","New Mexico","New York","North Carolina","North Dakota","Ohio","Oklahoma","Oregon",
  "Pennsylvania","Rhode Island","South Carolina","South Dakota","Tennessee","Texas","Utah","Vermont","Virginia",
  "Washington","West Virginia","Wisconsin","Wyoming","American Samoa","Guam","Northern Mariana Islands","Puerto Rico",
  "U.S. Virgin Islands"
];

const territoryPlaces = new Set(["American Samoa","Guam","Northern Mariana Islands","Puerto Rico","U.S. Virgin Islands"]);

const siteConfig = window.RERC_SITE_CONFIG || {};
const rankingConfig = siteConfig.ranking || {};
const rankingWeights = rankingConfig.weights || {};
const rankingBase = rankingConfig.base || {};
const rankingThresholds = rankingConfig.thresholds || {};

const defaultApplicantOptions = [
  ["local government|local governments|municipal|municipality|municipalities|county|counties|city|cities|town|towns|village|villages|political subdivision|political subdivisions", "Local government"],
  ["tribe|tribes|tribal|native|indian nation|indian nations|sovereign", "Tribe or Native community"],
  ["nonprofit|nonprofits|non-profit|non-profits|community organization|community organizations|land trust|land trusts", "Nonprofit or community group"],
  ["state agency|state agencies|state government", "State agency"],
  ["business|businesses|entrepreneur|entrepreneurs|tourism|destination marketing|convention|visitors bureau|visitor bureau", "Business or tourism group"],
  ["school|schools|college|colleges|university|universities|library|libraries|museum|museums", "School, library, or museum"],
  ["utility|utilities|authority|authorities|district|districts", "Utility or public authority"],
  ["landowner|landowners|individual|individuals|families", "Landowner or individual"],
  ["__other__", "Other or varies by program"]
];

const defaultTopicOptions = [
  ["trail|park|recreation|outdoor access", "Parks, trails, and outdoor access"],
  ["downtown|main street|gateway|placemaking", "Downtown and Main Street"],
  ["tourism|visitor|recreation economy", "Tourism and visitor economy"],
  ["business|entrepreneur|workforce|economic development", "Business and jobs"],
  ["transportation|street|road|roadway|highway|guardrail|barrier|traffic safety|hsip|bike|pedestrian|transit|mobility", "Transportation and safe access"],
  ["water|wastewater|stormwater|flood|coastal|resilience|disaster|hazard|mitigation|emergency|wildfire|drought|earthquake|storm", "Disaster, water, and resilience"],
  ["river-access", "River access"],
  ["conservation|environment|environmental|habitat|forest|land|river|watershed", "Conservation and public lands"],
  ["historic|heritage|arts|culture|museum", "History, arts, and culture"],
  ["housing|community facility|community facilities|community services|public facilities|infrastructure|public safety|emergency services|education|health|food", "Community services"],
  ["energy|electric|electricity|power|grid|renewable|efficiency|climate|brownfield|cleanup", "Energy, climate, and cleanup"],
  ["planning|community development|data|mapping|capacity|technical assistance", "Planning and local capacity"]
];

const defaultStages = ["Any step", "Planning", "Early Design", "Engineering", "Construction", "Implementation", "Operations/Maintenance", "Capacity Building", "Acquisition", "Cleanup"];

const filterConfig = siteConfig.filters || {};
const applicantOptions = Array.isArray(filterConfig.applicants) && filterConfig.applicants.length
  ? filterConfig.applicants : defaultApplicantOptions;
const topicOptions = Array.isArray(filterConfig.topics) && filterConfig.topics.length
  ? filterConfig.topics : defaultTopicOptions;
const stages = Array.isArray(filterConfig.stages) && filterConfig.stages.length
  ? filterConfig.stages : defaultStages;
const stageAliases = filterConfig.stageAliases || {};
const topicMatchers = filterConfig.topicMatchers || {};
const specificApplicantGroups = applicantOptions.filter(([value]) => value !== "__other__").map(([value]) => value);

const elements = Object.fromEntries([
  "stateSelect","keywordSearch","applicantOptions","topicOptions","fundingTypeOptions","resourceTypeOptions","caseStudyPhaseOptions","stageSelect",
  "includeClosed","toggleFilters","resetButton","sortSelect","limitSelect","caseStudyViewSelect","caseStudyViewControl","caseStudyCollections","exportWord","exportCsv","communityTitle","communitySummary",
  "matchCount","fundingMatchCount","resourceMatchCount","caseStudyMatchCount","activeFilters","results","matchAnnouncement",
  "fundingCount","resourceCount","caseStudyCount","showFunding","showResources","showCases",
  "nextDeadlinePanel","nextDeadlineDate","nextDeadlineMeta","nextDeadlineLink","profileStatus",
  "resultsToolbar"
].map((id) => [id, document.getElementById(id)]));

let mode = "All";
let currentMatches = [];
const fundingFilterOptions = [
  ["grant", "Grant"],
  ["loan", "Loan or financing"],
  ["match", "Match or cost share required"],
  ["amount", "Award amount listed"]
];
const resourceTypeOptions = [
  ["technical", "Technical assistance"],
  ["guide", "Guides and toolkits"],
  ["data", "Data, maps, and calculators"],
  ["training", "Training and webinars"],
  ["directory", "Directories and resource hubs"],
  ["report", "Reports and research"],
  ["other", "Other resources"]
];
const caseStudyPhaseOptions = [["Plan", "Plan"], ["Design", "Design"], ["Build", "Build"], ["Operate", "Operate"]];

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>'"]/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
  })[character]);
}

function cleanText(value) {
  return String(value ?? "").trim();
}

function safeUrl(value) {
  const source = cleanText(value);
  if (!source) return "";
  try {
    const url = new URL(source);
    return url.protocol === "http:" || url.protocol === "https:" ? url.href : "";
  } catch {
    return "";
  }
}


function replaceSelectOptions(select, placeholder, options, selectedValue = "") {
  if (!select) return;
  select.innerHTML = `<option value="">${escapeHtml(placeholder)}</option>${options.join("")}`;
  select.disabled = options.length === 0;
  select.value = options.length && selectedValue ? selectedValue : "";
}

function setCommunitySelectorStatus(message) {
  if (elements.profileStatus) elements.profileStatus.textContent = message;
}

function populateStateOptions(selectedState = "") {
  replaceSelectOptions(
    elements.stateSelect,
    "Choose a state, D.C., or U.S. territory",
    places.map((stateName) => `<option value="${escapeHtml(stateName)}">${escapeHtml(stateName)}</option>`),
    selectedState
  );
  elements.stateSelect.disabled = false;
}

function setStateSelection(stateName) {
  populateStateOptions(stateName);
  setCommunitySelectorStatus(elements.stateSelect.value
    ? "State or territory selected."
    : "Choose a state or territory first.");
  render();
}
function summaryTopic(item) {
  const topics = cleanText(item.topic_tags)
    .split(/[;,|]/)
    .map((topic) => topic.trim().toLowerCase().replace("/", " and "))
    .filter(Boolean)
    .slice(0, 2);
  return topics.length ? topics.join(" and ") : "community projects";
}

function publicSummary(item) {
  if (item.item_type === "Case Study") return cleanText(item.summary);
  const reviewed = {
    "RERC-FND-0017": "Helps eligible local governments identify, evaluate, and protect historic properties in Alaska.",
    "RERC-FND-0021": "Develops and repairs recreational trails and trail facilities for motorized and non-motorized use.",
    "RERC-FND-0024": "Offers potential funding for eligible snowmachine recreation projects in Alaska. Check the current program page for eligible work and cycle details.",
    "RERC-FND-0274": "Offers potential support for eligible projects connected to the Chesapeake Gateways Network. Check the current program page for applicant and project rules.",
    "RERC-FND-0475": "Supports projects that promote understanding of Japan.",
    "RERC-FND-0541": "Supports smaller transportation projects such as walking and biking facilities, recreational trails, safe routes to school, historic preservation, environmental work, overlooks, and safety studies.",
    "RERC-RES-0077": "Helps communities coordinate housing and services to prevent and end homelessness, rehouse people quickly, connect households with mainstream programs, and support long-term stability."
  };
  let text = reviewed[item.item_id] || cleanText(item.summary || item.why_it_matters);
  const placeholder = !text || text === "-" || text.length < 18 ||
    /^(potential rerc fit|purpose tags|varies by)/i.test(text) ||
    (/^for\s/i.test(text) && text.length < 80);
  if (placeholder) {
    const topic = summaryTopic(item);
    text = item.item_type === "Resource"
      ? `Offers information or technical help related to ${topic}. Check the provider's page for current services and access details.`
      : `Offers potential funding related to ${topic}. Check the current program page for eligible applicants, activities, and timing.`;
  }
  text = text[0].toUpperCase() + text.slice(1);
  return text.endsWith(".") || text.endsWith("!") || text.endsWith("?") ? text : text + ".";
}
function matchLabel(score) {
  if (score >= (rankingThresholds.high ?? 80)) return "High";
  if (score >= (rankingThresholds.medium ?? 65)) return "Medium";
  return "Broad";
}

function corpus(item) {
  return [
    item.title, item.organization, item.geography, item.eligible_users, item.project_stage, item.topic_tags,
    item.support_type, item.summary, item.why_it_matters, item.case_place, item.case_state, item.case_place_type,
    item.case_program, item.case_partners
  ].join(" ").toLowerCase();
}

function topicCorpus(item) {
  return [item.title, item.organization, item.project_stage, item.topic_tags, item.support_type, item.summary, item.why_it_matters, item.case_program]
    .join(" ").toLowerCase();
}

function selectedValues(container) {
  return [...container.querySelectorAll("input:checked")].map((input) => input.value);
}

function matchesAny(text, groups) {
  if (!groups.length) return true;
  return groups.some((group) => (topicMatchers[group] || group).split("|").some((term) => {
    const escaped = term.trim().replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replace(/\\\s+/g, "\\s+");
    return new RegExp(`(^|[^a-z0-9])${escaped}(?=$|[^a-z0-9])`, "i").test(text);
  }));
}

function matchesApplicants(text, groups) {
  if (!groups.length) return true;
  const explicit = groups.filter((group) => group !== "__other__");
  if (explicit.length && matchesAny(text, explicit)) return true;
  if (!groups.includes("__other__")) return false;
  return !specificApplicantGroups.some((group) => matchesAny(text, [group]));
}

function matchesStage(item, selectedStage) {
  if (selectedStage === "Any step") return true;
  const terms = stageAliases[selectedStage] || selectedStage.toLowerCase();
  return matchesAny(cleanText(item.project_stage).toLowerCase(), [terms]);
}

function isClosed(item) {
  if (cleanText(item.status).toLowerCase() === "cycle closed") return true;
  return /\b(?:cycle|round|application(?: period)?|applications?)\b.{0,35}\b(?:closed|ended|not accepting)\b|\bnot accepting applications\b/i.test(cleanText(item.deadline_or_availability));
}

function isNational(geography) {
  const value = cleanText(geography).toLowerCase();
  return ["national", "nationwide", "united states", "all states", "federal"].some((term) => value.includes(term));
}

function isNationalForPlace(item, selectedPlace) {
  if (!isNational(item.geography)) return false;
  if (!territoryPlaces.has(selectedPlace)) return true;
  const coverageText = [item.geography, item.eligible_users, item.coverage_note].join(" ").toLowerCase();
  return /territor|insular|island area/.test(coverageText) || matchesAny(coverageText, [selectedPlace.toLowerCase()]);
}

function appliesToPlace(geography, selectedPlace) {
  const selected = cleanText(selectedPlace).toLowerCase();
  return cleanText(geography).split(/[;,|/]/).some((area) => {
    const normalized = area.trim().toLowerCase();
    return normalized === selected || normalized.startsWith(`${selected} (`);
  });
}

function coveredStates(item) {
  const raw = item?.covered_states;
  const values = Array.isArray(raw) ? raw : cleanText(raw).split(/[;,|]/);
  return values.map((value) => cleanText(value)).filter(Boolean);
}

const appalachianPlaces = new Set([
  "Alabama", "Georgia", "Kentucky", "Maryland", "Mississippi", "New York", "North Carolina",
  "Ohio", "Pennsylvania", "South Carolina", "Tennessee", "Virginia", "West Virginia"
]);

function isBroadArea(item, selectedPlace) {
  const geography = cleanText(item.geography).toLowerCase();
  if (geography.includes("appalachian region")) return appalachianPlaces.has(selectedPlace);
  return false;
}

function matchesGeography(item, selectedPlace) {
  if (!selectedPlace || item.item_type === "Case Study") return true;
  const geography = cleanText(item.geography);
  const regionalCoverage = coveredStates(item);
  if (geography.toLowerCase().includes("multi-state")) return regionalCoverage.includes(selectedPlace);
  if (regionalCoverage.length) return regionalCoverage.includes(selectedPlace);
  if (appliesToPlace(geography, selectedPlace)) return true;
  if (isNationalForPlace(item, selectedPlace)) return true;
  if (isNational(geography)) return false;
  return isBroadArea(item, selectedPlace);
}

function selectedMatchFactors() {
  return {
    selectedPlace: elements.stateSelect.value,
    applicants: selectedValues(elements.applicantOptions),
    topics: selectedValues(elements.topicOptions),
    fundingFilters: selectedValues(elements.fundingTypeOptions),
    resourceTypes: selectedValues(elements.resourceTypeOptions),
    caseStudyPhases: selectedValues(elements.caseStudyPhaseOptions),
    selectedStage: elements.stageSelect.value
  };
}

function resourceTypeLabels(item) {
  const text = `${cleanText(item.title)} ${cleanText(item.support_type)} ${cleanText(item.topic_tags)} ${cleanText(item.summary)} ${cleanText(item.why_it_matters)}`.toLowerCase();
  const labels = [];
  if (/technical assistance|business support|workshop|coaching/.test(text)) labels.push("technical");
  if (/training|webinar|video|curriculum|instructor/.test(text)) labels.push("training");
  if (/data|map|gis|calculator|analysis|software|viewer|database|benchmark/.test(text)) labels.push("data");
  if (/directory|hub|library|network|collection|contacts/.test(text)) labels.push("directory");
  if (/report|research|methodology|plan and data/.test(text)) labels.push("report");
  if (/guide|toolkit|framework|worksheet|checklist|planning menu|tactics|reference/.test(text)) labels.push("guide");
  if (!labels.length) labels.push("other");
  return [...new Set(labels)];
}

function fundingFilterLabels(item) {
  const text = `${cleanText(item.title)} ${cleanText(item.support_type)} ${cleanText(item.amount_or_cost)} ${cleanText(item.match_or_cost)}`.toLowerCase();
  const labels = [];
  if (/\bgrant\b/.test(text)) labels.push("grant");
  if (/\bloan\b|\bfinanc|\bcredit\b/.test(text)) labels.push("loan");
  if (/\bmatch\b|cost share|local share|non-federal share/.test(text)) labels.push("match");
  const amount = cleanText(item.amount_or_cost).toLowerCase();
  if (amount && !/varies|not listed|check|unknown|n\/a/.test(amount)) labels.push("amount");
  return labels;
}

function caseStudyPhase(item) {
  const stage = cleanText(item.project_stage).toLowerCase();
  if (/^(early design|design|engineering|predevelopment)$/.test(stage)) return "Design";
  if (/^(construction|implementation|acquisition|cleanup)$/.test(stage)) return "Build";
  if (/^(operations\/maintenance|operations|maintenance|capacity building)$/.test(stage)) return "Operate";
  if (stage === "planning") return "Plan";
  const text = cleanText(item.topic_tags).toLowerCase();
  if (/design|engineer|predevelopment/.test(text)) return "Design";
  if (/build|construct|implement|acquisition|capital|cleanup/.test(text)) return "Build";
  if (/operat|maint|capacity|business/.test(text)) return "Operate";
  return "Plan";
}

function scoreItem(item, text, factors) {
  const { selectedPlace, applicants, topics, selectedStage } = factors;
  const topicText = topicCorpus(item);
  const base = item.item_type === "Case Study"
    ? (rankingBase.caseStudy ?? 52)
    : (item.item_type === "Resource" ? (rankingBase.resource ?? 45) : (rankingBase.funding ?? 45));
  let score = base;
  if (item.item_type === "Case Study") {
    if (selectedPlace && appliesToPlace(item.geography, selectedPlace)) score += rankingWeights.caseState ?? 18;
    if (topics.length) score += Math.min(rankingWeights.caseTopicMaximum ?? 21, topics.filter((group) => matchesAny(topicText, [group])).length * (rankingWeights.caseTopicEach ?? 7));
    if (selectedStage !== "Any step" && cleanText(item.project_stage).toLowerCase() === selectedStage.toLowerCase()) score += rankingWeights.caseStage ?? 8;
    if (item.source_url) score += rankingWeights.caseSource ?? 5;
  } else {
    if (isClosed(item)) score += rankingWeights.closed ?? -18;
    else if (item.status === "Open when checked" || item.status === "Available") score += rankingWeights.available ?? 18;
    else if (item.status === "Recurring") score += rankingWeights.recurring ?? 14;
    if (selectedPlace && appliesToPlace(item.geography, selectedPlace)) score += rankingWeights.selectedState ?? 15;
    if (selectedPlace && coveredStates(item).includes(selectedPlace)) score += rankingWeights.regional ?? 12;
    if (selectedPlace && isNationalForPlace(item, selectedPlace)) score += rankingWeights.nationwide ?? 8;
    if (applicants.length && matchesApplicants(cleanText(item.eligible_users).toLowerCase(), applicants)) score += rankingWeights.applicant ?? 12;
    if (topics.length) score += Math.min(rankingWeights.topicMaximum ?? 18, topics.filter((group) => matchesAny(topicText, [group])).length * (rankingWeights.topicEach ?? 7));
    if (selectedStage !== "Any step") score += cleanText(item.project_stage).toLowerCase() === "mixed" ? (rankingWeights.mixedStage ?? 4) : (matchesStage(item, selectedStage) ? (rankingWeights.exactStage ?? 10) : 0);
    if (item.summary) score += rankingWeights.summary ?? 3;
  }
  return Math.max(1, Math.min(99, score));
}

function getMatches() {
  const factors = selectedMatchFactors();
  const {
    selectedPlace, applicants, topics, fundingFilters, resourceTypes, caseStudyPhases, selectedStage
  } = factors;
  const keyword = elements.keywordSearch.value.trim().toLowerCase();

  const matches = catalog.filter((item) => {
    if (mode !== "All" && item.item_type !== mode) return false;
    if (!elements.includeClosed.checked && isClosed(item)) return false;
    if (!matchesGeography(item, selectedPlace)) return false;
    const text = corpus(item);
    if (keyword && !text.includes(keyword)) return false;
    if (item.item_type !== "Case Study" && !matchesApplicants(cleanText(item.eligible_users).toLowerCase(), applicants)) return false;
    if (!matchesAny(topicCorpus(item), topics)) return false;
    if (item.item_type === "Funding" && fundingFilters.length && !fundingFilters.some((filter) => fundingFilterLabels(item).includes(filter))) return false;
    if (item.item_type === "Resource" && resourceTypes.length && !resourceTypes.some((filter) => resourceTypeLabels(item).includes(filter))) return false;
    if (item.item_type === "Case Study" && caseStudyPhases.length && !caseStudyPhases.includes(caseStudyPhase(item))) return false;
    const stageText = cleanText(item.project_stage).toLowerCase();
    if (selectedStage !== "Any step") {
      const exactStage = matchesStage(item, selectedStage);
      const broadFundingStage = item.item_type !== "Case Study" && stageText === "mixed";
      if (!exactStage && !broadFundingStage) return false;
    }
    return true;
  }).map((item) => ({
    ...item,
    score: scoreItem(item, corpus(item), factors)
  }));

  const sort = elements.sortSelect.value;
  matches.sort((a, b) => {
    if (sort === "title") return a.title.localeCompare(b.title);
    if (sort === "status") return a.status.localeCompare(b.status) || b.score - a.score;
    if (sort === "type") return a.item_type.localeCompare(b.item_type) || b.score - a.score;
    if (sort === "deadline") {
      const aDeadline = parseDeadline(a);
      const bDeadline = parseDeadline(b);
      if (aDeadline && bDeadline) return aDeadline - bDeadline || b.score - a.score || a.title.localeCompare(b.title);
      if (aDeadline) return -1;
      if (bDeadline) return 1;
      return b.score - a.score || a.title.localeCompare(b.title);
    }
    return b.score - a.score || a.title.localeCompare(b.title);
  });
  return matches;
}

function parseDeadline(item) {
  return window.RERCDeadlineUtils.parseDeadline(item);
}
function fundingTiming(item) {
  return window.RERCDeadlineUtils.fundingTiming(item);
}
function fundingTimingCounts(items) {
  const counts = { dated: 0, rolling: 0, recurring: 0, closed: 0, variable: 0, active_period: 0, date_pending: 0 };
  items.filter((item) => item.item_type === "Funding").forEach((item) => {
    const type = fundingTiming(item).type;
    counts[type] = (counts[type] || 0) + 1;
  });
  return counts;
}
function uiText(value) {
  return window.RERCI18N?.translate ? window.RERCI18N.translate(value) : value;
}

function renderNextDeadline(items) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const funding = items.filter((item) => item.item_type === "Funding");
  const counts = fundingTimingCounts(funding);
  const next = funding
    .map((item) => ({ item, date: parseDeadline(item) }))
    .filter((entry) => entry.date && entry.date >= today)
    .sort((a, b) => a.date - b.date || b.item.score - a.item.score || a.item.title.localeCompare(b.item.title))[0];

  if (!next) {
    const pending = counts.recurring + counts.variable + counts.active_period + counts.date_pending;
    elements.nextDeadlinePanel.classList.add("empty");
    elements.nextDeadlineDate.textContent = counts.rolling ? `${counts.rolling} rolling or ongoing funding options` : "No upcoming dated funding deadline found.";
    elements.nextDeadlineMeta.textContent = pending ? `${pending} options need a new cycle date; use the official program links to confirm timing.` : "Use the official program links to confirm current timing.";
    elements.nextDeadlineLink.hidden = true;
    elements.nextDeadlineLink.removeAttribute("href");
    return;
  }

  const days = Math.round((next.date - today) / 86400000);
  const locale = document.documentElement.lang === "es" ? "es-US" : "en-US";
  const dateText = new Intl.DateTimeFormat(locale, {
    year: "numeric",
    month: "long",
    day: "numeric"
  }).format(next.date);
  const source = safeUrl(next.item.source_url);
  elements.nextDeadlinePanel.classList.remove("empty");
  elements.nextDeadlineDate.textContent = dateText;
  elements.nextDeadlineMeta.textContent = uiText(`${next.item.title} - ${days === 0 ? "Due today" : `${days} day${days === 1 ? "" : "s"} left`}`);
  elements.nextDeadlineLink.hidden = !source;
  if (source) {
    elements.nextDeadlineLink.href = source;
    elements.nextDeadlineLink.setAttribute("aria-label", `View ${next.item.title} program details`);
  } else {
    elements.nextDeadlineLink.removeAttribute("href");
  }
}
function hasSubstantiveAnswers() {
  const factors = selectedMatchFactors();
  return Boolean(
    factors.applicants.length || factors.topics.length || factors.selectedStage !== "Any step" ||
    elements.keywordSearch.value.trim()
  );
}

function displayedMatchLabel(item) {
  return hasSubstantiveAnswers() ? matchLabel(item.score) : "Starting point";
}

function renderSourceLink(item, label) {
  const url = safeUrl(item.source_url);
  const accessibleLabel = `${label}: ${cleanText(item.title)} (opens in a new tab)`;
  return url
    ? `<a class="case-link" href="${escapeHtml(url)}" target="_blank" rel="noopener" aria-label="${escapeHtml(accessibleLabel)}">${escapeHtml(label)}</a>`
    : '<span class="case-link source-unavailable">Source link unavailable</span>';
}

function renderCard(item, headingLevel = 3) {
  const itemId = cleanText(item.item_id);
  const headingTag = headingLevel === 4 ? "h4" : "h3";
  const scoreLabel = displayedMatchLabel(item);
  if (item.item_type === "Case Study") {
    const year = item.case_year ? ` | ${escapeHtml(item.case_year)}` : "";
    return `<article class="result-card case-study" data-item-id="${escapeHtml(itemId)}">
      <div>
        <div class="card-kicker">
          <span class="pill">Case study</span>
          <span>${escapeHtml(item.case_program)}</span>
        </div>
        <${headingTag}>${escapeHtml(item.title)}</${headingTag}>
        <p class="organization">${escapeHtml(item.case_place)}, ${escapeHtml(item.case_state)}${year}</p>
        <p class="summary">${escapeHtml(publicSummary(item))}</p>
        <details class="card-details">
          <summary>Case study details</summary>
          <p class="details"><strong>Topics:</strong> ${escapeHtml(item.topic_tags || "Community development")}</p>
        </details>
        ${renderSourceLink(item, "Read the example")}
      </div>
      <div class="score"><strong>${escapeHtml(scoreLabel)}</strong><span>${hasSubstantiveAnswers() ? "match level" : "add details to rank"}</span></div>
    </article>`;
  }

  const coverage = coveredStates(item);
  const geography = coverage.length ? `Multi-State: ${coverage.join(", ")}` : item.geography;
  const classes = ["result-card", item.item_type === "Resource" ? "resource" : "funding", isClosed(item) ? "closed" : ""].join(" ");
  const timing = item.deadline_or_availability || item.amount_or_cost || "Check current availability";
  const timingInfo = item.item_type === "Funding" ? fundingTiming(item) : null;
  return `<article class="${classes}" data-item-id="${escapeHtml(itemId)}">
    <div>
      <div class="card-kicker">
        <span class="pill">${escapeHtml(item.item_type)}</span>
        <span class="pill status">${escapeHtml(item.status)}</span>
        <span>${escapeHtml(item.support_type)}</span>
      </div>
      <${headingTag}>${escapeHtml(item.title)}</${headingTag}>
      <p class="organization">${escapeHtml(item.organization)}</p>
      <p class="summary">${escapeHtml(publicSummary(item))}</p>
      <p class="eligibility"><strong>Who:</strong> ${escapeHtml(item.eligible_users || "Eligibility varies")}</p>
      <details class="card-details">
        <summary>Program details</summary>
        <p class="details"><strong>Where:</strong> ${escapeHtml(geography)}</p>
        ${item.coverage_note ? `<p class="details"><strong>Coverage note:</strong> ${escapeHtml(item.coverage_note)}</p>` : ""}
        <p class="details"><strong>${item.item_type === "Funding" ? "Application timing" : "Availability"}:</strong> ${timingInfo ? `<span class="timing-class ${escapeHtml(timingInfo.type)}">${escapeHtml(timingInfo.label)}</span><br>` : ""}<span class="timing-detail">${escapeHtml(timing)}</span> &nbsp; <strong>Last checked:</strong> ${escapeHtml(item.last_checked)}</p>
      </details>
      ${renderSourceLink(item, item.item_type === "Resource" ? "Open resource" : "Program Website")}
    </div>
    <div class="score"><strong>${escapeHtml(scoreLabel)}</strong><span>${hasSubstantiveAnswers() ? "match level" : "add details to rank"}</span></div>
  </article>`;
}

function activeFilterSummary() {
  const values = [];
  if (elements.stateSelect.value) values.push(elements.stateSelect.value);
  if (elements.keywordSearch.value.trim()) values.push(`Search: ${elements.keywordSearch.value.trim()}`);
  const applicants = selectedValues(elements.applicantOptions);
  const topics = selectedValues(elements.topicOptions);
  if (applicants.length) values.push(`${applicants.length} applicant choice${applicants.length === 1 ? "" : "s"}`);
  if (topics.length) values.push(`${topics.length} topic${topics.length === 1 ? "" : "s"}`);
  const fundingFilters = selectedValues(elements.fundingTypeOptions);
  const resourceTypes = selectedValues(elements.resourceTypeOptions);
  const caseStudyPhases = selectedValues(elements.caseStudyPhaseOptions);
  if (fundingFilters.length) values.push(`${fundingFilters.length} funding filter${fundingFilters.length === 1 ? "" : "s"}`);
  if (resourceTypes.length) values.push(`${resourceTypes.length} resource type${resourceTypes.length === 1 ? "" : "s"}`);
  if (caseStudyPhases.length) values.push(`${caseStudyPhases.join(", ")} case studies`);
  if (elements.stageSelect.value !== "Any step") values.push(elements.stageSelect.value);
  if (elements.includeClosed.checked) values.push("Closed rounds shown");
  return values.length ? values.join(" | ") : "Choose a state or territory to begin.";
}

function renderGroup(kind, title, description, items, total, className) {
  return `<section class="result-group ${className}" aria-label="${escapeHtml(title)}">
    <div class="result-group-heading">
      <div><p class="eyebrow">${escapeHtml(kind)}</p><h3>${escapeHtml(title)}</h3><p>${escapeHtml(description)}</p></div>
      <strong>${total.toLocaleString()} matches</strong>
    </div>
    ${items.length ? items.map((item) => renderCard(item, 4)).join("") : `<div class="empty-state"><h4>No ${escapeHtml(kind.toLowerCase())} matches</h4><p>Try fewer answers or a wider search.</p></div>`}
  </section>`;
}

function render() {
  currentMatches = getMatches();
  const limitValue = elements.limitSelect.value;
  const limit = limitValue === "all" ? Number.MAX_SAFE_INTEGER : Number(limitValue);
  const fundingResults = currentMatches.filter((item) => item.item_type === "Funding");
  const resourceResults = currentMatches.filter((item) => item.item_type === "Resource");
  const caseResults = currentMatches.filter((item) => item.item_type === "Case Study");
  const caseStudyLimit = Math.max(10, Math.min(24, Number(elements.caseStudyViewSelect?.value) || 10));
  let visible = currentMatches.slice(0, limit);
  if (mode === "All") {
    const each = limitValue === "all" ? Number.MAX_SAFE_INTEGER : Math.max(1, Math.floor(limit / 3));
    visible = [
      ...fundingResults.slice(0, each),
      ...resourceResults.slice(0, each),
      ...caseResults.slice(0, Math.min(each, 12))
    ];
  } else if (mode === "Case Study") {
    visible = caseResults.slice(0, Math.min(limit, caseStudyLimit));
  }
  if (elements.caseStudyViewControl) elements.caseStudyViewControl.hidden = mode !== "Case Study";
  if (elements.caseStudyCollections) elements.caseStudyCollections.hidden = mode !== "Case Study";
  const place = elements.stateSelect.value;
  const label = place || "rural communities";
  const fundingMatches = fundingResults.length;
  const resourceMatches = resourceResults.length;
  const caseMatches = caseResults.length;
  const modeLabel = {
    "All": "Funding, resources, and case studies",
    "Funding": "Funding",
    "Resource": "Resources",
    "Case Study": "Case studies"
  }[mode];

  elements.communityTitle.textContent = mode === "Case Study"
    ? "Community examples from across the country"
    : (mode === "All" ? "Funding and resources for " + label + ", plus community examples" : modeLabel + " for " + label);
  elements.communitySummary.textContent = currentMatches.length
    ? (hasSubstantiveAnswers()
      ? (mode === "Case Study" || mode === "All"
        ? "Examples may come from other states. Your topic choices help rank them. Match levels do not confirm eligibility or results."
        : "Match levels compare your priorities. They do not confirm eligibility.")
      : "These are starting points. Choose priorities to rank them for your needs.")
    : "Try fewer choices or a wider search.";
  elements.matchCount.textContent = currentMatches.length.toLocaleString();
  elements.fundingMatchCount.textContent = fundingMatches.toLocaleString();
  elements.resourceMatchCount.textContent = resourceMatches.toLocaleString();
  elements.caseStudyMatchCount.textContent = caseMatches.toLocaleString();
  renderNextDeadline(fundingResults);
  elements.activeFilters.textContent = activeFilterSummary();
  elements.matchAnnouncement.textContent = `${currentMatches.length} total matches; ${visible.length} cards displayed.`;
  if (!visible.length) {
    elements.results.innerHTML = `<div class="empty-state"><h3>No matches yet</h3><p>Try fewer answers, include closed rounds, or start over.</p><button class="secondary-button" type="button" data-reset-filters>Reset answers</button></div>`;
  } else if (mode === "All") {
    const shownFunding = visible.filter((item) => item.item_type === "Funding");
    const shownResources = visible.filter((item) => item.item_type === "Resource");
    const shownCases = visible.filter((item) => item.item_type === "Case Study");
    elements.results.innerHTML = [
      renderGroup("Funding", "Ways to pay for the work", "Grants, loans, tax credits, and other funding options.", shownFunding, fundingMatches, "funding-group"),
      renderGroup("Resources", "Tools and technical help", "Guides, data, training, and hands-on support.", shownResources, resourceMatches, "resource-group"),
      renderGroup("Case studies", "Independent community precedents", "Open the Case studies tab for detailed precedents not repeated in the linked libraries.", shownCases, caseMatches, "case-group")
    ].join("");
  } else {
    elements.results.innerHTML = visible.map((item) => renderCard(item, 3)).join("");
  }
  window.dispatchEvent(new CustomEvent("rerc:render", { detail: { matches: currentMatches } }));
}

function csvCell(value) {
  let text = cleanText(value);
  if (/^\s*[=+\-@]/.test(text)) text = `'${text}`;
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function downloadBlob(contents, mimeType, filename) {
  const blob = new Blob([contents], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function exportMatchView() {
  const plannerView = window.RERCPlannerView && window.RERCPlannerView.getActiveMatches();
  return Array.isArray(plannerView) ? plannerView : currentMatches;
}

function exportCsv() {
  const matches = exportMatchView();
  const headers = ["Item Type","Title","Organization or Program","Status","Geography","Covered States","Coverage Note","Who Can Use It","Project Step","Topics","Type of Help","Timing or Year","Summary","Program Website"];
  const lines = [headers.map(csvCell).join(",")];
  matches.forEach((item) => lines.push([
    item.item_type, item.title, item.organization, item.status,
    item.item_type === "Case Study" ? `${item.case_place}, ${item.case_state}` : item.geography,
    item.item_type === "Case Study" ? "" : coveredStates(item).join("; "), item.coverage_note || "",
    item.eligible_users, item.project_stage, item.topic_tags, item.support_type,
    item.item_type === "Case Study" ? item.case_year : (item.deadline_or_availability || item.amount_or_cost),
    publicSummary(item), safeUrl(item.source_url)
  ].map(csvCell).join(",")));
  downloadBlob(`\uFEFF${lines.join("\r\n")}`, "text/csv;charset=utf-8", "RERC-community-funding-resources-and-case-studies.csv");
}

function xmlEscape(value) {
  return cleanText(value)
    .replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/g, "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

function wordRunXml(text, options = {}) {
  const properties = [];
  if (options.bold) properties.push("<w:b/>");
  if (options.italic) properties.push("<w:i/>");
  if (options.color) properties.push('<w:color w:val="' + options.color + '"/>');
  return "<w:r>" + (properties.length ? "<w:rPr>" + properties.join("") + "</w:rPr>" : "") +
    '<w:t xml:space="preserve">' + xmlEscape(text) + "</w:t></w:r>";
}

function wordParagraphXml(runs, style = "") {
  const properties = style ? '<w:pPr><w:pStyle w:val="' + style + '"/></w:pPr>' : "";
  return "<w:p>" + properties + runs.join("") + "</w:p>";
}

function wordPageBreakXml() {
  return '<w:p><w:r><w:br w:type="page"/></w:r></w:p>';
}

function wordHyperlinkXml(text, relationshipId) {
  return '<w:hyperlink r:id="' + relationshipId + '"><w:r><w:rPr><w:color w:val="1B6A8F"/><w:u w:val="single"/></w:rPr><w:t>' +
    xmlEscape(text) + "</w:t></w:r></w:hyperlink>";
}

async function exportWord() {
  if (typeof JSZip === "undefined") {
    window.alert("The Word export tool did not load. Refresh the page and try again.");
    return;
  }
  const place = elements.stateSelect.value || "United States";
  const matches = exportMatchView();
  const funding = matches.filter((item) => item.item_type === "Funding");
  const resources = matches.filter((item) => item.item_type === "Resource");
  const cases = matches.filter((item) => item.item_type === "Case Study");
  const profile = activeFilterSummary();
  const relationships = [];
  const body = [];
  let relationshipNumber = 1;

  body.push(wordParagraphXml([wordRunXml("Appendix C: Funding, Resources, and Case Studies")], "Heading1"));
  body.push(wordParagraphXml([
    wordRunXml("Recreation Economy "),
    wordRunXml("for", { italic: true }),
    wordRunXml(" Rural Communities (RERC)")
  ]));
  body.push(wordParagraphXml([wordRunXml(place, { bold: true })]));
  body.push(wordParagraphXml([wordRunXml(profile)]));
  body.push(wordParagraphXml([
    wordRunXml("This explorer does not determine eligibility. ", { bold: true }),
    wordRunXml("Program rules and dates can change. Case studies show approaches, not guaranteed results. Confirm current requirements and local fit before making a decision.")
  ], "Notice"));

  const addSection = (title, items) => {
    items.forEach((item) => {
      body.push(wordPageBreakXml());
      body.push(wordParagraphXml([wordRunXml(title)], "Heading2"));
      body.push(wordParagraphXml([wordRunXml(item.title)], "Heading3"));
      body.push(wordParagraphXml([
        wordRunXml(item.organization, { bold: true }),
        wordRunXml(" | " + item.status + " | " + item.support_type)
      ]));
      body.push(wordParagraphXml([wordRunXml(publicSummary(item))]));
      if (item.item_type === "Case Study") {
        body.push(wordParagraphXml([
          wordRunXml("Community: ", { bold: true }),
          wordRunXml(`${item.case_place}, ${item.case_state}`),
          wordRunXml(" | Program: ", { bold: true }),
          wordRunXml(item.case_program)
        ]));
      } else {
        body.push(wordParagraphXml([
          wordRunXml("Who: ", { bold: true }),
          wordRunXml(item.eligible_users || "Eligibility varies"),
          wordRunXml(" | Where: ", { bold: true }),
          wordRunXml(coveredStates(item).join(", ") || item.geography)
        ]));
        if (item.coverage_note) {
          body.push(wordParagraphXml([wordRunXml("Coverage note: ", { bold: true }), wordRunXml(item.coverage_note)]));
        }
        body.push(wordParagraphXml([
          wordRunXml("Last checked: ", { bold: true }),
          wordRunXml(item.last_checked || "Not recorded")
        ]));
      }
      const sourceUrl = safeUrl(item.source_url);
      if (sourceUrl) {
        const relationshipId = "rId" + relationshipNumber++;
        relationships.push('<Relationship Id="' + relationshipId + '" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" Target="' + xmlEscape(sourceUrl) + '" TargetMode="External"/>');
        body.push(wordParagraphXml([
          wordRunXml(item.item_type === "Case Study" ? "Example: " : "Program: ", { bold: true }),
          wordHyperlinkXml(item.item_type === "Case Study" ? "Read the example" : "Program Website", relationshipId)
        ]));
      }
    });
  };

  addSection("Funding Opportunities", funding);
  addSection("Resources", resources);
  addSection("Case Studies", cases);

  const documentXml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
    '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">' +
    "<w:body>" + body.join("") +
    '<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1008" w:right="1008" w:bottom="1008" w:left="1008" w:header="720" w:footer="720" w:gutter="0"/></w:sectPr>' +
    "</w:body></w:document>";
  const stylesXml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
    '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">' +
    '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/><w:sz w:val="20"/></w:rPr></w:style>' +
    '<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:before="120" w:after="120"/></w:pPr><w:rPr><w:b/><w:color w:val="00573F"/><w:sz w:val="42"/></w:rPr></w:style>' +
    '<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:before="240" w:after="100"/></w:pPr><w:rPr><w:b/><w:color w:val="1B6A8F"/><w:sz w:val="30"/></w:rPr></w:style>' +
    '<w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:before="160" w:after="40"/><w:keepNext/></w:pPr><w:rPr><w:b/><w:color w:val="00573F"/><w:sz w:val="23"/></w:rPr></w:style>' +
    '<w:style w:type="paragraph" w:styleId="Notice"><w:name w:val="Notice"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:before="100" w:after="180"/><w:shd w:fill="FFF7DE"/><w:ind w:left="160" w:right="160"/></w:pPr></w:style>' +
    "</w:styles>";
  const contentTypes = '<?xml version="1.0" encoding="UTF-8"?>' +
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">' +
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>' +
    '<Default Extension="xml" ContentType="application/xml"/>' +
    '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>' +
    '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>' +
    '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>' +
    '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>' +
    "</Types>";
  const rootRelationships = '<?xml version="1.0" encoding="UTF-8"?>' +
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' +
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>' +
    '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>' +
    '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>' +
    "</Relationships>";
  const documentRelationships = '<?xml version="1.0" encoding="UTF-8"?>' +
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' +
    relationships.join("") + "</Relationships>";
  const now = new Date().toISOString();
  const coreXml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
    '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">' +
    "<dc:title>RERC Community Funding, Resources, and Case Studies Appendix</dc:title><dc:creator>Recreation Economy for Rural Communities</dc:creator><cp:lastModifiedBy>RERC Community Explorer</cp:lastModifiedBy>" +
    '<dcterms:created xsi:type="dcterms:W3CDTF">' + now + '</dcterms:created><dcterms:modified xsi:type="dcterms:W3CDTF">' + now + "</dcterms:modified></cp:coreProperties>";
  const appXml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
    '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">' +
    "<Application>RERC Community Explorer</Application><AppVersion>1.0</AppVersion></Properties>";

  const zip = new JSZip();
  zip.file("[Content_Types].xml", contentTypes);
  zip.file("_rels/.rels", rootRelationships);
  zip.file("docProps/core.xml", coreXml);
  zip.file("docProps/app.xml", appXml);
  zip.file("word/document.xml", documentXml);
  zip.file("word/styles.xml", stylesXml);
  zip.file("word/_rels/document.xml.rels", documentRelationships);
  const docx = await zip.generateAsync({ type: "uint8array", compression: "DEFLATE" });
  downloadBlob(docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "RERC-community-appendix.docx");
}

function buildCheckList(container, options, groupName) {
  container.innerHTML = options.map(([value, label], index) => `<label><input type="checkbox" name="${groupName}" value="${escapeHtml(value)}" id="${groupName}-${index}"><span>${escapeHtml(label)}</span></label>`).join("");
}

function reset() {
  // Keep the required place while clearing project priorities and result settings.
  elements.keywordSearch.value = "";
  elements.stageSelect.value = "Any step";
  elements.includeClosed.checked = false;
  elements.sortSelect.value = "score";
  elements.limitSelect.value = "all";
  if (elements.caseStudyViewSelect) elements.caseStudyViewSelect.value = "24";
  document.querySelectorAll(".filters input[type=checkbox]").forEach((input) => { input.checked = false; });
  mode = "All";
  document.querySelectorAll("[data-mode]").forEach((button) => {
    const active = button.dataset.mode === mode;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  });
  render();
}

function chooseMode(nextMode) {
  mode = nextMode;
  document.querySelectorAll("[data-mode]").forEach((candidate) => {
    const active = candidate.dataset.mode === mode;
    candidate.classList.toggle("active", active);
    candidate.setAttribute("aria-pressed", String(active));
  });
  render();
}

function initialize() {
  elements.fundingCount.textContent = fundingResources.filter((item) => item.item_type === "Funding").length.toLocaleString();
  elements.resourceCount.textContent = fundingResources.filter((item) => item.item_type === "Resource").length.toLocaleString();
  elements.caseStudyCount.textContent = caseStudies.length.toLocaleString();
  document.querySelector(".scene-catalog")?.setAttribute("aria-busy", "false");
  populateStateOptions();
  elements.stageSelect.innerHTML = stages.map((stage) => `<option value="${escapeHtml(stage)}">${escapeHtml(stage)}</option>`).join("");
  buildCheckList(elements.applicantOptions, applicantOptions, "applicant");
  buildCheckList(elements.topicOptions, topicOptions, "topic");
  buildCheckList(elements.fundingTypeOptions, fundingFilterOptions, "funding-filter");
  buildCheckList(elements.resourceTypeOptions, resourceTypeOptions, "resource-type");
  buildCheckList(elements.caseStudyPhaseOptions, caseStudyPhaseOptions, "case-study-phase");
  if (!elements.sortSelect.querySelector('option[value="deadline"]')) {
    const deadlineOption = document.createElement("option");
    deadlineOption.value = "deadline";
    deadlineOption.textContent = "Deadline: soonest first";
    elements.sortSelect.appendChild(deadlineOption);
  }
  elements.stateSelect.addEventListener("change", () => {
    setCommunitySelectorStatus(elements.stateSelect.value ? "State or territory selected." : "Choose a state or territory first.");
    render();
  });
  document.querySelectorAll("[data-mode]").forEach((button) => button.addEventListener("click", () => chooseMode(button.dataset.mode)));
  elements.showFunding.addEventListener("click", () => chooseMode("Funding"));
  elements.showResources.addEventListener("click", () => chooseMode("Resource"));
  elements.showCases.addEventListener("click", () => chooseMode("Case Study"));
  document.querySelectorAll("input, select").forEach((control) => control.addEventListener(control.type === "text" || control.type === "search" ? "input" : "change", render));
  elements.toggleFilters.addEventListener("click", () => {
    const open = document.querySelector(".filters").classList.toggle("open");
    elements.toggleFilters.setAttribute("aria-expanded", String(open));
    const label = elements.toggleFilters.querySelector("span");
    if (label) label.textContent = open ? "Hide questions" : "Show questions";
  });
  elements.resetButton.addEventListener("click", reset);
  document.addEventListener("click", (event) => {
    if (event.target.closest("[data-reset-filters]")) reset();
  });
  elements.exportCsv.addEventListener("click", exportCsv);
  elements.exportWord.addEventListener("click", exportWord);
  render();
}

window.RERCExplorer = {
  catalog,
  elements,
  getMatches: () => currentMatches,
  render,
  publicSummary,
  parseDeadline,
  fundingTiming,
  fundingTimingCounts,
  safeUrl,
  chooseMode,
  getMode: () => mode,
  setStateSelection,
  matchesGeography,
  matchesStage,
  matchesApplicants,
  matchesAny,
  resourceTypeLabels,
  caseStudyPhase,
  isClosed
};

initialize();
