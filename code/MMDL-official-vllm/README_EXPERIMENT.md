# Qwen3-VL-4B-Instruct MMMU 평가 실험

팀 **멂딥** | 고은성 · 김석민 · 김현진  
최종 수정: **2026-10-07** | 결과 및 테스트 기록 기준: **2026-10-06**

Qwen3-VL-4B-Instruct의 MMMU validation 평가를 수행하고, 반복 생성과 답 추출 오류를 분석한 실험입니다. 추가 학습이나 모델 가중치 변경은 하지 않았습니다.

> 현재 결과는 **563/900 = 62.56%**입니다. 기존 로컬 판정 819개와 규칙 재채점 81개를 합친 혼합 평가이며, 공식 성능 재현이나 reasoning 정확성 검증을 완료했다는 의미는 아닙니다.

## 1. 환경/재현성

### 하드웨어 및 소프트웨어

학교 실습실 Linux 장비에 VS Code Remote SSH로 접속하여 실행했습니다.

| 항목 | 실행 환경 |
|---|---|
| GPU | NVIDIA GeForce RTX 4090, 약 24GB VRAM |
| OS | Linux, kernel 6.8.0-138-generic |
| Python | 3.10.12 |
| NVIDIA driver | 550.163.01 |
| PyTorch | 2.9.0+cu128 |
| PyTorch CUDA runtime | 12.8 |
| 추론 백엔드 | vLLM 0.11.2, 반복 guard 활성화 시 AsyncLLM streaming |
| Transformers | 4.57.1 |
| qwen-vl-utils | 0.0.14 |
| 가상환경 | 기존 Transformers 환경과 분리한 `.venv-vllm` |
| dtype | 명시적 override 없이 모델/vLLM auto 선택, BF16 모델 구성 |
| 양자화 | 별도 요청하지 않음 |

추론 백엔드는 모델 가중치를 GPU에 올리고 입력 처리, 토큰 생성, KV cache 및 요청 실행을 관리하는 엔진입니다. 이번 실험은 vLLM을 사용했습니다.

CUDA 사용 가능 여부와 실제 GPU 텐서 연산을 확인한 후 추론했습니다. `nvidia-smi`의 CUDA 표시는 PyTorch에 포함된 CUDA runtime 버전과 다른 정보이며, 다른 장비에서 동일 조합의 호환성을 보장하지는 않습니다.

### 모델과 데이터 고정

| 항목 | 내용 |
|---|---|
| Student | `Qwen/Qwen3-VL-4B-Instruct` |
| 모델 revision | `ebb281ec70b05090aa6165b016eac8ec08e71b17` |
| Qwen 평가 코드 commit | `96588727e44c78b25ba03ea03b8e12f7e64fd0da` |
| 평가 데이터 | MMMU validation 900문항 |
| 구성 | 30개 과목 × 30문항, 객관식 847개 / 주관식 53개 |
| 데이터 입력 | 기존 HF DatasetDict를 JSONL 및 RGB PNG로 export |
| manifest SHA-256 | `eed2e5d5327debaa7602eb67dbcd12cf7e68358c62f464a170bd196bcf420697` |
| seed | engine 및 문항별 sampling에 `3407` |

upstream TSV 다운로드에서 인증서 만료 오류가 발생하여 로컬 HF export를 사용했습니다. TLS 검증을 끄지 않았습니다. 이미지 순서는 원래 `image_N` 순서를 유지했습니다.

upstream `MMMU_DEV_VAL.tsv`와 문항·선택지·이미지 표현의 동등성을 독립 검증하지 않았으며, 로컬 디렉터리 이름의 해시는 HF revision의 증거가 아닙니다.

### 재현성 관리

