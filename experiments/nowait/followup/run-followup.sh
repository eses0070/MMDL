#!/usr/bin/env bash
set -euo pipefail
cd /home/gpu/projects/MMDL-team
runtime=/home/gpu/projects/mmdl-b0.UjOD9U
export PYTHONPATH="$PWD/code/MMDL-official-vllm"
export HF_HOME="$runtime/hf" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_IMPLICIT_TOKEN=1
export CUDA_VISIBLE_DEVICES=0 VLLM_WORKER_MULTIPROC_METHOD=spawn PYTHONUNBUFFERED=1
export CC="$runtime/.toolchain/env/bin/x86_64-conda-linux-gnu-gcc"
export CPATH="$runtime/.toolchain/env/include/python3.12"
exec 8>/work/.followup-run.lock
flock -n 8
for stage in smoke generate judge; do
    echo "STAGE $stage $(date -Is)"
    "$runtime/.venv/bin/python" /work/nowait_followup.py "$stage"
done
echo "FOLLOWUP_END $(date -Is)"
