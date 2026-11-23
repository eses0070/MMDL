# MMMU NoWait 재현

## 저장 결과 검산

저장소 루트에서 `python3 experiments/nowait/verify_reference.py`를 실행한다. Python 기본 라이브러리로 아카이브와 JSONL의 SHA-256을 확인하고, 40개 ID의 생성·판정 파일을 읽어 정답 8건, 보류 2건, 출력 245,360토큰을 계산한다. [기본 NoWait 체크포인트](reference/nowait-reference.tar.gz) · [JSONL 해시](reference/RECORDS.sha256) · [후속 실행 설정](records/followup_config.json)

4,096토큰 전환의 정답 19건과 출력 143,648토큰은 [후속 집계](records/summary.json)의 값이다. 이 체크포인트에는 기본 NoWait 응답이 들어 있다. 후속 조건의 문항별 원문은 GPU 실행 후 생성된다.

## GPU 평가 준비

Linux와 CUDA 12.8용 PyTorch 2.9.0, vLLM 0.11.2를 사용한다. NoWait의 기록 환경은 Transformers 4.57.1, qwen-vl-utils 0.0.14, Pillow 13.0.0이다. Linux에서 Python 3.12 가상환경을 활성화하고 저장소 루트에서 실행한다. GPU가 없는 환경에서는 위 CPU 검산을 사용할 수 있다.

```bash
python -m pip install -r code/MMDL-official-vllm/requirements.txt 'Pillow==13.0.0' datasets
python -m pip check
python -c 'import torch; print(torch.__version__, torch.version.cuda, torch.cuda.get_device_name())'
export HF_HUB_CACHE="$PWD/../mmdl-model-cache"
export MMDL_INPUT="$PWD/../mmdl-validation-export"
export MMDL_RUN="$PWD/../mmdl-nowait-run"
export CUDA_VISIBLE_DEVICES=0
python - <<'PY'
from huggingface_hub import snapshot_download
for model, revision in [
    ("Qwen/Qwen3-VL-4B-Instruct", "ebb281ec70b05090aa6165b016eac8ec08e71b17"),
    ("Qwen/Qwen3-8B", "b968826d9c46dd6066d109eabc6255188de91218"),
]:
    snapshot_download(model, revision=revision)
PY
```

기존 MMMU validation DatasetDict가 있으면 다음 데이터 다운로드를 생략하고 해당 폴더를 `--data-root`로 지정한다. 새로 준비할 때는 NoWait 이미지 복원에 사용한 데이터 리비전을 선택한다.

```bash
PYTHONPATH=code/MMDL-official-vllm python - <<'PY'
from datasets import DatasetDict, load_dataset
from export_local_mmmu import SUBJECTS
revision = "876ce5cb130f7f7e290ce4d9984357737d4db5cf"
DatasetDict({s: load_dataset("MMMU/MMMU", s, revision=revision, split="validation")
             for s in sorted(SUBJECTS)}).save_to_disk("../mmdl-validation-hf")
PY
python code/MMDL-official-vllm/export_local_mmmu.py \
  --data-root ../mmdl-validation-hf --output-dir "$MMDL_INPUT"
```

### 과거 B0 설정으로 새로 생성할 때

900문항 입력은 과거 manifest SHA-256과 대조한다. 일치 여부를 확인한 뒤 별도 출력 디렉터리에서 실행한다. 원본 점수 검산에는 팀 Git의 저장 응답을 사용한다.

```bash
printf '%s  %s\n' eed2e5d5327debaa7602eb67dbcd12cf7e68358c62f464a170bd196bcf420697 "$MMDL_INPUT/validation.jsonl" | sha256sum -c - &&
python code/MMDL-official-vllm/run.py infer --local-manifest "$MMDL_INPUT/validation.jsonl" \
  --limit 0 --low-memory --max-model-len 49152 --max-new-tokens 8192 --use-cot \
  --repetition-guard --output-dir "$MMDL_RUN/b0" &&
python code/MMDL-official-vllm/run.py judge --limit 0 --judge-context 32768 \
  --judge-model "$HF_HUB_CACHE/models--Qwen--Qwen3-8B/snapshots/b968826d9c46dd6066d109eabc6255188de91218" \
  --predictions "$MMDL_RUN/b0/predictions.jsonl" --output-dir "$MMDL_RUN/b0-judge"
```

### NoWait 후속 실험

저장소 루트에서 `bash experiments/nowait/run_gpu.sh reference`를 실행한다. 기본 NoWait의 원본 체크포인트를 복원하고 실험 시점의 팀 커밋에 실행 코드를 배치한다. 40문항의 ID와 이미지 순서·PNG·RGB 해시, 모델 설정을 검사한 뒤 차단 목록 정제와 4,096토큰 전환의 smoke, 생성, 채점을 진행한다. 결과는 `$MMDL_RUN/followup`에 저장한다. 기본 NoWait부터 새로 실행하려면 `bash experiments/nowait/run_gpu.sh fresh`를 사용한다. GPU 재생성에서는 문항별 출력과 점수가 달라질 수 있다.

원자료 출처는 Hyeonjin1/mmdl 커밋 `2b41eafe3a1ec8b2857152cbae7b1579699900d4`의 `runs/20261123_lab_backup`이다. 팀 배포본은 평가자 경로를 환경변수로 받고 원본 체크포인트와 새 실행 결과를 각기 다른 폴더에 저장한다.
