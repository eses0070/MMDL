# 공유 폴더 파일 안내

검토 범위: 이 `weakness_finetuning/` 폴더에 게시한 파일만. 원본 실습컴이나 다른 저장소의 추가 자료는 이번 점검에서 열람하지 않았다.

## 권장 읽기 순서

1. [README.md](README.md): 목적, 학습 조건, 전체 결과와 한계.
2. 관심 있는 실험 폴더의 한국어 최종 보고서: 의도·데이터·과정.
3. [전체 혼합 채점](RESTORE_MIXED_ALL_v1/REPORT_KO.md): 최종 공통/혼합 비교.
4. [원인 감사](MIXED_MECHANISM_AUDIT_v1_20261017/REPORT_KO.md): 혼합 점수 차이의 해석.
5. 수치를 확인할 때 해당 CSV·metrics·settings와 [점검 기록](REVIEW_NOTES.md).

과거 보고서의 미완료 상태는 그 시점의 기록이다. 최신 점수는 `RESTORE_MIXED_ALL_v1`, 채점 원인의 후속 검토는 `MIXED_MECHANISM_AUDIT_v1_20261017`을 우선한다. 후속 감사는 점수를 수정하지 않았다.

## 최상위 파일

| 파일 | 역할 |
|---|---|
| [README.md](README.md) | 팀 공유용 전체 개요 보고서 |
| [FILE_GUIDE.md](FILE_GUIDE.md) | 현재 안내: 파일 역할·읽는 순서·집계 기준 |
| [REVIEW_NOTES.md](REVIEW_NOTES.md) | 이번 점검 결과·수정 사항·공개본의 한계 |
| [SOURCE_MANIFEST.json](SOURCE_MANIFEST.json) | 원본53개 파일의 출처/해시, 공유본 편집 내역, 안내 문서 해시 |
| [.gitattributes](.gitattributes) | Git의 자동 줄바꿈 변경을 막아 기록 파일 바이트를 유지 |

## E1·E2·E3: 데이터 종류 비교

`RESTORE_E123`

| 파일 | 역할 |
|---|---|
| [FINAL_BRIEF_KO.md](RESTORE_E123/FINAL_BRIEF_KO.md) | 처음 읽을 한국어 최종 비교. E1~E3의 목적·결과·한계. |
| [REPORT.md](RESTORE_E123/REPORT.md) | 동일 실험의 영어 종합 기록. |
| [E1_TRAINING_BRIEF.md](RESTORE_E123/E1_TRAINING_BRIEF.md) | E1 학습 완료 당시 브리핑과 후속 평가 안내. |
| [HOST_RUN.md](RESTORE_E123/HOST_RUN.md) | 당시 실습컴 환경·실행 순서·문제 해결 기록. 현재 폴더에서 곧바로 실행하는 설명서가 아님. |
| [config.json](RESTORE_E123/config.json) | 학습 및 평가 설정. |
| [environment_versions.json](RESTORE_E123/environment_versions.json) | 학습·평가 환경의 라이브러리 버전. |
| [metrics.json](RESTORE_E123/metrics.json) | B0·E1~E3 점수, 자체 점검, processor 검증. |
| [paired_changes.json](RESTORE_E123/paired_changes.json) | B0 대비 새 정답·새 오답 수. |
| [provenance.json](RESTORE_E123/provenance.json) | 실행 ID·코드·설정·데이터·어댑터 출처와 해시. |
| [question_decisions.csv](RESTORE_E123/question_decisions.csv) | B0·E1~E3의 MMMU900 문항별 공통 파서 판정. 3,600행(헤더 제외). |

## E4·E5: 학습률과 공식 풀이

`RESTORE_E45`

| 파일 | 역할 |
|---|---|
| [REPORT_KO.md](RESTORE_E45/REPORT_KO.md) | 학습률 감소와 공식 풀이 추가의 대응 비교. |
| [metrics.json](RESTORE_E45/metrics.json) | 점수·통제 조건·데이터 동일성·풀이 검증·실행 출처. 별도 settings 파일 대신 설정 근거도 포함. |
| [output_sample_review.json](RESTORE_E45/output_sample_review.json) | 선정한 출력 표본의 검토 기록. 전 문항 의미 검토로 일반화하지 않음. |
| [question_decisions.csv](RESTORE_E45/question_decisions.csv) | MMMU와 자체 점검 결과; dataset 필터 필요. 7,200행(헤더 제외). |

