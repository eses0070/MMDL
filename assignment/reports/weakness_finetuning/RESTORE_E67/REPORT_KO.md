# RESTORE_E67 과학 도식·공간 대응 실험

실제 실행 상태: `completed`. 가공·학습·재로드·평가 완료 여부는 아래와 metrics.json의 실제 영수증을 따른다. 모든 adapter는 원본 Qwen3-VL-4B-Instruct에서 독립 시작하며 선생 모델·KD·모델 생성 풀이를 사용하지 않았다. PrIMuS 및 E8은 제외했다.

| 실험 | 데이터 | 학습 | 재로드 | 평가 |
|---|---|---|---|---|
| E6-A | 완료 | 완료 | 완료 | 완료 |
| E6-B | 완료 | 완료 | 완료 | 완료 |
| E7 | 완료 | 완료 | 완료 | 완료 |

## 실제 데이터와 선정

실제 원본 경로는 /home/user/mmdl-work/datasets/ScienceQA, AI2D, Fusion360Gallery이다. datasets/raw/ 아래 이전 DNS 실패 manifest는 보존했고 이번에 실제 파일·annotation·archive CRC와 hash를 검증했다. ScienceQA git revision2cbf8318e07b9ece895bb2ae605e71e38d623264, 이미지 연결 누락0개. AI2D README v1.0.0(2016), 질문15501개·이미지4903개·official test IDs982개. Fusion r1.0.1 final CAD6900train/1725test이며8625 construction JSON을 확인해 기존 QA가 없음을 확인했다. 실제 전송 당시 HTTP/revision receipt가 남아 있지 않은 archive는 로컬 SHA256·공식 파일 구성/문서로 범위를 기록했으며 원격 불변 checksum까지 검증했다고 주장하지 않는다.

E6 최종 가공본 RESTORE_E67_v4. 자연과학 영역 제약에 더해 실제 원래 질문·native skill에 수치 연산/물리 관계/정량 읽기 근거가 있는 문항만 선택했다. 이미지 존재·과목명·context 표현만으로 계산을 분류하지 않았다. 초기 역사 연표/context 오분류는 실제 표본 검토에서 발견해 학습 전에 제외했고 이전 가공본을 보존했다.

| 실험 | ScienceQA | AI2D | ChartQA | 총문항 | 계산 | 수치 읽기 | 비계산 관계 | Chart 추가 |
|---|---|---|---|---|---|---|---|---|
| E6-A | 500 | 500 | 0 | 1000 | 26 | 211 | 763 | 0 |
| E6-B | 251 | 249 | 500 | 1000 | 13 | 105 | 382 | 500 |

E6-A 계산 비중2.6%, 수치 읽기21.1%, 비계산 관계76.3%이다. 계산은 주로 Punnett square 비율/확률이며 공학 물리 계산·단위 변환 전용 자료를 확보했다는 뜻은 아니다. 이 실험은 과학 도식·관계 보강으로 해석한다. E6-B는 A의 정확히500개(ScienceQA251+AI2D249)를 source/task stratum별 절반으로 선택하고 기존 E1 ChartQA학습500개와 혼합했다. 두 모델 모두1000문항/250update/LR2e-5이며 모든 target은 원본 정답만을 Final Answer: 접두어로 한 줄에 기록했다. 공식 solution·lecture는 입력이나 타깃에 넣지 않았다. target 템플릿/풀이 비율은 동일하나, 숫자와 자연어 답의 의미 분포는 데이터 혼합으로 달라져 별도 기록했다.

ScienceQA train/val, AI2D official test IDs를 제외한 원본 이미지 단위 train/heldout으로 나눴다. 실제 PNG에 필요한 ABC 표지가 없는 abcLabel=true 변형은 추측으로 표지를 만들지 않고 모두 제외했다. source checks ScienceQA/AI2D 각100개이며 official 최종 test 이미지와 동일한 pixels도 train에서 제외했다. 같은 pixels/original image 그룹이 train/check에 걸치지 않는다. MMMU982개 이미지와 기존 source check300개에 대해 파일 hash·decoded RGB pixel hash·질문 정규화·dHash≤2 후보 제외를 검사했다. 의미론적 중복이 전수 검증된 것은 아니다.

