# 저장 응답 전체 혼합 채점 감사

상태: **completed**. 재학습·adapter 변경·Student 답변 재생성 없이 저장 응답만 사용한다.

## 역사적 B0 기록 재현

저장 Judge 판정 + 당시 terminal-rule 코드를 CPU 재생하여 **563/900 (62.56%)**을 재현했다. 기존 정답537 + 규칙 회수26, 기존 판정819건 보존 + 미해결 객관식81건 규칙 처리, 반복 중단53, 규칙 추출 실패46이다. 이는 기존 판정 기록의 재현이며 새 Judge 실행 재현과 구분한다. 초기 Transformers493/900은 사용하지 않았다. 새 Judge B0가 산출되면 아래 동시 배치 비교의 기준으로 쓰며 역사적563점은 별도 보존한다.

## 고정 절차

Qwen3-8B snapshot `b968826d9c46dd6066d109eabc6255188de91218`, non-thinking, temperature0, 출력512, context32768. 당시 코드의 system prompt·task 구성·JSON 파싱·에러 처리를 그대로 사용한다. sampling seed는 당시처럼 별도 지정하지 않고 engine seed3407을 사용한다. 입력 초과는 자르지 않고 미해결로 남긴다. 반복 중단은 Judge 호출 없이 정책상 오답이다.

객관식 Judge에는 GT 없이 질문·실제 선택지·Student 응답을 전달하고 추출 키를 코드에서 GT와 비교한다. 주관식 Judge에는 당시 정책대로 accepted_answers를 제공하므로 이 단계는 정답 독립적 추출이 아니다. Judge 미해결 객관식에만 당시 `rescore_mc_rules.py` 마지막 비어 있지 않은 줄 규칙을 적용한다. 추출 실패는 정책상 오답이나 answer_correct=null/parse_success=false를 보존한다. 미해결 주관식은 미해결로 남기며 전체 정확도를 확정하지 않고 하한·상한을 제공한다. 전체 응답에서 GT 문자열을 검색하거나 여러 후보 중 GT를 인정하는 규칙을 추가하지 않았다. latest_vllm_final_v2는 비교용 기존 채점으로만 사용하며 혼합 규칙을 대체하지 않는다.

## 전체 MMMU 900문항

모든 원문900개 및 고유 ID·정답 매핑을 B0와 대조했다. source 점검·파일럿·중간 checkpoint는 포함하지 않았다. 아래 미완료는0점이 아니다.

| 실험 | 공통 파서 | 혼합 | 동일 혼합 B0 대비 pp | 새 정답 | 새 오답 | Judge 미해결 | 규칙 회수 정답 | 추출 실패 | 반복 중단 |
|---|---|---|---|---|---|---|---|---|---|
| B0 | 491/900 (54.56%) | 563/900 (62.56%) | 0.0 | 0 | 0 | 81 | 26 | 46 | 53 |
| E1 | 482/900 (53.56%) | 467/900 (51.89%) | -10.666666666666666 | 91 | 187 | 36 | 1 | 34 | 0 |
| E2 | 470/900 (52.22%) | 476/900 (52.89%) | -9.666666666666666 | 85 | 172 | 12 | 4 | 2 | 0 |
| E3 | 471/900 (52.33%) | 473/900 (52.56%) | -10.0 | 90 | 180 | 10 | 4 | 0 | 0 |
| E4 | 489/900 (54.33%) | 511 확정 / 900; 미해결 2 | None | 58 | 110 | 92 | 12 | 73 | 51 |
| E5 | 459/900 (51.00%) | 455/900 (50.56%) | -12.0 | 69 | 177 | 209 | 59 | 72 | 12 |
| E6-A | 460/900 (51.11%) | 458/900 (50.89%) | -11.666666666666666 | 89 | 194 | 41 | 5 | 34 | 0 |
| E6-B | 433/900 (48.11%) | 448/900 (49.78%) | -12.777777777777779 | 80 | 195 | 42 | 7 | 31 | 0 |
| E7 | 482/900 (53.56%) | 486/900 (54.00%) | -8.555555555555555 | 83 | 160 | 102 | 75 | 1 | 0 |
| LR_LOW_ANSWER | 463/900 (51.44%) | 446/900 (49.56%) | -13.0 | 83 | 200 | 57 | 1 | 56 | 0 |
| LR_LOW_SOLUTION | 478/900 (53.11%) | 504/900 (56.00%) | -6.555555555555555 | 59 | 118 | 123 | 34 | 53 | 67 |
| SPACE_ONLY_CONTROL | 485/900 (53.89%) | 489/900 (54.33%) | -8.222222222222221 | 87 | 161 | 93 | 67 | 1 | 0 |
| SPACE_RETENTION_MIX | 446/900 (49.56%) | 470/900 (52.22%) | -10.333333333333334 | 89 | 182 | 111 | 72 | 9 | 0 |
| L1 | 490/900 (54.44%) | 510/900 (56.67%) | -5.888888888888889 | 61 | 114 | 139 | 44 | 59 | 68 |
| L2 | 478/900 (53.11%) | 507/900 (56.33%) | -6.222222222222222 | 62 | 118 | 108 | 36 | 42 | 63 |
| L3 | 444/900 (49.33%) | 450/900 (50.00%) | -12.555555555555555 | 84 | 197 | 37 | 4 | 27 | 0 |

