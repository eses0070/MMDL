# CoT 압축 비교 실험

브랜치: `seokmin`

시작일: 2026-11-20 (KST)

목표는 정답률을 유지하면서 풀이 길이를 줄일 때, Teacher가 간결하게 수정한
CoT를 SFT하는 방법과 GSPO 보상으로 길이를 줄이는 방법을 비교하는 것이다.
현재 구현은 **환경 점검과 vLLM 합성 이미지 3문항 실행 확인**까지다.
Teacher, 외부 학습 데이터, SFT 및 GSPO trainer는 아직 정하지 않았고 실행하지 않았다.
기존 baseline 코드, 보고서, 결과는 이 폴더에서 수정하지 않는다.

## 폴더

```text
experiments/cot_compression/
  README.md          # 진행 상태, 실행 방법, 비교 계획
  preflight.py       # 환경 및 실제 CUDA 연산 점검; 설치/다운로드 없음
  smoke_vllm.py      # Qwen3-VL-4B의 이미지 추론 실행 확인
  test_smoke_cli.py  # CPU에서 preview와 기존 결과 보존 검사
  runs/              # 실행 기록; Git 제외
  data/              # 이후 외부 학습 데이터; Git 제외
  adapters/          # 이후 학습 산출물; Git 제외
```

## 1. 실습실 작업 위치

학교 안내에 따라 호스트에서는 `~/shared_dir`, 컨테이너에서는 `/shared_dir` 아래에
코드·데이터·결과를 둔다. 컨테이너 밖에서 설치한 venv가 컨테이너에서도 동작한다고
가정하지 않는다. 실제 실행할 터미널에서 `which python`과 CUDA 점검을 수행한다.
현재 동작하는 venv는 이동하지 않는다. 디렉터리 이동으로 venv 내부 경로가 깨질 수 있다.
`shared_dir`도 배정 종료 후 삭제되므로 시간 안에 결과를 회수한다.

이미 활성화된 venv에서 시작한다. 아래는 **호스트** 기준이며 컨테이너라면
`$HOME/shared_dir`를 `/shared_dir`로 바꾼다. 이미 같은 디렉터리가 있으면 덮어쓰지 말고
그 checkout의 변경 사항과 브랜치를 먼저 확인한다.

```bash
mkdir -p "$HOME/shared_dir/mmdl"
cd "$HOME/shared_dir/mmdl"
git clone --branch seokmin --single-branch https://github.com/eses0070/MMDL.git MMDL-cot-compression
cd MMDL-cot-compression/experiments/cot_compression
python -B preflight.py
```

추론 패키지 기준: torch 2.9.0+cu128, vLLM 0.11.2, Transformers 4.57.1,
qwen-vl-utils 0.0.14, Pillow, huggingface-hub. 이미 동작하는 환경에서 무조건 재설치하지 않는다.
`peft`, `trl`, `datasets`는 현황만 표시하며 이 smoke 실행의 필수 조건은 아니다.
SFT/GSPO 학습 환경의 호환성은 이후 별도로 검증한다.

## 2. 소규모 vLLM 실행 확인

```bash
python -B smoke_vllm.py --dry-run
```

이 명령은 설정을 출력할 뿐 모델 다운로드·GPU 실행·파일 생성을 하지 않는다.
실제 테스트는 빨강·파랑·초록의 합성 이미지에서 색을 읽게 한다. 원본 모델의
고정 revision `ebb281ec70b05090aa6165b016eac8ec08e71b17`을 사용한다.

```bash
# 호스트 기준. 컨테이너에서는 /shared_dir/hf-cache로 지정한다.
export HF_HOME="$HOME/shared_dir/hf-cache"
python -B smoke_vllm.py --output-dir runs/smoke3_20261120
```

첫 실제 실행은 모델 가중치를 다운로드할 수 있다. 기존 캐시를 재사용하려면
실제 cache 위치를 HF_HOME으로 지정하거나 기존 HF_HOME을 유지한다.
일반적인 GPU 사용률·가중치 로드·이미지 전처리·vLLM kernel 실행까지 확인한다.
가중치를 바꾸거나 유료 API를 호출하지 않는다. Teacher도 실행하지 않는다.