E7은 공식 최종 CAD triangulated mesh와 알려진 카메라(+Z top, X-right/Y-up)로 대응 QA를 제작했다. 중간 extrude geometry를 final design으로 사용하지 않았다. CPU z-buffer 렌더링의 전후 삼각형 occlusion·face order 불변성과 방향을 검사했다. 먼저20개를 실제로 보고 정답 연결/선택지 누출을 확인했다. 이후 official test parent project를 제외하고 parent_project 단위로 train/check를 분리한 뒤 distractor도 같은 split에서만 가져왔다. 색상은 균일 회색, 레이아웃/조명/카메라는 고정, 정답 위치만 균형 있게 배치했고 CAD파일명·정답·메타데이터는 입력에 넣지 않았다.

대칭/유사 top silhouette·빈 투상·잘린 렌더링을 제외한 유효 train445개/check100개를 확보했다. 1000개로 채우기 위한 반복/추측/모델생성은 없었다. 선택지는 train A112/B111/C111/D111, check각25개다. 정상 QA의 geometry identity와 카메라에서 정답을 결정했고, 최소 pairwise top mask XOR 비율5.5%를 요구했다. 이는 전수 사람 판별의 증명이 아니며192px mesh raster에서 작은 세부는 소실될 수 있다. 단면 문항은 포함하지 않았다. 원본 pilot/full 경로 충돌은 학습 전 분리했고20개 원래 이미지 hash를 복원·검증해 보존했다.

## 실제 학습·평가 조건

Qwen/Qwen3-VL-4B-Instruct @ ebb281ec70b05090aa6165b016eac8ec08e71b17. BF16 language attention/MLP LoRA r16/alpha32/dropout.05; vision/merger동결. micro1/accum4, AdamW LR2e-5/weight_decay.01, warmup13 후constant, clip1, 1epoch, seed3407, max4096, image200704–1003520pixels, checkpointing, assistant-only loss, no packing. E7은445개 전체를 한 번 사용해112update(111회×4micro + 마지막1micro)이며 마지막 update는 실제1micro 평균 loss로 계산했다. 이 데이터 크기 관련 admission/마지막 partial accumulation만 private wrapper에서 일반화했고 기존 shared code는 수정하지 않았다.

Processor 검사: E6-A/B 각각1600개(학습1000+점검600), E7 1045개(학습445+점검600). 최대 전체 길이 E6-A/B1023, E7 997이며 모두4096이내; input/image loss mask와 target decode 일치 확인, 무음 잘림0개. CUDA tensor연산/BF16 backward는 기존 E5 작업 종료 후 실제 training Python에서 수행하도록 admission했고 결과는 gpu_probe 영수증과 host_probe.json에 기록했다. 점검 실패를 통과/학습완료로 표시하지 않는다.

평가는 MMMU900+ChartQA/TabMWP/PGPS/ScienceQA/AI2D/Fusion각100, 각모델1500문항이다. 기존 저장 MMMU prompt/message/image순서, CoT suffix, vLLM0.11.2, seed3407/temp.7/top_p.8/top_k20/repetition1/presence1.5, out8192/context49152, image1003520–4014080pixels, 원래 streaming guard와 latest_vllm_final_v2를 유지했다. 추가 final-only 평가 prompt는 쓰지 않았다. 원본 MMMU900 응답은 재사용했다. 원본 모델 추가 추론의 허용 범위는 NEW ScienceQA/AI2D200개와 Fusion100개 점검뿐이며 실제 완료/미확보는 source 결과표를 따른다. 기존 Chart/Tab/PGPS300 baseline은 재사용했다.

E4/E5 학습률은 수정하지 않았다(E4 2e-5, E5 1e-4). E67 LR2e-5는 E5 점검 결과가 아직 없던 준비 시점에 요청의 fallback으로 고정했고, 실행 전에 E45 실제 설정/source check를 확인해 기록했다. MMMU 결과는 조건 선택이나 checkpoint 재선택에 사용하지 않았다.

## MMMU900 결과

| 모델 | 정답 | 정확도 | B0대비pp | 새로맞힘 | 새로틀림 |
|---|---|---|---|---|---|
| B0 | 491 | 54.56% | +0.00 | 0 | 0 |
| E1 | 482 | 53.56% | -1.00 | 124 | 133 |
| E2 | 470 | 52.22% | -2.33 | 119 | 140 |
| E3 | 471 | 52.33% | -2.22 | 125 | 145 |
| E4 | 489 | 54.33% | -0.22 | 86 | 88 |
| E5 | 459 | 51.00% | -3.56 | 98 | 130 |
| E6-A | 460 | 51.11% | -3.44 | 118 | 149 |
| E6-B | 433 | 48.11% | -6.44 | 104 | 162 |
| E7 | 482 | 53.56% | -1.00 | 119 | 128 |

