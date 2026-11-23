// Run from any directory with Node.js 18 or newer.
const { readFileSync } = require("node:fs");
const { join } = require("node:path");

const read = (filename) => readFileSync(join(__dirname, filename), "utf8");
const evidence = JSON.parse(read("evidence.json"));
const baselineRows = read("../parser_v2/results/verified_parser_v2/remaining.jsonl")
  .trim().split(/\r?\n/).map((line) => JSON.parse(line));
const ids = new Set(baselineRows.map((row) => row.question_id));
const total = baselineRows.length;

function requireCheck(condition, message) {
  if (!condition) throw new Error(message);
}

requireCheck(total === 40 && ids.size === total, "Expected 40 distinct Parser v2 targets");
requireCheck(baselineRows.every((row) => row.generation_finish_reason === "length"
  && row.old_parse_success === false && row.scoring_correct === false),
  "The selected archived B0 outputs must all be unextracted length stops");

const baselineTokens = total * evidence.archivedB0.generationLimit;
requireCheck(baselineTokens === evidence.archivedB0.totalTokens, "Archived token totals disagree");
const [original, , answerSwitch] = evidence.conditions;
const confirmed = [...evidence.originalNoWaitCorrect, ...original.pending, ...evidence.answerSwitchNewCorrect];
requireCheck(confirmed.every((id) => ids.has(id)) && new Set(confirmed).size === confirmed.length
  && evidence.originalNoWaitCorrect.length === original.correct
  && confirmed.length === answerSwitch.correct
  && answerSwitch.pending.every((id) => !confirmed.includes(id)), "Answer-switch counts do not reconcile");

const percent = (tokens) => (100 * (baselineTokens - tokens) / baselineTokens).toFixed(2) + "%";
const rows = ["| 조건 | 확인된 정답 | 채점 보류 | 생성 토큰 | 과거 B0 대비 감소율 |",
  "| --- | ---: | ---: | ---: | ---: |",
  "| 과거 팀 B0 | 0/" + total + " | — | " + baselineTokens.toLocaleString("en-US") + " | — |"];
for (const arm of evidence.conditions) {
  requireCheck(arm.generated === total && arm.scored + arm.pending.length === total
    && arm.correct >= 0 && arm.correct <= arm.scored && arm.tokens > 0
    && new Set(arm.pending).size === arm.pending.length && arm.pending.every((id) => ids.has(id)),
    "Invalid stored counts for " + arm.name);
  rows.push("| " + [arm.name, arm.correct + "/" + total, arm.pending.length,
    arm.tokens.toLocaleString("en-US"), percent(arm.tokens)].join(" | ") + " |");
}
console.log(rows.join("\n"));
