"""Roll back MC retries and apply a conservative terminal-answer parser (CPU only)."""
import argparse
import copy
import hashlib
import json
import re
from pathlib import Path

from rejudge_mc import eligible, merge_rows, read_rows, task_for


def extract_terminal(text, options):
    # Only the last nonempty line is eligible. Never infer an answer from reasoning.
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    while lines and re.fullmatch(r"[-_*]{3,}", lines[-1]):
        lines.pop()
    if not lines:
        return None, "empty_response", None
    original = lines[-1]
    line = original.replace("**", "").replace("__", "").replace("`", "")
    line = re.sub(r"^[\s#>*\-\u2705\u2714\ufe0f]+", "", line).strip()
    prefix = r"(?:(?:so|therefore|thus)[, ]+)?(?:the )?(?:final |correct |best )?answer(?: is)?\s*[:=]?\s*"
    match = re.fullmatch(prefix + r"(?:option\s+)?\(?([A-Z])\)?(?:[.!])?", line, re.I)
    if not match:
        match = re.fullmatch(r"\(?([A-Z])\)?[.!]?", line)
    if match:
        answer = match[1].upper()
        if answer in options:
            return answer, "terminal_explicit_letter", original
        return None, "invalid_option_key", original
    # When a choice includes its text, require exact option-content agreement.
    match = re.fullmatch(prefix + r"(?:option\s+)?([A-Z])[.:)]\s*(.+)", line, re.I)
    if match:
        answer, content = match[1].upper(), match[2]
        normalize = lambda s: re.sub(r"\s+", " ", s).strip().rstrip(".! ").casefold()
        if answer in options and normalize(content) == normalize(options[answer]):
            return answer, "terminal_letter_and_option_text", original
        return None, "option_content_mismatch", original
    return None, "no_unambiguous_terminal_answer", original


def rescore(original, retries):
    # Validate retry identity, task, gold and eligibility before discarding its verdict.
    merge_rows(original, retries)
    target_ids = {r["question_id"] for r in retries}
    expected = {r["question_id"] for r in original if eligible(r)}
    if target_ids != expected:
        raise ValueError("Supply all eligible retries, not a selected or smoke subset")
    previous = {r["question_id"]: r for r in retries}
    output, audit = [], []
    for source in original:
        row = copy.deepcopy(source)
        if row["question_id"] in target_ids:
            task = task_for(source)
            if str(source["gold"]).strip().upper() not in task["options"]:
                raise ValueError("Invalid gold option")
            answer, reason, evidence = extract_terminal(task["candidate_response"], task["options"])
            answer_correct = None if answer is None else answer == str(source["gold"]).strip().upper()
            row["previous_original_judgment"] = copy.deepcopy(source)
            row["previous_retry_judgment"] = copy.deepcopy(previous[row["question_id"]])
            for key in ("raw_judge_response", "finish_reason", "error", "extraction", "repair_protocol"):
                row.pop(key, None)
            row.update(prediction=answer, answer_correct=answer_correct,
                       correct=answer_correct is True, parse_success=answer is not None,
                       scoring_method="terminal_rules_v1_abstention_counts_wrong",
                       reasoning_correct=None, parser_reason=reason, evidence_quote=evidence)
            if answer is None:
                row["error"] = "unextractable_counted_wrong"
            audit.append({"question_id": row["question_id"],
                          "retry_correct": previous[row["question_id"]]["correct"],
                          "retry_prediction": previous[row["question_id"]].get("prediction"),
                          "prediction": answer, "correct": row["correct"],
                          "answer_correct": answer_correct, "parser_reason": reason,
                          "evidence_quote": evidence})
        output.append(row)
    hits = sum(r["correct"] is True for r in output)
    unresolved = sum(r["correct"] is None for r in output)
    summary = dict(completed=len(output), correct=hits, unresolved=unresolved,
        accuracy_pct=100 * hits / len(output) if output and not unresolved else None,
        rolled_back_retry_count=len(audit), unchanged_original_count=len(output)-len(audit),
        rules_extracted=sum(r["prediction"] is not None for r in audit),
        unextractable_counted_wrong=sum(r["prediction"] is None for r in audit),
        reasoning_evaluated=False,
        protocol="Original local judgments + rules for all originally unresolved MC; unextractable=wrong; NOT official MMMU scoring")
    return output, audit, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-judgments", type=Path, required=True)
    parser.add_argument("--retries", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    originals, retries = read_rows(args.original_judgments), read_rows(args.retries)
    rows, audit, summary = rescore(originals, retries)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.dry_run:
        return
    if args.output_dir is None:
        parser.error("--output-dir required without --dry-run")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    for name, values in (("judgments.jsonl", rows), ("audit.jsonl", audit)):
        with (args.output_dir / name).open("x", encoding="utf-8") as handle:
            for row in values:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    metadata = {"policy": "terminal_rules_v1_abstention_counts_wrong", "sources": {
        str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (args.original_judgments, args.retries)},
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "limitations": ["Not the old parser or official MMMU parser",
            "No reasoning verification: reasoning_correct=null",
            "Terminal syntax is conservative and can miss valid answers",
            "Only originally unresolved MC rows changed; other local judge errors may remain",
            "Unextractable is a scoring policy, not proof of a wrong answer or reasoning"]}
    for name, value in (("summary.json", summary), ("run_config.json", metadata)):
        with (args.output_dir / name).open("x", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
