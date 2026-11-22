# 파서 v2 재채점

대상 46/46 검사. 새 모델 추론·judge 호출 0.

| 항목 | 결과 |
|---|---:|
| 기존 규칙이 해결한 MC81 중 문항 | 35 |
| 이번에 새로 답 추출 | 6 |
| 새 추출 중 정답 / 오답 | 4 / 2 |
| 아직 추출하지 못한 객관식 | 40 |
| 전체 기존 점수 | 564/900 (62.67%) |
| 전체 새 점수 | 568/900 (63.11%) |

미추출은 기존 정책대로 점수에서는 오답입니다. scoring_unresolved=0이어도 모든 답이 추출된 것은 아닙니다.
정답 판정은 최종 선택지 문자와 GT의 일치만 뜻합니다. 풀이가 타당하다는 판정이 아닙니다.

| 경로 | 문항 수 |
|---|---:|
| generation_guard | 40 |
| cached_qwen_supported | 4 |
| diagram_label_as_option_content | 1 |
| letter_with_literal_content | 1 |

## 과목별 결과

| 과목 | 이전 정답 | 이후 정답 / 문항 수 | 이후 정확도 % |
|---|---:|---:|---:|
| Accounting | 23 | 23/30 | 76.67 |
| Agriculture | 15 | 15/30 | 50.00 |
| Architecture_and_Engineering | 15 | 15/30 | 50.00 |
| Art | 20 | 20/30 | 66.67 |
| Art_Theory | 26 | 26/30 | 86.67 |
| Basic_Medical_Science | 22 | 23/30 | 76.67 |
| Biology | 19 | 20/30 | 66.67 |
| Chemistry | 11 | 11/30 | 36.67 |
| Clinical_Medicine | 18 | 18/30 | 60.00 |
| Computer_Science | 18 | 18/30 | 60.00 |
| Design | 22 | 23/30 | 76.67 |
| Diagnostics_and_Laboratory_Medicine | 10 | 10/30 | 33.33 |
| Economics | 25 | 25/30 | 83.33 |
| Electronics | 13 | 13/30 | 43.33 |
| Energy_and_Power | 14 | 14/30 | 46.67 |
| Finance | 21 | 21/30 | 70.00 |
| Geography | 17 | 17/30 | 56.67 |
| History | 21 | 21/30 | 70.00 |
| Literature | 25 | 25/30 | 83.33 |
| Manage | 21 | 21/30 | 70.00 |
| Marketing | 25 | 25/30 | 83.33 |
| Materials | 14 | 14/30 | 46.67 |
| Math | 18 | 18/30 | 60.00 |
| Mechanical_Engineering | 11 | 11/30 | 36.67 |
| Music | 10 | 10/30 | 33.33 |
| Pharmacy | 25 | 25/30 | 83.33 |
| Physics | 23 | 23/30 | 76.67 |
| Psychology | 20 | 21/30 | 70.00 |
| Public_Health | 24 | 24/30 | 80.00 |
| Sociology | 18 | 18/30 | 60.00 |
