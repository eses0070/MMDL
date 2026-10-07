# Repetition early-abort evaluation

This is an opt-in resource policy, NOT the official evaluation protocol and NOT
a semantic verifier. It does not establish that an aborted response would have
been incorrect if allowed to finish. Keep the baseline and guarded runs separate.

## Detection policy

- Begin checks after 1024 observed generated tokens, then every 128 tokens.
- Inspect the latest 600 normalized words. Case and punctuation are ignored;
  numbers are preserved. This is lexical matching, not semantic similarity.
- Require a 32-word phrase with at least 16 alphabetic words to appear at least
  four times without overlapping, covering at least 20 percent of the window.
- Its latest occurrence must be within 80 words of the output tail.
- Require a second positive check with a newly advancing occurrence. Short
  rechecking and numbers alone are not enough. This conservative heuristic can
  miss paraphrased loops or falsely flag legitimate repeated prose.
- No 180-second timeout is added. No prompt, seed, image limit or token budget
  is changed by the flag. The existing optional CoT still contains its original
  guess instruction, but a detected loop is aborted without requesting a guess.

## Execution and scoring

The opt-in adapter uses vLLM 0.11.2 AsyncLLM cumulative streaming and abort(request_id)
on a persistent asyncio loop, still processing one request at a time. This version
is checked explicitly. The API cancellation and cleanup paths are mock-tested;
live GPU integration must be verified on the school server. Async execution may
differ from the previous synchronous path; bitwise-identical outputs are not promised.
Some tokens can be in flight when cancellation is requested; saved token counts
are observed output tokens, not exact total GPU work.

Detected requests retain raw text and evidence, but result.gen is empty,
prediction is null, correct is false, judge_skipped is true, and finish_reason is
repetition_abort. Partial answer letters are never used. The judge stage bypasses
the LLM for these records and includes them in the denominator. Summary reports
repetition_aborted separately from judged_incorrect and unresolved. Normal EOS
or length termination already received is not retroactively changed to an abort.

Checkpoint contracts include the policy and code hashes; aborted records can be
resumed with the same configuration. Old runs cannot be resumed under the updated
code. Never delete old results; use a new output directory. Do not run two writers
against the same directory. Interrupting an active question saves only previously
completed records; the unfinished question is rerun on resume.

## Install and smoke test

Extract the patch files directly into the existing school MMDL-official-vllm
directory, replacing matching code files. No package installation is necessary.
Do not overwrite files while an inference or judge process is running.

```bash
source .venv-vllm/bin/activate
python -m unittest test_repetition_guard test_cot test_runner test_checkpointing test_local_input
python run.py infer --local-manifest data/local_validation/validation.jsonl --limit 0 --low-memory --max-model-len 49152 --max-new-tokens 8192 --use-cot --repetition-guard --stop-after 6 --output-dir results/validation900_cot8192_guard
python inspect_saved.py results/validation900_cot8192_guard
```

Six questions allow checking that generation proceeds after Accounting 5.
Review any repetition_evidence and gen_raw before expanding the experiment.
Use identical flags plus --resume and remove --stop-after only after verification.
The output budget remains the diagnostic 8192, not the official default 32768.

Scoring is a separate process after inference exits:

```bash
python run.py judge --predictions results/validation900_cot8192_guard/predictions.jsonl --limit 0 --judge-context 32768 --output-dir results/validation900_cot8192_guard_judge
```

## Offline checks and limitations

The CLI `python repetition_guard.py FILE [FILE ...] --report NEW_REPORT.json`
replays saved responses with approximate word-prefix checkpoints, without a GPU.
It does NOT predict exact online stop tokens or seconds. Sources are not modified.

On the two provided Accounting 5 outputs (vLLM and Transformers), both were detected.
On the earlier full900_v3 outputs, 3 of 5 length-limited outputs were detected;
inspection confirmed repetitive tails in Electronics 11, Architecture and
Engineering 14, and Electronics 29. None of the 895 EOS-terminated responses
was flagged in this approximate replay. Many were short answer-only responses,
so this is not evidence of zero false positives on long CoT responses and does
not establish precision/recall on future data. Rules were checked on known cases,
not an independent validation set. No GPU speedup or accuracy gain is claimed.

API reference:
https://github.com/vllm-project/vllm/blob/v0.11.2/vllm/v1/engine/async_llm.py
