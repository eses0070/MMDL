"""Create the publication report from completed follow-up checkpoints."""
import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parent
out = root / 'results/mmmu_nowait_followup_20261123'
source = root / 'results/mmmu_nowait_pilot_20261123'
destination = Path(sys.argv[1])
config = json.loads((out / 'followup_config.json').read_text())
summary = json.loads((out / 'summary.json').read_text())
conditions = ('refined_mask', 'answer_switch')
targets = set(config['targets'])


def read(path):
    with path.open() as handle:
        records = [json.loads(line) for line in handle]
    indexed = {row['question_id']: row for row in records}
    assert len(indexed) == len(records), path
    return indexed


records = {}
for name, folder in [('original', source/'nowait'), *((c, out/c) for c in conditions)]:
    generated = read(folder/'generations.jsonl')
    judged = read(folder/'judgments.jsonl')
    assert set(generated) == targets and judged.keys() <= generated.keys()
    records[name] = generated, judged
for c in conditions:
    assert summary[c]['generated'] == len(targets)
    assert summary[c]['scored'] == len(records[c][1])

shared = set.intersection(*(set(judged) for _, judged in records.values()))
original_tokens = sum(r['generated_tokens'] for r in records['original'][0].values())
rows = []
for name, label in zip(records, ('기존 NoWait', '차단 목록 정제', '4,096토큰 답안 전환')):
    generated, judged = records[name]
    tokens = sum(r['generated_tokens'] for r in generated.values())
    correct = sum(judged[q]['correct'] for q in shared)
    unextracted = sum(not r['extracted'] for r in judged.values())
    length = sum(r['finish_reason']=='length' for r in generated.values())
    abort = sum(r['finish_reason']=='repetition_abort' for r in generated.values())
    rows.append(f'| {label} | {tokens:,} | {1-tokens/original_tokens:+.2%} | '
                f'{correct}/{len(shared)} | {len(judged)}/{len(targets)} | {unextracted} | {length} | {abort} |')

lines = ['# MMMU NoWait 후속 실험', '',
         '기존 NoWait 40문항을 기준으로 차단 목록 정제와 답안 전환을 각각 실행했다. '
         'Student는 동일한 Qwen3-VL-4B-Instruct이며, 첫 요청의 확장 프롬프트 토큰 SHA-256을 기존 NoWait와 대조했다.', '',
         '| 조건 | 생성 토큰 합계 | 기존 대비 절감률 | 공통 채점 정답 | 채점 완료 | 채점된 응답 중 미추출 | 길이 종료 | 반복 중단 |',
         '|---|---:|---:|---:|---:|---:|---:|---:|', *rows, '',
         '세 조건 모두 판정된 문항을 정확도 비교의 공통 분모로 썼다. 토큰은 생성이 끝난 40문항 전체를 합산했다.', '',
         '## 구현', '',
         f'- 차단 목록 정제는 디코드 후 공백과 대소문자를 정규화해 사전 고정 예외 '
         f'({", ".join(config["exempt_terms"])})에 정확히 일치하는 토큰만 제외했다. '
         f'마스크는 918개에서 {config["mask_sizes"]["refined_mask"]}개로 줄었다. 생성 예산과 채점 조건은 기존과 동일하다.',
         '- 답안 전환은 918개 원래 마스크에서 4,096토큰 한도까지 첫 요청을 실행한다. '
         '그 전에 종료하면 기존 흐름을 유지하고, 한도에 도달하면 원래 이미지와 생성 토큰을 '
         '붙여 최종 선택지만 요청한다. 추가 생성 한도는 128토큰이다. 이어받은 멀티모달 프롬프트의 토큰을 대조했다. '
         '전환 후에는 두 번째 요청의 출력으로 답을 채점했다.',
         f'- 답안 전환은 {summary["answer_switch"]["switched"]}문항에서 발동했다. '
         f'재요청 지시문은 합계 {summary["answer_switch"]["cue_tokens"]:,} 입력 토큰이며, '
         f'재요청 프롬프트에는 이미지와 기존 생성 토큰을 포함해 합계 {summary["answer_switch"]["second_prompt_tokens"]:,} 입력 토큰이 들어갔다. '
         '이 입력 비용은 표의 생성 토큰에서 제외한다.', '',
         '## 정답 변화와 한계', '']
base = records['original'][1]
for c in conditions:
    _, judged = records[c]
    gained = sorted(q for q in shared if judged[q]['correct'] and not base[q]['correct'])
    lost = sorted(q for q in shared if base[q]['correct'] and not judged[q]['correct'])
    missing = sorted(targets - judged.keys())
    lines += [f'- **{c}** 정답 획득 {len(gained)}개, 손실 {len(lost)}개. '
              f'획득 ID는 {", ".join(gained) or "없음"}. 손실 ID는 {", ".join(lost) or "없음"}. '
              f'채점 보류는 {len(missing)}건 ({", ".join(missing) or "없음"}).']
lines += ['',
          '기존 로컬 Judge와 고정 규칙을 사용했다. 채점에서 보류된 응답은 임의로 판정하지 않았다. '
          '실험은 과거 미추출 40문항과 단일 seed에 한정된다. 모델 생성량 절감은 입력 재처리와 생성·채점의 총비용 절감과 별개다.',
          '',
          '[재현 설정](followup_config.json) · [집계 JSON](summary.json) · [실행 코드](nowait_followup.py) · [실행 스크립트](run-followup.sh)', '']
destination.write_text('\n'.join(lines), encoding='utf-8')
