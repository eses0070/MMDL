# 혼합 채점의 점수 변화 원인 감사

기존 점수·응답·Judge 원문·checkpoint는 보존했다. **재학습·Student 답변 재생성·신규 Judge 추론0회**이며 CPU에서 저장 로그와 당시 코드를 재생·감사했다. 시작 시 RTX4090은 display18MiB 외 compute 작업0개, 기존 mixed controller는 completed, tmux 실행 없음이었다. 원격 main과 로컬 시작 commit은 `b65417e662b7af92dcd879a15e893c974c985630`로 일치했다.

## 핵심 판단

B0 상승과 학습 모델 탈락에는 서로 다른 채점 경로의 영향이 크다. 학습 모델 탈락151모델–문항 쌍 중 **150건은 원문에 공식GT와 일치하는 명시적 최종 선택지/내용이 있음**을 확인했다(전체 짧은 원문 또는 동일내용 대표 검토). 나머지1건 L1 `validation_Electronics_18`은 앞선 답 뒤 재고와 다른 후보가 이어져 최종 의도를 확정하지 않았다. 기계적 경로148건을 모두 무조건 채점 결함으로 단정하지 않은 이유다.

B0의 추가 정답74건은 명시적 답 회수/동등표현62건, 정밀도 해석3건, 재고·중간답 채택 또는 검토 유보9건으로 나뉜다. **적어도2건에서 Judge 스스로 최종 답이 없다고 인정하면서 답을 추정**했다. 과거563/900을 전부 정당한 형식 회수로 볼 수 없다. 이 감사에서 점수는 수정하지 않았다.

## 실제 검토 범위와 한계

자동 재현: 전체16조건×900 = **14,400모델–문항 쌍, 고유900문항**. 진단은 별도로18정책 시리즈×72 = **1,296정책–문항 기록**이며 학생 응답을 추가 생성한 수가 아니다. 총15,696기록의 원문·문항ID·GT·Judge·규칙·종료상태를 연결했다. Judge 원문15,262건과 정책상 반복 skip434건을 구분했고 원문 누락은0건이다.

실제 판독: 모델·GT·기존 판정을 숨긴247레코드를 먼저 검토하고 notes SHA256을 봉인한 후 Judge/GT를 연결했다. 이 중 **Student 전체125건, 끝900자 구간122건**이다. 추가 탈락85모델–문항 쌍은 전체 원문41대표 기록을 읽고 나머지44건을 동일 질문·선택지·Student·Judge 내용으로 연결했다. 따라서 직접 읽은 완전한 Student 대표 기록은 **166건**, 추가E4미해결2건·E5코드펜스2건을 포함한 구간 판독은 **126건**이다. 읽은 Judge 원문은247대상의240건 + 추가41대표 + E4/E5추가4건 = **285건**이며 반복정책7건에는 Judge 원문이 없다. 같은 텍스트가 다른 모델에서 반복된 경우를 고유 텍스트 수로 부풀리지 않았다.

B074추가+2탈락은 **76건 모두 최종 구간과 Judge를 대조**했지만 전체 풀이를 읽은 것은14건, 최종900자만 읽은 것은62건이다. 따라서 장문 전체 풀이·이미지 인식·모든 중간 모순을 검토 완료했다고 주장하지 않는다. 151학습 탈락은150건 전체 원문/정확한 동일내용 연결,1건 장문 구간과 재고 확인이다. E1탈락19·E5탈락12·LR_LOW_ANSWER탈락30은61건 모두 전체 Student와 Judge 원문을 읽었다. B0/L1 합집합93문항의 두 응답186건은 같은 질문 기준으로 최종 구간 또는 전체를 판독했다. 진단72는 이번 감사에서 자동 재생만 했으며 의미적 원문 전수 검토를 수행하지 않았다.

이 절차는 **이전 감사 맥락을 가진 AI assistant가 수행한 두 단계 마스킹 검토**다. 독립적인 인간 블라인드 패널이 아니며 일부 사례에 대한 사전 친숙함도 있다. 애매한 경우를 새 점수로 강제 확정하지 않았다. 원문 근거·char위치·sealed mapping은 로컬에만 있다.

## 점수 및 변화 독립 재현

