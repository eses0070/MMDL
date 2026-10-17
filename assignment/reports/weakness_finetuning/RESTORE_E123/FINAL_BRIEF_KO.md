# E1·E2·E3 최종 비교

세 실험의 학습·재로드·MMMU900 및 점검셋 평가가 완료됐다. 세 실험 모두 동일 채점 B0보다 전체 정확도가 낮았다.

| 모델 | MMMU 정답/900 | 정확도 | B0 대비 |
|---|---:|---:|---:|
| B0 (저장 응답 재채점) |491|54.56%|—|
| E1 |482|53.56%|-1.00pp|
| E2 |470|52.22%|-2.33pp|
| E3 |471|52.33%|-2.22pp|

| 모델 | ChartQA 점검/100 | TabMWP 점검/100 | PGPS9K 점검/100 |
|---|---:|---:|---:|
| original_source_checks | 37 | 81 | 63 |
| E1 | 56 | 66 | 45 |
| E2 | 52 | 76 | 41 |
| E3 | 54 | 54 | 49 |

B0는 원본 MMMU 재추론 없이 과거 vLLM900 응답을 고정 파서로 재채점한491/900이다. 기존 혼합563/900을 보존하며, 초기493/900은 사용하지 않았다. 점검셋 원본300문항 추론은 MMMU 원본 재추론과 다르다.

E1=ChartQA1000; E2=E1 중 ChartQA500+TabMWP500; E3=PGPS9K1000. 각 실험은 원본 모델에서 독립 시작했으며 teacher/KD 없이 원본 정답 SFT를 수행했다. 각250업데이트/1epoch, BF16 LoRA r16/alpha32/dropout0.05, micro1/accum4, lr1e-4, seed3407. 정확한 조건과 revision·manifest hash는 [config.json](config.json)에 있다.

평가: 각900 MMMU validation + source별100문항. 동일8192 출력토큰 상한,49152 context, 원본 프롬프트·이미지·샘플링·반복 감지·파서를 적용했다. 학습 모델의 길이 제한·반복 중단은 세 실험 모두0건이었다. 파싱 실패는 E1=12,E2=14,E3=0건으로 B0=130건보다 줄었지만 정확도는 개선되지 않았다.

단일 seed이며 validation 개발 비교다. 새로 재구성한 학습 샘플은 과거 샘플과 동일성이 확인되지 않았다. 검토된 과거 오답 유형 라벨이 없어 기존 유형별·비대상 유형별 변화는 제공하지 않는다. 과목별·객관식/주관식 결과는 [metrics.json](metrics.json)에 별도 보존한다.

사전 환경 오류: inherited SciPy/scikit-learn 등 NumPy ABI 충돌을 별도 평가 venv에서 수정했다. SciPy1.15.3은 과거 기록과 일치한다. vLLM0.11.2가 GPU UUID를 정수로 파싱하는 문제는 단일 GPU 확인 후 숫자 인덱스로 지정해 해결했다. 긴 smoke 평가를 학습 우선 진행을 위해 한 차례 중단하고 별도 재실행을 완료했다. 모든 실패/중단 로그는 로컬에 보존했다. 드라이버·타인의 프로세스·원본 데이터는 변경하지 않았다.

가벼운 문항별 판정은 [question_decisions.csv](question_decisions.csv), 개선/퇴행 문항 개수는 [paired_changes.json](paired_changes.json), 실행 출처와 체크포인트 hash는 [provenance.json](provenance.json)에 있다. 원문 질문·이미지·정답·전체 생성 응답과 adapter는 게시하지 않는다.
