"use strict";

// Maintainers can adjust public filters and match ranking here without changing app.js.
window.RERC_SITE_CONFIG = {
  schemaVersion: 1,
  geography: {
    regionalCoverageField: "covered_states",
    failClosedWithoutRegionalCoverage: true
  },
  contributions: {
    issueReportUrl: "https://docs.google.com/forms/d/e/1FAIpQLScBYulkwgoEVhLKftiGBm81LZxPdhojZVQtUT8ZQjWj4Sit6g/viewform?usp=header",
    catalogSubmissionUrl: "https://docs.google.com/forms/d/e/1FAIpQLSdL4GfgKT_ub6I8zd0d7vXXszwZG498b81XR12L-ZCYiUvqfQ/viewform?usp=header"
  },
  filters: {
    applicants: [
      ["local government|local governments|municipal|municipality|municipalities|county|counties|city|cities|town|towns|village|villages|political subdivision|political subdivisions", "Local government"],
      ["tribe|tribes|tribal|native|indian nation|indian nations|sovereign", "Tribe or Native community"],
      ["nonprofit|nonprofits|non-profit|non-profits|community organization|community organizations|land trust|land trusts", "Nonprofit or community group"],
      ["state agency|state agencies|state government", "State agency"],
      ["business|businesses|entrepreneur|entrepreneurs|tourism|destination marketing|convention|visitors bureau|visitor bureau", "Business or tourism group"],
      ["school|schools|college|colleges|university|universities|library|libraries|museum|museums", "School, library, or museum"],
      ["utility|utilities|authority|authorities|district|districts", "Utility or public authority"],
      ["landowner|landowners|individual|individuals|families", "Landowner or individual"],
      ["__other__", "Other or varies by program"]
    ],
    topics: [
      ["trail|park|recreation|outdoor access", "Parks, trails, and outdoor access"],
      ["downtown|main street|gateway|placemaking", "Downtown and Main Street"],
      ["tourism|visitor|recreation economy", "Tourism and visitor economy"],
      ["business|entrepreneur|workforce|economic development", "Business and jobs"],
      ["transportation|street|bike|pedestrian|transit|mobility", "Transportation and safe access"],
      ["water|wastewater|stormwater|flood|coastal|resilience", "Water and resilience"],
      ["river-access", "River access"],
      ["conservation|environment|environmental|habitat|forest|land|river|watershed", "Conservation and public lands"],
      ["historic|heritage|arts|culture|museum", "History, arts, and culture"],
      ["housing|community facility|community facilities|community services|public facilities|infrastructure|public safety|emergency services|education|health|food", "Community services"],
      ["energy|electric|electricity|power|grid|renewable|efficiency|climate|brownfield|cleanup", "Energy, climate, and cleanup"],
      ["planning|community development|data|mapping|capacity|technical assistance", "Planning and local capacity"]
    ],
    topicMatchers: {
      "river-access": "river access|water access|public water access|boat ramp|boat ramps|boat launch|boat launches|boating access|canoe access|kayak access|blueway|blueways|riverwalk|riverwalks|paddling access|water trail|water trails|lake access|fishing access|riverfront trail|riverfront park|river landing"
    },
    stages: ["Any step", "Planning", "Early Design", "Engineering", "Construction", "Implementation", "Operations/Maintenance", "Capacity Building", "Acquisition", "Cleanup"],
    stageAliases: {
      "Planning": "planning|assessment|feasibility|application|idea|project screening",
      "Early Design": "early design|concept design|conceptual design|predevelopment|pre-development|design",
      "Engineering": "engineering|final design|design and engineering|preconstruction",
      "Construction": "construction|capital project|development",
      "Implementation": "implementation|delivery",
      "Operations/Maintenance": "operations|maintenance|stewardship",
      "Capacity Building": "capacity building|training|technical assistance|business development|workforce",
      "Acquisition": "acquisition|land purchase|easement",
      "Cleanup": "cleanup|remediation|brownfield"
    }
  },
  ranking: {
    thresholds: { high: 80, medium: 65 },
    base: { funding: 45, resource: 45, caseStudy: 52 },
    weights: {
      available: 18,
      recurring: 14,
      closed: -18,
      selectedState: 15,
      nationwide: 8,
      regional: 12,
      applicant: 12,
      topicEach: 7,
      topicMaximum: 18,
      exactStage: 10,
      mixedStage: 4,
      summary: 3,
      caseState: 18,
      caseTopicEach: 7,
      caseTopicMaximum: 21,
      caseStage: 8,
      caseSource: 5
    }
  }
};