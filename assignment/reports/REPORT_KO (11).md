# RESTORE_E45 대응 실험 결과

E4·E5를 RTX 4090에서 순차 완료했다. 각 모델은 같은 원본에서 독립 초기화했다. teacher/KD는 사용하지 않았고 기존 B0 MMMU 응답을 재사용했다. 일반 비교는 latest_vllm_final_v2이며 과거 혼합 점수는 별도 기록한다.

## 전체 결과

| 모델 | 정답/900 | 정확도 | B0 대비 pp | 대응 비교군 | 대응 변화 pp | 새로 맞힘/틀림 |
|---|---|---|---|---|---|---|
| B0 | 491/900 | 54.56% | +0.00 | — | — | — |
| E1 | 482/900 | 53.56% | -1.00 | — | — | — |
| E2 | 470/900 | 52.22% | -2.33 | — | — | — |
| E3 | 471/900 | 52.33% | -2.22 | — | — | — |
| E4 | 489/900 | 54.33% | -0.22 | E1 | +0.78 | 114/107 |
| E5 | 459/900 | 51.00% | -3.56 | E2 | -1.22 | 97/108 |

## 실제 변경과 통제

기준 데이터는 현재 호스트에서 완료된 RESTORE_E123의 실제 manifest다. 이 manifest의 previous_sample_identity_verified=false는 더 오래된 P03 가공 데이터의 미복원을 뜻하며, 이번 E4/E5와 완료된 RESTORE_E1/E2 사이 동일성 미확인을 뜻하지 않는다. E4: E1과 파일 SHA256·이미지·원래 순서·실제 250회 update의 문항 노출 순서가 같으며 learning_rate만 1e-4→2e-5이다. E5: E2와 동일한 1,000문항·순서·입력·분할이며 TabMWP 500개 target만 원본 solution + 줄바꿈 + Final Answer: 원본 정답으로 변경했다. ChartQA 500개 target과 LR 1e-4는 유지했다. 500개 원본 풀이가 모두 존재했고 결론 문장에서 답을 나타내는 절(명시 count·확률·변화율·비교 차이·빈도 범주 등)을 정답 참조 없이 추출한 후 원본 정답과 정확한 수치 일치를 확인했다. 정답이 문장 어딘가에 포함됐다는 사실만으로 승인하지 않았다. 500개 결론 및 파싱 가능한 산술 등식268개에 모순0개였다. 제외·교체 0개라 E5-control은 필요하지 않았다. 다만 모든 풀이의 의미론적 증명이나 표 OCR 재검산을 완료했다는 뜻은 아니다.

공통: Qwen/Qwen3-VL-4B-Instruct @ ebb281ec70b05090aa6165b016eac8ec08e71b17; BF16 LoRA r=16/alpha=32/dropout=.05; language attention+MLP 252개 모듈·33,030,144개 파라미터; vision/merger 동결. microbatch1·accum4·250update·1epoch·seed3407; AdamW weight_decay=.01, warmup13 뒤 constant, max_grad_norm1; 길이4096, 이미지200704–1003520pixels, checkpointing, assistant-only mask, no packing. E4/E5 모두 독립 저장 후 별도 프로세스 재로드와 생성이 통과했다.

Processor가 학습1000+점검300개를 각 run에서 실제 검사했고 잘림 0개다. E5 추가 풀이의 최대 supervised 길이는391, 전체 최대995토큰으로4096 이내다. 입력에 정답·풀이를 추가하지 않았다. 기존 이미지/group 단위 분할·MMMU 중복 제외를 그대로 유지했다.

평가: 기존 저장 messages와 이미지 순서, CoT 추가 문구, processor/hash, vLLM0.11.2, seed3407, temperature.7/top_p.8/top_k20/repetition_penalty1/presence_penalty1.5, 출력8192, context49152, 이미지1003520–4014080pixels, 기존 streaming repetition guard·parser를 유지했다. guard min1024/every128/window600words/phrase32/occ4/coverage.2/tail80/confirm2. 동적 LoRA 커널 사용으로 원본 backend와 비트 단위 동일성은 보장하지 않는다. 평가 응답을 한 번 생성해 보존했고 결과로 설정이나 checkpoint를 재선택하지 않았다.

## 객관식·주관식

