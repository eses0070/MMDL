// Run from a team repository checkout containing both recorded commits (Node.js 18+).
const { execFileSync } = require("node:child_process");
const assert = require("node:assert/strict");

const main = "d99860997b0a18541a3187b6a35db878621793c1";
const parser = "8734934b029a01879207052d34ded8ab9a970c70";
const directory = "experiments/parser_v2";
const result = directory + "/results/verified_parser_v2";

function read(revision, path) {
  return execFileSync("git", ["show", revision + ":" + path], {
    encoding: "utf8", maxBuffer: 32 * 1024 * 1024
  });
}

function indexed(revision, path) {
  const rows = read(revision, path).trim().split(/\r?\n/).map(line => JSON.parse(line));
  const records = new Map(rows.map(row => [row.question_id, row]));
  assert.equal(records.size, rows.length, "Duplicate question ID: " + path);
  return records;
}

function hits(records) {
  return [...records.values()].filter(row => row.correct === true).length;
}

function changes(before, after) {
  assert.equal(before.size, after.size);
  const changed = [];
  for (const [id, row] of before) {
    assert.ok(after.has(id), "Missing question: " + id);
    if (row.correct !== after.get(id).correct) changed.push(id);
  }
  return changed.sort();
}

const b0 = indexed(main, "results/validation900_rules_v1/judgments.jsonl");
const previous = indexed(parser, directory + "/inputs/current_judgments.jsonl");
const updated = indexed(parser, result + "/judgments.jsonl");
const remaining = indexed(parser, result + "/remaining.jsonl");
const evidence = JSON.parse(read(parser, "experiments/nowait/evidence.json"));
assert.equal(b0.size, 900);
assert.equal(remaining.size, 40);
for (const [id, row] of remaining) {
  assert.equal(row.generation_finish_reason, "length");
  assert.equal(updated.get(id).correct, false);
}
console.log("B0 → Parser v2 input:", changes(b0, previous));
console.log("Parser v2 input → output:", changes(previous, updated));
console.log("B0 / Parser v2 input / output:", hits(b0), hits(previous), hits(updated));
for (const arm of evidence.conditions) {
  assert.equal(arm.generated, remaining.size);
  assert.equal(arm.scored + arm.pending.length, arm.generated);
  const correct = hits(updated) + arm.correct;
  console.log(arm.name + ": " + correct + "/" + b0.size +
    " (" + (100 * correct / b0.size).toFixed(2) + "%)");
}
