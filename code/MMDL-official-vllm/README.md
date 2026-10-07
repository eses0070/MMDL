# Qwen3-VL MMMU 실험

**최신 실험 기록은 [README_EXPERIMENT.md](README_EXPERIMENT.md)를 참고하세요.**

2026-10-06 기준 환경, 전체 실행 결과, 반복 중단, 채점 수정 이력 및 최신
563/900 (62.56%) 혼합 채점 결과를 정리했습니다. 공식 점수 재현이나 reasoning
정확성 검증을 완료한 결과는 아닙니다.

아래 내용은 초기 배포 당시 안내를 이력으로 보존한 것입니다. GPU 검증 여부,
배치 저장, resume 미지원 등의 설명은 현재 코드와 다르므로 최신 실행에는 위
문서의 명령과 한계를 우선 적용하세요.

---

# Initial Setup Notes (Historical)

This is a runnable experiment, not a claim to reproduce the reported official score.
No paid API is used. GPU runs have NOT been verified on the school machine yet.

## Optional repetition early-abort experiment

See [REPETITION_GUARD.md](REPETITION_GUARD.md) for the opt-in streaming guard,
smoke test, and scoring policy. This is NOT official scoring or a semantic
correctness verifier: lexical repetition may be missed or falsely flagged.
Detected requests are cancelled, retained as policy-wrong in the denominator,
and never sent to the local judge, even if partial text contains an answer.
Only offline replay and mocked streaming were verified locally for this feature;
school-GPU cancellation and performance still require the six-question smoke test.
Use new result folders; old checkpoint contracts cannot resume after this update.

## Protocol

The bundled Qwen MMMU files are unchanged at commit
96588727e44c78b25ba03ea03b8e12f7e64fd0da. Source hashes are checked before execution.
run.py directly calls their build_mmmu_prompt and prepare_inputs_for_vllm functions.
Do not run package.py again to bless edited upstream code.

- Model: Qwen3-VL-4B-Instruct, revision ebb281ec70b05090aa6165b016eac8ec08e71b17.
- Backend: vLLM, no quantization requested; dtype follows model/vLLM auto selection.
- Official basic prompt, no answer-only constraint and no optional CoT added.
- Pixel budget per image: 1,003,520 to 4,014,080 (not fixed dimensions).
- Output budget: 32,768; temperature .7, top_p .8, top_k 20, penalties 1.0/1.5.
- Seed: 3407 as requested and in root README; upstream MMMU code instead uses 42.
- Context: 128000 by default, tensor parallel 1, GPU allocation .9.
- Dataset: upstream MD5-checked MMMU_DEV_VAL TSV; validation-only default (900),
  --split all selects all upstream rows. This is not the old HF export.
- Default --limit 3 is a smoke run, NOT a benchmark score.
- Local Judge: Qwen3-8B non-thinking, temperature 0, no GPT service. Downloads on
  first use; snapshot path is saved. For repeat runs pass that exact snapshot to
  --judge-model. MC gold is not sent to Judge; open references are sent.
- Judge JSON is validated, not repaired. Invalid JSON, uncertain judgments and
  overlong inputs remain unresolved. No random fallback and no silent truncation.
  A score with unresolved items is reported as bounds, not a definitive accuracy.
- Stop the inference process before launching Judge, so both models do not occupy
  the GPU together. Judge quality must be checked against human-reviewed samples.

## First check (school SSH terminal)

Upload/extract this directory under /home/user/mmdl, then:

```bash
cd /home/user/mmdl/MMDL-official-vllm
python3 run.py preflight
```

Old driver 550.163.01 was observed previously. vLLM binary CUDA/PTX compatibility
must be tested, not inferred solely from nvidia-smi's CUDA label. CUDA 12.x minor
compatibility has limitations. Do not upgrade a shared machine's driver yourself.
If import/kernel initialization fails, stop and discuss a compatible installation
or administrator driver update. No promise that this wheel runs on that driver.

## Separate environment

Do NOT install these packages into the old baseline .venv. Linux commands:

```bash
python3 -m venv .venv-vllm
source .venv-vllm/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip check
python run.py preflight
python -c "import torch, vllm; print(torch.__version__, torch.version.cuda, vllm.__version__); print(torch.ones(1, device='cuda') + 1)"
```

These pins are a local starting configuration, not official reported dependency
versions. The official requirements are unpinned. Separate flash_attn from upstream
requirements is not installed here; this runner relies on vLLM's packaged backends.
The complete resolved Python environment is recorded for each actual run.

## Preview and 3-question inference

```bash
python run.py infer --dry-run
python run.py infer --limit 3 --output-dir results/smoke3
```

The model downloader reuses the existing pinned HF cache. The TSV may require a
large download and disk space. Inference stores output only after the vLLM batch
finishes, like upstream; an interrupted batch needs a new output directory.

If 128k context/concurrent profiling does not fit 24GB, do not reduce pixels or
output tokens first. An explicitly DIFFERENT resource configuration to test is:

```bash
python run.py infer --limit 3 --low-memory --max-model-len 65536 --output-dir results/smoke3_lowmem
```

This sets concurrency to 1 and eager execution, and lowers total context to 65536;
it keeps official pixel/output budgets. It is NOT identical to upstream engine
defaults, may change numerical outcomes, and still has no guarantee of fitting.
Inputs too long for the context should fail rather than silently truncate. Use
the SAME tested engine flags in the full run and record this deviation.

## Local scoring (separate process)

```bash
python run.py judge --predictions results/smoke3/predictions.jsonl --limit 0 --output-dir results/smoke3_judge
```

For the low-memory inference example, change the prediction path accordingly.
The first Judge run downloads Qwen3-8B weights (roughly 16 GB at 16-bit precision,
plus other files/runtime memory). It uses max_num_seqs=1 and eager execution.
Judge default context is 40960. If it cannot initialize, a shorter --judge-context
can be tested; inputs that exceed it are marked unresolved, never silently cut.
No API fees, but GPU/storage costs and model-license obligations still apply.

## Full validation, only after inspecting smoke results

```bash
python run.py infer --limit 0 --output-dir results/validation900
python run.py judge --predictions results/validation900/predictions.jsonl --limit 0 --output-dir results/validation900_judge
```

For inference use --low-memory --max-model-len 65536 only if that was the tested
configuration. Each output directory must be new. No automatic resume/overwrite.
Do not interpret differences from official GPT scoring as model improvements.
The independent MMMU benchmark-author scoring comparison is not implemented in
this package yet. The current summary is LOCAL JUDGE scoring only.

Sources:
- https://github.com/QwenLM/Qwen3-VL/tree/96588727e44c78b25ba03ea03b8e12f7e64fd0da/evaluation/mmmu
- https://github.com/QwenLM/Qwen3-VL/blob/96588727e44c78b25ba03ea03b8e12f7e64fd0da/README.md
- https://huggingface.co/Qwen/Qwen3-8B
- https://docs.vllm.ai/en/v0.11.2/getting_started/installation/gpu/

CPU tests: python -m unittest test_runner -v
