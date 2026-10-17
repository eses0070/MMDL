# RESTORE_RETENTION_v1 학습률·풀이·유지 혼합 비교

실행 상태: completed. 기존 E1–E7/체크포인트/응답은 보존했다. E8은 PrIMuS용으로 남겨두었다. 선생 모델·KD·모델 생성 풀이 없음.

## 학습률 × 공식 풀이

| 조건 | LR | Tab target | MMMU 정답/900 | 정확도 | 기존 대응군 대비 |
|---|---|---|---|---|---|
| E2 | 1e-4 | 정답만 | 470 | 52.22% | 기준 |
| LR_LOW_ANSWER | 2e-5 | 정답만 | 463 | 51.44% | -7 |
| E5 | 1e-4 | 원본 풀이+정답 | 459 | 51.00% | 기준 |
| LR_LOW_SOLUTION | 2e-5 | 원본 풀이+정답 | 478 | 53.11% | 19 |

새 두 조건은 실제 E2/E5 1000행과 이미지·입력·정답 타깃·파일 순서·실제 노출 순서가 동일하며 LR만1e-4→2e-5다. 원본 Qwen3-VL-4B-Instruct revision ebb281ec70b05090aa6165b016eac8ec08e71b17에서 각각 독립 시작했다. E5의 기존 원본풀이 검증500개/산술식268개/제외0개 기록을 재사용했다. 전체 의미론적 풀이 증명은 제한적이며 새 풀이를 생성하지 않았다.

## 공간 집중 × 유지 혼합

| 조건 | 공간 노출 | Tab | Science | 총 노출 | update | MMMU 정답/900 |
|---|---|---|---|---|---|---|
| SPACE_ONLY_CONTROL | 1000 | 0 | 0 | 1000 | 250 | 485 |
| SPACE_RETENTION_MIX | 700 | 150 | 150 | 1000 | 250 | 446 |

두 공간 조건은 CAD target QA445개의 동일 pool을 모두 사용한다. 집중군1000회는 QA별2–3회, 혼합군700회는1–2회 노출이며 1000개의 독립 CAD 모델을 뜻하지 않는다. 공간 정답 위치의 노출은 집중군 A–D각250회, 혼합군각175회로 균형을 맞췄다. 고유 원본 모델/parent/distractor 수와 반복 횟수는 metrics.json에 있다. 기존 E7 445문항/112update는 예산이 다르므로 직접 대조군으로 취급하지 않는다. 공간 노출량도 함께 달라지는 구성 비교다. 유지용 Tab150/Science150은 기존 train pool에서 고정했고 Science는 native skill round-robin으로 다양성을 확보했다. 재무 지식까지 보존하는 데이터라고 가정하지 않는다.

## 유지 타깃 선택 근거

{
  "chosen": "LR_LOW_SOLUTION",
  "criteria": [
    "source macro accuracy",
    "maximize worst source delta versus B0",
    "fewest parse failures"
  ],
  "candidates": {
    "LR_LOW_ANSWER": {
      "macro_accuracy_pct": 54.666666666666664,
      "worst_source_delta_pp": -23,
      "parse_failures": 0,
      "source_correct_per100": {
        "ChartQA": 54,
        "TabMWP": 70,
        "PGPS9K": 40
      },
      "source_run": "/home/user/mmdl-work/runs/P04_20261012T070959199095Z_restore_evaluate_LR_LOW_ANSWER",
      "source_responses_sha256": "0a24c9d38e941ce7f9b5b5e408b4a61abc749a0474a00c3d70e7f4e13307a324"
    },
    "LR_LOW_SOLUTION": {
      "macro_accuracy_pct": 60.333333333333336,
      "worst_source_delta_pp": -8,
      "parse_failures": 20,
      "source_correct_per100": {
        "ChartQA": 53,
        "TabMWP": 73,
        "PGPS9K": 55
      },
      "source_run": "/home/user/mmdl-work/runs/P04_20261012T102051853902Z_restore_evaluate_LR_LOW_SOLUTION",
      "source_responses_sha256": "0a0345f8842b15aeda92148bebaa584b07e82ddefcca83a29e85d9f3d8fdb8cd"
    }
  },
  "MMMU_used": false,
  "checkpoint_selection": false,
  "exact_remaining_tie_rule": "answer-only for simplicity; all requested tie rules equal"
}