| 모델 | 객관식 정답/847 | 객관식 % | 주관식 정답/53 | 주관식 % |
|---|---|---|---|---|
| B0 | 483 | 57.02 | 8 | 15.09 |
| E1 | 473 | 55.84 | 9 | 16.98 |
| E2 | 463 | 54.66 | 7 | 13.21 |
| E3 | 464 | 54.78 | 7 | 13.21 |
| E4 | 483 | 57.02 | 6 | 11.32 |
| E5 | 455 | 53.72 | 4 | 7.55 |

## 과목별 결과

| 과목 | B0 | E1 | E2 | E3 | E4 | E5 | E4−E1 | E5−E2 |
|---|---|---|---|---|---|---|---|---|
| Accounting | 22 | 14 | 15 | 14 | 21 | 15 | 7 | 0 |
| Agriculture | 13 | 15 | 15 | 15 | 15 | 14 | 0 | -1 |
| Architecture_and_Engineering | 12 | 13 | 12 | 13 | 10 | 7 | -3 | -5 |
| Art | 19 | 20 | 20 | 20 | 18 | 18 | -2 | -2 |
| Art_Theory | 25 | 25 | 26 | 24 | 22 | 26 | -3 | 0 |
| Basic_Medical_Science | 21 | 21 | 21 | 20 | 20 | 21 | -1 | 0 |
| Biology | 19 | 16 | 16 | 12 | 13 | 15 | -3 | -1 |
| Chemistry | 8 | 10 | 9 | 8 | 12 | 8 | 2 | -1 |
| Clinical_Medicine | 16 | 19 | 15 | 19 | 23 | 15 | 4 | 0 |
| Computer_Science | 18 | 18 | 13 | 18 | 14 | 14 | -4 | 1 |
| Design | 22 | 25 | 25 | 25 | 23 | 26 | -2 | 1 |
| Diagnostics_and_Laboratory_Medicine | 10 | 11 | 11 | 11 | 9 | 12 | -2 | 1 |
| Economics | 21 | 20 | 20 | 23 | 25 | 22 | 5 | 2 |
| Electronics | 7 | 13 | 15 | 14 | 7 | 8 | -6 | -7 |
| Energy_and_Power | 9 | 12 | 13 | 9 | 8 | 8 | -4 | -5 |
| Finance | 17 | 10 | 10 | 13 | 18 | 14 | 8 | 4 |
| Geography | 16 | 16 | 15 | 14 | 13 | 13 | -3 | -2 |
| History | 21 | 20 | 20 | 20 | 20 | 20 | 0 | 0 |
| Literature | 24 | 24 | 26 | 26 | 24 | 25 | 0 | -1 |
| Manage | 16 | 15 | 14 | 11 | 13 | 10 | -2 | -4 |
| Marketing | 23 | 18 | 18 | 14 | 25 | 19 | 7 | 1 |
| Materials | 11 | 12 | 9 | 9 | 10 | 6 | -2 | -3 |
| Math | 11 | 12 | 12 | 11 | 14 | 10 | 2 | -2 |
| Mechanical_Engineering | 5 | 11 | 11 | 10 | 7 | 9 | -4 | -2 |
| Music | 10 | 5 | 7 | 6 | 10 | 9 | 5 | 2 |
| Pharmacy | 22 | 21 | 17 | 19 | 17 | 19 | -4 | 2 |
| Physics | 17 | 11 | 12 | 15 | 18 | 16 | 7 | 4 |
| Psychology | 18 | 22 | 20 | 22 | 22 | 21 | 0 | 1 |
| Public_Health | 21 | 16 | 15 | 19 | 22 | 20 | 6 | 5 |
| Sociology | 17 | 17 | 18 | 17 | 16 | 19 | -1 | 1 |

각 과목 30문항, 표는 정답 수다. 기존 900문항 취약 유형 라벨은 발견되지 않아 유형별 오답률은 제공할 수 없다. 다음 묶음은 공식 과목명에 따른 사전 고정 proxy이며 계산 유형 라벨이나 검증된 비대상 유형과 동등하지 않다.

| 공식 과목 묶음 | n | B0 | E1 | E2 | E3 | E4 | E5 | E4−E1 | E5−E2 |
|---|---|---|---|---|---|---|---|---|---|
| engineering_subject_proxy | 150 | 44 | 61 | 60 | 55 | 42 | 38 | -19 | -22 |
| finance_subject_proxy | 90 | 60 | 44 | 45 | 50 | 64 | 51 | 20 | 6 |
| math_subject_proxy | 30 | 11 | 12 | 12 | 11 | 14 | 10 | 2 | -2 |
| other_subjects_complement | 630 | 376 | 365 | 353 | 355 | 369 | 360 | 4 | 7 |

