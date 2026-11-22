# 파서 v2 — MMMU 객관식 재채점

저장된 Qwen3-VL 응답 중, 기존에 최종 답을 추출하지 못한 객관식 46개를 다시 처리했다. **6개에서 답을 추출했고 4개가 GT와 일치하여 전체 점수가 564/900에서 568/900으로 바뀌었다.**

[코드와 실행 방법](../../experiments/parser_v2/README.md) · [상세 결과·과목별 표](../../experiments/parser_v2/results/verified_parser_v2/comparison.md) · [추출된 6개](../../experiments/parser_v2/results/verified_parser_v2/recovered.jsonl)

| 항목 | 이전 | 파서 v2 적용 후 |
|---|---:|---:|
| 전체 정답 | 564/900 | **568/900** |
| 전체 정확도 | 62.67% | **63.11%** |
| 원래 미해결 객관식 81개 중 추출 완료 | 35개 | **41개** |
| 남은 미추출 객관식 | 46개 | **40개** |

이번 대상은 객관식 46개다. 주관식 53개와 이미 추출한 객관식 35개를 포함한 나머지 854개는 변경하지 않았다.

## 환경·재현

Python 3.10 이상, 기본 라이브러리만 사용한다. 저장된 모델 응답과 Qwen3-8B judge 응답을 재사용하므로 새 VLM 추론, 새 judge 호출, GPU 사용, 유료 API 호출은 없다. CPU 테스트 69개와 Git 배포 폴더에서의 재실행으로 검증했다.

```bash
cd experiments/parser_v2
python3 -B -m unittest discover -s tests -p 'test_*.py' -v
python3 -B replay.py --limit 0 --output-dir results/mc46_run1
```

## 채점 방식

최종 답을 GT 없이 추출한 뒤 각 선택지와 대응한다. 숫자·단위·백분율은 이전 AE의 정확한 수량 비교 규칙을 사용한다. 규칙으로 충분하지 않으면 원래 Qwen3-8B 응답의 답 제안과 모델 원문의 명시적 최종 선택이 일치하는지 검사한다. 과거 judge의 `correct/incorrect` 판정을 그대로 재사용하지 않는다. 추출한 선택지 키를 확정한 다음에만 GT와 비교한다.

실제 회복된 6개는 문자·선택지 내용 대응 2개와 저장 judge 제안/최종 답 근거 확인 4개다. **숫자 환산으로 새롭게 해결된 문항은 0개**이며, 수량 비교기 자체의 성능 향상으로 해석하지 않는다.

| 문항 | 추출 | GT | 판정 |
|---|---|---|---|
| Agriculture_12 | D | A | 오답 |
| Basic_Medical_Science_17 | A | A | 정답 |
| Biology_3 | A | A | 정답 |
| Design_27 | C | C | 정답 |
| Diagnostics_and_Laboratory_Medicine_30 | C | D | 오답 |
| Psychology_21 | D | D | 정답 |

## 남은 문제·한계

40개는 모두 원래 생성이 토큰 한도로 끊겨 자동 추출을 보류했다. 원문에 최종 답이 전혀 없다고 검증한 것은 아니다. `answer_correct=null`로 미추출을 구분하지만 기존 정책대로 전체 점수에서는 오답으로 센다.

이 평가는 **최종 답 채점**이며 풀이·이미지 해석의 타당성을 검증하지 않는다. 공식 MMMU 채점 또는 judge 정확도 측정도 아니다. 실제 사례를 확인한 뒤 일반 규칙을 작성한 만큼, 새로운 데이터에서의 추출 정확도와 잘못된 수용 여부는 별도로 검증해야 한다. 문항별 예외는 넣지 않았다.

기존 과제 보고서와 코드·결과는 보존하고 이번 결과를 별도 추가했다.
