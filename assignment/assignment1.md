# MMMU-val Baseline Evaluation Report — Qwen3-VL-4B-Instruct

- **팀명**: 멂딥
- **팀원**: 고은성 김석민 김현진
- **작성일**: 2026.09.28
- **재현 커맨드**: 아래 명령을 저장소 루트에서 실행한다. `DATA_ROOT`는 준비된 MMMU validation DatasetDict 경로로 지정한다.

```bash
python code/eval_mmmu_v3.py \
  --model_path Qwen/Qwen3-VL-4B-Instruct \
  --data_root "${DATA_ROOT}" \
  --output_dir results/reproduction_v3 \
  --max_new_tokens 2048 \
  --open_max_new_tokens 8192 \
  --limit 0
```

## 1. 환경 / 재현성

| 항목 | 값 |
|---|---|
| 모델 checkpoint | `Qwen/Qwen3-VL-4B-Instruct` (`ebb281ec70b05090aa6165b016eac8ec08e71b17`) |
| 추론 백엔드 | Transformers 4.57.1 `generate()`, SDPA, batch size 1 |
| 사용 GPU | NVIDIA GeForce RTX 4090, 명목 VRAM 24GB |
| dtype | `torch.bfloat16`, 양자화 없음 |
| 실측 peak VRAM | PyTorch allocated **9.457 GiB**, reserved **11.160 GiB**; 전체 장치 사용량이 아님 |
| 총 소요 시간 | **1,607.06초 (26분 47초)**, 900문제; 모델 로딩 포함, 데이터 로딩·환경 기록 제외 |
| 의존성 | Python 3.10.12, torch 2.6.0+cu124, torchvision 0.21.0+cu124, transformers 4.57.1, datasets 3.6.0, accelerate 1.15.0, pillow 12.3.0, huggingface_hub 0.36.2, numpy 2.2.6 |
| 실행 커맨드 | 문서 상단 명령. 모델과 데이터 경로를 인자로 전달 |
| 실행 코드 / 결과 | [eval_mmmu_v3.py](../code/eval_mmmu_v3.py), [predictions.jsonl](../results/full900_v3/predictions.jsonl) |

Transformers는 실습실에서 검증한 환경을 재사용하고 입력·응답을 직접 기록하기 위해 선택했다.
모델과 processor에 동일한 revision을 지정한다. 데이터는 `MMMU/MMMU`의
`98e6ac0cb9b7b2cd2c991b85a50762edc4aedc68` 버전에서 30개 config별 validation을 로드하여
`DatasetDict.save_to_disk()`로 저장했다. 과목별 30개, 총 900개 고유 문제를 평가했다.
평가 시 모델은 로컬 캐시, 데이터는 `load_from_disk()`로 읽는다.
모델은 `snapshot_download(repo_id="Qwen/Qwen3-VL-4B-Instruct", revision="ebb281ec70b05090aa6165b016eac8ec08e71b17")`로 준비한다.
각 과목 데이터는 `load_dataset("MMMU/MMMU", subject, split="validation", revision="98e6ac0cb9b7b2cd2c991b85a50762edc4aedc68")`로 받고,
과목명을 키로 하는 `DatasetDict`로 묶어 `save_to_disk(DATA_ROOT)`로 저장한다.
의존성은 동일 가상환경에서 앞서 기록한 버전을 기준으로 정리했다. CUDA 12.4용 PyTorch 패키지의 설치 인덱스는 `https://download.pytorch.org/whl/cu124`이다.

## 2. 프롬프트

**실제 모델에 들어간 프롬프트 전문** (변수 부분은 `{}`로 표시):

객관식:

```text
{question}

Choices:
{lettered_options}

Select the single best choice. Respond with exactly one line in the format 'Answer: X', where X is the option letter. Do not include an explanation.
```

`{lettered_options}`는 `A. {option_A}` 형식으로 실제 선택지 개수만큼 줄을 만든다.

주관식:

```text
{question}

Solve the problem. End your response with a separate line 'Answer: X', where X is your concise final answer.
```

- **출처**: 직접 설계.
- **선택 이유**: 객관식은 최종 선택지 추출과 짧은 출력을 위해 한 줄 답변을 요청했다.
  주관식은 한 줄 답변 실험에서 9/53, 기존 풀이 응답을 동일한 개선 파서로 채점했을 때 21/53이어서 풀이를 허용하는 형식으로 복원했다.
