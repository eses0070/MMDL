# 기존 정책을 바꾸지 않은 수정 제안

주점수·원본코드는변경하지않았다. 문제ID·모델명·GT를이용한예외규칙을제안하지않는다. 합성22검사의실행결과는synthetic_reproductions.json에있다.

- 역사적 run.py의 judge/score: JSON wrapper 오류, schema 오류, uncertain, 실행/context 실패를 별도 상태로 남길 것. 미래 Judge 생성에는 실제 선택지 키enum과 matched/uncertain schema를 사용할 수 있으나 이번에는 실행하지 않았다. correct/incorrect를무조건matched로치환하지말고 Student의실제선택근거·최종span을검증해야한다.
- rescore_mc_rules.py:12 extract_terminal: 단독키는통과하지만 접두어없는 `B. blue`, 내용만있는 `blue`, boxed답은실패한다. 개선안은유일한최종span에서실제선택지와일치하는표현을허용하되이후재고·모순을별도검출하는것이다. suffix를무조건삭제하거나이전답을마지막답으로삼지않는다.
- code/p04/scoring_latest_v2.py: candidate/extract: Final Answer 다음 수식delimiter만반환하는경우를명시적수식block/boxed에서추출하고, 선택지내용중 `and a` 같은정상문구를복수답으로오인하는정규식을선택지키영역으로제한하는변경을개발셋에서검증할것. 선택지본문일치검사를통째로제거하지않는다.
- open normalization: 숫자/차원/통화/의미별동등표현과허용정밀도를사전에문서화할것. 단위를모두버리거나큰허용오차를전역추가하지않는다. 실제GT에맞춰튜닝하지않는다.
- 원래반복정책과최종화정책을혼합하지않고분모·미해결·실행오류를보존할것. 원문과실제최종구간의근거없는Judge추론은JSON이유효해도안전하지않다.

어느제안도이번관측점수에적용하지않았다. 새버전의점수영향은독립개발검증후전체저장응답을동일정책으로재채점한별도결과여야한다.
