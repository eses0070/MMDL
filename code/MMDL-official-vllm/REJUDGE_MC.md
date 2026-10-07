# MC extraction repair (v1)

This standalone script does not change run.py, inference, original judgments,
or existing checkpoint contracts. It reuses the candidate responses already in
judgments.jsonl; no image inference is needed. No paid API is used.

## Scope

Only original correct=null multiple-choice records are eligible. This includes
both format errors and uncertain judgments, not just potentially correct answers.
The provided 900-row source has 81 eligible rows (44 invalid outputs, 37 uncertain).
The 53 repetition-aborted policy-wrong records and all already-resolved records
remain unchanged, including open-question judgments. No original source is edited.

## Extraction, not solving

The local Qwen3-8B is asked to quote the student's final intended answer and map
it to an option key. It never receives gold or the previous judge's verdict/reason.
Wrong but explicit student choices must be extracted without correction. Diagram
labels are mapped to option contents, not blindly treated as option letters.

vLLM 0.11.2 StructuredOutputsParams(json=...) constrains the output object to
status=matched|uncertain, answer in the actual option keys or null, evidence_quote,
and reason. Null is essential: do not force a choice when no answer exists.
Application validation checks that a matched evidence quote occurs verbatim in the
candidate response; correct is then computed locally from the key and gold.
This presence check does NOT establish that the quote supports the mapping or is
the final commitment. Constrained JSON prevents format errors, not semantic errors.
No image inspection, new problem solving, nearest-option guessing, or automatic
conversion of the old judge's correct/incorrect statuses is performed.

## Run

Place rejudge_mc.py and test_rejudge_mc.py in the existing project directory.
Use the existing .venv-vllm environment after other GPU work has finished.

```bash
python -m unittest test_rejudge_mc
python rejudge_mc.py --judgments results/validation900_cot8192_guard_full_judge/judgments.jsonl --dry-run
python rejudge_mc.py --judgments results/validation900_cot8192_guard_full_judge/judgments.jsonl --limit 3 --output-dir results/mc_rejudge_smoke3
```

After inspecting the three extraction results, retry all 81 from the ORIGINAL:

```bash
python rejudge_mc.py --judgments results/validation900_cot8192_guard_full_judge/judgments.jsonl --output-dir results/validation900_mc_rejudge_v1
```

Model snapshot defaults to the source folder's run_config.json model_snapshot.
If no configuration is available, Qwen/Qwen3-8B is resolved and its snapshot saved.
An unavailable absolute snapshot is an error; --judge-model can explicitly override.
No packages or model versions are silently upgraded. Context=32768, BF16 according
to model auto dtype, greedy decoding, output=512 tokens, seed=3407, no input truncation.

## Artifacts

- run_config.json: source SHA256, source count, selected IDs, model, prompt, environment.
- retries.jsonl: each new result flushed and fsynced, with prior judge fields retained.
- judgments.jsonl: full merged source set in original order, written after retries finish.
- summary.json: full-denominator metrics, retried/resolved/remaining counts.

New output directories are mandatory. A smoke run still writes a 900-row merged
file, but remaining_unretried identifies how many eligible items were not retried.
There is no resume mode: after interruption retain partial retries for inspection
and run again into a new folder. Original judgments are never overwritten.
Runtime/structured-output compilation failures are not hidden by unconstrained fallback.

This is a mixed local scoring revision, NOT official MMMU scoring. Old successful
judgments can still be wrong, and uncertain results are not guaranteed recoverable.
Review evidence quotes and mappings, especially diagram labels. A changed score
reflects scoring changes, not improved student-model performance. No GPU run was
performed locally; CPU tests validate selection, schemas, validation, and merging.

API source: https://github.com/vllm-project/vllm/blob/v0.11.2/vllm/sampling_params.py