선택은250update ChartQA/TabMWP/PGPS 개발 정확도 macro→최악 source 하락→추출실패 순서이며 MMMU 파일을 읽지 않고 두 저학습률 실험 완료 후 고정했다. 선택 원칙이 풀이 포함인 경우에도 검증 가능한 공식 풀이만 쓰고, Science 원본풀이가 없거나 일치 검증이 안 되면 정답만 사용했다. 공간 타깃은 항상 기존 E7과 같다. source별 실제 supervised 토큰과 풀이 포함 개수는 metrics.json에 있다.

## 학습 단계별 개발 점검

| 조건 | update | source | 정답/100 | B0대비pp | B0정답→오답/분모 | 추출실패 | 명시오답 | 반복중단 | 길이종료 | 평균토큰 | 중앙값 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| LR_LOW_ANSWER | 63 | ChartQA | 53 | +16.0 | 16/37 | 0 | 47 | 0 | 0 | 4.0 | 4.0 |
| LR_LOW_ANSWER | 63 | PGPS9K | 40 | -23.0 | 36/63 | 1 | 59 | 0 | 0 | 7.8 | 8.0 |
| LR_LOW_ANSWER | 63 | TabMWP | 47 | -34.0 | 42/81 | 0 | 53 | 0 | 0 | 2.9 | 3.0 |
| LR_LOW_ANSWER | 125 | ChartQA | 53 | +16.0 | 16/37 | 0 | 47 | 0 | 0 | 4.1 | 3.5 |
| LR_LOW_ANSWER | 125 | PGPS9K | 38 | -25.0 | 38/63 | 0 | 62 | 0 | 0 | 8.2 | 8.0 |
| LR_LOW_ANSWER | 125 | TabMWP | 60 | -21.0 | 33/81 | 0 | 40 | 0 | 0 | 2.9 | 3.0 |
| LR_LOW_ANSWER | 250 | ChartQA | 54 | +17.0 | 16/37 | 0 | 46 | 0 | 0 | 3.9 | 3.0 |
| LR_LOW_ANSWER | 250 | PGPS9K | 40 | -23.0 | 37/63 | 0 | 60 | 0 | 0 | 8.3 | 8.0 |
| LR_LOW_ANSWER | 250 | TabMWP | 70 | -11.0 | 25/81 | 0 | 30 | 0 | 0 | 2.8 | 3.0 |
| LR_LOW_SOLUTION | 63 | ChartQA | 50 | +13.0 | 16/37 | 1 | 49 | 0 | 0 | 8.6 | 4.0 |
| LR_LOW_SOLUTION | 63 | PGPS9K | 64 | +1.0 | 10/63 | 12 | 17 | 7 | 5 | 1834.3 | 477.5 |
| LR_LOW_SOLUTION | 63 | TabMWP | 71 | -10.0 | 17/81 | 4 | 25 | 0 | 0 | 64.5 | 59.5 |
| LR_LOW_SOLUTION | 125 | ChartQA | 53 | +16.0 | 15/37 | 0 | 47 | 0 | 0 | 6.5 | 4.0 |
| LR_LOW_SOLUTION | 125 | PGPS9K | 60 | -3.0 | 12/63 | 15 | 13 | 12 | 8 | 1579.1 | 351.5 |
| LR_LOW_SOLUTION | 125 | TabMWP | 69 | -12.0 | 17/81 | 5 | 26 | 0 | 0 | 51.7 | 54.0 |
| LR_LOW_SOLUTION | 250 | ChartQA | 53 | +16.0 | 16/37 | 0 | 47 | 0 | 0 | 4.0 | 3.0 |
| LR_LOW_SOLUTION | 250 | PGPS9K | 55 | -8.0 | 15/63 | 19 | 24 | 2 | 11 | 1356.3 | 220.0 |
| LR_LOW_SOLUTION | 250 | TabMWP | 73 | -8.0 | 17/81 | 1 | 26 | 0 | 0 | 53.5 | 54.5 |
| SPACE_ONLY_CONTROL | 63 | AI2D | 91 | +0.0 | 3/91 | 0 | 9 | 0 | 0 | 8.5 | 8.0 |
| SPACE_ONLY_CONTROL | 63 | ChartQA | 54 | +17.0 | 16/37 | 0 | 46 | 0 | 0 | 10.1 | 8.0 |
| SPACE_ONLY_CONTROL | 63 | Fusion360 | 86 | +20.0 | 5/66 | 0 | 14 | 0 | 0 | 5.0 | 5.0 |
| SPACE_ONLY_CONTROL | 63 | PGPS9K | 44 | -19.0 | 31/63 | 0 | 56 | 0 | 0 | 11.3 | 11.0 |
| SPACE_ONLY_CONTROL | 63 | ScienceQA | 69 | -17.0 | 24/86 | 1 | 30 | 0 | 0 | 9.3 | 8.0 |
| SPACE_ONLY_CONTROL | 63 | TabMWP | 65 | -16.0 | 22/81 | 0 | 35 | 0 | 0 | 7.1 | 7.0 |
| SPACE_ONLY_CONTROL | 125 | AI2D | 93 | +2.0 | 1/91 | 0 | 7 | 0 | 0 | 8.4 | 8.0 |
| SPACE_ONLY_CONTROL | 125 | ChartQA | 56 | +19.0 | 15/37 | 0 | 44 | 0 | 0 | 11.3 | 8.0 |
| SPACE_ONLY_CONTROL | 125 | Fusion360 | 87 | +21.0 | 4/66 | 0 | 13 | 0 | 0 | 5.0 | 5.0 |
| SPACE_ONLY_CONTROL | 125 | PGPS9K | 43 | -20.0 | 32/63 | 0 | 57 | 0 | 0 | 11.3 | 11.0 |
| SPACE_ONLY_CONTROL | 125 | ScienceQA | 69 | -17.0 | 24/86 | 1 | 30 | 0 | 0 | 8.1 | 8.0 |
| SPACE_ONLY_CONTROL | 125 | TabMWP | 69 | -12.0 | 20/81 | 0 | 31 | 0 | 0 | 6.8 | 6.5 |
| SPACE_ONLY_CONTROL | 250 | AI2D | 92 | +1.0 | 2/91 | 0 | 8 | 0 | 0 | 8.4 | 8.0 |
| SPACE_ONLY_CONTROL | 250 | ChartQA | 56 | +19.0 | 15/37 | 0 | 44 | 0 | 0 | 10.2 | 8.0 |
| SPACE_ONLY_CONTROL | 250 | Fusion360 | 89 | +23.0 | 3/66 | 0 | 11 | 0 | 0 | 5.0 | 5.0 |
| SPACE_ONLY_CONTROL | 250 | PGPS9K | 45 | -18.0 | 32/63 | 0 | 55 | 0 | 0 | 11.0 | 11.0 |
| SPACE_ONLY_CONTROL | 250 | ScienceQA | 66 | -20.0 | 26/86 | 1 | 33 | 0 | 0 | 8.0 | 8.0 |
| SPACE_ONLY_CONTROL | 250 | TabMWP | 72 | -9.0 | 20/81 | 0 | 28 | 0 | 0 | 6.8 | 6.0 |
| SPACE_RETENTION_MIX | 63 | AI2D | 91 | +0.0 | 3/91 | 0 | 9 | 0 | 0 | 8.5 | 8.0 |
| SPACE_RETENTION_MIX | 63 | ChartQA | 54 | +17.0 | 13/37 | 0 | 46 | 0 | 0 | 47.4 | 9.0 |
| SPACE_RETENTION_MIX | 63 | Fusion360 | 84 | +18.0 | 5/66 | 0 | 16 | 0 | 0 | 5.0 | 5.0 |
| SPACE_RETENTION_MIX | 63 | PGPS9K | 39 | -24.0 | 34/63 | 1 | 60 | 0 | 0 | 10.0 | 10.0 |
| SPACE_RETENTION_MIX | 63 | ScienceQA | 75 | -11.0 | 20/86 | 0 | 25 | 0 | 0 | 11.3 | 10.0 |
| SPACE_RETENTION_MIX | 63 | TabMWP | 64 | -17.0 | 24/81 | 3 | 33 | 0 | 0 | 26.5 | 7.0 |
| SPACE_RETENTION_MIX | 125 | AI2D | 92 | +1.0 | 2/91 | 0 | 8 | 0 | 0 | 24.6 | 8.0 |
| SPACE_RETENTION_MIX | 125 | ChartQA | 58 | +21.0 | 12/37 | 5 | 37 | 0 | 0 | 80.2 | 66.0 |
| SPACE_RETENTION_MIX | 125 | Fusion360 | 84 | +18.0 | 4/66 | 0 | 16 | 0 | 0 | 5.0 | 5.0 |
| SPACE_RETENTION_MIX | 125 | PGPS9K | 37 | -26.0 | 31/63 | 11 | 48 | 4 | 0 | 206.1 | 10.0 |
| SPACE_RETENTION_MIX | 125 | ScienceQA | 65 | -21.0 | 27/86 | 0 | 35 | 0 | 0 | 21.8 | 8.0 |
| SPACE_RETENTION_MIX | 125 | TabMWP | 75 | -6.0 | 15/81 | 1 | 24 | 0 | 0 | 59.1 | 58.0 |
| SPACE_RETENTION_MIX | 250 | AI2D | 94 | +3.0 | 1/91 | 1 | 5 | 0 | 0 | 10.0 | 7.0 |
| SPACE_RETENTION_MIX | 250 | ChartQA | 57 | +20.0 | 13/37 | 3 | 40 | 0 | 0 | 69.2 | 39.0 |
| SPACE_RETENTION_MIX | 250 | Fusion360 | 88 | +22.0 | 3/66 | 0 | 12 | 0 | 0 | 5.0 | 5.0 |
| SPACE_RETENTION_MIX | 250 | PGPS9K | 28 | -35.0 | 38/63 | 21 | 51 | 0 | 0 | 71.0 | 9.0 |
| SPACE_RETENTION_MIX | 250 | ScienceQA | 72 | -14.0 | 20/86 | 1 | 27 | 0 | 0 | 17.3 | 8.0 |
| SPACE_RETENTION_MIX | 250 | TabMWP | 82 | +1.0 | 16/81 | 2 | 16 | 0 | 0 | 60.3 | 67.0 |