- `requirements.txt`는 핵심 패키지 버전을 고정하지만 완전한 lockfile은 아닙니다. 실제 환경은 `run_config.json`에 기록합니다.
- upstream 코드의 해시를 검사하며 모델 snapshot, 설정, 입력 및 코드 해시를 보존합니다.
- Judge 모델은 기존 실행에 기록된 snapshot을 `--judge-model`로 지정해야 revision을 명확히 고정할 수 있습니다.
- 문항별 체크포인트를 저장하고 동일 코드·설정·환경·데이터 계약에서만 `--resume`합니다.
- 같은 seed라도 백엔드·환경·실행 방식 변경에 따른 bitwise 재현성을 보장하지 않습니다.

## 2. 프롬프트

### 초기 baseline

초기 Transformers 실험은 아래와 같이 설명 없이 선택지 한 글자만 요구했습니다.

```text
{question}

Choices:
{lettered_options}

Select the single best choice. Respond with exactly one line in the format 'Answer: X', where X is the option letter. Do not include an explanation.
```

### 현재 실험

고정된 Qwen 공개 코드의 `build_mmmu_prompt`와 `prepare_inputs_for_vllm`을 호출합니다. 객관식 기본 텍스트는 다음 형태이며 Hint가 있으면 추가합니다. 이미지는 별도 멀티모달 입력으로 전달됩니다.

```text
Question: {question}
Options:
A. {option_A}
B. {option_B}
...
Please select the correct answer from the options above.
```

주관식은 선택지 및 선택지 선택 지시 없이 질문과 이미지 입력을 구성합니다.

완료한 900문항 실험에서는 `--use-cot`으로 아래 공개 코드의 선택적 문구도 추가했습니다.

```text
If you are uncertain or the problem is too complex, make a reasoned guess based on the information provided. Avoid repeating steps indefinitely—provide your best guess even if unsure. Determine whether to think step by step based on the difficulty of the question, considering all relevant information before answering.
```

공개 `infer_instruct.sh`에서는 기본적으로 이 선택적 CoT를 켜지 않습니다. 현재 프롬프트에는 불확실하면 추측하라는 지시가 남아 있습니다. 별도 guard는 반복을 감지했을 때 요청을 취소하는 기능이며, 모든 추측을 금지하는 프롬프트 변경은 아닙니다.

## 3. 생성 설정

| 설정 | 완료한 900문항 실험 |
|---|---:|
| temperature | 0.7 |
| top_p | 0.8 |
| top_k | 20 |
| repetition_penalty | 1.0 |
| presence_penalty | 1.5 |
| seed | 3407 |
| 최대 생성 토큰 | 8192 |
| 최대 전체 context | 49152 |
| tensor_parallel_size | 1 |
| gpu_memory_utilization | 0.9 |
| max_num_seqs | 1 |
| enforce_eager | true |
| min_pixels / 이미지 | 1,003,520 |
| max_pixels / 이미지 | 4,014,080 |
| 선택적 CoT / 반복 guard | 모두 활성화 |

픽셀 예산은 각각 `1280 × 28 × 28`, `5120 × 28 × 28`입니다. 고정 가로·세로 크기가 아니며 실제 크기는 원본 비율과 전처리 규칙에 따라 달라집니다. 모든 이미지가 같은 visual token 수라는 의미도 아닙니다.

### 반복 중단 정책

- 생성 1,024토큰 이후부터 128토큰마다 검사합니다.
- 최근 정규화된 600단어에서 32단어 구문의 충분한 비중첩 반복 등을 확인합니다.
- 연속 확인 조건을 만족하면 해당 요청을 취소합니다.
- 원문과 반복 근거, `finish_reason=repetition_abort`를 저장합니다.
- 중단 응답은 부분 답을 사용하지 않고 정책상 오답 처리합니다.
- 180초 시간제한은 구현하지 않았습니다.

이는 의미적 오류 판별기가 아닌 표면적 반복 감지 휴리스틱입니다. 상세 조건은 [REPETITION_GUARD.md](REPETITION_GUARD.md)를 참고합니다. 해당 문서의 초기 GPU 검증 전 안내와 달리 본 문서는 이후 학교 실행 결과를 반영합니다.

