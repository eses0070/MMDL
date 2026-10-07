# Optional official CoT comparison

This patch adds `--use-cot`, off by default. The suffix is copied exactly from
the pinned upstream optional CoT branch, not a claim that the reported Instruct
score used this option. It requests a reasoned guess when uncertain and discourages
indefinite repetition. It does not guarantee termination or correctness.

Extract this patch into the existing MMDL-official-vllm folder, replacing run.py.
Offline adapter and checkpoint support files are included. Upstream files remain
unchanged and must already be present from the original package.

Run the same first five Accounting questions with the same 8192-token budget as
the preceding non-CoT comparison. No timeout or repetition-based cutoff is added.
This small diagnostic is not representative of the full benchmark.

```bash
python -m unittest test_cot test_runner test_checkpointing test_local_input
python run.py infer --local-manifest data/local_validation/validation.jsonl --limit 0 --low-memory --max-model-len 49152 --max-new-tokens 8192 --use-cot --stop-after 5 --output-dir results/validation900_cot8192
python inspect_saved.py results/validation900_cot8192
```

Use a new output directory. Old checkpoints cannot resume under this updated
runner because its code hash changed. Never mix CoT and non-CoT records. Future
resumes of this new run must keep `--use-cot` and all other protocol flags unchanged.

The prompt flag and exact suffix are recorded in run_config.json and the resume
contract; actual messages are stored per prediction. Seed remains 3407, pixel
limits and sampling parameters remain unchanged, and scoring remains separate.
The 8192 budget is a deliberate deviation from the public 32768-token default;
local data equivalence and official report reproduction are still unverified.

Source: https://github.com/QwenLM/Qwen3-VL/blob/96588727e44c78b25ba03ea03b8e12f7e64fd0da/evaluation/mmmu/run_mmmu.py
