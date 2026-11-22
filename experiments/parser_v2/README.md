# 파서 v2

MMMU의 저장된 응답을 사용해 **남은 객관식 46개**를 재채점합니다. 숫자·단위·백분율은 규칙으로 비교하고, 필요한 경우 저장된 Qwen3-8B의 답 제안을 원문 근거와 대조합니다.

## 결과

| 항목 | 결과 |
|---|---:|
| 원래 미해결 객관식 | 81개 |
| 이전 규칙으로 추출한 문항 | 35개 |
| 이번 대상 | 남은 46개 |
| 새로 답 추출 성공 | **6개: 정답 4개, 오답 2개** |
| 남은 미추출 | **40개** |
| 전체 정답 수 | **564 → 568 / 900** |
| 전체 정확도 | **62.67% → 63.11%** |
| 대상 밖 854개 변경 | 0개 |
| 새 VLM 추론 / 새 judge 호출 | 0 / 0 |

[과제 보고서](../../assignment/reports/parser_v2.md) · [실제 실행 결과](results/verified_parser_v2/comparison.md) · [과목별 수치](results/verified_parser_v2/summary.json)

이번에 새로 해결된 것은 **최종 답 추출·선택지 대응 문제**입니다. 문자/내용 대응으로 2개, 저장 judge 제안과 명시적 원문 근거 확인으로 4개를 추출했습니다. 숫자 환산 경로로 새롭게 해결된 문항은 0개입니다.

## 실행

Python 3.10 이상과 기본 라이브러리만 필요합니다. GPU, vLLM, 모델 다운로드, pip 설치, API 키는 필요 없습니다. 입력 응답과 판정 파일을 포함했습니다.

저장소를 처음 받는다면:

```bash
git clone --branch seokmin https://github.com/eses0070/MMDL.git MMDL-seokmin
cd MMDL-seokmin/experiments/parser_v2
```

이미 저장소의 `seokmin` 브랜치에 있다면 저장소 루트에서:

```bash
cd experiments/parser_v2
```

1. 테스트합니다.

```bash
python3 -B -m unittest discover -s tests -p 'test_*.py' -v
```

69개 테스트가 통과해야 합니다. 숫자 비교 테스트 36개와 객관식 추출·재채점 테스트 33개입니다. 생성한 질량·백분율 쌍 480개, GT를 바꿔도 추출 결과가 같은지, 비대상 문항과 기존 파일을 보존하는지도 확인합니다.

2. 파일을 만들지 않고 결과를 미리 확인합니다.

```bash
python3 -B replay.py --dry-run --limit 0 --output-dir results/mc46_run1
```

3. 전체를 새 폴더에 재채점합니다.

```bash
python3 -B replay.py --limit 0 --output-dir results/mc46_run1
```

`--limit 0`은 대상 46개 전체입니다. `--limit 3`이면 앞 3개만 검사합니다. 출력에는 기존 판정과 합친 전체 900개가 들어갑니다. 같은 출력 폴더가 이미 있으면 중단하므로, 재실행할 때는 `results/mc46_run2`처럼 새 이름을 쓰세요.

4. 결과를 읽습니다.

```bash
cat results/mc46_run1/comparison.md
python3 -B inspect_item.py --result-dir results/mc46_run1
```

문항 원문과 근거를 확인하려면:

```bash
python3 -B inspect_item.py --result-dir results/mc46_run1 --id validation_Basic_Medical_Science_17 --show-response
```

## 처리 방식

