#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")/../.."
stage=${1:-run}
output=${2:-results/mmmu_nowait_pilot_20261123}
runtime=/home/gpu/projects/mmdl-b0.UjOD9U
mkdir -p -- "$output"
export HF_HOME="$runtime/hf" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_IMPLICIT_TOKEN=1
export CUDA_VISIBLE_DEVICES=0 VLLM_WORKER_MULTIPROC_METHOD=spawn PYTHONUNBUFFERED=1
export CC="$runtime/.toolchain/env/bin/x86_64-conda-linux-gnu-gcc"
export CPATH="$runtime/.toolchain/env/include/python3.12"

pilot() {
    "$runtime/.venv/bin/python" code/MMDL-official-vllm/nowait_pilot.py "$1" --output "$output"
}

case "$stage" in
    run)
        exec 9>"$output/.run.lock"
        flock -n 9
        pilot smoke
        pilot judge-smoke
        pilot generate
        pilot judge
        ;;
    prepare|smoke|judge-smoke|generate|judge|report) pilot "$stage" ;;
    status)
        python3 - "$output" <<'PY'
import json
import sys
from pathlib import Path
out = Path(sys.argv[1])
for c in ("baseline", "nowait"):
    counts = {}
    for k in ("generations", "judgments"):
        p = out / c / f"{k}.jsonl"
        counts[k] = sum(line.endswith(b"\n") for line in p.open("rb")) if p.exists() else 0
    print(c, counts)
s = out / "summary.json"
if s.exists():
    summary = json.loads(s.read_text())
    print("complete", summary["complete"], "pairs", summary["completed_pairs"], "/", summary["expected_pairs"])
PY
        ;;
    *) printf 'Unknown stage: %s\n' "$stage" >&2; exit 2 ;;
esac