공학 proxy: Architecture_and_Engineering/Electronics/Energy_and_Power/Materials/Mechanical_Engineering. 재무 proxy: Accounting/Economics/Finance. 수학 proxy: Math. 나머지는 21개 과목이다. 해당 과목 내부에도 비계산 문항이 섞여 있으므로 계산 능력 자체에 대한 단정은 제한한다.

## 답 추출·종료 원인과 출력 길이

| 모델 | 추출 실패 | 명시 오답 | 반복 중단 | 길이 종료 | 8192 상한 | 토큰 평균 | 중앙값 | 여러 줄 출력 |
|---|---|---|---|---|---|---|---|---|
| B0 | 130 | 226 | 53 | 60 | 60 | 1770.7 | 562.0 | 897 |
| E1 | 12 | 406 | 0 | 0 | 0 | 6.8 | 6.0 | 0 |
| E2 | 14 | 416 | 0 | 0 | 0 | 2.6 | 2.0 | 0 |
| E3 | 0 | 429 | 0 | 0 | 0 | 2.2 | 2.0 | 0 |
| E4 | 94 | 266 | 51 | 50 | 50 | 1238.8 | 212.0 | 510 |
| E5 | 59 | 370 | 12 | 17 | 17 | 314.7 | 90.0 | 609 |

추출 실패·명시 오답·반복 중단은 배타적 오답 범주다. 길이 종료/출력 상한은 별도 교차 집계이며 추출 가능한 정답이면 인정한다. 반복 중단은 기존 정책대로 오답이다. 실행 오류 0개. 출력 토큰 수는 중단·상한 출력을 포함한다.

사전에 정답·평가 결과 없이 고정한 Accounting/Math/Mechanical_Engineering 각2개, 총6개 ID를 모든 모델에서 표본 점검했다. 문항별 출력 길이·여러 줄·산술식·설명 표지 포함 여부와 정오를 output_sample_review.json에 기록했다. 이는 자동 형식 검토이며 풀이의 논리적 타당성을 사람 수준으로 검증한 것은 아니다. E4 Accounting10·21의 실제 출력은 직접 읽어 분류/계산 단계와 명시적 최종 답이 있는 것을 확인했으며, 해당 두 문항의 제한적 관찰도 기록했다. 모든 중간 계산을 수동 검증했다는 뜻은 아니다. 전체 응답은 로컬 manual_samples_private.json에 보존한다. 출력이 길거나 풀이 형식이 있다는 사실만으로 추론 개선을 판단하지 않는다.

## 분리 점검셋

| 모델 | ChartQA /100 | TabMWP /100 | PGPS9K /100 |
|---|---|---|---|
| B0 | 37 | 81 | 63 |
| E1 | 56 | 66 | 45 |
| E2 | 52 | 76 | 41 |
| E3 | 54 | 54 | 49 |
| E4 | 56 | 48 | 67 |
| E5 | 53 | 83 | 50 |

공식 validation 또는 기존 고정 점검 분할이며 모든 모델에서 동일 문항이다. 점검셋도 기존 latest_vllm_final_v2의 답 추출·정확한 숫자/단위 판정을 사용했으며, ChartQA 별도5% 허용오차 등 공식 데이터셋 채점으로 전환하지 않았다. 원본 모델 점검셋 결과는 이미 저장된300문항 추론을 재사용했다. 원본 MMMU900 재추론은0회다. 대응 문항별 새로 맞힘/틀림과 점검셋 상세 종료 지표는 metrics.json에 있다.

## 시간·VRAM·재현 기록

| 모델 | 학습 초 | update | 학습 allocated GiB | 학습 reserved GiB | device peak MiB | 평가 초 |
|---|---|---|---|---|---|---|
| E1 | 208.96 | 250 | 10.37 | 15.97 | None | 425.23 |
| E2 | 196.56 | 250 | 10.43 | 19.88 | None | 300.68 |
| E3 | 185.25 | 250 | 9.58 | 12.83 | None | 282.92 |
| E4 | 215.93 | 250 | 10.37 | 15.97 | 16857.0 | 39422.78 |
| E5 | 195.50 | 250 | 10.43 | 20.14 | 21121.0 | 9678.02 |