## E6-A·E6-B·E7: 과학 도식·CAD

`RESTORE_E67`

| 파일 | 역할 |
|---|---|
| [REPORT_KO.md](RESTORE_E67/REPORT_KO.md) | 과학 도식 혼합과 CAD 상면도 대응 실험의 결과. |
| [settings.json](RESTORE_E67/settings.json) | 실험별 학습·타깃·평가 조건. |
| [metrics.json](RESTORE_E67/metrics.json) | 학습·가공·점수·CAD 렌더링·출처 검사. |
| [question_decisions.csv](RESTORE_E67/question_decisions.csv) | MMMU 및 자체 점검의 공통 파서 판정. 12,000행(헤더 제외). |
| [mixed_question_decisions.csv](RESTORE_E67/mixed_question_decisions.csv) | 이 단계의 혼합 판정 기록. 모든 실험의 최종 비교는 RESTORE_MIXED_ALL_v1을 사용. 8,100행(헤더 제외). |

## 학습률·풀이·유지 데이터 혼합

`RESTORE_RETENTION_v1`

| 파일 | 역할 |
|---|---|
| [REPORT_KO.md](RESTORE_RETENTION_v1/REPORT_KO.md) | 저학습률 두 조건 및 CAD 집중/유지 혼합 비교. |
| [settings.json](RESTORE_RETENTION_v1/settings.json) | 각 조건과 고정 평가·체크포인트·분할 설정. |
| [metrics.json](RESTORE_RETENTION_v1/metrics.json) | 최종 점수·중간 궤적·노출량·학습 자원·출처. |
| [question_decisions.csv](RESTORE_RETENTION_v1/question_decisions.csv) | 기존 대조군과 새 조건의 최종/중간 점검. model·update·dataset을 함께 구분. 12,900행(헤더 제외). |

## L1·L2·L3: 학습량 확대

`RESTORE_L123_v1`

| 파일 | 역할 |
|---|---|
| [REPORT_KO.md](RESTORE_L123_v1/REPORT_KO.md) | 반복 학습·고유 문항 확대·작업 혼합 비교. |
| [settings.json](RESTORE_L123_v1/settings.json) | 독립 초기화·학습 설정·manifest 및 코드 해시. |
| [metrics.json](RESTORE_L123_v1/metrics.json) | 학습·최종 점수·개발 궤적·토큰 길이·데이터 분포. |
| [question_decisions.csv](RESTORE_L123_v1/question_decisions.csv) | 63/250/500/750 업데이트 점검과 최종 MMMU. 기존 점검과 _new 점검을 구분. 14,700행(헤더 제외). |

## 진단72: G/P/K/R 실험

`RESTORE_DIAGNOSIS_v1`

| 파일 | 역할 |
|---|---|
| [REPORT_KO.md](RESTORE_DIAGNOSIS_v1/REPORT_KO.md) | G0/G1/G2/P1 및 P2/K1/R1의 목적과 결과. |
| [settings.json](RESTORE_DIAGNOSIS_v1/settings.json) | 72문항·파일럿·전환 규칙·이미지 확대·학습 조건. |
| [metrics.json](RESTORE_DIAGNOSIS_v1/metrics.json) | 생성·학습 진단·자체 점검·실패/완료 상태. |
| [FINAL_AUDIT.json](RESTORE_DIAGNOSIS_v1/FINAL_AUDIT.json) | 첫 단계 응답 차이, 읽기 타깃, 토큰 비용, 천장효과의 후속 확인. |
| [question_decisions.csv](RESTORE_DIAGNOSIS_v1/question_decisions.csv) | 12문항 파일럿·72문항 진단·자체 점검이 섞인 기록; run·dataset 필터 필요. 2,669행(헤더 제외). |

## 전체 저장 응답의 혼합 채점

`RESTORE_MIXED_ALL_v1`

