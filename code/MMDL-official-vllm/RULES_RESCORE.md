# Conservative MC rollback and rescoring

This CPU-only script discards the retry verdicts for ALL originally unresolved
multiple-choice rows, then reads only explicit terminal answer syntax from the
saved student responses. No model inference or paid API is used. Other original
judgments remain unchanged. This is NOT an all-rule evaluation of the 900 rows.

Accepted: terminal `Answer: B`, `Final Answer: B`, bare `B`, or an answer letter
with exactly matching option text. Markdown headings/bold are tolerated.
No nearest-choice matching, new arithmetic, diagram-label inference, or reading
answers from intermediate calculations is performed. Later reconsideration causes
abstention unless it ends in another accepted answer. This deliberately misses
some valid natural-language/LaTeX answers. It is not the old or official parser.

Unextractable answers count as wrong under this explicitly conservative policy.
They retain `answer_correct=null`, `parse_success=false` and a distinct error;
this does not establish that their reasoning or unknown final answer was wrong.
Reasoning is NOT evaluated. A correct final answer with flawed reasoning cannot
be automatically rejected by this parser; reasoning quality needs a separate,
validated component review and should not be conflated with answer accuracy.
Existing local judgments may still contain errors. Do not claim official scores.

```bash
python -m unittest test_rescore_mc_rules
python rescore_mc_rules.py \
  --original-judgments results/validation900_cot8192_guard_full_judge/judgments.jsonl \
  --retries results/validation900_mc_rejudge_v1/retries.jsonl \
  --output-dir results/validation900_rules_v1
```

`--dry-run` prints the summary without writing. No GPU or new packages required.
The output directory must not exist. Originals are never overwritten. Output:
`judgments.jsonl` (merged results plus provenance on modified rows), `audit.jsonl`
(all retry reversals and parser outcomes), `summary.json`, `run_config.json`
(input hashes, script hash, policy and limitations). All eligible retry IDs must
be supplied; selecting only favorable or unfavorable retries is disallowed.