63update=252노출,125=500노출,250=1000노출.checkpoint를 고르기 위해 중간 MMMU를 실행하지 않았다. 중간 source 결과는 이미 사용된 개발 점검셋이며 독립 최종 테스트가 아니다. 원본의 정답 중 오답으로 바뀐 비율은 표의 분자/분모이며 상세 %와 새 정답/새 오답은 metrics.json. 최초 변화 시점은 관찰한 checkpoint63/125/250 수준에서만 말할 수 있다.

## MMMU 개선·손실 및 종료

| 조건 | 정답 | B0대비 새정답 | B0대비 새오답 | B0정답→오답/491 | 추출실패 | 명시오답 | 반복중단 | 길이종료 | 평균토큰 | 중앙값 |
|---|---|---|---|---|---|---|---|---|---|---|
| E2 | 470 | 119 | 140 | 140/491 | 14 | 416 | 0 | 0 | 2.6 | 2.0 |
| E5 | 459 | 98 | 130 | 130/491 | 59 | 370 | 12 | 17 | 314.7 | 90.0 |
| E7 | 482 | 119 | 128 | 128/491 | 7 | 411 | 0 | 0 | 9.4 | 9.0 |
| LR_LOW_ANSWER | 463 | 116 | 144 | 144/491 | 27 | 410 | 0 | 0 | 11.9 | 7.0 |
| LR_LOW_SOLUTION | 478 | 92 | 105 | 105/491 | 78 | 277 | 67 | 39 | 933.5 | 249.0 |
| SPACE_ONLY_CONTROL | 485 | 125 | 131 | 131/491 | 6 | 409 | 0 | 0 | 8.4 | 8.0 |
| SPACE_RETENTION_MIX | 446 | 112 | 157 | 157/491 | 58 | 396 | 0 | 0 | 11.5 | 9.0 |

