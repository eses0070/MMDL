"""CPU-only parser v2 replay of saved MC responses. Source files are immutable."""
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import platform
import sys
import time

from mc_parser import decide, VERSION, NUMERIC_VERSION
import legacy

ROOT=Path(__file__).resolve().parent


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_rows(path):
    raw=[line for line in Path(path).read_bytes().splitlines(keepends=True) if line.strip()]
    rows=[json.loads(line.decode('utf-8-sig')) for line in raw]
    ids=[r['question_id'] for r in rows]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate IDs')
    return rows,dict(zip(ids,rows)),dict(zip(ids,raw))


def load(root=ROOT):
    root=Path(root).resolve()
    integrity=json.loads((root/'input_integrity.json').read_text(encoding='utf-8'))
    for name,h in integrity.items():
        p=(root/name).resolve()
        if not p.is_relative_to(root) or not p.is_file() or sha(p)!=h:raise ValueError('Frozen input changed: '+name)
    predictions,pm,_=read_rows(root/'inputs/predictions.jsonl')
    current,cm,raw=read_rows(root/'inputs/current_judgments.jsonl')
    originals,om,_=read_rows(root/'inputs/original_judgments.jsonl')
    if set(pm)!=set(cm) or set(pm)!=set(om):raise ValueError('ID sets differ')
    for qid,p in pm.items():
        if p['annotation']['index']!=qid:raise ValueError('Annotation ID mismatch')
        task=legacy.task_for(p)
        for r in (cm[qid],om[qid]):
            if r['gold']!=p['annotation']['answer']:raise ValueError('GT mismatch')
            if type(r.get('correct')) not in (bool,type(None)):raise ValueError('Invalid verdict')
            if r.get('task') is not None and r['task']!=task:raise ValueError('Task/response mismatch')
    cfg=json.loads((root/'inputs/original_judge_config.json').read_text(encoding='utf-8'))
    if cfg.get('input_sha256')!=sha(root/'inputs/predictions.jsonl') or cfg.get('judge_system')!=legacy.JUDGE_SYSTEM:
        raise ValueError('Historical judge provenance mismatch')
    originally=[r['question_id'] for r in originals if r['correct'] is None and r.get('task',{}).get('kind')=='multiple-choice']
    targets=[qid for qid in originally if cm[qid].get('parse_success') is False]
    if len(predictions)!=900 or len(originally)!=81 or len(targets)!=46:raise ValueError('Not the fixed900/81/46 experiment')
    for qid in targets:
        r=om[qid]
        if r['task']!=legacy.task_for(pm[qid]) or set(r['task'])!={'question','candidate_response','kind','options'}:
            raise ValueError('Cached MC judge input mismatch or unexpected fields')
        if cm[qid].get('answer_correct') is not None or cm[qid]['correct'] is not False:
            raise ValueError('Target not an unresolved-as-wrong current record')
    return {'predictions':predictions,'pm':pm,'current':current,'cm':cm,'om':om,
            'raw_current':raw,'targets':targets,'originally':originally,'integrity':integrity}


def score(rows,pm):
    subjects={}
    for r in rows:
        sub=pm[r['question_id']]['annotation']['category']
        item=subjects.setdefault(sub,{'count':0,'correct':0})
        item['count']+=1;item['correct']+=r['correct'] is True
    for item in subjects.values():item['accuracy_pct']=100*item['correct']/item['count']
    correct=sum(r['correct'] is True for r in rows)
    return {'count':len(rows),'correct':correct,'accuracy_pct':100*correct/len(rows),
            'scoring_unresolved':sum(r['correct'] is None for r in rows),'subjects':subjects}