완료된 평가의 결과만 표에 넣었다. 미완료/차단 실험을0/900으로 처리하거나 부분 문항을 전체 정확도로 표시하지 않았다.

## 답 추출·출력·종료 정책

| 모델 | 추출실패 | 명시오답 | 반복중단 | 길이종료 | 상한8192 | 토큰평균 | 중앙값 |
|---|---|---|---|---|---|---|---|
| B0 | 130 | 226 | 53 | 60 | 60 | 1770.7 | 562.0 |
| E1 | 12 | 406 | 0 | 0 | 0 | 6.8 | 6.0 |
| E2 | 14 | 416 | 0 | 0 | 0 | 2.6 | 2.0 |
| E3 | 0 | 429 | 0 | 0 | 0 | 2.2 | 2.0 |
| E4 | 94 | 266 | 51 | 50 | 50 | 1238.8 | 212.0 |
| E5 | 59 | 370 | 12 | 17 | 17 | 314.7 | 90.0 |
| E6-A | 44 | 396 | 0 | 0 | 0 | 11.5 | 9.0 |
| E6-B | 75 | 392 | 0 | 0 | 0 | 11.3 | 9.0 |
| E7 | 7 | 411 | 0 | 0 | 0 | 9.4 | 9.0 |

반복중단은 기존정책 오답, 길이상한은 추출가능한 답으로 판정하며 무조건오답이 아니다. 정답/추출실패/명시오답/반복중단은 배타적이고 길이상한은 교차 집계다. MC847/open53 및30과목 전체 결과는 metrics.json에 기록한다. 기존900문항 계산/기하/공간 유형 라벨을 발견하지 못해 유형별 오답률을 새로 만들어 채우지 않았다. 새 source의 선정 유형은900문항 기존 라벨이 아니다.

## 주요 공식 과목별 변화

| 공식 과목 | B0 정답/30 | E6-A | E6-B | E7 |
|---|---|---|---|---|
| Accounting | 22 | 17 | 8 | 18 |
| Economics | 21 | 20 | 18 | 20 |
| Finance | 17 | 11 | 11 | 11 |
| Math | 11 | 11 | 10 | 11 |
| Architecture_and_Engineering | 12 | 12 | 9 | 14 |
| Electronics | 7 | 12 | 10 | 13 |
| Mechanical_Engineering | 5 | 11 | 7 | 12 |
| Physics | 17 | 14 | 14 | 12 |
| Public_Health | 21 | 11 | 11 | 14 |

공식 과목명에 따른 집계이며 계산/기하/공간 유형 라벨이 아니다. 나머지 과목 및 동일 문항 새 정답/새 오답은 metrics.json과 공개판정에 보존했다.

## source 점검셋

| 모델 | ChartQA | TabMWP | PGPS9K | ScienceQA | AI2D | Fusion360 |
|---|---|---|---|---|---|---|
| B0 | 37 | 81 | 63 | 86 | 91 | 66 |
| E1 | 56 | 66 | 45 | 미확보 | 미확보 | 미확보 |
| E2 | 52 | 76 | 41 | 미확보 | 미확보 | 미확보 |
| E3 | 54 | 54 | 49 | 미확보 | 미확보 | 미확보 |
| E4 | 56 | 48 | 67 | 미확보 | 미확보 | 미확보 |
| E5 | 53 | 83 | 50 | 미확보 | 미확보 | 미확보 |
| E6-A | 57 | 63 | 46 | 86 | 96 | 56 |
| E6-B | 55 | 78 | 46 | 75 | 94 | 54 |
| E7 | 54 | 68 | 46 | 68 | 92 | 83 |

모든 각 source100문항, 동일 split/문항으로 비교한다. 점검셋 상승이나 출력 길이 증가를 MMMU 추론 개선의 증거로 대신하지 않는다.

## 시간·VRAM·update·hash

| 모델 | 학습문항 | update | 학습초 | peak allocated GiB | peak reserved GiB |
|---|---|---|---|---|---|
| E1 | 1000 | 250 | 208.96 | 10.37 | 15.97 |
| E2 | 1000 | 250 | 196.56 | 10.43 | 19.88 |
| E3 | 1000 | 250 | 185.25 | 9.58 | 12.83 |
| E4 | 1000 | 250 | 215.93 | 10.37 | 15.97 |
| E5 | 1000 | 250 | 195.50 | 10.43 | 20.14 |
| E6-A | 1000 | 250 | 203.10 | 10.48 | 17.88 |
| E6-B | 1000 | 250 | 207.84 | 10.48 | 18.91 |
| E7 | 445 | 112 | 84.74 | 9.12 | 9.31 |