device peak는 nvidia-smi 1초 샘플이며 worker·parent·display를 포함한다. allocator peak와 의미가 다르다. 학습시간은 model loading·LoRA 부착·optimizer loop·저장을 포함하며 CPU 사전 processor 검사는 제외한다. run wall_seconds는 사전 검사도 포함한다. 평가시간은 engine 초기화를 포함한다. 구체 run ID·실제 config/manifest/response/adapter/code hash·데이터 revision·노출 순서 증거는 metrics.json에 기록했다. 원본·전체 응답·adapter는 로컬에서만 보존했다.

실행 경로: /home/user/mmdl-work. train Python .venv-restore-train/bin/python (torch2.7.0+cu118); eval Python .venv-restore-eval/bin/python (torch2.9.0/cu128). 호스트 RTX4090 24GB, driver535.274.02에서 실제 CUDA 연산·BF16 backward 통과. 드라이버 변경이나 다른 사용자 프로세스 종료 없음. 모델은 검증된 /dev/shm snapshot을 사용했으므로 재부팅 시 해당 모델 파일은 재확보가 필요하다.

정확한 stage 명령은 각 로컬 run commands.sh에 있으며 실행은 다음 명령으로 유지했다. 완료 영수증이 있는 stage는 중복 실행하지 않는다.

```bash
cd /home/user/mmdl-work
/home/user/mmdl-work/.venv-restore-train/bin/python -u /home/user/mmdl-work/.restore/e45_runtime.py --suite
```

## 혼합 채점

혼합 채점 미완료. 과거 B0는 실제 저장 Qwen3-8B judge847개 + repetition-abort53개와 원래 unresolved81개 객관식 terminal-rule 처리를 CPU 재생해563/900(62.56%) 및900개 판정을 재현했다. E1–E5의 동일 Judge 기록이 없어 같은 전 모델 혼합 비교는 수행할 수 없다. 새로운 Judge나 대체 혼합 규칙을 만들지 않았다. 역사적 open Judge 입력에는 accepted_answers 정답이 들어가므로 전체 혼합 절차는 정답 독립적 답 추출이라고 할 수 없다. 객관식 terminal parser는 정답 독립이다. 전체 응답에서 정답 문자열 검색/복수 후보 인정 규칙으로 대체하지 않았으며 일반491/900과 분리했다. 과거 audit 보고서는 ../MIXED_SCORING_AUDIT_20261011/REPORT_KO.md를 참고한다.

## 해석과 다음 실험

E4↔E1: 전체 정답 +7개(+0.78pp), 새로 맞힘 114개·새로 틀림 107개. 원인 해석은 이 대응 비교를 기준으로 하며 다른 데이터 실험 사이 차이를 동일 조건 효과로 해석하지 않는다.
E5↔E2: 전체 정답 -11개(-1.22pp), 새로 맞힘 97개·새로 틀림 108개. 원인 해석은 이 대응 비교를 기준으로 하며 다른 데이터 실험 사이 차이를 동일 조건 효과로 해석하지 않는다.

단일 seed·소규모1,000문항·MMMU validation 개발 비교이며 통계적 재현이나 인과적 일반화의 증거가 제한적이다. output 길이·표면 풀이 형식 증가만으로 추론 향상을 주장하지 않는다. 과목 proxy가 실제 취약 유형을 대신하지 않으며 원본 풀이의 의미론적 검증도 제한적이다. 동적 LoRA backend와 표본 stochastic 생성의 차이를 함께 고려해야 한다.

다음 실험은 먼저 동일 조건의 추가 seed 재현을 사전 고정하고, 독립 라벨 검토로 계산 문항과 비대상 문항을 구분해 대응 효과와 기존 능력 손실을 확인하는 것을 제안한다. 이후 동일 E2 문항에서 LR(1e-4/2e-5)×target(정답만/원본 풀이 포함)의 사전 고정2×2 비교로 상호작용을 분리할 수 있다. 기존 평가 결과를 보고 이번 checkpoint를 교체하거나 추가 학습하지 않았다.

## 공개 범위와 보존

이 폴더에는 설명·집계 지표·공개 가능한 문항 ID별 판정만 게시했다. 원문 질문/정답·이미지·전체 생성 응답·adapter·인증 정보는 포함하지 않는다. 기존 RESTORE_E123 및 혼합 audit는 수정하지 않았다. 새 run의 환경·manifest·설정·명령·진행·응답·오류·checkpoint 검증은 로컬 runs/에 보존한다.