- 질문·선택지의 `<image n>` 위치에 해당 이미지를 삽입하고 순서·반복 참조를 유지했다.
  사용자 메시지를 모델의 `apply_chat_template(..., add_generation_prompt=True)`로 렌더링했으며 별도 system 메시지는 추가하지 않았다.
  실제 `prompt`, `rendered_prompt`, `image_keys`를 문제별로 저장했다. 정답과 해설은 입력하지 않았다.

## 3. 생성(Decoding) 설정

### 3.1 Sampling recipe

| 파라미터 | 값 |
|---|---|
| `do_sample` | `True` |
| `temperature` | `0.7` |
| `top_p` | `0.8` |
| `top_k` | `20` |
| `repetition_penalty` | `1.0` |
| `presence_penalty` | `1.5` |
| `seed` | `3407`, 매 문제 생성 직전에 초기화 |

- **출처**: [Qwen3-VL 공식 저장소의 Evaluation Reproduction / Instruct models](https://github.com/QwenLM/Qwen3-VL#evaluation-reproduction).
- `presence_penalty`는 custom logits processor로 구현했다. 프롬프트를 제외하고 이미 생성한 각 토큰의 logit에서 1.5를 한 번 차감한 뒤 temperature/top-k/top-p를 적용한다.
  seed 운용 방식과 백엔드까지 공식 실행과 같다고 주장하지 않는다.

### 3.2 생성 예산 / 이미지 해상도

| 파라미터 | 값 |
|---|---|
| `max_new_tokens` | 객관식 **2,048**, 주관식 **8,192** (`--open_max_new_tokens`) |
| 이미지 해상도 처리 | 이미지당 `min_pixels=4096`, `max_pixels=1048576`; RGB 변환 후 모델 processor 사용 |

**선택 근거**: 4090 24GB에서 batch size 1과 이미지당 픽셀 상한으로 메모리 부담을 제한했다.
초기 2,048토큰 실행에서 주관식 16개가 잘려 주관식만 8,192로 늘렸다.
최종 실행에서 잘림은 5개로 감소했으나 시간은 약 15분에서 약 26분 47초로 증가했다.
동일한 개선 파서로 비교한 전체 정확도는 두 실행 모두 54.78%여서, 길이 증가에 따른 정답률 향상은 관찰되지 않았다.
공식 출력 한도 32,768보다 작은 값이며, 현재 값이 최적이거나 하드웨어의 필수 상한이라는 의미는 아니다.

## 4. 채점(파싱) 방식

- **사용한 파서/로직**: 자체 구현한 final-answer parser v2.
  [MMMU 공식 평가 코드](https://github.com/MMMU-Benchmark/MMMU/blob/main/mmmu/utils/eval_utils.py)를 참고했으나 동일한 파서는 아니다.
- **객관식**: bold/backtick 제거 후 마지막 `Answer:` 또는 `Final answer:` 줄에서 유효한 선택지 문자를 추출한다.
  해당 줄이 없으면 응답 전체가 선택지 문자 하나인 경우만 허용한다. 실패 시 임의 추측 없이 오답 처리한다.
- **주관식**: 마지막 최종 답 줄을 사용하고, 없으면 한 줄 응답만 허용한다. 정답 대안 목록,
  소문자·공백 정규화, 숫자의 소수 둘째 자리 반올림, 제한된 사칙연산·분수·제곱근 계산을 지원한다.
  숫자 정답에 대해서는 명시된 단위·부가 표기(U/F 등)를 제거할 수 있다.
- 짧은 문자 답변은 정답 구절의 단어 경계 일치를 허용한다(정답 3문자 이상, 응답 6단어 이하, 명시적 부정·대안 표현 제외).
  예를 들어 `2√2`/`2.83`, `2960 U`/`2960`, `Tampa Bay region`/`Tampa`를 같은 답으로 인정한다.
  모든 문항에 같은 규칙을 적용했고 개별 답을 수동 보정하지 않았다.
- 단위 환산과 일반적인 의미 동치 판정은 지원하지 않는다. 숫자 반올림·구절 매칭·단위 제거로 인한 오채점 가능성은 남는다.

## 5. 결과

| No. | Subject | Data Num | Acc (%) |
|---|---|---:|---:|
| 1 | Accounting | 30 | 43.33 |
| 2 | Agriculture | 30 | 50.00 |
| 3 | Architecture_and_Engineering | 30 | 30.00 |
| 4 | Art | 30 | 66.67 |
| 5 | Art_Theory | 30 | 73.33 |
| 6 | Basic_Medical_Science | 30 | 73.33 |
| 7 | Biology | 30 | 53.33 |
| 8 | Chemistry | 30 | 43.33 |
| 9 | Clinical_Medicine | 30 | 63.33 |
| 10 | Computer_Science | 30 | 53.33 |
| 11 | Design | 30 | 83.33 |
| 12 | Diagnostics_and_Laboratory_Medicine | 30 | 43.33 |
| 13 | Economics | 30 | 60.00 |
| 14 | Electronics | 30 | 40.00 |
| 15 | Energy_and_Power | 30 | 43.33 |
| 16 | Finance | 30 | 33.33 |
| 17 | Geography | 30 | 70.00 |
| 18 | History | 30 | 66.67 |
| 19 | Literature | 30 | 76.67 |
| 20 | Manage | 30 | 53.33 |
| 21 | Marketing | 30 | 66.67 |
| 22 | Materials | 30 | 50.00 |
| 23 | Math | 30 | 46.67 |
| 24 | Mechanical_Engineering | 30 | 40.00 |
| 25 | Music | 30 | 36.67 |
| 26 | Pharmacy | 30 | 56.67 |
| 27 | Physics | 30 | 33.33 |
| 28 | Psychology | 30 | 70.00 |
| 29 | Public_Health | 30 | 60.00 |
| 30 | Sociology | 30 | 63.33 |
| | **Overall (macro avg)** | **900** | **54.78** |

계산식: `Overall = mean(30개 과목의 반올림 전 accuracy) × 100 = 493 / 900 × 100`.
과목당 문항 수가 같아 전체 정답 비율과 동일하다.

객관식 **472/847 (55.73%)**, 주관식 **21/53 (39.62%)**.
파싱 실패 **4개**, 출력 잘림 **5개**는 모두 주관식이며 4개가 겹친다.

## 6. 공식 수치와의 비교

| | Overall (MMMU val, %) |
|---|---:|
| 공식 (Qwen3-VL Technical Report, 과제 제시 기준) | 67.40 |
| 우리 재현 결과 | 54.78 |
| 차이 (Δ, 우리 − 공식) | **−12.62%p** |

## 7. 격차 분석

공식 67.4% 대비 54.78%로 12.62%p 낮았다. 객관식은 472/847, 주관식은 21/53이었다. 초기 실행에서 기호식·부가 표기를 엄격하게 비교해 `2√2`와 2.83 등 동등한 답을 놓쳤고, 개선 파서로 기존 응답을 재채점하자 54.44%에서 54.78%가 됐다. 주관식 한 줄 출력 실험은 9/53으로 낮아 풀이를 복원했다. 출력 상한을 2,048에서 8,192로 늘린 최종 실행은 잘림 16→5개, 파싱 실패 15→4개로 감소했지만 동일 파서 기준 정확도는 54.78%로 같았다. Electronics_11 등은 여전히 최종 답 없이 잘렸고, Finance_10은 답을 냈으나 오답이었다. 남은 잘림 5개를 모두 정답으로 바꿔도 상승 상한은 0.56%p라 전체 격차를 설명할 수 없다. 객관식 오답도 375개다. 자체 프롬프트·채점 규칙, 이미지 해상도, 백엔드와 seed 운용 차이가 후보이나 각 영향은 통제 실험 없이 단정할 수 없다.

## 8. 기타 특이사항 / 한계 (Optional)

- 추가 학습 없이 지정 모델을 평가했다. 최종 결과는 v3 설정으로 900문제를 모두 실행한 기록이며 이전 실행의 정답만 합치지 않았다.
- validation 결과를 보고 프롬프트·채점 규칙을 조정했으므로 독립적인 미사용 평가셋 성능으로 해석하지 않는다.
- GPU 메모리는 PyTorch 측정값이며 드라이버·디스플레이 등의 전체 사용량을 포함하지 않는다.
- 이후 파인튜닝 비교에서도 동일한 프롬프트·생성 예산·파서·seed 정책을 적용해야 한다.
