# MMMU Best Model 결과 보고서

최종 발표의 **Best Model**은 Qwen3-VL-4B-Instruct에 혼합 채점, Parser v2, NoWait 및 4,096토큰 답안 전환을 적용한 평가 구성이다. 모델 가중치는 고정했다. MMMU validation 900문항에서 **587/900(65.22%)**을 기록했다. 이 점수는 Parser v2까지 반영한 568건에 동일한 미추출 객관식 40문항의 답안 전환 결과 19건을 더한 값이다.

초기 베이스라인은 프로젝트 시작 시점의 Transformers 실행 결과 **493/900(54.78%)**이다. 이후 vLLM B0의 혼합 채점 **563/900(62.56%)**은 미추출 문항을 분석하고 후속 실험을 설계할 때 사용한 비교 기록이다.

## 1. 시작점과 후속 B0 실행

초기 Transformers 실행에서는 객관식에 선택지 한 글자를 요청하고, 주관식에는 풀이 후 마지막 줄에 답을 쓰도록 했다. 생성 상한은 객관식 2,048토큰, 주관식 8,192토큰이었다. 객관식 472/847, 주관식 21/53으로 전체 **493/900(54.78%)**을 기록했다. [초기 베이스라인 보고서](mmmu_baseline.md)

후속 B0 실행에서는 vLLM으로 900개 응답을 새로 생성했다. Qwen의 선택적 CoT 프롬프트를 사용하고 생성 상한을 8,192토큰, 전체 컨텍스트를 49,152토큰으로 설정했다. 반복 감지 시 생성을 중단했다. 900건 중 60건은 길이 한도에서, 53건은 반복 감지로 종료됐다. 초기 실행과 B0는 프롬프트·백엔드·생성 설정과 채점 절차가 함께 달라졌다. [B0 생성 및 채점 보고서](mmmu_baseline_vllm_cot_rules.md)

## 2. 혼합 채점으로 과거 B0 점수 확정

로컬 Qwen3-8B Judge와 반복 중단 처리 결과는 정답 537건, 오답 282건, 미해결 81건이었다. 미해결 객관식 81건에만 응답 마지막 줄의 선택지 문자·내용을 확인하는 규칙을 적용했다. 35건에서 답을 추출해 정답 26건, 오답 9건을 확인했고, 남은 46건은 미추출 오답으로 집계했다. **537 + 26 = 563건**이다. 객관식은 539/847, 주관식은 24/53이었다.

객관식은 최종 선택지를 추출한 뒤 정답표와 비교했다. 주관식은 Judge에 허용 답안 목록을 제공해 동치 여부를 판정했다. 팀의 CPU 재집계에서 과거 B0의 900개 판정이 모두 일치했다. [혼합 채점 검증 보고서](weakness_finetuning/MIXED_SCORING_AUDIT_20261011/REPORT_KO.md) · [B0 집계](../../results/validation900_rules_v1/summary.json)

## 3. Parser v2로 미추출 원인 분리

미추출 객관식 46건의 저장 응답을 다시 읽었다. 최종 답 뒤의 주석, 그림 라벨과 선택지 문자의 차이, 문장 안에 쓴 최종 선택을 처리했다. 필요한 경우 저장된 Judge의 답 제안과 모델 원문의 최종 선택을 대조했다. 정상 종료된 6건에서 최종 선택을 추가로 추출했고, 이 중 4건이 정답이었다. 예를 들어 기초의학 17번에서 모델이 답한 그림 라벨 E는 선택지 A의 내용이어서 A로 채점했다.

