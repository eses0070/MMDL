# Current-host E1/E2/E3 restoration

Suite status: **completed**.

Current host verified by the agent outside the Codex sandbox: user user, AIX408-4, one RTX4090 (24564MiB), driver535.274.02. At probe:0% utilization,18MiB used, no compute processes. Training Python torch2.7.0+cu118 passed CUDA arithmetic and BF16 backward. Codex sandbox nvidia-smi exit9 and missing CUDA access are recorded separately; these are not host driver failures. No driver changes.

Separate training venv inherits existing sam3 torch2.7.0+cu118; own transformers4.57.1, PEFT0.17.1, accelerate1.15.0. Existing parent packages preserved. Training torch differs from the historical installation; all three experiments use the same restored environment. Evaluation requires pinned vLLM0.11.2/torch2.9.0/transformers4.57.1/qwen-vl-utils0.0.14; actual engine compatibility is checked before main learning. Model weights use a volatile RAM cache because persistent disk is constrained; adapters/results stay on disk. Reboot requires re-downloading the pinned model.

MMMU official validation was recovered at revision98e6ac0cb9b7b2cd2c991b85a50762edc4aedc68:900 questions,982 images. Historical manifest SHA256 eed2e5d5327debaa7602eb67dbcd12cf7e68358c62f464a170bd196bcf420697 matches exactly. QA/options/image ordering and all decoded images verified. Original MMMU model inference is forbidden. Initial493/900 responses were not used.

Official pinned ChartQA train_human and validation, TabMWP train/dev and table PNGs, and password-protected PGPS9K ZIP/diagram PNGs were downloaded. E1=ChartQA1000; E2=500 of E1 plus TabMWP500; E3=PGPS9K1000. Checks100/source. Published historical train manifests/IDs were absent, so these are new seed3407 manifests. E2 ChartQA is stratified by new training-question operations and answer forms, not historical MMMU labels. Exact image/table group overlap across training/checks is zero; exact MMMU text/RGB and dHash<=2 candidates excluded. PGPS/Geometry3K official test diagrams are excluded. Unsafe PGPS option mappings are rejected without rounding or guessing. Relations/programs are not input. Semantic contamination is not exhaustively ruled out.

| Model/record | Correct /900 | Accuracy | Meaning |
|---|---:|---:|---|
| Historical mixed |563/900|62.56%|Preserved mixed judge/rules|
| B0 uniform |491/900|54.56%|Saved-response rescoring; no new inference|
| E1 |482/900|53.56%|Delta B0 -1.00pp|
| E2 |470/900|52.22%|Delta B0 -2.33pp|
| E3 |471/900|52.33%|Delta B0 -2.22pp|

B0: parse failures130, length finishes60, repetition aborts53. Delta from mixed is−8.00pp from scoring policy, not learning. Exact frozen latest_vllm_final_v2 extraction does not see GT. Unextractable/aborted outputs count wrong; length limits retain extractable final answers. Synthetic checks and all900 real response formats were checked; original scorer code is frozen.

Training: BF16 language attention/MLP LoRA r16/alpha32/dropout0.05; vision/merger frozen; micro1/accum4; AdamW lr1e-4/weight_decay0.01; warmup13 actual updates then constant;1epoch/1000 exposures/250 updates; max4096/pixels200704–1003520; seed3407. Separate8-question/2-update smoke adapter never continues into E1/E2/E3. Each main run starts original weights independently. Reload generation is a separate process. GPU stages run sequentially and preserve unrelated jobs.

Evaluation reuses historical messages, image processing, CoT suffix,8192 output/49152 context,seed3407,.7/.8/top_k20,repetition1.0/presence1.5 and frozen streaming guard. Dynamic BF16 LoRA kernels are a required adapter-specific backend difference. Expanded input-token counts must equal historical counts. Source heldout checks have a separately authorized original-model comparator; no MMMU re-inference. Work-type/non-target metrics remain unavailable without reviewed old ID-level labels; subjects and MC/open formats are reported separately.

Full private run records retain command/config/environment/data hashes/source provenance/progress/errors/checkpoints/responses/decisions. Publication contains code, regeneration settings and aggregates only. Publication failure never re-executes learning. One seed and MMMU validation development comparison; no official-score or replicated-improvement claim.

See [metrics.json](metrics.json) for subject/format/error rates and [config.json](config.json) for exact settings and data hashes. [Host commands](HOST_RUN.md).
