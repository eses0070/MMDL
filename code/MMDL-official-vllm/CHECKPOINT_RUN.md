# Checkpointed inference and length diagnostics

This update prevents completed answers from being lost when an inference job is
interrupted. It does NOT promise faster generation. GPU utilization was high;
long generated answers are a hypothesis to check using saved raw text.

## Changes

- Submit one problem at a time; release preprocessed images after each request.
- Append and fsync each completed answer immediately to predictions.jsonl.
- Refresh summary.json atomically after each completed answer.
- Print START/SAVED, token count, elapsed time, finish reason, last 600 characters.
- --stop-after N pauses after N additional completions while keeping the planned
  --limit unchanged. This allows --limit 0 with a five-question diagnostic pause.
- --resume skips saved rows after checking ordered IDs, source hash, environment,
  engine/generation configuration, model snapshot and code hashes.
- Resume only supports this NEW checkpoint format. Old interrupted all-at-once
  runs cannot be recovered if no predictions were saved. Never merge those runs.
- A malformed/truncated checkpoint is rejected without changing it. Preserve it
  for manual recovery rather than silently dropping bytes. One writer per folder.
- Explicit per-request SamplingParams(seed=3407) is now used, in addition to the
  engine seed. The old implementation set only the engine seed. This is an
  intentional RNG-policy difference to make resumed requests less dependent on
  preceding requests. Bitwise reproducibility across restarts is not guaranteed.
- Default pixels, prompt, dtype, sampling values and 32768 output limit unchanged.
- --max-new-tokens permits an explicitly separate short-budget experiment. It
  changes the evaluation protocol and must use a different output folder.
- context_budget_limited flags inputs that leave less than the requested output
  budget; there is no claim that all inputs can receive 32768 output tokens.
- The Judge is unchanged. This patch provides inference resume, NOT Judge resume.

## Install

Stop the old inference job first. Transfer run.py, checkpointing.py,
inspect_saved.py, test_checkpointing.py and this guide from the patch zip into the
existing school MMDL-official-vllm folder. Keep the environment, upstream files,
source hashes, local_input.py and datasets unchanged. No pip commands needed.

## Start with a five-question pause

In the active .venv-vllm:

```bash
python run.py infer --local-manifest data/local_validation/validation.jsonl --limit 0 --low-memory --max-model-len 49152 --stop-after 5 --output-dir results/validation900_checkpoint
python inspect_saved.py results/validation900_checkpoint
```

The first five rows follow the existing sorted local manifest order; they are
not a representative accuracy sample. Inspect long outputs to distinguish genuine
reasoning from repetition. All raw text is in predictions.jsonl, not just the tail.
No automatic repetition-based stopping or answer-line stopping is introduced.

## Resume the same planned run

After reviewing diagnostics, remove --stop-after and add --resume:

```bash
python run.py infer --local-manifest data/local_validation/validation.jsonl --limit 0 --low-memory --max-model-len 49152 --resume --output-dir results/validation900_checkpoint
```

Do not change the context, generation budget, data, code or packages while resuming.
The first command plans 900 questions but pauses after 5; completed=5, expected=900
is correct. A Ctrl+C during question 6 retains questions 1-5; question 6 reruns.
If interrupted during a disk write, a truncated line can require manual recovery.
Do not run the same output folder from multiple terminals.

## Next speed decisions

If responses are repeatedly long, compare an explicitly labeled 8192-token run
using --max-new-tokens 8192 in a NEW folder, and report accuracy/truncations beside
the 32768 baseline. Do not silently substitute this score for the full budget.
Batch/concurrency tuning may improve throughput but requires GPU-memory tests;
it is not changed by this patch. No live GPU execution was possible locally.