### 전체 추론 명령

학교 Linux 실험 디렉터리에서 실행한 설정입니다. 기존 결과 폴더가 있다면 새 경로를 사용합니다.

```bash
python run.py infer \
  --local-manifest data/local_validation/validation.jsonl \
  --limit 0 --low-memory --max-model-len 49152 \
  --max-new-tokens 8192 --use-cot --repetition-guard \
  --output-dir results/validation900_cot8192_guard_full
```

처음에는 새 출력 경로에서 `--limit 3`으로 검사합니다. 중단 후 이어하기는 동일한 전체 명령에 `--resume`을 추가합니다. 기본 limit은 3이므로 전체 실행에는 `--limit 0`이 필요합니다.

## 4. 채점(파싱) 방식

### 초기 규칙 파서

초기 baseline은 별도 Judge 모델 없이 응답의 답을 추출하고 GT와 비교했습니다. 현재 아래의 규칙 보완은 그때와 동일한 코드가 아니라, 장문 응답에서 중간 추론을 답으로 오인하지 않도록 더 보수적으로 만든 별도 파서입니다.

### 최초 로컬 Judge

유료 GPT API 대신 `Qwen3-8B`를 non-thinking, temperature 0, 최대 출력 512토큰, context 32768로 실행했습니다. Student 추론 종료 후 별도 프로세스에서 채점합니다.

| 대상 | 처리 방식 |
|---|---|
| 객관식 | Student 최종 답을 실제 선택지 키에 대응 |
| 객관식 GT | Judge에 전달하지 않고 반환된 키와 코드에서 비교 |
| 주관식 | Student 응답과 허용 정답을 Judge에 제공해 동등성 판단 |
| 반복 중단 | Judge 호출 없이 정책상 오답 |
| 형식 오류·불확실·입력 초과 | 미해결 처리, 임의 답을 생성하지 않음 |

```bash
python run.py judge \
  --predictions results/validation900_cot8192_guard_full/predictions.jsonl \
  --limit 0 --judge-context 32768 \
  --output-dir results/validation900_cot8192_guard_full_judge
```

### 미해결 객관식 81개 재채점

처음에는 `rejudge_mc.py`로 선택지/null로 제한된 구조화 출력과 원문 인용 검사를 도입했습니다. 하지만 인용이 원문에 존재해도 그것이 최종 답이라는 보장은 없었습니다.

| 사례 | 발견한 추출 오류 |
|---|---|
| Architecture_and_Engineering_26 | 끝나지 않은 사인 법칙 계산을 근거로 D 반환 |
| Electronics_7 | 잠정적인 C 추측을 확정 답으로 설명 |
| Accounting_28 | 중간 변수 비용 계산을 최종 선택지에 대응 |

이후 일부 사례만 고르지 않고 **81개 전체의 LLM 재채점 판정을 되돌린 뒤**, `rescore_mc_rules.py`를 적용했습니다.

- 마지막 비어 있지 않은 줄의 `Answer: B`, `Final Answer: B`, 단독 `B` 등을 추출합니다. 끝 구분선과 일부 Markdown 서식을 허용합니다.
- 선택지 내용까지 붙어 있으면 정규화 후 해당 선택지 내용과 일치해야 합니다.
- 실제 선택지 밖 문자를 허용하지 않습니다.
- 중간 계산을 완성하거나 가장 가까운 선택지를 추측하지 않습니다.
- 추출 성공은 GT와 비교하고, 추출 불가는 정책상 오답으로 집계합니다.
- 추출 불가에는 `answer_correct=null`, `parse_success=false`를 남겨 실제 오답과 구분합니다.

```bash
python rescore_mc_rules.py \
  --original-judgments results/validation900_cot8192_guard_full_judge/judgments.jsonl \
  --retries results/validation900_mc_rejudge_v1/retries.jsonl \
  --output-dir results/validation900_rules_v1
```