def evaluate(bundle,limit=0):
    if limit<0:raise ValueError('limit must be >=0')
    targets=bundle['targets'];selected=targets[:limit] if limit else targets
    audits=[];updates={}
    for qid in selected:
        p=bundle['pm'][qid];old=bundle['cm'][qid];cached=bundle['om'][qid];task=cached['task']
        # Whitelist: GT/ID/old verdict are NOT passed to the extractor/comparator.
        decision=decide(question=task['question'],options=task['options'],response=task['candidate_response'],
            finish_reason=p['finish_reason'],context_budget_limited=p.get('context_budget_limited',False),
            cached_raw=cached.get('raw_judge_response'),cached_finish=cached.get('finish_reason'))
        answer=decision['prediction']
        if answer is not None and answer not in task['options']:raise AssertionError('Invalid mapped option')
        if answer is not None:
            start,end=decision['evidence_span']
            if task['candidate_response'][start:end]!=decision['evidence_quote']:raise AssertionError('Nonliteral evidence')
        # GT is first used here for scoring, after option extraction is complete.
        correct=answer==old['gold'] if answer is not None else None
        audit={'question_id':qid,'generation_finish_reason':p['finish_reason'],
            'old_parse_success':old['parse_success'],'old_scoring_correct':old['correct'],
            'extraction':decision,'prediction':answer,'gold':old['gold'],
            'answer_correct':correct,'scoring_correct':correct is True,
            'changed_verdict':(correct is True)!=old['correct'],'parse_recovered':answer is not None,
            'new_judge_calls':0,'reasoning_correct':None}
        audits.append(audit)
        # Unresolved records are byte-preserved; the new audit records that they were checked.
        if answer is not None:
            row=deepcopy(old)
            row['previous_mc46_hybrid_judgment']=deepcopy(old)
            row.update(prediction=answer,answer_correct=correct,correct=correct,parse_success=True,
                reasoning_correct=None,scoring_method=VERSION,parser_reason=decision['route'],
                evidence_quote=decision['evidence_quote'],mc46_hybrid=deepcopy(audit))
            row.pop('error',None);updates[qid]=row
    rows=[updates.get(r['question_id'],deepcopy(r)) for r in bundle['current']]
    recovered=sum(a['parse_recovered'] for a in audits)
    before,after=score(bundle['current'],bundle['pm']),score(rows,bundle['pm'])
    remaining=[qid for qid in targets if qid not in updates]
    summary={'protocol':VERSION,'target_total':len(targets),'selected':len(selected),'audited':len(audits),
        'complete_target_audit':len(selected)==len(targets),'originally_unresolved_mc':81,
        'previously_recovered_mc':35,'newly_extracted':recovered,
        'newly_extracted_correct':sum(a['answer_correct'] is True for a in audits),
        'newly_extracted_incorrect':sum(a['answer_correct'] is False for a in audits),
        'remaining_unextracted_mc':len(remaining),'remaining_ids':remaining,'unselected':len(targets)-len(selected),
        'generation_finish_counts':dict(Counter(a['generation_finish_reason'] for a in audits)),
        'routes':dict(Counter(a['extraction']['route'] for a in audits)),
        'unresolved_reasons':dict(Counter(a['extraction']['reason'] for a in audits if not a['parse_recovered'])),
        'newly_extracted_ids':[a['question_id'] for a in audits if a['parse_recovered']],
        'changed_verdict_ids':[a['question_id'] for a in audits if a['changed_verdict']],
        'new_model_inferences':0,'new_judge_calls':0,
        'cached_judge_records_used':sum(a['extraction'].get('cached_judge_used',False) for a in audits),
        'before':before,'after':after,'untargeted_records_unchanged':len(rows)-len(targets),
        'open_records_unchanged':sum(p['annotation']['question_type']=='open' for p in bundle['predictions']),
        'numeric_rules_version':NUMERIC_VERSION,
        'interpretation':'Local final-answer scoring with remaining abstentions counted wrong; not official MMMU scoring or judge accuracy.',
        'limitations':['40 originally length-limited target answers are guarded; this is not proof that no final choice appears anywhere in them.',
            'Cached original Qwen answer proposals are not fresh judge calls; explicit supporting choice anchors are required.',
            'The MC extraction/mapping layer is new; only the AE quantity comparison module is unchanged.',
            'No image, reasoning verification, independent extraction labels, or unseen evaluation here.']}
    return rows,audits,summary