## 진단 72문항

오류 사례를 강화한 고정72문항이며 전체 MMMU 결과로 환산할 수 없다. G1/G2의 A는 첫 단계 출력과 원래 반복 중단 정책, B는 실제 최종화 단계가 있으면 그 출력 구간만 사용한 결과다. B는 답 판정 절차는 같지만 생성·종료 정책이 달라진 조건이다. 정답을 보고 단계를 선택하거나 답을 합치지 않는다.

| 조건 | 종료 정책 | 공통 파서 | 혼합 | 대응 비교군 | 차이 pp | 새 정답 | 새 오답 | 실제 최종화 수 |
|---|---|---|---|---|---|---|---|---|
| B0_G0 | historical_stop | 23/72 | 32/72 (44.44%) | B0_G0__historical_stop | 0.0 | 0 | 0 | 0 |
| L1_G0 | historical_stop | 27/72 | 32/72 (44.44%) | B0_G0__historical_stop | 0.0 | 7 | 7 | 0 |
| B0_G1 | original_stop_A | 23/72 | 32/72 (44.44%) | B0_G0__historical_stop | 0.0 | 0 | 0 | 8 |
| B0_G1 | finalization_B | 25/72 | 34/72 (47.22%) | B0_G0__historical_stop | 2.7777777777777777 | 2 | 0 | 8 |
| L1_G1 | original_stop_A | 34/72 | 35/72 (48.61%) | L1_G0__historical_stop | 4.166666666666667 | 9 | 6 | 2 |
| L1_G1 | finalization_B | 36/72 | 37/72 (51.39%) | L1_G0__historical_stop | 6.944444444444445 | 10 | 5 | 2 |
| B0_G2 | original_stop_A | 23/72 | 32/72 (44.44%) | B0_G0__historical_stop | 0.0 | 0 | 0 | 12 |
| B0_G2 | finalization_B | 29/72 | 38/72 (52.78%) | B0_G0__historical_stop | 8.333333333333334 | 6 | 0 | 12 |
| L1_G2 | original_stop_A | 31/72 | 32/72 (44.44%) | L1_G0__historical_stop | 0.0 | 8 | 8 | 10 |
| L1_G2 | finalization_B | 34/72 | 35/72 (48.61%) | L1_G0__historical_stop | 4.166666666666667 | 10 | 7 | 10 |
| B0_P1 | historical_stop | 26/72 | 34/72 (47.22%) | B0_G0__historical_stop | 2.7777777777777777 | 9 | 7 | 0 |
| L1_P1 | historical_stop | 30/72 | 35/72 (48.61%) | L1_G0__historical_stop | 4.166666666666667 | 12 | 9 | 0 |
| P2_CONTROL | historical_stop | 37/72 | 37/72 (51.39%) | B0_G0__historical_stop | 6.944444444444445 | 13 | 8 | 0 |
| P2_READ | historical_stop | 31/72 | 34/72 (47.22%) | P2_CONTROL__historical_stop | -4.166666666666667 | 9 | 12 | 0 |
| K1_CONTROL | historical_stop | 33/72 | 33/72 (45.83%) | B0_G0__historical_stop | 1.3888888888888888 | 12 | 11 | 0 |
| K1_PAIRED | historical_stop | 36/72 | 36/72 (50.00%) | K1_CONTROL__historical_stop | 4.166666666666667 | 3 | 0 | 0 |
| R1_CONTROL | historical_stop | 35/72 | 41/72 (56.94%) | B0_G0__historical_stop | 12.5 | 14 | 5 | 0 |
| R1_CHECK | historical_stop | 32/72 | 37/72 (51.39%) | R1_CONTROL__historical_stop | -5.555555555555555 | 7 | 11 | 0 |