이 명령은 최초 Judge 파일과 기존 81개 retries 파일이 모두 필요합니다. GPU 추론이나 Judge를 다시 실행하지 않습니다. `--dry-run`은 쓰기 없이 요약만 출력합니다.

**전체 900개를 규칙 채점한 것이 아닙니다.** 나머지 819개는 최초 판정을 유지합니다. 주관식도 이번 규칙 보완의 대상이 아닙니다.

또한 **reasoning을 검증하는 평가가 아닙니다.** 최종 답이 맞지만 풀이가 틀린 경우를 자동으로 제외하지 않으며, 수정 레코드의 `reasoning_correct`는 null입니다.

## 5. 결과

### 최신 혼합 채점 결과

| 구분 | 문항 수 |
|---|---:|
| 전체 | 900 |
| 정답 | **563** |
| 정책상 오답 합계 | 337 |
| 유지한 최초 판정 중 정답 / 일반 오답 / 반복 중단 | 537 / 229 / 53 |
| 81개 규칙 재채점 중 정답 | 26 |
| 81개 규칙 재채점 중 명시적 답이 GT와 다른 경우 | 9 |
| 81개 규칙 재채점 중 추출 불가로 오답 집계 | 46 |

**정확도 = 563 / 900 × 100 = 62.56%**

`unresolved=0`은 모든 답을 확실히 판정했다는 뜻이 아니라 미추출 46개를 오답으로 집계한 정책의 결과입니다. 이 수치는 reasoning 정확도나 공식 MMMU 점수가 아닙니다.

### 과목별 정확도

최신 `validation900_rules_v1/judgments.jsonl`의 900개 레코드를 과목별로 집계했습니다. 정확도는 과목별 `정답 수 / 전체 문항 수 × 100`이며, 반복 중단과 추출 불가도 분모에 포함하고 정책상 오답으로 계산합니다. 기존 로컬 판정과 규칙 재채점을 합친 결과이며 공식 채점 결과는 아닙니다.

| 번호 | 과목 | 문항 수 | 정답 수 | 정확도 (%) |
|---:|---|---:|---:|---:|
| 1 | Accounting | 30 | 23 | 76.67 |
| 2 | Agriculture | 30 | 15 | 50.00 |
| 3 | Architecture_and_Engineering | 30 | 15 | 50.00 |
| 4 | Art | 30 | 20 | 66.67 |
| 5 | Art_Theory | 30 | 26 | 86.67 |
| 6 | Basic_Medical_Science | 30 | 22 | 73.33 |
| 7 | Biology | 30 | 19 | 63.33 |
| 8 | Chemistry | 30 | 11 | 36.67 |
| 9 | Clinical_Medicine | 30 | 18 | 60.00 |
| 10 | Computer_Science | 30 | 18 | 60.00 |
| 11 | Design | 30 | 22 | 73.33 |
| 12 | Diagnostics_and_Laboratory_Medicine | 30 | 10 | 33.33 |
| 13 | Economics | 30 | 25 | 83.33 |
| 14 | Electronics | 30 | 12 | 40.00 |
| 15 | Energy_and_Power | 30 | 14 | 46.67 |
| 16 | Finance | 30 | 21 | 70.00 |
| 17 | Geography | 30 | 17 | 56.67 |
| 18 | History | 30 | 21 | 70.00 |
| 19 | Literature | 30 | 25 | 83.33 |
| 20 | Manage | 30 | 21 | 70.00 |
| 21 | Marketing | 30 | 25 | 83.33 |
| 22 | Materials | 30 | 14 | 46.67 |
| 23 | Math | 30 | 18 | 60.00 |
| 24 | Mechanical_Engineering | 30 | 11 | 36.67 |
| 25 | Music | 30 | 10 | 33.33 |
| 26 | Pharmacy | 30 | 25 | 83.33 |
| 27 | Physics | 30 | 23 | 76.67 |
| 28 | Psychology | 30 | 20 | 66.67 |
| 29 | Public_Health | 30 | 24 | 80.00 |
| 30 | Sociology | 30 | 18 | 60.00 |
| **전체** | **Overall** | **900** | **563** | **62.56** |

