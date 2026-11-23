"""Materialize checkpoints and summarize complete NoWait pairs."""
from collections import Counter
import json
from statistics import mean, median

from checkpointing import atomic_json
from nowait_pilot import CONDITIONS, indexed, read_json


TRANSITIONS = ("unextracted->correct", "incorrect->correct", "correct->incorrect", "correct->unextracted")


def jsonl(path, records):
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for row in records:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    temporary.replace(path)


def outcome(row):
    if row["correct"]:
        return "correct"
    return "incorrect" if row["extracted"] else "unextracted"


def metrics(rows):
    tokens = [r["generated_tokens"] for r in rows]
    timings = [r["elapsed_seconds"] for r in rows]
    correct = sum(r["correct"] for r in rows)
    return dict(count=len(rows), correct=correct, accuracy=correct/len(rows) if rows else None,
                extracted=sum(r["extracted"] for r in rows),
                length=sum(r["finish_reason"] == "length" for r in rows),
                repetition_abort=sum(r["finish_reason"] == "repetition_abort" for r in rows),
                generated_tokens_total=sum(tokens), generated_tokens_mean=mean(tokens) if tokens else None,
                generated_tokens_median=median(tokens) if tokens else None,
                seconds_total=sum(timings), seconds_mean=mean(timings) if timings else None)


def token_comparison(pairs):
    sums = {c: sum(r[c]["generated_tokens"] for r in pairs) for c in CONDITIONS}
    return dict(count=len(pairs), tokens=sums, savings=1-sums["nowait"]/sums["baseline"] if sums["baseline"] else None)


def report(directory, generated=None, judged=None):
    config = read_json(directory / "run_config.json")
    target = read_json(directory / "target_ids.json")
    catalog = read_json(directory / "blocked_tokens.json")
    ids = [r["id"] for r in target["targets"]]
    for condition in CONDITIONS:
        (directory / condition).mkdir(exist_ok=True)
    if generated is None:
        generated = {c: indexed(directory / c / "generations.jsonl") for c in CONDITIONS}
    if judged is None:
        judged = {c: indexed(directory / c / "judgments.jsonl") for c in CONDITIONS}
    blocked = {r["id"] for r in catalog["blocked"]}
    original_ids = {c: [r["generated_token_ids"] for r in generated[c].values()
                        if r.get("generated_token_ids") is not None] for c in CONDITIONS}
    counts = {c: Counter(i for tokens in original_ids[c] for i in tokens if i in blocked) for c in CONDITIONS}
    merged = {c: {q: dict(r, **{k: v for k, v in judged[c].get(q, {}).items() if k not in r},
                          scored=q in judged[c]) for q, r in generated[c].items()} for c in CONDITIONS}
    for c in CONDITIONS:
        jsonl(directory / c / "predictions.jsonl", (merged[c][q] for q in ids if q in merged[c]))
    pairs = []
    pair_fields = ("generated_tokens", "finish_reason", "prediction", "extracted", "answer_correct",
                   "correct", "elapsed_seconds", "reused", "scoring_route", "blocked_token_matches")
    for q in ids:
        if not all(q in judged[c] for c in CONDITIONS):
            continue
        rows = {c: {k: merged[c][q].get(k) for k in pair_fields} for c in CONDITIONS}
        for c, row in rows.items():
            row["raw_ref"] = {"path": f"{c}/predictions.jsonl", "question_id": q, "field": "raw_response"}
        pairs.append(dict(question_id=q, gold=merged["baseline"][q]["gold"], **rows,
                          transition=f"{outcome(rows['baseline'])}->{outcome(rows['nowait'])}"))
    transitions = {t: [r["question_id"] for r in pairs if r["transition"] == t] for t in TRANSITIONS}
    fresh_length = [q for q, r in generated["baseline"].items() if not r["reused"] and r["finish_reason"] == "length"]
    length_pairs = [r for r in pairs if r["question_id"] in fresh_length]
    normal = [r for r in pairs if all(r[c]["finish_reason"] == "stop" for c in CONDITIONS)]
    early_aborts = [r for r in pairs if r["nowait"]["finish_reason"] == "repetition_abort"]
    paired_ids = {r["question_id"] for r in pairs}
    summary = dict(
        expected_pairs=len(ids), completed_pairs=len(pairs), complete=len(ids) == len(pairs),
        missing_ids=[q for q in ids if q not in paired_ids],
        conditions={c: dict(metrics([r[c] for r in pairs]), generated=len(generated[c]), scored=len(judged[c]),
                            missing_generation_ids=[q for q in ids if q not in generated[c]],
                            pending_score_ids=[q for q in ids if q in generated[c] and q not in judged[c]])
                    for c in CONDITIONS},
        changes={t: dict(count=len(values), ids=values) for t, values in transitions.items()},
        net_correct=sum(len(transitions[t]) for t in TRANSITIONS[:2])-sum(len(transitions[t]) for t in TRANSITIONS[2:]),
        fresh_baseline_length=dict(count=len(fresh_length), ids=fresh_length, completed_pairs=len(length_pairs),
                                   nowait_normal_stop=sum(r["nowait"]["finish_reason"] == "stop" for r in length_pairs),
                                   nowait_extracted=sum(r["nowait"]["extracted"] for r in length_pairs),
                                   nowait_correct=sum(r["nowait"]["correct"] for r in length_pairs),
                                   nowait_repetition_abort=sum(r["nowait"]["finish_reason"] == "repetition_abort"
                                                              for r in length_pairs)),
        token_savings=dict(all_pairs=token_comparison(pairs), both_normal=token_comparison(normal),
                           nowait_repetition_abort=token_comparison(early_aborts),
                           without_nowait_repetition_abort=token_comparison(
                               [r for r in pairs if r["nowait"]["finish_reason"] != "repetition_abort"])),
        mask_check=dict(nowait_violations=sum(counts["nowait"].values()), nowait_id_coverage=len(original_ids["nowait"]),
                        baseline_id_coverage=len(original_ids["baseline"]),
                        baseline_id_unavailable=len(generated["baseline"])-len(original_ids["baseline"]),
                        baseline_questions_with_blocked_ids=sum(any(i in blocked for i in t) for t in original_ids["baseline"]),
                        baseline_blocked_token_count=sum(counts["baseline"].values()),
                        baseline_blocked_id_frequencies=dict(sorted(counts["baseline"].items()))),
    )
    jsonl(directory / "paired_results.jsonl", pairs)
    atomic_json(directory / "summary.json", summary)
    markdown(directory, summary, config, target, catalog, merged)