## 범위·해석 및 남은 작업

L1 G1/G2는 G0와 첫 단계부터 달라진 사례가 있다는 기존 FINAL_AUDIT를 보존한다. 혼합 점수 차이 전체를 최종 답 전환의 인과효과로 해석하지 않는다. 같은 응답의 A↔B 비교와 G0 대비 비교를 분리한다. 과목별 정답·오답률과 객관식/주관식 지표는 metrics.json/subject_metrics.csv에 있다. 신뢰할 수 있는 기존 작업 유형 매핑은 미확보이며 과목명으로 공학/재무/수학/공간 유형을 추정하지 않는다. 최종 답의 정확도는 풀이의 정확도를 보장하지 않는다.

불일치 표본은 실행 전 고정 seed3407·조건/방향/문항형식별 최대2개·hash순서로 선정한다. 형식 차이 회수·주관식 동등성 인정·Judge가 중간 추론을 최종 답으로 오인할 가능성을 검토하되 표본 검토로 주 점수를 수정하지 않는다. 완료된 수동 검토는 별도 감사 기록에 명시하며 미실시 표본을 검토 완료로 주장하지 않는다.

응답·모델·코드 hash와 실행 계약은 로컬 `.restore/mixed_all_v1/`에 보존한다. 전체 원문·Judge 원문·GT·이미지·adapter는 공개하지 않는다. 공개 CSV는 문항 ID와 판정·오류 분류만 포함한다. 이번 작업은 단일 Judge 환경의 재채점이며 추론 개선 실험이 아니다.