모든 과목이 30문항이므로 반올림 전 과목별 정확도의 단순 평균(macro average)과 전체 정확도(micro accuracy)는 같으며, 둘 다 표시상 **62.56%**입니다. 과목당 문항 수가 적고 채점 오류 가능성도 남아 있으므로 이 순위를 일반적인 과목별 능력 순위로 단정하지 않습니다.

### 추론 실행 통계

| 항목 | 기록 |
|---|---:|
| 완료 | 900/900 |
| 정상 종료 | 787 |
| 생성 길이 제한 | 60 |
| 반복 guard 중단 | 53 |
| 생성 토큰 합계 | 1,593,588 |
| 문항당 평균 생성 토큰 | 약 1,771 |
| 기록된 문항 처리 시간 합계 | 약 5시간 18분 |

문항 처리 시간 합계는 모델 로딩 등 모든 overhead를 포함한 전체 wall-clock 시간과 같은 정의가 아닙니다. 길이 제한 여부와 최종 채점 결과는 별도 분류이므로 길이 제한 60개를 자동으로 모두 오답이라 간주하지 않습니다.

### 점수 변경 이력

| 단계 | 정답 | 미해결 | 보고값 |
|---|---:|---:|---|
| 초기 Transformers baseline v3 | 493/900 | 초기 파서 기준 | 54.78% |
| vLLM + CoT + guard, 최초 Judge | 537/900 | 81 | 59.67~68.67% |
| 구조화 LLM 재추출 v1 | 566/900 | 30 | 62.89~66.22%, 추출 오류 발견 |
| 81개 규칙 재채점 v1 | 563/900 | 정책상 0 | **62.56%** |

범위는 기존 판정이 맞다고 가정하고 미해결 문항을 전부 오답 또는 정답으로 놓은 산술적 범위이지 통계적 신뢰구간이 아닙니다. 566개 정답은 추출 오류가 발견되어 확정 결과로 채택하지 않았습니다. 동일한 응답의 채점 변경은 모델 자체의 성능 향상이 아닙니다.

## 6. 공식 수치와의 비교

이번 기록에서는 **동일 모델·벤치마크·split·평가 프로토콜에 대응하는 공식 수치의 출처를 확정하지 않았으므로**, 특정 공식 점수 및 그와의 퍼센트포인트 차이를 임의로 기재하지 않습니다. 현재 확인한 것은 고정 commit의 공개 구현과 자체 실행 결과입니다.

| 비교 대상 | 값 / 상태 |
|---|---|
| 자체 MMMU validation 결과 | 62.56%, 혼합 채점 |
| 동일 조건의 공식 보고값 | 이 문서에서 확정하지 않음 |
| 공식 점수 대비 수치 격차 | 산출하지 않음 |
| 공식 프로토콜 동일 재현 | 미완료 |

공식 보고값을 추가할 때는 반드시 `Qwen3-VL-4B-Instruct`인지, MMMU인지 MMMU-Pro인지, validation/test 중 어느 split인지와 채점 조건을 함께 확인해야 합니다. Thinking 모델이나 다른 parameter 규모의 수치를 섞지 않습니다.

### 공개 구현과 현재 조건 차이