고정 모델, BF16, seed3407, 이미지당 1,003,520~4,014,080픽셀을 사용한다.
가벼운 실행 확인을 위해 context8192, 출력64, temperature0, 동시 요청1,
TP1, GPU 메모리 비율0.8, eager 실행으로 제한한다. CoT와 반복 guard는 끈다.
**이 설정은 기존 MMMU baseline 평가 설정이 아니며**, 색 판독 결과를 정확도 개선으로
해석하지 않는다. 이 테스트 통과가 긴 context 또는 SFT/GSPO 실행 성공을 보장하지 않는다.

`summary.json`의 completed=3, complete=true, color_checks_passed=3을 확인한다.
오답·잘림은 raw_response와 finish_reason을 확인한다. `error.json`이 있으면 터미널의
첫 원인 오류부터 점검한다. 실패한 폴더를 지우지 않고 다음 실행에 새 출력 경로를 쓴다.
이미 존재하는 출력 폴더는 덮어쓰거나 자동 이어하기 하지 않는다.

## 3. 다음에 정할 실험 조건

다음은 제안된 비교 설계이며 완료 결과가 아니다.

| 조건 | Teacher 수정 CoT로 SFT | GSPO 보상 |
|---|---|---|
| A | 오류 수정, 길이 축소 지시 없음 | 정답 중심 |
| B | 같은 오류 수정본에서 불필요한 풀이 압축 | A와 동일한 정답 중심 보상 |
| C | A와 같은 SFT checkpoint | 정답 + 길이 선호 |
| D | B와 같은 SFT checkpoint | 정답 + 길이 선호 |

B의 보상은 A와 완전히 같다. A/B는 SFT 타깃 압축의 효과, A/C는 RL 길이 보상의 효과를
비교한다. 학습 전 모델과 두 SFT 직후 checkpoint도 평가한다. 같은 문제·분할을 사용하며
Teacher의 오류 수정과 단순 압축을 구분한다. Teacher가 이미지 근거·필수 계산을 삭제하지
않았는지 확인한다. GSPO 자체는 길이 단축 보상이 아니다. 정답률을 우선하고 오답이 짧다는
이유만으로 유리해지지 않도록 보상을 설계한다.

학습은 MMMU/MMMU-Pro와 분리된 외부 데이터의 train split을 사용한다.
MMMU 문항·정답·수정 CoT를 학습 타깃으로 내보내거나 학습에 사용하지 않는다.
학습 모델과 Teacher의 이름·revision, dataset revision·분할·문항 ID, prompt,
학습 설정 및 output token 통계를 저장한다. Teacher 모델과 데이터가 정해지기 전에는
대규모 CoT 생성이나 학습을 시작하지 않는다.

동일한 평가 문항·프롬프트·생성 예산·채점 규칙으로 모든 조건을 비교한다.
정확도, 전체/정답 응답의 생성 토큰 수, 반복·잘림·추출 실패율, 시간과 학습 계산량을
각각 기록한다. 현재 혼합 채점에는 수식 동등성·최종 답 추출 오류가 남아 있으므로
새 정책은 모델별로 다르게 적용하지 않는다. 같은 업데이트 수가 같은 계산량은 아니다.

## 검증 범위

```bash
python -B -m unittest discover -s experiments/cot_compression -p 'test_*.py' -v
```

위 테스트는 저장소 루트에서 실행한다. GPU 없이 dry-run과 기존 출력 보존을 검사한다.
학교 GPU에서의 모델 초기화 및 실제 이미지 추론은 실행 후 결과로 확인해야 한다.
이 폴더에는 완료한 GPU smoke 결과나 SFT/GSPO 학습 결과를 포함하지 않는다.

## 출처

- [기존 MMMU baseline](../../assignment/reports/mmmu_baseline_vllm_cot_rules.md)
- [기존 취약 유형 보완 결과](../../assignment/reports/weakness_finetuning/README.md)
- [Qwen3-VL 모델](https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct)
- [vLLM 0.11.2 Qwen3-VL 예시](https://docs.vllm.ai/en/v0.11.2/examples/offline_inference/vision_language/)
- [GSPO 원 논문](https://arxiv.org/abs/2507.18071)
