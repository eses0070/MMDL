"""Inference checkpoint validation and progress reporting (stdlib only)."""
import hashlib
import json
import os
from pathlib import Path


def contract_hash(contract):
    return hashlib.sha256(json.dumps(contract, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def atomic_json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def load_checkpoint(directory, contract):
    config = json.loads((directory / "run_config.json").read_text(encoding="utf-8"))
    digest = contract_hash(contract)
    if config.get("checkpoint_contract_hash") != digest:
        raise ValueError("Resume contract mismatch or old non-checkpoint run. Use a NEW output directory.")
    path = directory / "predictions.jsonl"
    if not path.exists():
        return []
    content = path.read_text(encoding="utf-8")
    if content and not content.endswith("\n"):
        raise ValueError("Incomplete last checkpoint line; preserve file for recovery, do not append.")
    rows = [json.loads(line) for line in content.splitlines() if line.strip()]
    expected_ids = contract["selected_ids"]
    if len(rows) > len(expected_ids):
        raise ValueError("Too many checkpoint rows")
    for i, row in enumerate(rows):
        if (str(row["question_id"]) != expected_ids[i]
                or row.get("checkpoint_contract_hash") != digest):
            raise ValueError("Checkpoint IDs/order/config mismatch")
        if not isinstance(row["result"]["gen"], str) or row["finish_reason"] not in ("stop", "length", "repetition_abort"):
            raise ValueError("Invalid checkpoint output")
        if row["finish_reason"] == "repetition_abort":
            if (row.get("prediction", "missing") is not None or row.get("correct") is not False
                    or row["result"]["gen"] != "" or not row.get("repetition_evidence")
                    or row.get("judge_skipped") is not True):
                raise ValueError("Invalid repetition-abort record")
    return rows


def append_checkpoint(handle, row):
    handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    handle.flush()
    os.fsync(handle.fileno())


def summarize(rows, expected):
    count = len(rows)
    seconds = sum(r.get("elapsed_seconds", 0) for r in rows)
    tokens = sum(r["generated_tokens"] for r in rows)
    return dict(completed=count, expected=expected, complete=count == expected,
                length_limited=sum(r["finish_reason"] == "length" for r in rows),
                repetition_aborted=sum(r["finish_reason"] == "repetition_abort" for r in rows),
                policy_wrong=sum(r["finish_reason"] == "repetition_abort" for r in rows),
                context_budget_limited=sum(r.get("context_budget_limited", False) for r in rows),
                generated_tokens=tokens, mean_generated_tokens=tokens/count if count else None,
                max_generated_tokens=max((r["generated_tokens"] for r in rows), default=0),
                mean_seconds_per_question=seconds/count if count else None,
                elapsed_question_seconds=seconds, scoring="pending")