| 항목 | 고정된 Qwen 공개 코드/예시 | 완료한 실험 |
|---|---|---|
| 기본 프롬프트·픽셀 예산 | 공개 함수 | 동일 함수 호출 |
| 데이터 | MMMU_DEV_VAL TSV | 로컬 HF export, 동등성 미검증 |
| seed | MMMU engine seed 42 | engine 및 문항별 seed 3407 |
| 최대 생성 토큰 | Instruct 예시 32768 | 8192 |
| context | 기본 128000 | 49152 |
| CoT | 선택 가능, Instruct shell 예시는 꺼짐 | 켜짐 |
| 요청 제출 | 입력 목록 제출 | 문항별 제출·저장 |
| 반복 중단 | 현재 guard와 같은 별도 정책 없음 | 자체 guard로 중단, 오답 집계 |
| 채점 | 규칙 추출 및 GPT fallback 경로 | 로컬 Qwen3-8B + 81개 규칙 보완 |

공개 코드 기본값이 technical report의 모든 실행 조건을 설명한다고 가정하지 않습니다.

### 출처

아래 고정 소스와 로컬 실행 기록을 기준으로 정리했습니다. 최신 upstream 전체를 반영한다는 의미는 아닙니다.

- [Qwen MMMU 평가 README](https://github.com/QwenLM/Qwen3-VL/blob/96588727e44c78b25ba03ea03b8e12f7e64fd0da/evaluation/mmmu/README.md)
- [프롬프트·전처리·추론 코드](https://github.com/QwenLM/Qwen3-VL/blob/96588727e44c78b25ba03ea03b8e12f7e64fd0da/evaluation/mmmu/run_mmmu.py)
- [Instruct 추론 예시](https://github.com/QwenLM/Qwen3-VL/blob/96588727e44c78b25ba03ea03b8e12f7e64fd0da/evaluation/mmmu/infer_instruct.sh)
- [Instruct 평가 예시](https://github.com/QwenLM/Qwen3-VL/blob/96588727e44c78b25ba03ea03b8e12f7e64fd0da/evaluation/mmmu/eval_instruct.sh)
- [공개 답 추출·평가 유틸리티](https://github.com/QwenLM/Qwen3-VL/blob/96588727e44c78b25ba03ea03b8e12f7e64fd0da/evaluation/mmmu/eval_utils.py)

## 7. 격차 분석

아래는 **확인된 현상과 가능한 원인을 구분한 분석**입니다. 공식 점수와의 차이에 대한 인과적 기여도를 측정한 결과는 아닙니다.

| 관찰 또는 조건 차이 | 가능한 영향 | 현재 확인 수준 |
|---|---|---|
| 길이 제한 60개 | 답 확정 전에 생성 종료 가능 | 발생 확인, 예산 확대의 정답 개선량은 미측정 |
| 반복 중단 53개 | 해당 문항을 정책상 오답 집계 | 중단하지 않았을 때의 최종 정답률은 미확인 |
| 추출 불가 46개 | 내용상 답이 있어도 엄격한 끝줄 규칙이 놓칠 수 있음 | 46개 모두 추론 오류라고 단정할 수 없음 |
| Judge의 중간 계산·잠정 답 오인 | 추출 결과 및 점수 왜곡 | 실제 사례 확인, 기존 819개 전체 검수는 미완료 |
| CoT 및 생성 방식 변경 | 답 길이·추론 경로·정답률 변화 가능 | 통제된 ablation 미실시 |
| 데이터 표현·seed·context·실행 방식 차이 | 입력 또는 생성 경로 차이 가능 | 각 차이의 기여도 미측정 |

Accounting 5의 Transformers 비교에서도 장문 재검토가 관찰됐으므로 반복 현상을 vLLM만의 결함으로 단정하지 않습니다. 한 문항 비교만으로 두 백엔드가 전반적으로 동등하다고 주장하지도 않습니다.

초기 54.78%와 현재 62.56%는 프롬프트, 이미지 처리, 생성 및 채점 조건이 함께 달라졌습니다. 따라서 상승분을 CoT나 백엔드 변경 하나의 효과로 설명할 수 없습니다.

후속 실험에서는 데이터와 채점기를 먼저 고정한 뒤 CoT, 생성 예산, 반복 guard 등을 하나씩 바꾸고, 명시적 오답·추출 실패·반복 중단을 분리해 비교해야 합니다.

## 8. 기타 특이사항 / 한계

- **추가 학습 없음:** 이번 작업은 baseline 추론·평가 개선이며 distillation, SFT, RL 실험이 아닙니다.
- **유료 API 없음:** Student와 Judge 모두 학교 GPU에서 실행했습니다. 규칙 재채점은 CPU만 사용합니다.
- **혼합 채점:** 81개만 규칙으로 처리했으므로 전체가 Judge-free인 평가는 아닙니다. 기존 819개와 주관식 판정의 오류 가능성이 남아 있습니다.
- **reasoning 미검증:** 답이 맞아도 잘못된 풀이가 있을 수 있습니다. 이를 제외하려면 별도의 구성요소 검수와 신뢰성 평가가 필요합니다.
- **보수적 파서:** 자연어·LaTeX 최종 답을 놓칠 수 있습니다. 초기 파서 및 공식 파서와도 다릅니다.
- **guard 한계:** 의미를 바꿔 반복하는 경우를 놓치거나 정상적인 재검토를 중단할 수 있습니다. 중단이 곧 reasoning 오류의 증거는 아닙니다.
- **validation 적응:** validation 응답을 관찰하며 정책을 조정했으므로 독립적인 held-out 성능이나 일반화된 신뢰성으로 과장하지 않습니다.
- **원본 보존:** 기존 채점 파일을 덮어쓰지 않고 새 결과와 변경 이력을 별도 저장했습니다.
- **버전 의존성:** streaming adapter는 vLLM 0.11.2에 맞춰 검증했습니다. 버전 변경 시 호환성을 다시 확인해야 합니다.
- **GPU 테스트 범위:** 학교 실행 로그와 로컬 CPU 테스트는 별개의 증거입니다. CPU 테스트가 Judge의 의미적 정확성이나 GPU 동작 전체를 보장하지 않습니다.

### 결과 파일 및 관련 코드

| 파일 | 역할 |
|---|---|
| `predictions.jsonl` | Student 원본 응답 및 추론 기록 |
| `judgments.jsonl` | 전체 채점 결과, 수정 문항의 이전 판정 보존 |
| `audit.jsonl` | 81개 재채점 변경 내역 |
| `summary.json` | 집계 결과 |
| `run_config.json` | 실행 설정, 입력·코드 해시 및 정책 한계 |
| `run.py` | 추론 및 최초 로컬 Judge |
| `checkpointing.py` | 문항별 저장·이어하기 |
| `repetition_guard.py`, `streaming_guard.py` | 반복 감지와 생성 취소 |
| `rejudge_mc.py` | 이전 LLM 재추출 및 공통 검증 함수 |
| `rescore_mc_rules.py` | 최신 규칙 재채점 |
| `compare_transformers.py` | 단일 문항 백엔드 비교 |

실행 보충 설명은 [OFFLINE_INPUT.md](OFFLINE_INPUT.md), [CHECKPOINT_RUN.md](CHECKPOINT_RUN.md), [COT_RUN.md](COT_RUN.md), [REJUDGE_MC.md](REJUDGE_MC.md), [RULES_RESCORE.md](RULES_RESCORE.md)를 참고합니다.

### 테스트와 공유

```bash
python -m unittest discover -p 'test_*.py'
```

2026-10-06 로컬 검증에서 67개 중 66개 통과, 1개 건너뜀이었습니다. 이번 수정은 README 형식 변경이며 추론·채점 결과를 새로 생성하지 않았습니다.

Git 공유 시 코드·문서·설정·결과의 대응 관계를 보존하고 `.venv*`, 가중치, HF cache, 이미지 데이터 전체, API 키 및 SSH 정보는 일반 코드 commit에서 제외합니다. 큰 결과 파일은 별도 저장소나 Release로 공유하고 해시를 남길 수 있습니다.

이 문서 수정 작업에서는 Git commit/push를 수행하지 않았습니다.