원본 MMMU900은 저장491/900 판정을 재사용했다. source B0도 기존600응답을 재사용했으며 새 원본 추론은0회다. 프롬프트/CoT suffix/이미지 처리/temp.7/top_p.8/top_k20/presence1.5/repetition1/seed3407/8192 출력 상한/49152 context/streaming guard/latest_vllm_final_v2 고정. 추출실패·명시오답·반복중단은 배타적이고 길이종료·상한은 교차 집계다. 상한을 무조건 오답 처리하거나 파서를 바꾸지 않았다. 공식30과목/객관식·주관식은metrics.json. 기존900 유형 라벨은 없어 계산/재무/기하/공간 유형을 임의로 만들지 않았다.

## 실제 학습 조건·시간·메모리

| 조건 | 고유 QA | 노출 | update | 학습초 | allocated GiB | reserved GiB | max전체토큰 |
|---|---|---|---|---|---|---|---|
| LR_LOW_ANSWER | 1000 | 1000 | 250 | 196.63 | 10.43 | 19.88 | 995 |
| LR_LOW_SOLUTION | 1000 | 1000 | 250 | 201.12 | 10.43 | 20.14 | 995 |
| SPACE_ONLY_CONTROL | 445 | 1000 | 250 | 181.77 | 9.12 | 9.31 | 311 |
| SPACE_RETENTION_MIX | 745 | 1000 | 250 | 183.44 | 10.42 | 14.77 | 1033 |

