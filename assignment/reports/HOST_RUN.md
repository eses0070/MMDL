# Current-host runtime and commands

This publication includes the code executed for this restoration, exact resolved configuration and aggregate/lightweight decision records. Private raw assets, processed QA, runtime pointers under `.restore`, local run receipts, weights and adapters are excluded. Cloning Git alone does not reconstruct those private assets or bootstrap state. The preparation scripts require the locally restored source snapshot, pinned model metadata and recorded B0/runtime pointers; missing these prerequisites must be restored explicitly, not treated as already available.

## Current host

Training Python: `/home/user/mmdl-work/.venv-restore-train/bin/python` (torch2.7.0+cu118).
Evaluation Python: `/home/user/mmdl-work/.venv-restore-eval/bin/python` (vLLM0.11.2, torch2.9.0, CUDA12.8 build).
GPU: one RTX4090, driver535.274.02. CUDA arithmetic/backward and the actual vLLM engine passed. Drivers were unchanged. Model uses volatile `/dev/shm/mmdl-user/ebb281ec70b05090aa6165b016eac8ec08e71b17`; reboot removes this cache. No automatic restart/retraining after reboot or failed receipts.

## Completed execution

The executed stages used `code/restore/run.py --stage train --experiment E1` (and independently E2/E3), then `--stage reload --experiment E1 --adapter <successful-run>/adapter`, then evaluation Python `--stage evaluate --experiment E1 --adapter <successful-run>/adapter`. Evaluation has no `--smoke` for main runs. Existing original MMMU responses were rescored without another original MMMU inference. The only original-model inference was `--stage check_base` on three source heldout checks (300 questions).

Before the main runs, a separate eight-question/two-update adapter passed training/reload; its full diagnostic evaluation completed separately. Main adapters initialize the original model independently.

## Read progress and reports

```bash
cd /home/user/mmdl-work
bash scripts/restored_status.sh
cat .restore/suite_state.json
tail -n 30 .restore/host_suite.log
nvidia-smi
```

The suite is now completed. These commands only inspect it. Do not launch another suite to publish reports. Report refresh is CPU-only:

```bash
/home/user/mmdl-work/.venv-restore-train/bin/python /home/user/mmdl-work/code/restore/report.py
```

The host suite was kept alive in tmux, with owned GPU jobs executed one at a time. `tmux list-sessions` lists surviving sessions; completed sessions may have exited. New launches use a suite lock and refuse source/config mismatch or unreviewed failures. Publication errors never require new training.

## Environment repairs

Pinned evaluation NumPy2.2.6 conflicted with inherited NumPy1 binary modules. Installed **inside the evaluation venv only**: scipy1.15.3 (same as historical), scikit-learn1.5.2, numexpr2.10.2 and bottleneck1.4.2. Parent packages stayed intact. A separate vLLM0.11.2 UUID parsing error was fixed by selecting physical GPU index0 only after confirming the host has one GPU. Historical prompts, token budgets, sampling, image processing and parser remain fixed. Actual environments and source hashes are recorded in provenance and local run receipts.
