# NoWait — MMMU 미추출 문항 재추론

기존 Qwen3-VL-4B-Instruct 베이스라인에서 [Parser v2](parser_v2.md) 적용 후에도 최종 답을 추출하지 못한 객관식 40문항에 NoWait을 적용했다. 이 문항들은 과거 응답이 모두 8,192토큰 한도에서 종료된 사례다. 재추론 결과 **정답 8건을 추가로 확인했다.**

## 적용 방법

[NoWait 논문](https://aclanthology.org/2025.findings-emnlp.394/)의 방식을 참고해, 답변 생성 중 `wait`, `hmm` 등 자기검토 표현과 관련된 토큰의 선택을 억제했다. [미추출 목록](../../experiments/parser_v2/results/verified_parser_v2/remaining.jsonl)의 40문항 전체를 재추론하고, Qwen3-8B Judge와 최종 답 추출 규칙으로 선택지를 채점했다.

## 결과

| MMMU validation 집계 | 정답 수 | 정확도 |
| --- | ---: | ---: |
| 기존 베이스라인 · Parser v2 반영 | 568 / 900 | 63.11% |
| 미추출 40문항에 NoWait 재추론 반영 | **576 / 900** | **64.00%** |
| 증가분 | **+8건** | **+0.89%p** |

NoWait을 적용한 40문항의 채점 결과를 기존 860문항의 판정과 합산했다. 채점 보류 2문항은 정답 수에 포함하지 않았다.

| 비교 범위 | 기존 저장 응답 | NoWait 재추론 | 생성 토큰 감소율 |
| --- | ---: | ---: | ---: |
| 재추론 대상 40문항 | 327,680 | 245,360 | 25.12% |
| NoWait에서 정답을 확인한 8문항 | 65,536 | 24,995 | 61.86% |

[실행 기록](https://github.com/Hyeonjin1/mmdl/blob/13257042f002d58b575ed4f99dd4d797277486f9/runs/20261123_lab_backup/NOWAIT_REPORT_KO.md) · [문항별 토큰 집계](https://github.com/Hyeonjin1/mmdl/blob/13257042f002d58b575ed4f99dd4d797277486f9/runs/20261123_lab_backup/nowait-input-audit.json)