| 모델 | 공통 | 혼합(확정/범위) | 추가 정답 | 탈락 | 공통 B0와 격차 | 혼합 B0와 격차 | 채점 선택에 따른 격차 변화 |
|---|---|---|---|---|---|---|---|
| B0 | 491 | 563 | 74 | 2 | 0 | 0 | 0 |
| E1 | 482 | 467 | 4 | 19 | -9 | -96 | -87 |
| E2 | 470 | 476 | 7 | 1 | -21 | -87 | -66 |
| E3 | 471 | 473 | 2 | 0 | -20 | -90 | -70 |
| E4 | 489 | 511–513 | 38 | 16 | -2 | 하한 -52 | -50 |
| E5 | 459 | 455 | 8 | 12 | -32 | -108 | -76 |
| E6-A | 460 | 458 | 17 | 19 | -31 | -105 | -74 |
| E6-B | 433 | 448 | 33 | 18 | -58 | -115 | -57 |
| E7 | 482 | 486 | 4 | 0 | -9 | -77 | -68 |
| LR_LOW_ANSWER | 463 | 446 | 13 | 30 | -28 | -117 | -89 |
| LR_LOW_SOLUTION | 478 | 504 | 34 | 8 | -13 | -59 | -46 |
| SPACE_ONLY_CONTROL | 485 | 489 | 4 | 0 | -6 | -74 | -68 |
| SPACE_RETENTION_MIX | 446 | 470 | 25 | 1 | -45 | -93 | -48 |
| L1 | 490 | 510 | 25 | 5 | -1 | -53 | -52 |
| L2 | 478 | 507 | 34 | 5 | -13 | -56 | -43 |
| L3 | 444 | 450 | 23 | 17 | -47 | -113 | -66 |

수치는 모두 /900이며 정확도는 metrics.json에 있다. E4는511–513/900(56.78–57.00%) 범위이고 확정 정확도가 아니다. 격차는 정답 수 단위다. 예: E1의 B0 격차가 −9에서−96으로 벌어진 추가−87은 같은 저장 응답에 채점법을 바꾼 효과다. 이 대수적 분해가 공통 파서의 완전한 타당성 또는 수정 점수를 보장하지는 않는다.

B0 추가74 = 정상종료 객관식50 + 길이종료 객관식8 + 주관식16이 실제 파일에서 일치했다. 15개 학습 조건의 탈락151건은 **고유 문항50개**에서 발생했다. Judge 미해결과 규칙 실패는 같은 사건의 연속 단계이므로 더하지 않는다.

## 학습 모델 탈락151건의 기계적 경로와 원문 판독

| 배타적 주 경로 | 모델–문항 쌍 | 원문 판독 결과 |
|---|---|---|
| MC status 오류 | 106 | correct102 + incorrect4; 추출기 대신 정오답 판정자로 행동한 경우 포함 |
| MC answer에 키 대신 키+내용/내용 | 34 | 키+내용28 + 내용만6 |
| JSON 유효하지만 uncertain 후 규칙 실패 | 8 | 7건 명시적 최종 선택지,1건 L1 재고·잘림 유보 |
| 유효한 Judge JSON이 다른 키에 대응 | 3 | 같은 고유문항1개, E6-A/E6-B/L3; 원문 내용과 선택지 매핑 오류 |

앞의106+34=140은 **JSON 문법 파싱 실패가 아니라 프로토콜/스키마 거부**다. 이151건 중 JSON 문법/코드펜스 오류는0건이다. 140출력오류 +8기타미해결 +3잘못된 매핑은 참고값과 일치한다. 이 중150건은 최종 선택지의 공식GT 일치가 원문으로 지지되며, 그 답에 이르는 풀이의 정확성까지 확인한 것은 아니다.

우선 전수 검토: E1 19건 = 잘못된status12 + 키+내용7. E5 12건 = 잘못된status7 + 키+내용4 + uncertain1. LR_LOW_ANSWER 30건 = 잘못된status19 + 키+내용10 + uncertain1. 세 조건61건 모두 명시적 최종 선택지의 공식GT 일치가 확인됐다. 일부 Judge는 선택지에 이미지 placeholder가 있다는 이유로 이미 제시된 선택지 키 추출을 거부했다. 실제 이미지 없이도 Student가 선택한 키를 추출할 수 있는 상황을 문제 풀이 실패와 혼동한 것이다.

최종 키가 맞아도 풀이가 틀릴 수 있다. E5 `validation_Mechanical_Engineering_20`과 LR_LOW_SOLUTION `validation_Manage_24`는 설명·계산과 최종 답 사이의 불일치가 보인다. 전자는 우선61건에, 후자는 추가 대표 검토에 포함됐다. 이것은 최종 답 채점 실패의 근거를 지우지 않지만 추론 능력 개선을 입증하지도 않는다.