BF16 language attention/MLP LoRA r16/alpha32/dropout.05,vision/merger동결,micro1/accum4,AdamW2e-5/decay.01,warmup13후constant,clip1,seed3407,max4096,image200704–1003520,assistant-only loss,no packing,gradient checkpointing. 입력·풀이·정답 잘림 없음. 타깃 형식 변화는 supervised 토큰 노출량도 바꾸므로 풀이의 의미만 달라진 효과로 단정하지 않는다. 첫 실제 forward/backward/update부터 finite loss/gradient를 검사했으며 최종 LoRA B의nonzero와504BF16 tensor를 확인했다. 각adapter는 별도프로세스 재로드·생성을 통과했다.63/125/250 저장 전후 모든 RNG hash가 같고 학습 중 추론은 없다. 학습초는 loading/optimizer/save를 포함하며 별도 CPU검사를 제외한다.

## 해석·다음 재현

LoRA 활성화 시 관찰된 성능 저하를 지식 소실이라고 단정하지 않는다. 답 형식 변화, 고정 파서의 추출 실패, 명시 오답, stochastic 표본 변동을 나눠 기록했다. 긴 출력이나 loss 감소는 추론 개선 증거가 아니다. 단일seed3407 탐색으로 추가seed 반복이 필요하다. source개발점검 기반으로 고정한 target원칙과 동일 데이터/예산을 먼저 추가seed로 재현하고, 결과에 따라 혼합비를 사전등록한 별도 실험으로 비교할 수 있다. MMMU 결과로 이번 설정이나 checkpoint를 다시 고르지 않았다.

이미지·문제·CAD parent 단위 기존 분할과 official test 제외를 유지했다. 유지 학습 대 모든6개sourcechecks/MMMU의 ID·원본group·픽셀·hash 중복을 검사했다. 다른 도식/CAD에 공통 질문 템플릿을 적용한 경우는 동일 image-question 문항으로 간주하지 않았으며 shared template 횟수를 별도 기록했다. 기존perceptual screen을 계승했으나 모든 의미론적 중복/렌더링지각동등성 증명은 아니다.

## 기록·게시

호스트 AIX408-4 / user / RTX4090 24GB / driver535.274.02. torch2.7.0+cu118 실제 CUDA/BF16 backward통과; driver패키지변경/다른프로세스종료없음. 모델/데이터다운로드없음,기존검증파일재사용. 새 run명과private runtime/manifest/config/code/response/adapter hashes·명령·진행·loss·오류·checkpoint영수증은로컬보존. 공개는이보고서/settings.json/metrics.json/question_decisions.csv만이며 QA·이미지·전체생성응답·CAD·adapter·인증정보는없다. 혼합채점은필수가아니므로미산출을0점으로채우지않았다. 게시실패는학습실패와구분하고모델을재실행하지않는다.

실행 명령 metadata 감사: 공통 record helper가 자신의 run.py 경로에 private-runtime 인자를 기록한 오류를 발견했다. 실제 controller argv와 config로 commands.sh를 바로잡고 원본 commands_original_helper.sh 및 감사JSON을 보존했다. 실행 코드·모델·파서 변경이나 재실행은 없었다.

학습/평가 실패: None; controller error: None.

## 변화 관찰 요약

