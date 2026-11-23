"""Verify the archived NoWait records and reconcile the published follow-up summary."""
import hashlib
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parent
ref = ROOT / "reference"
archive = ref / "nowait-reference.tar.gz"
plan = json.loads((ROOT / "records/followup_config.json").read_text())
audit = json.loads((ROOT / "records/nowait-input-audit.json").read_text())
summary = json.loads((ROOT / "records/summary.json").read_text())["answer_switch"]


def check(condition, message):
    if not condition:
        raise ValueError(message)


check(hashlib.sha256(archive.read_bytes()).hexdigest() == (ref / "SHA256SUMS").read_text().split()[0], "Archive SHA-256 mismatch")
with tarfile.open(archive) as bundle:
    def records(kind):
        data = bundle.extractfile(f"nowait/{kind}.jsonl").read()
        check(hashlib.sha256(data).hexdigest() == plan[f"source_{kind}_sha256"], kind)
        rows = [json.loads(line) for line in data.splitlines()]
        index = {row["question_id"]: row for row in rows}
        check(len(index) == len(rows), "Duplicate question")
        return index
    generated = records("generations")
    judged = records("judgments")

targets = set(plan["targets"])
check(len(targets) == 40 and generated.keys() == targets and judged.keys() <= targets, "Target IDs")
correct = {qid for qid, row in judged.items() if row["correct"]}
pending = targets - judged.keys()
check(pending == set(audit["nowait_pending_ids"]), "Pending IDs")
check(correct == {row["question_id"] for row in audit["nowait_correct_rows"]}, "Correct IDs")
tokens = sum(row["generated_tokens"] for row in generated.values())
check(tokens == audit["nowait_tokens"] == summary["reference_generated_tokens"], "Token totals")
print(f"NoWait from JSONL: {len(generated)} generated, {len(judged)} judged, {len(correct)} correct, {len(pending)} pending, {tokens:,} tokens")
print(f"Answer switch from stored summary: {summary['correct']}/{summary['targets']}, {summary['generated_tokens']:,} tokens")
