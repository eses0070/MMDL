# E1 학습 완료 브리핑

학습 완료. 평가 점수는 아직 없음. GPU 작업은 순차 진행하며 E1 평가 후 E2, E3를 실행한다.

- 원본 모델: Qwen/Qwen3-VL-4B-Instruct, revision `ebb281ec70b05090aa6165b016eac8ec08e71b17`. 원본에서 독립 시작.
- 데이터: 공식 ChartQA train_human, revision `044eabfc306abfe9340c5741f0093aefc5973d06`, 새 seed3407 manifest의 1,000문항. 1 epoch, 250 optimizer updates. 과거 학습 샘플과 동일하다고 주장하지 않음.
- 학습: 원본 정답 SFT, teacher/KD 없음. BF16 language attention/MLP LoRA r16/alpha32/dropout0.05, vision/merger 동결. Micro batch1/accum4, AdamW lr1e-4/weight_decay0.01, warmup13 후 일정 LR, 길이4096, 이미지200704–1003520pixels, seed3407.
- 학습 시간: 208.96초. 프로세스 전체 230.31초.
- 첫/마지막 업데이트 평균 loss: 4.426011 / 0.199937. 서로 다른 문항의 batch loss이므로 일반화 성능이나 정확도 개선의 증거로 해석하지 않음.
- Peak CUDA allocated: 10.37GiB; reserved: 15.97GiB.
- 체크포인트 저장 완료. 별도 프로세스 재로드 및 정답 없는 입력으로 3건 생성 검증 완료. 이 검증은 최대8토큰의 실행 검사이며 benchmark 점수가 아님.
- 코드 HEAD: `98ea8cc5e1fa9cb62f78451ff5e7e77057bcdcec`; 실제 수정 코드는 run의 파일별 hash inventory에 기록됨.
- 데이터 기록 SHA256: `83961d5bf9629692b807b56af5869852078609cbb8db99700512d00c53458616`. Adapter SHA256: `7af7976ccd261a22fd5c20cc65a080a070b27507c61d8bac230942ab6dc0efb8`.
- 실행 명령: `/home/user/mmdl-work/.venv-restore-train/bin/python /home/user/mmdl-work/code/restore/run.py --stage train --experiment E1`.

MMMU900 평가에는 별도 고정8192토큰/49152 context 및 과거 프롬프트·샘플링·반복 감지·GT-blind parser를 적용한다. B0는 저장 응답 재채점491/900이고 과거 혼합563/900과 구분한다. 현재 정확도, 과목별·답 추출·중단률 비교는 미완료.

전체 조건/환경/manifest/전처리·mask 검사/명령/실패 로그/체크포인트 hash는 해당 run 기록에 보존됨. E1 본 학습에서 OOM이나 실행 오류는 발생하지 않았음. 사전 환경 오류와 중단된 진단 평가 기록은 별도 run에 보존됨.

## 최종 평가 업데이트

이 문서의 위 내용은 학습 완료 시점의 브리핑이다. 이후 E1 MMMU900 평가가 완료되어482/900(53.56%)을 기록했다. 동일 채점 B0491/900보다1.00pp 낮다. E2/E3 및 source 점검셋 비교까지 완료됐으며 [최종 비교](FINAL_BRIEF_KO.md)에 결과가 있다.