[기준 보고서](https://github.com/eses0070/MMDL/blob/0c0b415f6f93923a4249d3da32c5cbb447a518ea/assignment/reports/mmmu_baseline_vllm_cot_rules.md) · [원본 채점 코드](https://github.com/eses0070/MMDL/tree/0c0b415f6f93923a4249d3da32c5cbb447a518ea/code/MMDL-official-vllm)

## 역사적 B0 불일치 수동 검토

사전 고정 hash 순서로 고른6건을 실제 저장 Student 출력과 Judge JSON으로 검토했다. 명시적 최종 선택지의 형식 회수2건, 단위 표현 동등성1건, 정밀도 차이 허용1건, MC Judge 스키마 위반 후 마지막 줄 규칙 실패1건, 재고·잘림으로 최종 확정이 불분명한 응답1건이다. 정밀도 차이 허용은 Judge의 완화 가능성이 있고, MC 스키마 위반은 형식상 올바른 답도 규칙에서 놓칠 수 있다. 어느 주 판정도 수정하지 않았다. 상세 ID와 관찰은 historical_manual_review.json에 있다. 이는 역사적 B0 기록 표본이며 새 Judge 배치 표본과 구분한다.

## 새 Judge 소규모 점검

사전 고정 16사례: 역사적 Judge와 정오답/미해결 상태 차이 0개, 혼합 판정 차이 0개, Judge 원문 차이 1개. task 일치 여부 True. 드라이버·GPU·Python 환경 차이를 보존하며 프롬프트를 기존 판정에 맞춰 수정하지 않는다.

## 채점 방식에 따른 결론 변화

| 조건 | 비교군 | 공통 파서 정답 순변화 | 혼합 정답 순변화 | 방향 변화 |
|---|---|---|---|---|
| B0__historical_stop | B0__historical_stop | 0 | 0 | False |
| E1__historical_stop | B0__historical_stop | -9 | -96 | False |
| E2__historical_stop | B0__historical_stop | -21 | -87 | False |
| E3__historical_stop | B0__historical_stop | -20 | -90 | False |
| E4__historical_stop | B0__historical_stop | -2 | None | None |
| E5__historical_stop | B0__historical_stop | -32 | -108 | False |
| E6-A__historical_stop | B0__historical_stop | -31 | -105 | False |
| E6-B__historical_stop | B0__historical_stop | -58 | -115 | False |
| E7__historical_stop | B0__historical_stop | -9 | -77 | False |
| LR_LOW_ANSWER__historical_stop | B0__historical_stop | -28 | -117 | False |
| LR_LOW_SOLUTION__historical_stop | B0__historical_stop | -13 | -59 | False |
| SPACE_ONLY_CONTROL__historical_stop | B0__historical_stop | -6 | -74 | False |
| SPACE_RETENTION_MIX__historical_stop | B0__historical_stop | -45 | -93 | False |
| L1__historical_stop | B0__historical_stop | -1 | -53 | False |
| L2__historical_stop | B0__historical_stop | -13 | -56 | False |
| L3__historical_stop | B0__historical_stop | -47 | -113 | False |
| B0_G0__historical_stop | B0_G0__historical_stop | 0 | 0 | False |
| L1_G0__historical_stop | B0_G0__historical_stop | 4 | 0 | True |
| B0_G1__original_stop_A | B0_G0__historical_stop | 0 | 0 | False |
| B0_G1__finalization_B | B0_G0__historical_stop | 2 | 2 | False |
| L1_G1__original_stop_A | L1_G0__historical_stop | 7 | 3 | False |
| L1_G1__finalization_B | L1_G0__historical_stop | 9 | 5 | False |
| B0_G2__original_stop_A | B0_G0__historical_stop | 0 | 0 | False |
| B0_G2__finalization_B | B0_G0__historical_stop | 6 | 6 | False |
| L1_G2__original_stop_A | L1_G0__historical_stop | 4 | 0 | True |
| L1_G2__finalization_B | L1_G0__historical_stop | 7 | 3 | False |
| B0_P1__historical_stop | B0_G0__historical_stop | 3 | 2 | False |
| L1_P1__historical_stop | L1_G0__historical_stop | 3 | 3 | False |
| P2_CONTROL__historical_stop | B0_G0__historical_stop | 14 | 5 | False |
| P2_READ__historical_stop | P2_CONTROL__historical_stop | -6 | -3 | False |
| K1_CONTROL__historical_stop | B0_G0__historical_stop | 10 | 1 | False |
| K1_PAIRED__historical_stop | K1_CONTROL__historical_stop | 3 | 3 | False |
| R1_CONTROL__historical_stop | B0_G0__historical_stop | 12 | 9 | False |
| R1_CHECK__historical_stop | R1_CONTROL__historical_stop | -3 | -4 | False |

불일치 표본 자동 감사 138건. 분류: {"terminal_rule_policy_failure_or_explicit_wrong": 34, "judge_final_intent_extraction_without_rule_parseable_terminal_review_needed": 44, "judge_open_equivalence_acceptance": 48, "same_explicit_terminal_format_recovery_or_strict_parser_difference": 12}. 이는 저장 텍스트의 마지막 답과 Judge 추출 키 비교 감사이며 사람의 전 사례 의미 검토를 대신하지 않는다. 중간 추론 오인 가능성 플래그는 확정 판정이 아니다. 표본의 주 점수는 수정하지 않았다. 상세는 discrepancy_samples.json에 있다.