| 파일 | 역할 |
|---|---|
| [REPORT_KO.md](RESTORE_MIXED_ALL_v1/REPORT_KO.md) | 전체900과 진단72를 같은 역사적 혼합 정책으로 채점한 종합 결과. |
| [settings.json](RESTORE_MIXED_ALL_v1/settings.json) | Judge·wrapper·원본 코드·응답 해시와 채점 계약. |
| [metrics.json](RESTORE_MIXED_ALL_v1/metrics.json) | 전체 결과·B0 재현·조건별 비교·미해결 수. |
| [question_decisions.csv](RESTORE_MIXED_ALL_v1/question_decisions.csv) | 16개 전체900 조건 및 18개 진단72 정책의 판정. 전체 비교의 기본 CSV. 15,696행(헤더 제외). |
| [subject_metrics.csv](RESTORE_MIXED_ALL_v1/subject_metrics.csv) | 조건·과목별 집계. 과목을 작업 유형으로 해석하지 않음. 804행(헤더 제외). |
| [discrepancy_samples.json](RESTORE_MIXED_ALL_v1/discrepancy_samples.json) | 사전 규칙으로 고른 불일치 표본138건의 자동 감사. |
| [historical_manual_review.json](RESTORE_MIXED_ALL_v1/historical_manual_review.json) | 역사적 B0 불일치6건의 당시 검토; 후속 감사 결과와 함께 읽음. |

## 혼합 채점 차이의 원인 감사

`MIXED_MECHANISM_AUDIT_v1_20261017`

| 파일 | 역할 |
|---|---|
| [REPORT_KO.md](MIXED_MECHANISM_AUDIT_v1_20261017/REPORT_KO.md) | 명시적 정답 탈락·B0 과잉 인정·wrapper 및 규칙 점검 결론. |
| [REVIEW_STATUS.md](MIXED_MECHANISM_AUDIT_v1_20261017/REVIEW_STATUS.md) | 실제로 읽은 범위와 추가 팀원 검토가 필요한 부분. |
| [PROPOSED_POLICY.md](MIXED_MECHANISM_AUDIT_v1_20261017/PROPOSED_POLICY.md) | 개선 채점 정책의 제안. 기존 결과에 적용 완료된 정책이 아님. |
| [settings.json](MIXED_MECHANISM_AUDIT_v1_20261017/settings.json) | 입력 파일·코드·실행 계약·CPU 재생의 출처. |
| [metrics.json](MIXED_MECHANISM_AUDIT_v1_20261017/metrics.json) | 정답 변화·오류 경로·검토 범위의 집계. |
| [model_item_audit.csv](MIXED_MECHANISM_AUDIT_v1_20261017/model_item_audit.csv) | 16조건×900문항의 Judge/규칙 경로별 자동 감사. 14,400행(헤더 제외). |
| [trained_loss_review.csv](MIXED_MECHANISM_AUDIT_v1_20261017/trained_loss_review.csv) | 학습15조건의 공통 정답→혼합 오답151쌍 검토. 고유 문항151개가 아님. 151행(헤더 제외). |
| [B0_review.csv](MIXED_MECHANISM_AUDIT_v1_20261017/B0_review.csv) | B0 채점 불일치76건의 검토 범위·분류·유보 사항. 76행(헤더 제외). |
| [B0_L1_pairs.csv](MIXED_MECHANISM_AUDIT_v1_20261017/B0_L1_pairs.csv) | B0/L1 불일치 관련93문항의 최종 답 비교. 전체900의 대표 표본이 아님. 93행(헤더 제외). |
| [diagnostic_summary.json](MIXED_MECHANISM_AUDIT_v1_20261017/diagnostic_summary.json) | 진단72의 별도 집계; 전체900 감사에 합산하지 않음. |
| [synthetic_reproductions.json](MIXED_MECHANISM_AUDIT_v1_20261017/synthetic_reproductions.json) | 가상 답안으로 확인한 파서/규칙 동작 사례. 모델 능력 평가가 아님. |

## 이전 혼합 채점 재현 이력

`MIXED_SCORING_AUDIT_20261011`