## 모델별 Judge 오류 세분화

다음 열은 **비배타적**이다. 예를 들어 wrong status와 잘못된answer형식이 한 응답에 동시에 있을 수 있다. 서로 합산하지 않는다. primary의 배타적 분해와 문항형식별status/answer shape 분포는 metrics.json에 있다. 원시answer값 분포는 원문 노출 방지를 위해 로컬에만 보존했다.

| 모델 | JSON 문법/포장 실패 | MC 잘못된status | MC 키·내용 형식 위반 | uncertain | 미해결이나 읽을 수 있는 answer |
|---|---|---|---|---|---|
| B0 | 0 | 19 | 39 | 37 | 45 |
| E1 | 0 | 25 | 24 | 2 | 36 |
| E2 | 0 | 11 | 2 | 0 | 12 |
| E3 | 0 | 10 | 0 | 0 | 10 |
| E4 | 0 | 39 | 48 | 37 | 61 |
| E5 | 2 | 164 | 83 | 33 | 186 |
| E6-A | 0 | 33 | 35 | 2 | 39 |
| E6-B | 0 | 33 | 38 | 1 | 41 |
| E7 | 0 | 23 | 98 | 0 | 102 |
| LR_LOW_ANSWER | 0 | 38 | 41 | 4 | 57 |
| LR_LOW_SOLUTION | 0 | 81 | 61 | 27 | 99 |
| SPACE_ONLY_CONTROL | 0 | 21 | 88 | 0 | 93 |
| SPACE_RETENTION_MIX | 0 | 39 | 108 | 2 | 111 |
| L1 | 1 | 80 | 57 | 39 | 102 |
| L2 | 0 | 71 | 46 | 24 | 87 |
| L3 | 0 | 31 | 26 | 1 | 36 |

전체900군에서는 JSON 포장 실패가E5의 코드펜스2건, JSON 문법 실패가L1의 잘못된LaTeX escape1건이다. 필수키/추가키/이유타입 등 다른 schema 원인, 실제 범위 밖 키, null 등은 모델별 모든 비배타적원인을 JSON으로 보존했다. Judge 출력은 전체15,262호출 모두 stop이며 출력 길이 상한·비정상 종료·context초과·실행오류는 관측0건이다. Student의 길이종료와 Judge의 종료 상태를 혼동하지 않았다.

L1 `validation_Math_30`의 잘못된escape를 수리하기만 하면, 확정되지 않은 Student 출력에 대해 Judge가 만들어 낸 최종 선택지를 그대로 인정할 위험이 있다. 따라서 코드펜스 제거/JSON수리만으로 답변 충실성 문제가 해결된다고 주장하지 않는다. E5코드펜스2건은 내부JSON도uncertain이므로 단순포장 수리로 정답이 회수된다는 근거가 없다.

## 규칙 파서와 공통 파서의 차이

| 모델 | 규칙 대상 | 규칙 실패 | 마지막줄 문법 미인식 | 선택지본문 불일치 | 빈응답 | 범위밖 키 |
|---|---|---|---|---|---|---|
| B0 | 81 | 46 | 45 | 0 | 0 | 1 |
| E1 | 36 | 34 | 34 | 0 | 0 | 0 |
| E2 | 12 | 2 | 2 | 0 | 0 | 0 |
| E3 | 10 | 0 | 0 | 0 | 0 | 0 |
| E4 | 90 | 71 | 69 | 2 | 0 | 0 |
| E5 | 209 | 72 | 71 | 1 | 0 | 0 |
| E6-A | 41 | 34 | 34 | 0 | 0 | 0 |
| E6-B | 42 | 31 | 31 | 0 | 0 | 0 |
| E7 | 102 | 1 | 0 | 1 | 0 | 0 |
| LR_LOW_ANSWER | 57 | 56 | 56 | 0 | 0 | 0 |
| LR_LOW_SOLUTION | 123 | 53 | 51 | 1 | 0 | 1 |
| SPACE_ONLY_CONTROL | 93 | 1 | 0 | 1 | 0 | 0 |
| SPACE_RETENTION_MIX | 111 | 9 | 7 | 2 | 0 | 0 |
| L1 | 139 | 59 | 58 | 1 | 0 | 0 |
| L2 | 108 | 42 | 41 | 1 | 0 | 0 |
| L3 | 37 | 27 | 27 | 0 | 0 | 0 |

