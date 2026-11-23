# NoWait — MMMU 미추출 문항 재추론

과거 팀 B0에서 8,192토큰 한도에 도달했고 [Parser v2](parser_v2.md)로도 최종 답을 추출하지 못한 객관식 40문항을 재추론했다.

| 조건 | 확인된 정답 | 채점 보류 | 생성 토큰 | 과거 B0 대비 감소율 |
| --- | ---: | ---: | ---: | ---: |
| 과거 팀 B0 | 0/40 | — | 327,680 | — |
| NoWait | 8/40 | 2 | 245,360 | 25.12% |
| NoWait · 차단 목록 정제 | 8/40 | 2 | 244,736 | 25.31% |
| **NoWait · 4,096토큰 답안 전환** | **19/40** | **1** | **143,648** | **56.16%** |

NoWait은 자기검토 관련 토큰을 생성 중 억제한다. 답안 전환 방식은 풀이가 4,096토큰 한도에 도달하면 원래 이미지와 기존 풀이를 다시 제시하고 최종 선택지 하나를 요청한다. 29문항에서 전환이 발동했다.

후속 실험의 정답 19건은 NoWait 정답을 유지한 8건, NoWait에서 채점 보류였던 2건, 새로 맞힌 9건이다. 채점 보류 1건은 정답 수에서 제외했다. 토큰은 40문항 전체의 생성량이며 재요청 입력은 포함하지 않는다.

[미추출 문항 목록](../../experiments/parser_v2/results/verified_parser_v2/remaining.jsonl) · [NoWait 상세 보고서](https://github.com/Hyeonjin1/mmdl/blob/experiment-backup-20261123/runs/20261123_lab_backup/NOWAIT_REPORT_KO.md) · [답안 전환 상세 보고서](https://github.com/Hyeonjin1/mmdl/blob/experiment-backup-20261123/runs/20261123_lab_backup/nowait-followup/experiment.md)