| 파일 | 역할 |
|---|---|
| [REPORT_KO.md](MIXED_SCORING_AUDIT_20261011/REPORT_KO.md) | B0 혼합563 재현과 당시 E1~E3 Judge 기록 부족 상태. |
| [metrics.json](MIXED_SCORING_AUDIT_20261011/metrics.json) | 당시 재현·설정 검사·미확보 상태의 집계. |
| [question_decisions.csv](MIXED_SCORING_AUDIT_20261011/question_decisions.csv) | B0 및 당시 E1~E3 기록. 최신 혼합 최종 비교 자료와 구분. 3,600행(헤더 제외). |

## CSV 집계 기준

| 목적 | 파일과 필터 |
|---|---|
| 전체900 공통·혼합 비교 | `RESTORE_MIXED_ALL_v1/question_decisions.csv`: `scope=full900`, `condition=<모델>__historical_stop`. 조건별900개 고유 ID |
| 진단72 공통·혼합 비교 | 같은 CSV에서 `scope=diagnostic72`. G1/G2 최종화 결과는 `__finalization_B`; 자체 첫 단계는 `__original_stop_A` |
| L123 최종 공통 점수 | `RESTORE_L123_v1/question_decisions.csv`: `dataset=MMMU`, `update=750`, `model=L1/L2/L3` |
| Retention 최종 공통 점수 | `RESTORE_RETENTION_v1/question_decisions.csv`: `dataset=MMMU`, 새4조건은 `update=250`. 참조 E7은112 |
| E45/E67 공통 점수 | 각 `question_decisions.csv`: `dataset=MMMU`, 비교할 `model` |
| E123 공통 점수 | `RESTORE_E123/question_decisions.csv`: `model`별900행; dataset 열 없음 |
| 기존 진단 공통 판정 | `RESTORE_DIAGNOSIS_v1/question_decisions.csv`: `dataset=MMMU`, 정확한 `run` 선택. 각 run은72행 |
| 과목별 혼합 결과 | `RESTORE_MIXED_ALL_v1/subject_metrics.csv`: 동일한 `condition`을 먼저 선택; 전체900과 진단72의 분모가 다름 |

- CSV의 `True`/`False`는 문자열이므로 명시적으로 비교한다. 빈 셀은 미확정으로 보존한다.
- E4의 `mixed_correct` 빈 셀2개는 확정 오답이 아니다. 확정 정답511, 가능한 정답 범위511~513, 분모900을 함께 보고한다.
- `judge_unresolved=True`는 Judge 단계의 미해결을 뜻한다. 객관식은 후속 규칙으로 해결될 수 있으므로 이것을 최종 미해결 수로 합산하지 않는다. 최종 판정은 `mixed_correct`를 확인한다.
- 정답률(%) = 정답 수 ÷ 해당 평가 분모 ×100. B0 대비 변화는 같은 채점·같은 문항·같은 정책의 정답률 차이(pp)다.
- `historical_stop`은 원래 반복 중단 정책, `original_stop_A`는 해당 G1/G2 실행의 첫 단계, `finalization_B`는 최종 답 출력 단계까지 적용한 결과다. A와 B는 별도 문항 집합이 아니므로 합산하지 않는다.
- `_new` 자체 점검셋과 기존 점검셋, 중간 체크포인트와 최종 모델을 합산하지 않는다. L123에 B0 독립 행이 없어도 `B0_correct`로 대응 판정을 확인할 수 있다.
- `parse_failure`, 반복 중단, 명시적 오답과 `finish_reason=length`는 같은 분류 축이 아니다. 길이 종료는 다른 항목과 겹칠 수 있으므로 단순 합산하지 않는다.

## 이 묶음으로 확인 가능한 범위

목표·설정·학습 기록·문항별 정오·점수 변화·출처를 검토하고 집계를 재계산할 수 있다. 원문 Student/Judge 응답 전체와 원본 정답·이미지·어댑터·실행 코드가 모두 포함되어 있지는 않으므로, 새로운 파서를 적용한 원문 재채점이나 재학습의 완전 재현에는 별도 실행 자료가 필요하다.

보고서 안의 `/home/user/...`와 `.restore/...`는 당시 실습컴 경로다. `source_sha256`는 원본 파일, `published_sha256`는 안내 문구를 포함한 현재 게시 파일을 가리킨다. 해시가 있다는 사실만으로 그 실행 파일을 이 폴더에서 다운로드할 수 있는 것은 아니다.