이 표는 실제 원본 extract_terminal의 반환 사유이며 의미적 실패 원인의 전수 판정이 아니다. 규칙 대상은 Judge 미해결 MC의 부분집합이고 규칙 실패도 그 부분집합이다. E4의 별도 주관식미해결2건은 여기 포함하지 않는다.

원본 terminal parser는 마지막 비어 있지 않은 줄을 대상으로 하며 `Final Answer:` 같은 답 접두어가 있는 키+내용은 처리하지만 **접두어 없는 키+내용 및 선택지 내용만 있는 답을 처리하지 못한다**. 학습 탈락151건의 공통 추출 method는 단일 짧은 키+내용92건, 명시적FinalAnswer 뒤 선택지 내용57건, 명시적키+내용2건이다. 마지막 줄 모양 분류와 이 method는 다른 기준이며 합산하지 않는다. 실제 Student 텍스트에 원본 terminal/common 함수를 모두 적용해 결과를 대조했다.

원인별 synthetic22검사는 실제 문항 검토와 분리했고 모두 통과했다. [합성 재현 기록](synthetic_reproductions.json)에는 bare key, key+content, content-only, boxed, 답 뒤 설명, 공백 차이, 재고, 다중줄수식, JSON상태/키/타입/코드펜스/escape/길이 조건이 포함된다. 합성 문자열은 실제 문제·선택지·답변에서 가져오지 않았다.

공통 파서도 결함이 있다. (1) 마지막 explicit answer를 찾은 뒤 나중의 재고를 확인하지 않아 이전 답을 채택할 수 있다. 실제 L1 `validation_Electronics_18`과 B0 `validation_Electronics_14`가 그 위험을 보인다. (2) 선택지 내용의 영어 접속사+단일문자를 여러 후보로 오인할 수 있다. (3) LaTeX/Unicode·추가문장·동등 선택지 표현을 exact option-content와 비교해 거부한다. (4) `Final Answer:` 다음 줄의 수식 delimiter를 답으로 잡는 사례가 있다. (5) 통화·단위·추가명사·지명 qualifier 및 정밀도 정책이 너무 엄격하거나 정의되지 않은 부분이 있다.

공통 경로는 원문 전체를 정규화하고, 혼합 Judge 입력은 마지막 `</think>` 뒤를 취한다. 이번 전체900기록14,400쌍에는 이태그가0개여서 이 차이는 **관측 점수 차이 원인이 아니다**. 공백/줄바꿈/LaTeX 차이는 실제 사례와 합성 검사를 구분해 기록했다. 반복중단은 두 경로 모두 원래 정책상 오답이며 모든 분모는900으로 유지했다. 길이종료는 자동오답이 아니고 실제 최종 답의 확정 여부와 별개로 다뤘다.

## B0 추가74건과 탈락2건의 두 단계 검토

| 분류 | 추가 정답 수 | 확인 범위 |
|---|---|---|
| A 명시적 답의 형식·표현 회수 | 54 | 선택지49 + 문장/수식/qualifier5; 최종 구간 관찰 |
| B 수치·분수·통화·단위/번호 동등표현 | 8 | 최종 답 존재, 추가 풀이 검증 아님 |
| C 정밀도·반올림 해석 | 3 | Judge 허용 기준 미고정; 팀원 정책 검토 필요 |
| D 재고·모순으로 의도 불명확 | 4 | 정상종료1 + 길이종료3 |
| E 중간 추론을 답으로 채택한 명시적 증거 | 2 | Judge 이유 자체가 명시적 최종 답 부재를 인정 |
| F 없는 답의 추론·보완 확정 | 확정하지 않음 | 전 구간을 읽지 않은 사례에서 배제할 수 없음 |
| G 현재 판독 범위로 확정 불가 | 3 | 모두 장문 길이종료; prefix 전체 판독 필요 |

A는 final extraction뿐 아니라 qualifier 때문에 공통 문자열 matching이 놓친 경우도 포함한다. 명시적 최종 답의 회수와 풀이의 참/거짓은 별개다. C의3건은 `validation_Electronics_12`, `validation_Finance_30`, `validation_Manage_25`이며 자동적인 허용오차 규칙으로 새 점수를 만들지 않았다. B0 탈락2건은 모두 D로 남겼다: `validation_Design_27`에는 MC status/answer 위반도 있지만 최종 답 이후 부정하는 주석이 있고, `validation_Electronics_14`는 선택지 언급 뒤 재고·잘림이 이어진다. 단순히 공통 파서가 맞혔으므로 혼합이 틀렸다고 확정하지 않았다.