LR_LOW_ANSWER / ChartQA: 63update 53/100 → 125update 53/100 → 250update 54/100; 원본 정답의 새 오답은 최초 관찰 63update부터 존재했다. 관찰 사이의 정확한 발생 update는 알 수 없다.
LR_LOW_ANSWER / PGPS9K: 63update 40/100 → 125update 38/100 → 250update 40/100; 원본 정답의 새 오답은 최초 관찰 63update부터 존재했다. 관찰 사이의 정확한 발생 update는 알 수 없다.
LR_LOW_ANSWER / TabMWP: 63update 47/100 → 125update 60/100 → 250update 70/100; 원본 정답의 새 오답은 최초 관찰 63update부터 존재했다. 관찰 사이의 정확한 발생 update는 알 수 없다.
LR_LOW_SOLUTION / ChartQA: 63update 50/100 → 125update 53/100 → 250update 53/100; 원본 정답의 새 오답은 최초 관찰 63update부터 존재했다. 관찰 사이의 정확한 발생 update는 알 수 없다.
LR_LOW_SOLUTION / PGPS9K: 63update 64/100 → 125update 60/100 → 250update 55/100; 원본 정답의 새 오답은 최초 관찰 63update부터 존재했다. 관찰 사이의 정확한 발생 update는 알 수 없다.
LR_LOW_SOLUTION / TabMWP: 63update 71/100 → 125update 69/100 → 250update 73/100; 원본 정답의 새 오답은 최초 관찰 63update부터 존재했다. 관찰 사이의 정확한 발생 update는 알 수 없다.
SPACE_ONLY_CONTROL / AI2D: 63update 91/100 → 125update 93/100 → 250update 92/100; 원본 정답의 새 오답은 최초 관찰 63update부터 존재했다. 관찰 사이의 정확한 발생 update는 알 수 없다.
SPACE_ONLY_CONTROL / ChartQA: 63update 54/100 → 125update 56/100 → 250update 56/100; 원본 정답의 새 오답은 최초 관찰 63update부터 존재했다. 관찰 사이의 정확한 발생 update는 알 수 없다.
SPACE_ONLY_CONTROL / Fusion360: 63update 86/100 → 125update 87/100 → 250update 89/100; 원본 정답의 새 오답은 최초 관찰 63update부터 존재했다. 관찰 사이의 정확한 발생 update는 알 수 없다.
SPACE_ONLY_CONTROL / PGPS9K: 63update 44/100 → 125update 43/100 → 250update 45/100; 원본 정답의 새 오답은 최초 관찰 63update부터 존재했다. 관찰 사이의 정확한 발생 update는 알 수 없다.
SPACE_ONLY_CONTROL / ScienceQA: 63update 69/100 → 125update 69/100 → 250update 66/100; 원본 정답의 새 오답은 최초 관찰 63update부터 존재했다. 관찰 사이의 정확한 발생 update는 알 수 없다.
SPACE_ONLY_CONTROL / TabMWP: 63update 65/100 → 125update 69/100 → 250update 72/100; 원본 정답의 새 오답은 최초 관찰 63update부터 존재했다. 관찰 사이의 정확한 발생 update는 알 수 없다.
SPACE_RETENTION_MIX / AI2D: 63update 91/100 → 125update 92/100 → 250update 94/100; 원본 정답의 새 오답은 최초 관찰 63update부터 존재했다. 관찰 사이의 정확한 발생 update는 알 수 없다.
SPACE_RETENTION_MIX / ChartQA: 63update 54/100 → 125update 58/100 → 250update 57/100; 원본 정답의 새 오답은 최초 관찰 63update부터 존재했다. 관찰 사이의 정확한 발생 update는 알 수 없다.
SPACE_RETENTION_MIX / Fusion360: 63update 84/100 → 125update 84/100 → 250update 88/100; 원본 정답의 새 오답은 최초 관찰 63update부터 존재했다. 관찰 사이의 정확한 발생 update는 알 수 없다.
SPACE_RETENTION_MIX / PGPS9K: 63update 39/100 → 125update 37/100 → 250update 28/100; 원본 정답의 새 오답은 최초 관찰 63update부터 존재했다. 관찰 사이의 정확한 발생 update는 알 수 없다.
SPACE_RETENTION_MIX / ScienceQA: 63update 75/100 → 125update 65/100 → 250update 72/100; 원본 정답의 새 오답은 최초 관찰 63update부터 존재했다. 관찰 사이의 정확한 발생 update는 알 수 없다.
SPACE_RETENTION_MIX / TabMWP: 63update 64/100 → 125update 75/100 → 250update 82/100; 원본 정답의 새 오답은 최초 관찰 63update부터 존재했다. 관찰 사이의 정확한 발생 update는 알 수 없다.