def report(summary):
    s=summary
    lines=['# 파서 v2 재채점','',f"대상 {s['audited']}/{s['target_total']} 검사. 새 모델 추론·judge 호출 0.",'',
        '| 항목 | 결과 |','|---|---:|',f"| 기존 규칙이 해결한 MC81 중 문항 | 35 |",
        f"| 이번에 새로 답 추출 | {s['newly_extracted']} |",
        f"| 새 추출 중 정답 / 오답 | {s['newly_extracted_correct']} / {s['newly_extracted_incorrect']} |",
        f"| 아직 추출하지 못한 객관식 | {s['remaining_unextracted_mc']} |",
        f"| 전체 기존 점수 | {s['before']['correct']}/900 ({s['before']['accuracy_pct']:.2f}%) |",
        f"| 전체 새 점수 | {s['after']['correct']}/900 ({s['after']['accuracy_pct']:.2f}%) |",'',
        '미추출은 기존 정책대로 점수에서는 오답입니다. scoring_unresolved=0이어도 모든 답이 추출된 것은 아닙니다.',
        '정답 판정은 최종 선택지 문자와 GT의 일치만 뜻합니다. 풀이가 타당하다는 판정이 아닙니다.','',
        '| 경로 | 문항 수 |','|---|---:|']
    for route,count in s['routes'].items():lines.append(f'| {route} | {count} |')
    lines+=['','## 과목별 결과','','| 과목 | 이전 정답 | 이후 정답 / 문항 수 | 이후 정확도 % |','|---|---:|---:|---:|']
    for subject,item in s['after']['subjects'].items():
        lines.append(f"| {subject} | {s['before']['subjects'][subject]['correct']} | {item['correct']}/{item['count']} | {item['accuracy_pct']:.2f} |")
    return '\n'.join(lines)+'\n'


def dump(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def run(root,output_dir,limit=0,dry_run=False):
    root=Path(root).resolve();out=Path(output_dir)
    out=(root/out).resolve() if not out.is_absolute() else out.resolve()
    allowed=(root/'results').resolve()
    if out==allowed or not out.is_relative_to(allowed):raise ValueError('Use a new child of this package/results/')
    if out.exists():raise FileExistsError('Existing results are not overwritten; choose a new output directory')
    start=time.perf_counter();bundle=load(root);rows,audits,summary=evaluate(bundle,limit)
    summary.update(dry_run=dry_run,elapsed_seconds=time.perf_counter()-start)
    if dry_run:return summary
    out.mkdir(parents=True,exist_ok=False)
    cfg={'status':'writing','python':sys.version,'platform':platform.platform(),
        'limit':limit,'input_integrity':bundle['integrity'],
        'code_sha256':{p.name:sha(p) for p in root.glob('*.py')},
        'new_judge_calls':0,'judge':'Original saved Qwen3-8B answer field plus candidate-evidence checks',
        'gt_policy':'Only after extraction to score selected letter; no GT passed to mc_parser.decide',
        'length_policy':'Do not extract incomplete generation; preserve existing verdict',
        'remaining_policy':'Keep parse_success=false and answer_correct=null; correct=false for aggregate score',
        'reasoning_evaluated':False,'official_scoring':False}
    dump(out/'run_config.json',cfg)
    with (out/'judgments.jsonl').open('xb') as f:
        for row in rows:
            qid=row['question_id']
            data=bundle['raw_current'][qid] if row==bundle['cm'][qid] else (json.dumps(row,ensure_ascii=False)+'\n').encode('utf-8')
            f.write(data if data.endswith(b'\n') else data+b'\n')
    for filename,records in [('audit.jsonl',audits),('recovered.jsonl',[a for a in audits if a['parse_recovered']]),
        ('changed_verdicts.jsonl',[a for a in audits if a['changed_verdict']]),
        ('remaining.jsonl',[a for a in audits if not a['parse_recovered']])]:
        with (out/filename).open('x',encoding='utf-8',newline='\n') as f:
            for a in records:f.write(json.dumps(a,ensure_ascii=False)+'\n')
    dump(out/'summary.json',summary)
    (out/'comparison.md').write_text(report(summary),encoding='utf-8')
    cfg.update(status='complete',output_sha256={p.name:sha(p) for p in out.iterdir() if p.name!='run_config.json'})
    dump(out/'run_config.json',cfg)
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--limit',type=int,default=0,help='First N of the remaining46; 0=all')
    parser.add_argument('--dry-run',action='store_true')
    parser.add_argument('--output-dir',type=Path,default=Path('results/mc46_run1'))
    a=parser.parse_args();summary=run(ROOT,a.output_dir,a.limit,a.dry_run)
    print(json.dumps({k:({key:val for key,val in v.items() if key!='subjects'} if k in ('before','after') else v)
        for k,v in summary.items()},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