### 길이종료 추가8건 전건

| 문항ID | 현재 분류 | 근거와 남은 범위 |
|---|---|---|
| validation_Accounting_15 | D | 다른 후보/재고/잘림; 전체prefix 미판독, 확정 유보 |
| validation_Architecture_and_Engineering_3 | E | Judge가 최종 답 부재를 인정하고 추정 |
| validation_Architecture_and_Engineering_6 | G | 다른 후보/재고/잘림; 전체prefix 미판독, 확정 유보 |
| validation_Architecture_and_Engineering_20 | G | 다른 후보/재고/잘림; 전체prefix 미판독, 확정 유보 |
| validation_Electronics_10 | E | Judge가 최종 답 부재를 인정하고 추정 |
| validation_Energy_and_Power_7 | D | 다른 후보/재고/잘림; 전체prefix 미판독, 확정 유보 |
| validation_Mechanical_Engineering_13 | D | 다른 후보/재고/잘림; 전체prefix 미판독, 확정 유보 |
| validation_Mechanical_Engineering_25 | G | 다른 후보/재고/잘림; 전체prefix 미판독, 확정 유보 |

길이종료만으로 틀렸다고 판정하지 않았다. 정답 문자열 등장 여부로 답을 인정하지도 않았다. E2건은 `validation_Electronics_10`, `validation_Architecture_and_Engineering_3`다. 나머지6건은 앞선 답/잠정 값이 존재할 가능성을 포함해 추가 검토가 필요하다. 8건 전체 응답을 처음부터 끝까지 독해했다는 뜻은 아니다.

## B0와 L1 동일 문항 대응

공통↔혼합이 달라진 두 모델의 ID합집합은93개이며 총186응답을 대응했다. 이 표본은 채점불일치를 의도적으로 모은 편향 표본이므로 전체 능력 변화 비율로 확장하지 않는다.

| 원문 대응 분류 | 문항 수 |
|---|---|
| both_unsettled_or_truncated | 9 |
| same_explicit_option_scoring_or_format_difference | 48 |
| clear_B0_correct_final_option_changed_to_L1_wrong_option | 3 |
| same_explicit_open_answer_scoring_or_format_difference | 11 |
| unsettled_B0_to_clear_L1_not_causal_gain | 5 |
| open_unit_precision_or_numeric_form_difference | 4 |
| clear_B0_to_unsettled_L1_completion_loss | 8 |
| clear_final_answer_content_changed_L1_not_matching_GT | 3 |
| different_place_names_alias_scope_uncertain | 1 |
| clear_final_answer_content_changed_L1_matching_GT | 1 |

같은 명시적 최종 답은59문항(객관식48+주관식11)에서 보인다. 한편 명확한 B0 정답이 L1의 다른 최종 답으로 바뀐 사례도6문항(객관식3+주관식3) 있어 실제 답변 오류 변화가 모두 채점 탓인 것은 아니다. 반대 방향의 명확한 최종 답 개선1건도 확인했다. 숫자·단위·정밀도4건 및 지명 alias범위1건은 별도 비교다. clear→unsettled8, unsettled→clear5, both-unsettled9를 지식 소실/회복으로 단정하지 않는다.

명확한 최종 답 내용 변화: L1 불일치 방향은 `validation_Art_17`, `validation_Marketing_15`, `validation_Mechanical_Engineering_29`, `validation_Finance_20`, `validation_Finance_25`, `validation_Psychology_20`; 반대 방향은 `validation_Manage_23`다. 내부 기록에는 두 모델의 짧은 원문 근거·문자 위치·원본 파일과 response hash가 있다. 이미지·문제 전문은 공개하지 않았다.

Judge의 과도한 추정은 B0에만 있는 문제가 아니다. 일부 L1 장문에서도 끝에서 확정되지 않은 답을 Judge가 확정했다고 주장한다. 반대로 B0의 정확한 대수식 표현을 주관식 Judge가 수치표현과 다르다는 이유로 거부한 사례도 있다. 따라서 결과를 모델 이름에 대한 일방적 우대/차별로 해석하지 않는다. 모든 MC task에 모델명 필드와GT가 없고 같은 시스템/설정이었다는 prompt hash를 CPU에서 확인했다. 출력 길이와 오류율의 관련성은 관찰적이며 인과관계가 아니다.

