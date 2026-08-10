"use strict";

const fs = require("fs");
const path = require("path");
const deadlines = require(path.join(__dirname, "..", "deadline-utils.js"));

const PREFIX = "window.RERC_CATALOG = ";
const jsonOnly = process.argv.includes("--json");
const pathArg = process.argv.find((value, index) => index > 1 && value !== "--json");
const dataPath = path.resolve(pathArg || path.join(__dirname, "..", "data.js"));
const raw = fs.readFileSync(dataPath, "utf8").trim();
if (!raw.startsWith(PREFIX) || !raw.endsWith(";")) throw new Error("data.js is not in the RERC catalog format");
const payload = JSON.parse(raw.slice(PREFIX.length, -1));
const funding = payload.items.filter((item) => item.item_type === "Funding");
const counts = { dated: 0, rolling: 0, recurring: 0, closed: 0, variable: 0, active_period: 0, date_pending: 0 };
const records = {};
for (const item of funding) {
  const type = deadlines.fundingTiming(item).type;
  if (!(type in counts)) throw new Error(`Unexpected deadline class ${type} for ${item.item_id}`);
  counts[type] += 1;
  records[item.item_id] = type;
}
const report = {
  status: funding.length === payload.counts.funding && Object.keys(records).length === funding.length ? "PASS" : "FAIL",
  funding_records: funding.length,
  counts,
  records
};
process.stdout.write(JSON.stringify(report, null, jsonOnly ? 0 : 2) + "\n");
if (report.status !== "PASS") process.exitCode = 1;