1. 기존 900개 응답·판정의 해시와 ID, 질문, 선택지, GT를 검사합니다. 원래 미해결 81개 중 현재도 `parse_success=false`인 객관식 46개만 선택합니다.
2. 길이 제한·반복 중단·context 제한이 있는 생성은 새 답 추출을 보류합니다.
3. 정상 종료 응답에서 최종 답을 추출합니다. `A. increase`는 실제 선택지 A의 내용과 대조합니다. `E`가 선택지 키에 없지만 선택지 A의 내용이 E라면 A로 대응합니다. 키와 그림 라벨이 겹쳐 모호하면 보류합니다.
4. 숫자 답은 각 선택지 내용과 정확한 수량 비교를 합니다. 예를 들어 `2500 g`와 `2.5 kg`를 대응합니다. 가장 가까운 숫자로 찍거나, GT에서 누락 단위를 가져오지 않습니다. 여러 선택지가 동치이면 보류합니다.
5. 규칙만으로 추출하지 못하면 저장된 Qwen3-8B judge의 `answer` 필드를 답 제안으로 사용합니다. 원문에 명시적인 최종 선택이 있고 해당 제안과 일치해야 합니다. 최종 답 뒤의 `Note:`는 새로운 선택이나 철회가 없는지 제한된 검사를 거칩니다. 단순히 judge의 기존 정오 판정을 복원하지 않습니다.
6. **선택지 키 추출이 끝난 뒤에만 GT와 비교**합니다. 추출 함수에는 GT, 문항 ID, 이전 정오를 전달하지 않습니다.

`frozen/numeric_rules.py`는 이전 AE 수량 비교기와 동일합니다. 객관식 추출·선택지 대응은 이번에 추가했습니다. 임의 수식, 제곱근, 반올림/허용 오차, 모호한 단위, 문자열 부분 일치를 무리하게 수용하지 않습니다.

## 파일

- `mc_parser.py`: GT 없는 추출, 선택지 대응, 저장 judge 제안의 근거 확인.
- `replay.py`: 입력 검증, 대상 선택, 재채점과 전체 결과 병합.
- `inspect_item.py`: 원문·추출 근거 조회.
- `inputs/`: 저장된 모델 응답, 현재 판정, 원래 judge 판정과 설정.
- `frozen/`: 변경하지 않은 AE 숫자 규칙과 과거 도우미.
- `tests/`: CPU 테스트.
- `results/verified_parser_v2/`: 검증한 실제 결과. 새 실행 결과는 별도 폴더에 저장합니다.
- `PROVENANCE.json`, `input_integrity.json`, `PUBLICATION.json`: 출처, 해시, 이번 Git 배포 기록.

각 결과 폴더에는 `judgments.jsonl`(900개), `audit.jsonl`(46개), `recovered.jsonl`(새 추출), `changed_verdicts.jsonl`(정오 변화), `remaining.jsonl`(보류), `summary.json`, `comparison.md`, `run_config.json`이 있습니다. 변경된 레코드 안에도 이전 레코드를 보존합니다.

원래 ZIP에서 검증한 결과와 프로토콜 식별자는 이력 확인을 위해 보존했습니다. Git에서의 폴더·문서 이름은 **파서 v2 (`parser_v2`)**입니다. 코드 모듈의 표시 이름과 실행 안내만 Git 배포에 맞췄으며 재채점 논리는 변경하지 않았습니다.

## 한계

- 남은 40개는 모두 `finish_reason=length`라 자동 추출을 보류했습니다. **원문 어디에도 최종 답이 없다는 판정은 아닙니다.** 불완전한 풀이에서 답을 고르지 않으려는 정책입니다.
- 미추출은 `parse_success=false`, `answer_correct=null`로 구분하지만 기존 점수 정책대로 `correct=false`로 집계합니다. `scoring_unresolved=0`이 추출 실패 0개를 뜻하지 않습니다.
- 최종 답 채점입니다. 선택지가 GT와 같다고 풀이·시각적 근거까지 맞았다는 뜻은 아니며 `reasoning_correct=null`입니다.
- 실제 응답 6개의 형식을 확인한 뒤 일반 규칙을 작성했습니다. 문항별 예외는 없지만 처음 보는 데이터의 일반화 성능이나 judge 정확도를 검증한 실험은 아닙니다.
- 저장 judge와 인용 확인은 최소한의 신뢰도 검사입니다. 완벽한 의미 검증이나 공식 MMMU 평가라고 주장하지 않습니다.
- 대상 밖 854개와 보류 40개는 원본 JSONL 레코드 바이트까지 보존했습니다. 과거 코드·결과와 기존 과제 보고서를 덮어쓰지 않습니다.