학습초는 model/LoRA loading·optimizer loop·저장을 포함하고 CPU 사전검사는 제외한다. wall time/평가시간/nvidia-smi device peak/개별 config/data/code/adapter/response hash는 metrics.json에 있다. device peak는 parent/worker/display 포함1초샘플이며 allocator peak와 다르다. 각 run의 환경·정확한 명령·loss·update·실패·checkpoint hash·독립 reload·문항별 원본 응답은 로컬 private runs에 보존했다.

## 대응 해석·한계

E6-B↔E6-A: 새 정답16개·새 오답43개, 정답 변화-27개(-3.00pp). 동일 총문항/update/LR/target-template에서 data mixture 효과를 본다. 새 오답43개 중18개는 unrecognized_choice 추출 실패,25개는 명시 오답이다. 출력 표본에서 일부는 통화 표지/정확한 option text를 생략했고 다른 일부는 숫자 자체도 달랐다.18개를 모두 순수 formatting 오류나 실제 정답이라고 재해석하지 않았고 채점도 변경하지 않았다.
E7↔B0: 새 정답119개·새 오답128개로 정답9개 감소(-1.00pp)했다. Fusion360 점검은66/100에서83/100으로17개 개선됐으나, MMMU 전체는 개선되지 않았다. 공간 source 개선을 기존900의 공간유형 효과라고 동일시하지 않는다. 다른 과목의 새 오답/성능손실도 같은 판정으로 비교한다.

단일 seed 개발 비교, E7은445개로 다른1000문항 실험과 exposure가 다르다. 과학 계산 문항이26개뿐이며 genetics probability/ratio에 치우쳤다. 선택/중복 제거는 규칙과hash/perceptual screen 기반이며 의미적 중복·모든 사고과정 타당성·모든CAD지각동등성을 전수검증하지 않았다. 동적 LoRA backend도 원본과 비트 단위 동일성을 보장하지 않는다.

다음에는 source별 문제 의미를 사람이 독립 검토하고, 계산/비계산 관계 source 비중을 사전 고정한 추가seed 반복과 공간QA의 mesh 해상도/지각모호성 검증을 권장한다. 이번 MMMU 결과를 보고 학습을 반복하거나 checkpoint를 선택하지 않았다.

## 혼합 채점·실패·게시

| 모델 | 재생 가능한 판정/900 | 미확보 | 확인된 정답(부분) | 전체 혼합 정답 |
|---|---|---|---|---|
| B0 | 900 | 0 | 563 | 563 |
| E1 | 2 | 898 | 1 | 미산출 |
| E2 | 1 | 899 | 0 | 미산출 |
| E3 | 1 | 899 | 0 | 미산출 |
| E4 | 53 | 847 | 1 | 미산출 |
| E5 | 14 | 886 | 1 | 미산출 |
| E6-A | 1 | 899 | 0 | 미산출 |
| E6-B | 0 | 900 | 0 | 미산출 |
| E7 | 2 | 898 | 0 | 미산출 |

혼합 채점 미완료. 과거 실제코드+저장Judge를 재생해B0 563/900을 재현했다. 전 모델에 같은 실제 절차를 적용하되, 전체 Judge 입력과 finish reason이 완전히 같은 cached 사례 및 강제 repetition-abort 판정만 재생할 수 있었다. 그 외 E1–E7 Judge 기록과 Qwen3-8B checkpoint가 없어 전체모델 혼합 비교는 미완료다. 미확보를 오답으로 세지 않았고 부분 정답 수를 전체 정확도로 표시하지 않았다. 임의대체·정답문자열검색·새Judge추론은 실행하지 않았다. 과거 open Judge 입력은 accepted_answers 정답을 포함하므로 정답독립 채점이라고 표현하지 않는다. 일반B0 491/900과 혼합563/900을 분리한다.

실패/차단: {"failed": null, "blocked": {}}. 게시 실패는 학습/평가 실패와 별개이며 로컬 보고서 보존 후 게시만 재시도한다.

공개파일은 설명·설정·집계·문항ID별 판정뿐이며 원본 QA/이미지/CAD/전체생성응답/adapter/인증정보를 포함하지 않는다. 원래 E123/E45 결과는 보존했다. 공식 파일 형식 확인: [Fusion 360 Gallery reconstruction 문서](https://github.com/AutodeskAILab/Fusion360GalleryDataset/blob/master/docs/reconstruction.md), [AI2D 공식 안내](https://prior.allenai.org/projects/diagram-understanding).
