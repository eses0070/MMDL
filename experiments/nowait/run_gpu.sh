#!/usr/bin/env bash
set -euo pipefail
: "${MMDL_INPUT:?Set MMDL_INPUT to the MMMU validation export directory}"
: "${HF_HUB_CACHE:?Set HF_HUB_CACHE to the pinned snapshots cache}"
: "${MMDL_RUN:?Set MMDL_RUN to a separate experiment directory}"
pkg=$(cd "$(dirname "$0")" && pwd)
repo=$(git -C "$pkg" rev-parse --show-toplevel)
mkdir -p "$MMDL_RUN"
run=$(cd "$MMDL_RUN" && pwd)
export MMDL_INPUT=$(realpath "$MMDL_INPUT") HF_HUB_CACHE=$(realpath "$HF_HUB_CACHE")
base=1c4d7b32ab254d8444b401b06750dfb6e2bfca9e
checkout="$run/team"
if [[ ! -e "$checkout" ]]; then git -C "$repo" worktree add --detach "$checkout" "$base"; fi
[[ $(git -C "$checkout" rev-parse HEAD) == "$base" ]]
code="$checkout/code/MMDL-official-vllm"
cp "$pkg"/pilot/nowait* "$code/"
lookback="$checkout/results/mmmu_lookback_pilot_20261123"
mkdir -p "$lookback/baseline"
gzip -dc "$pkg/records/lookback_predictions.jsonl.gz" > "$lookback/baseline/predictions.jsonl"
cp "$pkg/records/lookback_config.json" "$lookback/pilot_config.json"
for file in target_ids.json image_manifest.json; do
  if [[ -e "$MMDL_INPUT/$file" ]]; then cmp "$pkg/records/$file" "$MMDL_INPUT/$file"; else cp "$pkg/records/$file" "$MMDL_INPUT/$file"; fi
done
export MMDL_PILOT_OUTPUT="$run/pilot" MMDL_FOLLOWUP_OUTPUT="$run/followup"
export PYTHONPATH="$code" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 VLLM_WORKER_MULTIPROC_METHOD=spawn
case "${1:-reference}" in
  reference)
    export MMDL_PILOT_OUTPUT="$run/reference"
    (cd "$pkg/reference" && sha256sum -c SHA256SUMS)
    if [[ ! -e "$MMDL_PILOT_OUTPUT" ]]; then
      tmp=$(mktemp -d "$run/reference.XXXXXX")
      tar xzf "$pkg/reference/nowait-reference.tar.gz" -C "$tmp"
      mv -T "$tmp" "$MMDL_PILOT_OUTPUT"
    fi
    (cd "$MMDL_PILOT_OUTPUT" && sha256sum -c "$pkg/reference/RECORDS.sha256")
    export MMDL_REFERENCE_PLAN="$pkg/records/followup_config.json"
    ;;
  fresh)
    unset MMDL_REFERENCE_PLAN
    export MMDL_FOLLOWUP_OUTPUT="$run/followup-fresh"
    for stage in smoke judge-smoke generate; do python "$code/nowait_pilot.py" "$stage" --output "$MMDL_PILOT_OUTPUT"; done
    # The judge may leave pending items. Continue only for its explicit pending-score error.
    log="$run/pilot-judge.log"
    if ! python "$code/nowait_pilot.py" judge --output "$MMDL_PILOT_OUTPUT" > "$log" 2>&1; then
      tail -n 1 "$log" | grep -q '^RuntimeError: Unscored Judge failures, can resume:' || { cat "$log" >&2; exit 1; }
    fi
    ;;
  *) echo "Use reference or fresh" >&2; exit 2 ;;
esac
for stage in smoke generate judge; do python "$pkg/followup/nowait_followup.py" "$stage"; done