Parser v2 기준본에서는 전자공학 주관식 2번의 모델 답 `2√2`를 기준 답 `2.83`과 소수점 둘째 자리에서 동치로 인정한 판정이 이미 반영돼 있었다. 따라서 미추출 객관식 46건 재채점의 출발점은 564건이고, 새 객관식 정답 4건을 더한 결과는 **568/900**이다. 900개 문항 ID를 기준으로 세 채점 파일을 대조했다. 563 → 564에서 정오가 바뀐 문항은 `validation_Electronics_2` 한 건이다. 564 → 568에서 오답에서 정답으로 바뀐 문항은 기초의학 17번, 생물 3번, 디자인 27번, 심리 21번이다. 남은 40건은 전부 8,192토큰 한도에 도달한 객관식이었다. [Parser v2 보고서](https://github.com/eses0070/MMDL/blob/b5bd7c706208de056174719746511ef27588ff1f/assignment/reports/parser_v2.md) · [선정된 40문항](https://github.com/eses0070/MMDL/blob/b5bd7c706208de056174719746511ef27588ff1f/experiments/parser_v2/results/verified_parser_v2/remaining.jsonl)

## 4. NoWait으로 미추출 40문항 재추론

NoWait은 생성 중 `wait`, `hmm` 등 자기검토 표현과 철자가 겹치는 토큰의 선택을 억제한다. 기본 실험은 918개 토큰을 차단했다. 후속 실험에서는 차단 예외를 적용해 886개로 줄이는 방식과, 원래 918개 마스크를 사용하면서 4,096토큰에서 답안으로 전환하는 방식을 각각 평가했다.

답안 전환은 풀이가 4,096토큰에 도달하면 원래 이미지와 생성한 풀이를 다시 제시하고 최종 선택지 하나를 요청한다. 추가 출력 한도는 128토큰이며, 40문항 중 29문항에서 전환이 발동했다.

| 동일한 객관식 40문항 | 확인된 정답 | 채점 보류 | 생성 토큰 | 과거 B0 대비 출력 감소율 |
| --- | ---: | ---: | ---: | ---: |
| 과거 B0 | 0/40 | — | 327,680 | — |
| NoWait | 8/40 | 2 | 245,360 | 25.12% |
| NoWait · 차단 목록 정제 | 8/40 | 2 | 244,736 | 25.31% |
| **NoWait · 4,096토큰 답안 전환** | **19/40** | **1** | **143,648** | **56.16%** |

답안 전환에서 확인한 19건은 기본 NoWait에서도 맞힌 8건, 기본 NoWait에서 채점 보류였던 2건, 그 밖에 새로 맞힌 9건이다. 토큰 감소율은 과거 저장 응답과 재추론 응답의 출력 길이를 비교한 값이다. 29건의 답안 전환에서 재요청에 사용한 입력 156,034토큰은 별도로 집계했다. [40문항 실험 기록과 과거 B0 기준 과목별 결과](https://github.com/Hyeonjin1/mmdl/blob/0de911b19a2e4ff5c207731278f4d792aa1cb554/runs/20261123_lab_backup/NOWAIT_REPORT_KO.md)

## 5. Best Model 전체 점수

최종 구성에 이르기까지의 점수는 아래와 같다. 마지막 두 행은 각각 Parser v2의 568건에 같은 미추출 40문항의 재추론 결과를 반영한 것이다. 이 40개 ID는 Parser v2의 미추출 목록과 답안 전환 설정에서 일치하며, Parser v2에서는 전부 점수상 오답이었다. 나머지 860건의 판정을 유지하고 보류도 분모 900에 포함한다.

| 단계 | 전체 정답 | 정확도 |
| --- | ---: | ---: |
| 초기 베이스라인 (Transformers) | 493/900 | 54.78% |
| 후속 B0 혼합 채점 (vLLM) | 563/900 | 62.56% |
| 주관식 판정 보완 후 · Parser v2 적용 직전 | 564/900 | 62.67% |
| Parser v2 적용 후 | 568/900 | 63.11% |
| Parser v2 + NoWait | 576/900 | 64.00% |
| **Best Model · Parser v2 + NoWait·4,096토큰 답안 전환** | **587/900** | **65.22%** |

객관식·주관식으로 풀어 쓰면 Parser v2는 **543/847 + 25/53 = 568/900**, 답안 전환을 반영한 최종 결과는 **562/847 + 25/53 = 587/900**이다. 초기 Transformers 실행의 493건은 별도 생성 결과다. 개인 NoWait 보고서의 582건은 과거 혼합 채점 563건에 재추론 정답 19건만 더한 집계이며, 이 문서의 587건은 그 사이의 재채점 증가분 5건까지 포함한다.

## 6. 재현 코드와 실행 방법

### 저장된 판정에서 900문항 점수 검산

Git과 Node.js 18 이상이 있는 환경에서 아래 명령을 실행한다. 스크립트는 두 고정 커밋의 채점 파일을 문항 ID로 읽어 정오가 바뀐 문항을 출력한다. 이어서 Parser v2의 미추출 40건이 모두 기존 점수상 오답인지 확인하고, 저장된 NoWait 조건별 정답 수를 반영한다. [900문항 검산 코드](../../experiments/nowait/verify_baseline_totals.cjs) · [NoWait 조건별 집계 입력](https://github.com/eses0070/MMDL/blob/8734934b029a01879207052d34ded8ab9a970c70/experiments/nowait/evidence.json)

```bash
git clone https://github.com/eses0070/MMDL.git MMDL
cd MMDL
git fetch origin seokmin
node experiments/nowait/verify_baseline_totals.cjs
```

기대 결과는 혼합 채점 563건, Parser v2 입력 564건, Parser v2 출력 568건, 기본 NoWait 반영 576건, 답안 전환 반영 587건이다.

### 단계별 실행 코드

| 단계 | 실행 코드와 입력 | 확인할 결과 |
| --- | --- | --- |
| 초기 Transformers 평가 | [평가 스크립트](../../code/eval_mmmu_v3.py) · [모델·데이터 리비전 및 실행 명령](mmmu_baseline.md) | GPU에서 MMMU 900문항을 생성·채점한 초기 결과 493건 |
| B0 응답 생성·Judge 채점 | [로컬 MMMU 데이터 변환](../../code/MMDL-official-vllm/export_local_mmmu.py) · [추론 및 채점 진입점](../../code/MMDL-official-vllm/run.py) · [실행 명령과 환경](mmmu_baseline_vllm_cot_rules.md) | `infer`로 B0 응답 생성 후 `judge`로 저장 판정 생성 |
| B0 혼합 채점 재현 | [규칙 재채점 코드](../../code/MMDL-official-vllm/rescore_mc_rules.py) · [원 Judge 판정](../../results/validation900_cot8192_guard_full_judge/judgments.jsonl) · [81개 재시도 기록](../../results/validation900_mc_rejudge_v1/retries.jsonl) | 저장 판정 819건 유지, 미해결 81건 처리, 전체 정답 563건 |
| Parser v2 재채점 | [재실행 코드](https://github.com/eses0070/MMDL/blob/8734934b029a01879207052d34ded8ab9a970c70/experiments/parser_v2/replay.py) · [입력 해시](https://github.com/eses0070/MMDL/blob/8734934b029a01879207052d34ded8ab9a970c70/experiments/parser_v2/PROVENANCE.json) · [테스트와 실행 안내](https://github.com/eses0070/MMDL/blob/8734934b029a01879207052d34ded8ab9a970c70/experiments/parser_v2/README.md) | 저장 입력에서 564 → 568건, 미추출 40건 |
| NoWait 생성·채점 | [실험 스크립트](https://github.com/Hyeonjin1/mmdl/blob/0de911b19a2e4ff5c207731278f4d792aa1cb554/runs/20261123_lab_backup/code/MMDL-official-vllm/nowait.sh) · [파일럿 코드](https://github.com/Hyeonjin1/mmdl/blob/0de911b19a2e4ff5c207731278f4d792aa1cb554/runs/20261123_lab_backup/code/MMDL-official-vllm/nowait_pilot.py) · [마스크 구현](https://github.com/Hyeonjin1/mmdl/blob/0de911b19a2e4ff5c207731278f4d792aa1cb554/runs/20261123_lab_backup/code/MMDL-official-vllm/nowait_mask.py) · [실행 설정](https://github.com/Hyeonjin1/mmdl/blob/0de911b19a2e4ff5c207731278f4d792aa1cb554/runs/20261123_lab_backup/nowait-snapshot/run_config.json) | 모델 출력과 Qwen3-8B Judge 판정 생성 |
| 차단 목록 정제·답안 전환 | [실행 스크립트](https://github.com/Hyeonjin1/mmdl/blob/0de911b19a2e4ff5c207731278f4d792aa1cb554/runs/20261123_lab_backup/nowait-followup/run-followup.sh) · [전환·채점 코드](https://github.com/Hyeonjin1/mmdl/blob/0de911b19a2e4ff5c207731278f4d792aa1cb554/runs/20261123_lab_backup/nowait-followup/nowait_followup.py) · [고정 설정](https://github.com/Hyeonjin1/mmdl/blob/0de911b19a2e4ff5c207731278f4d792aa1cb554/runs/20261123_lab_backup/nowait-followup/followup_config.json) · [실행 결과](https://github.com/Hyeonjin1/mmdl/blob/0de911b19a2e4ff5c207731278f4d792aa1cb554/runs/20261123_lab_backup/nowait-followup/summary.json) | 4,096토큰 도달 시 추가 답안 요청. 저장 결과는 40건 중 29건 전환, 정답 19건 |

**혼합 채점.** 위에서 받은 팀 저장소 루트에서 실행한다. `--dry-run`은 원본 파일을 읽고 재집계 결과를 출력한다.

```bash
python3 code/MMDL-official-vllm/rescore_mc_rules.py \
  --original-judgments results/validation900_cot8192_guard_full_judge/judgments.jsonl \
  --retries results/validation900_mc_rejudge_v1/retries.jsonl \
  --dry-run
```

**Parser v2와 NoWait 40문항 재집계.** 같은 저장소 루트에서 고정 커밋을 별도 작업 폴더에 연다. Parser v2는 Python 3.10 이상과 기본 라이브러리를 사용한다. 마지막 명령은 저장된 40문항 결과로 과거 B0 대비 정답 수·출력 토큰 감소율을 계산한다. [40문항 재집계 코드](https://github.com/eses0070/MMDL/blob/8734934b029a01879207052d34ded8ab9a970c70/experiments/nowait/reproduce_b0.cjs)

```bash
git worktree add --detach ../MMDL-replay 8734934b029a01879207052d34ded8ab9a970c70
cd ../MMDL-replay/experiments/parser_v2
python3 -B -m unittest discover -s tests -p 'test_*.py' -v
python3 -B replay.py --limit 0 --output-dir results/mc46_replay
node ../nowait/reproduce_b0.cjs
```

**GPU에서 NoWait을 다시 실행할 때.** 두 셸 스크립트는 실습실에 준비된 팀 체크아웃, Python 가상환경, 오프라인 모델 캐시와 이미지 매니페스트를 사용한다. 기본 실험은 팀 코드 디렉터리에서 `bash nowait.sh run`으로 실행한다. 후속 스크립트는 `/work/results/mmmu_nowait_pilot_20261123`의 완료된 NoWait 응답·판정과 해시를 확인한 뒤 `smoke → generate → judge` 순서로 진행한다. 다른 장비에서는 스크립트와 Python 파일의 `/home/gpu/projects/...`, `/work/...` 경로를 실제 배치에 맞춰야 한다. 실행 설정에 기록된 Student·Judge 리비전과 MMMU 이미지가 필요하다. 위의 900문항 검산은 저장 결과를 다시 집계하며, GPU 재생성 결과는 실행 환경에 따라 달라질 수 있다. [백업 구성과 복원 방법](https://github.com/Hyeonjin1/mmdl/blob/0de911b19a2e4ff5c207731278f4d792aa1cb554/runs/20261123_lab_backup/README.md) · [백업 파일 목록 및 해시](https://github.com/Hyeonjin1/mmdl/blob/0de911b19a2e4ff5c207731278f4d792aa1cb554/runs/20261123_lab_backup/archives/MANIFEST.json)