## E4 미해결2건

`validation_Architecture_and_Engineering_14`, `validation_Electronics_21` 모두 주관식이다. Student는 길이종료, Judge는 정상stop과 유효JSON의uncertain/null이다. Judge input은 각각8995/8886토큰으로32768context 초과가 아니며 Judge 실행/JSON 오류도 아니다. 규칙은 MC에만 적용되므로 미해결을 유지한다. **511–513/900 범위**를 보존하고 새 Judge 호출이나 임의오답 처리를 하지 않았다.

## 유지할 결론·보류할 결론과 최소 후속 검증

유지 가능: 동일 저장 응답에 대한 기존 점수와 변화 재현;150건의 명시적GT일치 답이 채점 경로에서 탈락한 사실; B0의 다수 형식/동등표현 회수; 최소2건의 Judge 추출 지침 위반; 같은 문항의 명확한 최종 답 변화도 일부 존재한다는 관찰.

보류: 혼합점수 격차만으로 학습 모델의 추론/지식 저하 크기를 정량화하는 결론, B0추가74건 모두의 정당성, precision3건과 장문확정유보의 최종 판정, 길거나 짧은 답변이 오류를 유발했다는 인과 주장, 이번93문항을900문항 전체 능력의 대표로 보는 주장. LoRA 활성화 시 답변 변화가 비가역적인 지식 소실임을 주장하지 않는다.

최소 다음 검증은 새 모델 추론보다 **원문 기반 독립 팀원 판독**이다: B0의 길이종료8건·정상종료 재고1건·탈락2건·precision3건, L1 Electronics18, 대수/소수 동등성 및 지명 alias범위를 우선 확정한다. 그 뒤 합성/source 개발 문항으로 parser/schema 개선안을 검증하고 새 채점 버전으로 별도 산출해야 한다. 이번에는 아무 정책도 적용하지 않았다.

## 수정안과 가정 계산

[수정 제안](PROPOSED_POLICY.md)은 실행 당시 코드 위치와 synthetic 재현을 명시한다. 원본 코드는 그대로다. hypothetically148개 미해결후규칙실패를 무조건 회수하면 그중 최종 의도가 불명확한 L1사례도 회수하므로 정당한 수정 점수가 아니다. 전수 판독에서 지지된150건을 더하는 것도 **GT와 검토에 의존한 가정 계산**일 뿐 배포 가능한 파서의 성능으로 제시하지 않는다. JSON을 수리하거나status를강제치환하는 것만으로 문제를 해결할 수 없다.

## 출처·보존·재현

입력 보고서 commit `b65417e662b7af92dcd879a15e893c974c985630`, 역사적 코드 commit `0c0b415f6f93923a4249d3da32c5cbb447a518ea`. Judge Qwen3-8B revision `b968826d9c46dd6066d109eabc6255188de91218`; non-thinking/temperature0/512/context32768, engine seed3407, sampling seed는 당시 기본값None. 실행 wrapper·원본score/task/규칙/strict parser hash를 실제 실행 계약과 대조했다. 15,262개 task와 tokenizer chat prompt hash를 저장 기록과 재구성 비교했고 모두 일치했다. 공통 parser의 간접 dependency인 scoring_v2.py는 Judge계약에서 직접 pin되지 않았으므로 보존된 Student 실행 provenance와 대조하고 전 문항 기존 판정 일치로 보완했다. 이 출처상의 한계를 settings.json에 명시했다.

로컬 감사 폴더: `.restore/mixed_mechanism_audit_v1_20261017/`. `records_private.jsonl`, `blind_records.jsonl`, `pass1_notes.jsonl`, `pass1_seal.json`, `sealed_mapping_PRIVATE.json`, `trained_loss_full_review_PRIVATE.json`, `B0_L1_pairs_PRIVATE.json`에 원문·근거·범위를 보존했다. 실험 원본·기존 공식 점수/보고서·checkpoint는 변경하지 않았다. 공개 파일에는 전체 문제·선택지·GT·Student/Judge 원문·이미지·가중치·인증정보가 없다.

CPU 재현 명령(모델 실행 없음):
```bash
cd /home/user/mmdl-work
/home/user/mmdl-work/.venv-restore-eval/bin/python .restore/mixed_mechanism_audit_v1_20261017/reproduce.py
```
