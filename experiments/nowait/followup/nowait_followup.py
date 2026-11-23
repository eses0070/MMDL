"""Two paired follow-up arms on the frozen MMMU 40-question NoWait pilot."""
import argparse
from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
import sys
from time import perf_counter

import nowait_pilot as pilot
from checkpointing import atomic_json, contract_hash

CONDITIONS = ('refined_mask', 'answer_switch')
EXEMPT = ('anyone', 'button', 'company', 'know', 'knowledge', 'mother', 'ohio')
SWITCH = 4096
ANSWER_CAP = 128
CUE = ('<|im_end|>\n<|im_start|>user\n'
       'Using the question, choices, and work above, give your best final answer now. '
       'Output only the letter of one of the given options.<|im_end|>\n<|im_start|>assistant\n')
SOURCE = Path(os.environ.get('MMDL_PILOT_OUTPUT', '/work/results/mmmu_nowait_pilot_20261123')).resolve()
OUT = Path(os.environ.get('MMDL_FOLLOWUP_OUTPUT', '/work/results/mmmu_nowait_followup_20261123')).resolve()


@contextmanager
def lock(directory):
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / '.lock').open('a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def prepare():
    reference_plan = os.environ.get("MMDL_REFERENCE_PLAN")
    runtime_dir = OUT / "runtime" if reference_plan else SOURCE
    runtime_dir.mkdir(parents=True, exist_ok=True)
    selected, examples, config, catalog = pilot.prepare(runtime_dir)
    archived = pilot.read_json(SOURCE / "run_config.json")
    if reference_plan:
        expected = pilot.read_json(Path(reference_plan))
        for kind in ("generations", "judgments"):
            if pilot.sha(SOURCE / "nowait" / f"{kind}.jsonl") != expected[f"source_{kind}_sha256"]:
                raise ValueError(f"Archived NoWait {kind} hash mismatch")
        for field in ("student_sampling", "judge_sampling", "image_preprocessing", "mask",
                      "blocked_ids_sha256", "student_files", "judge_files", "repetition_guard",
                      "judge_system", "environment", "historical_rule_config_sha256"):
            if config[field] != archived[field]:
                raise ValueError(f"Runtime differs from archived NoWait: {field}")
        for field in ("student_engine", "judge_engine"):
            if {k:v for k,v in config[field].items() if k != "model"} != {k:v for k,v in archived[field].items() if k != "model"}:
                raise ValueError(f"Engine settings differ: {field}")
    original_digest = contract_hash(archived)
    original = pilot.indexed(SOURCE / 'nowait/generations.jsonl')
    if set(original) != set(examples) or any(r['contract'] != original_digest for r in original.values()):
        raise ValueError('Original NoWait records do not match the frozen contract')
    blocked = [r['id'] for r in catalog['blocked']]
    removed = [r for r in catalog['blocked'] if r['decoded'].strip().casefold() in EXEMPT]
    removed_ids = {r['id'] for r in removed}
    masks = {'refined_mask': [i for i in blocked if i not in removed_ids], 'answer_switch': blocked}
    plan = dict(runtime_contract=contract_hash(config), original_contract=original_digest, source_generations_sha256=pilot.sha(SOURCE / 'nowait/generations.jsonl'),
                source_judgments_sha256=pilot.sha(SOURCE / 'nowait/judgments.jsonl'),
                targets=[row['id'] for row in selected['targets']], exempt_terms=EXEMPT,
                removed_tokens=removed, mask_sizes={c: len(ids) for c, ids in masks.items()},
                mask_hashes={c: contract_hash(ids) for c, ids in masks.items()},
                switch_at=SWITCH, answer_budget=ANSWER_CAP, cue=CUE,
                scoring='original NoWait judge and terminal rules, applied to answer turn when switched',
                code_sha256=pilot.sha(Path(__file__)))
    plan['exempt_terms'] = list(EXEMPT)
    pilot.freeze(OUT / 'followup_config.json', plan)
    return examples, config, original, masks, contract_hash(plan)


def read_records(kind, ids, digest, generated=None):
    result = {}
    for condition in CONDITIONS:
        folder = OUT / condition
        folder.mkdir(exist_ok=True)
        rows = pilot.indexed(folder / f'{kind}.jsonl', repair=True)
        allowed = set(ids) if generated is None else set(generated[condition])
        if set(rows) - allowed or any(r['contract'] != digest or r['condition'] != condition for r in rows.values()):
            raise ValueError(f'Incompatible {kind} checkpoint for {condition}')
        result[condition] = rows
    return result


def generate(ids, examples, config, original, masks, generated, digest):
    from transformers import AutoProcessor
    from vllm import SamplingParams
    from nowait_mask import PARAM
    from streaming_guard import StreamingGuardEngine

    sys.path.insert(0, str(pilot.UPSTREAM))
    from run_mmmu import prepare_inputs_for_vllm

    pending = [(qid, condition) for qid in ids for condition in CONDITIONS if qid not in generated[condition]]
    if not pending:
        return
    pilot.gpu_snapshot(OUT, 'student')
    processor = AutoProcessor.from_pretrained(pilot.STUDENT, local_files_only=True)
    tokenizer = processor.tokenizer
    cue_ids = tokenizer.encode(CUE, add_special_tokens=False)
    engine = StreamingGuardEngine(config['student_engine'])
    try:
        for qid, condition in pending:
            print(f'START {condition} {qid}', flush=True)
            old = original[qid]
            prepared = prepare_inputs_for_vllm(examples[qid][1], processor)
            switching = condition == 'answer_switch'
            extra = {PARAM: masks[condition]}
            start = perf_counter()
            first_params = dict(config['student_sampling'])
            if switching:
                first_params['max_tokens'] = SWITCH
            first = engine.generate([prepared], SamplingParams(**first_params, extra_args=extra))[0]
            if pilot.token_digest(first.prompt_token_ids) != old['prompt_token_sha256']:
                raise RuntimeError(f'Original prompt hash differs for {qid}')
            first_answer = first.outputs[0]
            first_ids = list(first_answer.token_ids)
            finish = first_answer.finish_reason
            switched = switching and finish == 'length' and len(first_ids) == SWITCH
            response = first_answer.text
            answer_ids = []
            evidence = getattr(first, 'repetition_evidence', None)
            second_prompt_tokens = 0
            if switched:
                resumed = {k: v for k, v in prepared.items() if k != 'prompt'}
                raw_prompt = tokenizer.encode(prepared['prompt'], add_special_tokens=False)
                resumed['prompt_token_ids'] = raw_prompt + first_ids + cue_ids
                second_params = dict(config['student_sampling'], max_tokens=ANSWER_CAP)
                second = engine.generate([resumed], SamplingParams(**second_params, extra_args=extra))[0]
                expected = list(first.prompt_token_ids) + first_ids + cue_ids
                if list(second.prompt_token_ids) != expected:
                    raise RuntimeError(f'Expanded multimodal prefix changed for {qid}')
                second_prompt_tokens = len(expected)
                answer = second.outputs[0]
                finish = answer.finish_reason
                response = answer.text
                evidence = getattr(second, 'repetition_evidence', None)
                answer_ids = list(answer.token_ids)
            tokens = first_ids + answer_ids
            if not tokens or finish not in ('stop', 'length', 'repetition_abort') or set(tokens).intersection(masks[condition]):
                raise RuntimeError(f'Invalid generation for {condition} {qid}')
            record = dict(question_id=qid, condition=condition, contract=digest, finish_reason=finish,
                          raw_response=response, gen=response.split('</think>')[-1].strip() if finish != 'repetition_abort' else '',
                          reasoning_prefix=first_answer.text if switched else None, switched=switched,
                          generated_tokens=len(tokens), generated_token_ids=tokens, first_generated_tokens=len(first_ids),
                          answer_generated_tokens=len(answer_ids), cue_tokens=len(cue_ids) if switched else 0,
                          second_prompt_tokens=second_prompt_tokens, elapsed_seconds=perf_counter()-start,
                          prompt_token_sha256=old['prompt_token_sha256'], repetition_evidence=evidence)
            pilot.save(OUT, generated, condition, 'generations', record)
            print(f'SAVED {condition} {qid} {finish} tokens={len(tokens)} switched={switched}', flush=True)
    finally:
        engine.close()


def report(original, generated, judgments):
    original_judged = pilot.indexed(SOURCE / 'nowait/judgments.jsonl')
    summary = {}
    for condition in CONDITIONS:
        rows = generated[condition]
        scores = judgments[condition]
        paired = sorted(scores.keys() & original_judged.keys())
        total = sum(r['generated_tokens'] for r in rows.values())
        ref_total = sum(original[q]['generated_tokens'] for q in rows)
        summary[condition] = dict(generated=len(rows), scored=len(scores), targets=len(original),
                                  pending_score_ids=sorted(rows.keys()-scores.keys()),
                                  correct=sum(r['correct'] for r in scores.values()),
                                  extracted=sum(r['extracted'] for r in scores.values()),
                                  length=sum(r['finish_reason']=='length' for r in rows.values()),
                                  repetition_abort=sum(r['finish_reason']=='repetition_abort' for r in rows.values()),
                                  paired=len(paired), reference_paired_correct=sum(original_judged[q]['correct'] for q in paired),
                                  paired_correct=sum(scores[q]['correct'] for q in paired),
                                  gained_ids=[q for q in paired if scores[q]['correct'] and not original_judged[q]['correct']],
                                  lost_ids=[q for q in paired if original_judged[q]['correct'] and not scores[q]['correct']],
                                  generated_tokens=total, reference_generated_tokens=ref_total,
                                  token_saving_fraction=1-total/ref_total if ref_total else None,
                                  switched=sum(r['switched'] for r in rows.values()),
                                  cue_tokens=sum(r['cue_tokens'] for r in rows.values()),
                                  second_prompt_tokens=sum(r['second_prompt_tokens'] for r in rows.values()),
                                  request_elapsed_seconds=sum(r['elapsed_seconds'] for r in rows.values()))
    atomic_json(OUT / 'summary.json', summary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('smoke', 'generate', 'judge'))
    stage = parser.parse_args().stage
    with lock(OUT):
        examples, config, original, masks, digest = prepare()
        ids = list(examples)
        generated = read_records('generations', ids, digest)
        judgments = read_records('judgments', ids, digest, generated)
        if stage == 'smoke':
            smoke = ['validation_Accounting_22']
            generate(smoke, examples, config, original, masks, generated, digest)
            if not generated['answer_switch'][smoke[0]]['switched']:
                raise RuntimeError('Smoke did not exercise the answer switch')
            pilot.freeze(OUT / 'smoke.json', dict(contract=digest, ids=smoke, passed=True))
        elif stage == 'generate':
            assert pilot.read_json(OUT / 'smoke.json')['contract'] == digest
            generate(ids, examples, config, original, masks, generated, digest)
        else:
            if any(set(generated[c]) != set(ids) for c in CONDITIONS):
                raise RuntimeError('Generate all targets before judging')
            pilot.CONDITIONS = CONDITIONS
            try:
                pilot.grade(OUT, ids, examples, generated, judgments, config, digest,
                            lambda: report(original, generated, judgments))
            except RuntimeError as exc:
                if not str(exc).startswith('Unscored Judge failures, can resume:'):
                    raise
                print(exc, flush=True)
                if not (OUT / 'judge_failures.jsonl').is_file():
                    raise
        report(original, generated, judgments)


if __name__ == '__main__':
    main()