def percent(n):
    return f"{n:.2%}" if n is not None else "—"


def markdown(directory, s, config, target, catalog, merged):
    smoke = directory / "smoke_report.json"
    lines = [
        "# Qwen3-VL-4B-Instruct MMMU NoWait 파일럿", "",
        "과거 팀 B0에서 8,192토큰에 도달했고 보완 규칙으로도 답을 추출하지 못한 객관식 40문항에 한정한다. "
        "동일한 선정 ID에서 새로 생성한 baseline과 NoWait를 비교한다.", "",
        "## 재현 설정", "",
        "- 논문 본문은 15개를 설명한다. 이 파일럿은 키워드 상자에 열거된 17개를 사용했다. "
        "고정 Student 토크나이저에서 개별 일반 토큰을 디코딩하고 대소문자를 무시한 부분 문자열로 비교했다. "
        "vLLM 0.11.2 V1의 요청별 사용자 정의 프로세서가 NoWait의 매 샘플링 직전에 차단 ID를 −∞로 바꾼다. "
        "Instruct의 생성 출력 전체에 적용했다. 프롬프트와 Judge에는 마스크가 비활성화된다. "
        f"[EMNLP Findings 원문]({config['paper']})",
        f"- 어휘 {catalog['vocabulary_ids']:,}개에서 {catalog['blocked_count']:,}개 차단. 특수 ID "
        f"{len(catalog['excluded_special_tokens'])}개 제외. 차단 ID SHA-256 `{catalog['blocked_ids_sha256']}`. "
        "실제 부분 문자열 부수 차단 사례는 " + ", ".join(f"`{r['decoded'].strip()}`(ID {r['id']})"
                                                           for r in catalog["collateral_examples"][:12]) + ".",
        f"- 팀 checkout `{config['team_commit']}`. Qwen Student `{config['student_revision']}`. "
        f"Judge Qwen3-8B `{config['judge_files']['revision']}`. 엔진·입력·체크포인트 해시의 세부값은 `run_config.json`과 `target_ids.json`에 있다.",
        f"- 팀 B0 SHA-256 `{target['sources']['historical_predictions']['sha256']}`, "
        f"과거 판정 SHA-256 `{target['sources']['historical_judgments']['sha256']}`, "
        f"이미지 매니페스트 SHA-256 `{target['sources']['image_manifest']['sha256']}`. "
        "캐시 이미지의 순서, PNG·RGB 해시를 검증했다. 과거 실행의 이미지 파일과 바이트 동일성은 미검증이다.",
        f"- 이전 Lookback 대조군 재사용은 0건이다. 컨텍스트 차이는 {config['baseline_reuse']['recorded_max_model_len']:,}"
        f" 대 {config['baseline_reuse']['required_max_model_len']:,}이다. 이전 기록 SHA-256 "
        f"`{config['baseline_reuse']['sha256']}`.",
        "- 두 Student 조건은 팀 CoT 메시지, Qwen 이미지 전처리 1,003,520/4,014,080 픽셀, 반복 감지, "
        "temperature 0.7, top-p 0.8, top-k 20, repetition penalty 1.0, presence penalty 1.5, "
        "요청 seed 3407, 출력 8,192, 컨텍스트 49,152를 공유한다. Student KV 접두사 캐시는 껐고 CUDA graphs를 사용한다. "
        "생성 시간은 엔진 호출 시작부터 종료까지다.",
        "- 팀 Qwen3-8B Judge를 temperature 0, 최대 512토큰, context 32,768, thinking 비활성으로 사용했다. "
        "Judge에는 질문·보기·응답만 전달한다. 유효한 선택지 판정을 우선하고 불확실 판정에는 팀 terminal_rules_v1을 적용한다. "
        "규칙 기권 및 repetition_abort는 B0 집계 정책을 따른다. 유효하지 않은 Judge 출력이 규칙으로도 해소되지 않으면 미채점 상태로 남긴다.",
        f"- CPU 합성 검증과 실제 GPU smoke의 결과는 `cpu_validation.json`, `smoke_report.json`에서 확인할 수 있다. "
        f"GPU smoke {'통과' if smoke.exists() else '미완료'}. 실행 직전 장비와 다른 GPU 작업을 `gpu_preflight.jsonl`에 기록한다.",
        "- 실행 명령은 `bash code/MMDL-official-vllm/nowait.sh run results/mmmu_nowait_pilot_20261123`. "
        "실제 단계별 Python 명령은 `commands.log`에 기록한다.", "",
        "## 결과", "",
        f"채점 완료 쌍 {s['completed_pairs']}/{s['expected_pairs']}. 미완료 ID {', '.join(s['missing_ids']) or '0개'}.", "",
        "| 조건 | 생성/채점 | 정답 | 정확도 | 추출 | 길이 종료 | 반복 종료 | 생성 토큰 합계/평균/중앙값 | 총 생성 초 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for c, r in s["conditions"].items():
        tokens = (f"{r['generated_tokens_total']:,} / {r['generated_tokens_mean']:,.2f} / {r['generated_tokens_median']:,.1f}"
                  if r["count"] else "—")
        lines.append(f"| {c} | {r['generated']}/{r['scored']} | {r['correct']} | {percent(r['accuracy'])} | "
                     f"{r['extracted']} | {r['length']} | {r['repetition_abort']} | {tokens} | {r['seconds_total']:.2f} |")
    labels = dict(zip(TRANSITIONS, ("미추출→정답", "오답→정답", "정답→오답", "정답→미추출")))
    lines.extend(["", f"순증 정답 {s['net_correct']:+d}개. 표와 변화량의 분모는 채점이 완료된 짝이다.", ""])
    for key, r in s["changes"].items():
        lines.append(f"- {labels[key]} {r['count']}건. " + ", ".join(f"`{q}`" for q in r["ids"]))
    length = s["fresh_baseline_length"]
    lines.extend(["",
                  f"새 baseline 실제 길이 종료 {length['count']}개 중 채점 완료 {length['completed_pairs']}쌍. "
                  f"해당 NoWait에서 정상 종료 {length['nowait_normal_stop']}개, 추출 {length['nowait_extracted']}개, "
                  f"정답 {length['nowait_correct']}개, 반복 종료 {length['nowait_repetition_abort']}개.", "",
                  "### 토큰 절감", "",
                  "| 완료 쌍 기준 | 쌍 | Baseline 토큰 | NoWait 토큰 | 절감률 |",
                  "|---|---:|---:|---:|---:|"])
    label = dict(all_pairs="전체", both_normal="양쪽 정상 종료", nowait_repetition_abort="NoWait 반복 종료",
                 without_nowait_repetition_abort="NoWait 반복 종료 제외")
    for name, vals in s["token_savings"].items():
        lines.append(f"| {label[name]} | {vals['count']} | {vals['tokens']['baseline']:,} | "
                     f"{vals['tokens']['nowait']:,} | {percent(vals['savings'])} |")
    m = s["mask_check"]
    lines.extend(["", f"원본 ID 검증에서 NoWait {m['nowait_id_coverage']}문항의 위반 {m['nowait_violations']}건. "
                  f"Baseline은 원본 ID가 있는 {m['baseline_id_coverage']}문항 중 "
                  f"{m['baseline_questions_with_blocked_ids']}문항에서 차단 대상 토큰 총 "
                  f"{m['baseline_blocked_token_count']}회가 나왔다. 측정 불가 {m['baseline_id_unavailable']}문항.", "",
                  "### 변화 사례", ""])
    for key, r in s["changes"].items():
        lines.append(f"- {labels[key]} {r['count']}건.")
        for q in r["ids"][:2]:
            lines.append(f"  - `{q}` 정답 `{merged['baseline'][q]['gold']}`.")
            for c in CONDITIONS:
                row = merged[c][q]
                excerpt = row.get("evidence_quote") or row["raw_response"].strip()[-240:]
                lines.append(f"    - {c} · {row['finish_reason']} · 추출 `{row['prediction']}` · "
                             f"{row['scoring_route']} · 원문 발췌 {json.dumps(excerpt, ensure_ascii=False)}")
    lines.extend(["", "해석 범위는 과거 길이 제한 미추출 40문항이다. 부분 문자열 차단은 일반 어휘와 최종 답 표현에도 영향을 줄 수 있다."])
    draft = directory / "experiment.tmp"
    draft.write_text("\n".join(lines) + "\n", encoding="utf-8")
    draft.replace(directory / "experiment.md")
