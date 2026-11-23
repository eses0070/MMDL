"""Offline, resumable NoWait pilot using the pinned team inputs and judge."""
import argparse
import copy
import fcntl
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import shlex
import subprocess
import sys
import time
from types import SimpleNamespace

from checkpointing import append_checkpoint, atomic_json, contract_hash
from repetition_guard import POLICY
from rescore_mc_rules import extract_terminal
from run import COMMIT, JUDGE_SYSTEM, OFFICIAL_COT_PROMPT, REVISION, ROOT, SETTINGS, UPSTREAM, score, task_for

REPO = ROOT.parents[1]
LAB = Path("/home/gpu/projects")
WORK = Path(os.environ.get("MMDL_INPUT", LAB / "mmdl-lookback.0XCHOF")).resolve()
HF = Path(os.environ.get("HF_HUB_CACHE", LAB / "mmdl-b0.UjOD9U/hf/hub")).resolve()
TEAM = "1c4d7b32ab254d8444b401b06750dfb6e2bfca9e"
JUDGE_REV = "b968826d9c46dd6066d109eabc6255188de91218"
STUDENT = HF / f"models--Qwen--Qwen3-VL-4B-Instruct/snapshots/{REVISION}"
JUDGE = HF / f"models--Qwen--Qwen3-8B/snapshots/{JUDGE_REV}"
B0 = REPO / "results/validation900_cot8192_guard_full/predictions.jsonl"
B0_SHA = "a2336c6a92acbb190ae6c1a40085c97db942158ea107ae1db5469451c3734e39"
OLD_JUDGMENTS = REPO / "results/validation900_rules_v1/judgments.jsonl"
OLD_JUDGE_CONFIG = REPO / "results/validation900_cot8192_guard_full_judge/run_config.json"
OLD_RULE_CONFIG = OLD_JUDGMENTS.with_name("run_config.json")
LOOKBACK_DIR = REPO / "results/mmmu_lookback_pilot_20261123"
PAPER = "https://aclanthology.org/2025.findings-emnlp.394.pdf"
KEYWORDS = ("wait", "alternatively", "hmm", "but", "however", "alternative", "another", "check",
            "double-check", "oh", "maybe", "verify", "other", "again", "now", "ah", "any")
CONDITIONS = ("baseline", "nowait")
SMOKE = ("validation_Accounting_22", "validation_Accounting_28")
GENERATION = dict(temperature=0.7, top_p=0.8, top_k=20, repetition_penalty=1.0,
                  presence_penalty=1.5, max_tokens=8192, seed=3407, stop_token_ids=[])
STUDENT_ENGINE = dict(model=str(STUDENT), seed=3407, tensor_parallel_size=1,
                      max_model_len=49152, gpu_memory_utilization=0.90, max_num_seqs=1,
                      limit_mm_per_prompt={"image": 10}, trust_remote_code=True,
                      enable_prefix_caching=False, logits_processors=["nowait_mask:NoWaitMask"])
JUDGE_ENGINE = dict(model=str(JUDGE), seed=3407, tensor_parallel_size=1, max_model_len=32768,
                    gpu_memory_utilization=0.90, max_num_seqs=1, enforce_eager=True)
JUDGE_SAMPLING = dict(temperature=0, max_tokens=512)


def sha(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def indexed(path, repair=False):
    if not path.exists():
        return {}
    raw = path.read_bytes()
    if repair and raw and not raw.endswith(b"\n"):
        end = raw.rfind(b"\n") + 1
        with path.open("r+b") as handle:
            handle.truncate(end)
            os.fsync(handle.fileno())
        raw = raw[:end]
    records = [json.loads(line) for line in raw.splitlines() if line.strip()]
    result = {r["question_id"]: r for r in records}
    if len(result) != len(records):
        raise ValueError(f"Duplicate checkpoint IDs: {path}")
    return result


def freeze(path, value):
    if path.exists():
        if read_json(path) != value:
            raise ValueError(f"Frozen configuration changed: {path}")
    else:
        atomic_json(path, value)


def command(*args):
    return subprocess.check_output(args, cwd=REPO, text=True).strip()


def inputs():
    from PIL import Image

    if command("git", "rev-parse", "HEAD") != TEAM or sha(B0) != B0_SHA:
        raise ValueError("Team checkout or historical predictions mismatch")
    target_file = WORK / "target_ids.json"
    selected = read_json(target_file)
    target_items = [t for t in selected["targets"] if t["group"] == "diagnostic_length"]
    ids = [t["id"] for t in target_items]
    rules_sha = sha(OLD_JUDGMENTS)
    if len(ids) != 40 or len(set(ids)) != 40 or not set(SMOKE) <= set(ids):
        raise ValueError("Expected 40 distinct diagnostic IDs including both smoke items")
    if (selected["team_commit"], selected["student_predictions_sha256"], selected["baseline_judgments_sha256"]) != (
            TEAM, B0_SHA, rules_sha):
        raise ValueError("Selection provenance mismatch")
    historical = indexed(B0)
    judgments = indexed(OLD_JUDGMENTS)
    image_file = WORK / "image_manifest.json"
    manifest = read_json(image_file)
    if manifest["errors"] or (manifest["dataset"], manifest["revision"], manifest["split"]) != (
            "MMMU/MMMU", "876ce5cb130f7f7e290ce4d9984357737d4db5cf", "validation"):
        raise ValueError("Unexpected image source")
    images = {r["id"]: r for r in manifest["items"]}
    if len(images) != len(manifest["items"]):
        raise ValueError("Duplicate image manifest ID")
    targets, examples = [], {}
    for t in target_items:
        qid = t["id"]
        old, j, item = historical[qid], judgments[qid], images[qid]
        a = old["annotation"]
        if not (old["finish_reason"] == "length" and old["generated_tokens"] == 8192
                and a["index"] == qid and a["question_type"] == "multiple-choice"
                and j["gold"] == a["answer"] and j["prediction"] is None
                and j["parse_success"] is False and j["scoring_method"] == "terminal_rules_v1_abstention_counts_wrong"):
            raise ValueError(f"ID is not a historical length-limited, rules-unextracted MC: {qid}")
        messages = copy.deepcopy(old["messages"])
        parts = messages[-1]["content"]
        image_parts = [part for part in parts if part["type"] == "image"]
        old_paths = t["original_image_paths"]
        if (item["differences"] or not image_parts or len(image_parts) != len(item["images"])
                or [part["image"] for part in image_parts] != old_paths or old_paths != a["image_path"]
                or not parts[-1]["text"].endswith(OFFICIAL_COT_PROMPT)):
            raise ValueError(f"Image order or team CoT prompt mismatch for {qid}")
        for part, image in zip(image_parts, item["images"]):
            path = (WORK / "images" / Path(image["path"]).name).resolve()
            if (path.parent != WORK / "images" or path.name != Path(part["image"]).name
                    or part["min_pixels"] != 1003520 or part["max_pixels"] != 4014080
                    or sha(path) != image["png_sha256"]):
                raise ValueError(f"Image bytes or settings changed for {qid}")
            with Image.open(path) as data:
                if (list(data.size) != image["size"]
                        or hashlib.sha256(data.convert("RGB").tobytes()).hexdigest() != image["rgb_pixels_sha256"]):
                    raise ValueError(f"Image pixels changed for {qid}")
            part["image"] = str(path)
        targets.append(dict(t, images=item["images"], historical_finish_reason="length",
                            historical_answer_extracted=False, gold=a["answer"]))
        examples[qid] = (old, messages)
    source = dict(historical_predictions={"path": str(B0), "sha256": B0_SHA},
                  historical_judgments={"path": str(OLD_JUDGMENTS), "sha256": rules_sha},
                  source_selection={"path": str(target_file), "sha256": sha(target_file)},
                  image_manifest={"path": str(image_file), "sha256": sha(image_file),
                                  "dataset": manifest["dataset"], "revision": manifest["revision"],
                                  "historical_image_equivalence": manifest["historical_image_equivalence"]})
    return dict(team_commit=TEAM, smoke_ids=list(SMOKE), targets=targets, sources=source), examples


def block_tokens():
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(STUDENT, local_files_only=True)
    special = set(tokenizer.all_special_ids)
    special.update(i for i, entry in tokenizer.added_tokens_decoder.items() if entry.special)
    for name in ("config.json", "generation_config.json"):
        cfg = read_json(STUDENT / name)
        for key, value in cfg.items():
            if key in {"eos_token_id", "bos_token_id", "pad_token_id", "image_token_id", "video_token_id",
                       "vision_start_token_id", "vision_end_token_id"} and value is not None:
                special.update(value if isinstance(value, list) else [value])
    for control in ("<think>", "</think>"):
        ident = tokenizer.get_vocab().get(control)
        if ident is not None:
            special.add(ident)
    vocab = sorted(set(tokenizer.get_vocab().values()))
    blocked = []
    special_rows = []
    for ident in vocab:
        value = tokenizer.decode([ident], skip_special_tokens=False, clean_up_tokenization_spaces=False)
        if ident in special:
            special_rows.append({"id": ident, "decoded": value})
        else:
            matched = [word for word in KEYWORDS if word in value.casefold()]
            if matched:
                blocked.append({"id": ident, "decoded": value, "keywords": matched})
    blocked_ids = [row["id"] for row in blocked]
    if not blocked or set(blocked_ids) & special or {r["id"] for r in special_rows} != special:
        raise RuntimeError("Invalid NoWait token catalog")
    collateral = [r for r in blocked if r["decoded"].strip().casefold() in
                  {"know", "knowledge", "button", "company", "anyone", "mother", "otherwise", "ohio"}]
    catalog = dict(keywords=list(KEYWORDS), model_revision=REVISION, vocabulary_ids=len(vocab),
                   blocked_count=len(blocked), blocked=blocked, excluded_special_tokens=special_rows,
                   blocked_ids_sha256=contract_hash(blocked_ids), blocked_entries_sha256=contract_hash(blocked),
                   collateral_examples=collateral)
    return tokenizer, catalog


def cpu_mask_test(catalog):
    import torch
    from vllm import SamplingParams
    from vllm.v1.sample.logits_processor import BatchUpdate
    from vllm.v1.sample.sampler import Sampler
    from nowait_mask import PARAM, NoWaitMask

    ids = [r["id"] for r in catalog["blocked"]]
    vocab_size = read_json(STUDENT / "config.json")["text_config"]["vocab_size"]
    cfg = SimpleNamespace(model_config=SimpleNamespace(get_vocab_size=lambda: vocab_size))
    proc = NoWaitMask(cfg, torch.device("cpu"), False)
    base = SamplingParams(**GENERATION)
    mask = SamplingParams(**GENERATION, extra_args={PARAM: ids})
    proc.update_state(BatchUpdate(batch_size=2, removed=[], added=[(0, base, [], []), (1, mask, [], [])], moved=[]))
    original = torch.full((2, vocab_size), -10.0)
    allowed = next(i for i in range(vocab_size) if i not in set(ids))
    original[:, allowed] = 1.0
    original[:, ids[0]] = 5.0
    metadata = SimpleNamespace(bad_words_token_ids={}, no_penalties=True, output_token_ids=[[], []],
                               allowed_token_ids_mask=None,
                               logitsprocs=SimpleNamespace(non_argmax_invariant=[proc]))
    tested = Sampler.apply_logits_processors(Sampler(), original.clone(), metadata, False)
    allowed_mask = torch.ones(vocab_size, dtype=torch.bool)
    allowed_mask[ids] = False
    if (not torch.equal(tested[0], original[0]) or tested[0].argmax().item() != ids[0]
            or tested[1].argmax().item() != allowed or not torch.isneginf(tested[1, ids]).all()
            or not torch.equal(tested[1, allowed_mask], original[1, allowed_mask])):
        raise RuntimeError("Synthetic V1 sampler mask test failed")
    return {"passed": True, "baseline_argmax": ids[0], "nowait_argmax": allowed,
            "allowed_logits_unchanged": True, "blocked_logits_negative_infinity": len(ids)}


def snapshot_files(snapshot):
    model = read_json(snapshot / "model.safetensors.index.json")
    names = sorted(set(model["weight_map"].values()))
    for name in names:
        blob = (snapshot / name).resolve(strict=True)
        if len(blob.name) != 64 or not blob.is_file():
            raise ValueError(f"Invalid model cache blob {blob}")
    return {"revision": snapshot.name,
            "weight_blob_sha256_from_cache": {name: (snapshot / name).resolve().name for name in names},
            "metadata_sha256": {p.name: sha(p) for p in sorted(snapshot.iterdir())
                                if p.suffix in {".json", ".txt", ".jinja"}}}


def prepare(output):
    selected, examples = inputs()
    freeze(output / "target_ids.json", selected)
    tokenizer, catalog = block_tokens()
    freeze(output / "blocked_tokens.json", catalog)
    old_judge = read_json(OLD_JUDGE_CONFIG)
    if (old_judge["judge_system"] != JUDGE_SYSTEM or old_judge["arguments"]["judge_context"] != 32768
            or Path(old_judge["model_snapshot"]).name != JUDGE_REV
            or old_judge["runner_sha256"] != sha(ROOT / "run.py")
            or read_json(OLD_RULE_CONFIG)["script_sha256"] != sha(ROOT / "rescore_mc_rules.py")):
        raise ValueError("Historical Judge/fallback implementation mismatch")
    prior = read_json(LOOKBACK_DIR / "pilot_config.json")
    prior_engine = prior["engine"]
    if prior_engine["max_model_len"] != 16384:
        raise ValueError("Unexpected engine metadata for the known Lookback baseline")
    versions = {k: version(k) for k in ("vllm", "torch", "transformers", "qwen-vl-utils", "pillow")}
    for k, v in {"vllm": "0.11.2", "torch": "2.9.0", "transformers": "4.57.1"}.items():
        if versions[k].split("+")[0] != v:
            raise ValueError(f"Unexpected {k} version: {versions[k]}")
    import torch
    if torch.version.cuda != "12.8":
        raise ValueError(f"Unexpected Torch CUDA build: {torch.version.cuda}")
    config = dict(
        paper=PAPER, team_commit=TEAM, upstream_qwen_commit=COMMIT,
        target_ids_sha256=sha(output / "target_ids.json"), blocked_tokens_file_sha256=sha(output / "blocked_tokens.json"),
        blocked_ids_sha256=catalog["blocked_ids_sha256"],
        student_engine=STUDENT_ENGINE, student_sampling=GENERATION,
        student_revision=REVISION, student_files=snapshot_files(STUDENT),
        image_preprocessing={"min_pixels": SETTINGS["min_pixels"], "max_pixels": SETTINGS["max_pixels"]},
        model_prompt="historical team messages and CoT; remapped cache image paths",
        repetition_guard=POLICY, environment=dict(versions, cuda_build=torch.version.cuda),
        judge_engine=JUDGE_ENGINE, judge_sampling=JUDGE_SAMPLING, judge_thinking=False, judge_system=JUDGE_SYSTEM,
        judge_files=snapshot_files(JUDGE), historical_judge_config_sha256=sha(OLD_JUDGE_CONFIG),
        historical_rule_config_sha256=sha(OLD_RULE_CONFIG),
        scoring="team Qwen3-8B matched/uncertain, terminal_rules_v1 fallback, repetition abort policy",
        baseline_reuse={"eligible": 0, "path": str(LOOKBACK_DIR / "baseline/predictions.jsonl"),
                        "sha256": sha(LOOKBACK_DIR / "baseline/predictions.jsonl"),
                        "config_sha256": sha(LOOKBACK_DIR / "pilot_config.json"),
                        "recorded_max_model_len": prior_engine["max_model_len"],
                        "required_max_model_len": STUDENT_ENGINE["max_model_len"],
                        "reason": "engine max_model_len mismatch", "new": len(selected["targets"])},
        mask={"scope": "all student generation steps in nowait", "vllm_api": "V1 AdapterLogitsProcessor via extra_args",
              "keywords": list(KEYWORDS), "substring_casefold": True},
        code_sha256={str(p.relative_to(ROOT)): sha(p) for p in
                     [*(ROOT / n for n in ("nowait_pilot.py", "nowait_mask.py", "nowait_report.py", "nowait.sh", "run.py",
                                           "streaming_guard.py", "repetition_guard.py", "checkpointing.py",
                                           "rescore_mc_rules.py", "rejudge_mc.py")), *sorted(UPSTREAM.glob("*.py"))]},
    )
    freeze(output / "run_config.json", config)
    cpu = cpu_mask_test(catalog)
    blocked = {row["id"] for row in catalog["blocked"]}
    historic_counts = {qid: sum(i in blocked for i in tokenizer.encode(examples[qid][0]["result"]["gen_raw"],
                                                                      add_special_tokens=False)) for qid in SMOKE}
    if not any(historic_counts.values()):
        raise RuntimeError("Smoke has no historically observed blocked tokens")
    freeze(output / "cpu_validation.json", dict(cpu, historical_retokenized_smoke_counts=historic_counts,
                                                special_count=len(catalog["excluded_special_tokens"])))
    return selected, examples, config, catalog


def gpu_snapshot(output, stage):
    gpu = command("nvidia-smi", "--query-gpu=name,uuid,driver_version,memory.total,memory.free",
                  "--format=csv,noheader")
    apps = command("nvidia-smi", "--query-compute-apps=pid,process_name,used_gpu_memory", "--format=csv,noheader")
    record = dict(stage=stage, at=time.strftime("%Y-%m-%dT%H:%M:%S%z"), host=platform.node(),
                  os=platform.freedesktop_os_release()["PRETTY_NAME"], gpu=gpu, compute_apps=apps)
    with (output / "gpu_preflight.jsonl").open("a") as f:
        append_checkpoint(f, record)
    print(f"GPU {stage}: {gpu}; active apps: {apps}", flush=True)


def sampling_check(params, expected, expected_extra):
    actual = {key: getattr(params, key) for key in expected}
    if actual != expected or params.extra_args != expected_extra:
        raise RuntimeError(f"Sampling parameters mismatch: {actual}")
    return actual


def token_digest(ids):
    return contract_hash(list(ids))


def generate(output, ids, examples, config, catalog, generated, digest, publish):
    from transformers import AutoProcessor
    from vllm import SamplingParams
    from nowait_mask import PARAM
    from streaming_guard import StreamingGuardEngine

    sys.path.insert(0, str(UPSTREAM))
    from run_mmmu import prepare_inputs_for_vllm

    pending = [(qid, c) for i, qid in enumerate(ids) for c in
               (CONDITIONS if i % 2 == 0 else CONDITIONS[::-1]) if qid not in generated[c]]
    if not pending:
        return
    gpu_snapshot(output, "student")
    processor = AutoProcessor.from_pretrained(STUDENT, local_files_only=True)
    blocked_ids = [r["id"] for r in catalog["blocked"]]
    blocked = set(blocked_ids)
    engine = StreamingGuardEngine(config["student_engine"])
    try:
        cfg = engine.engine.vllm_config
        if (cfg.model_config.max_model_len != 49152 or cfg.scheduler_config.max_num_seqs != 1
                or cfg.cache_config.enable_prefix_caching or cfg.model_config.model != str(STUDENT)
                or [str(p) for p in cfg.model_config.logits_processors] != STUDENT_ENGINE["logits_processors"]):
            raise RuntimeError("Resolved Student engine config mismatch")
        freeze(output / "student_engine_resolved.json",
               dict(max_model_len=cfg.model_config.max_model_len, max_num_seqs=cfg.scheduler_config.max_num_seqs,
                    model=cfg.model_config.model, enable_prefix_caching=cfg.cache_config.enable_prefix_caching,
                    logits_processors=[str(p) for p in cfg.model_config.logits_processors],
                    dtype=str(cfg.model_config.dtype), model_vocab_size=cfg.model_config.get_vocab_size(),
                    compilation_mode=str(cfg.compilation_config.mode), enforce_eager=cfg.model_config.enforce_eager))
        for qid, condition in pending:
            old, messages = examples[qid]
            print(f"START {condition} {qid}", flush=True)
            prepared = prepare_inputs_for_vllm(messages, processor)
            extra = {PARAM: blocked_ids} if condition == "nowait" else None
            params = SamplingParams(**GENERATION, extra_args=extra)
            actual = sampling_check(params, GENERATION, extra)
            start = time.perf_counter()
            result = engine.generate([prepared], params)[0]
            elapsed = time.perf_counter() - start
            answer = result.outputs[0]
            tokens = list(answer.token_ids)
            finish = answer.finish_reason
            violation_count = sum(i in blocked for i in tokens)
            if (finish not in {"stop", "length", "repetition_abort"} or not tokens
                    or len(tokens) > GENERATION["max_tokens"] or (finish == "length" and len(tokens) != 8192)
                    or (condition == "nowait" and violation_count)):
                raise RuntimeError(f"Invalid output {condition}/{qid}: {finish}, {len(tokens)} tokens, {violation_count} matches")
            record = dict(question_id=qid, condition=condition, contract=digest, reused=False,
                          source="new_student_request", finish_reason=finish, request_sampling=actual,
                          raw_response=answer.text, gen=answer.text.split("</think>")[-1].strip()
                          if finish != "repetition_abort" else "",
                          generated_token_ids=tokens, generated_tokens=len(tokens), elapsed_seconds=elapsed,
                          prompt_token_sha256=token_digest(result.prompt_token_ids),
                          prompt_tokens=len(result.prompt_token_ids),
                          ordered_image_sha256=[sha(Path(part["image"])) for part in messages[-1]["content"]
                                                if part["type"] == "image"],
                          messages_sha256=contract_hash(messages), gold=old["annotation"]["answer"],
                          repetition_evidence=getattr(result, "repetition_evidence", None),
                          mask_applied=extra is not None, blocked_token_matches=violation_count,
                          mask_id_sha256=catalog["blocked_ids_sha256"] if extra else None)
            other = next(c for c in CONDITIONS if c != condition)
            paired = generated[other].get(qid)
            if paired and any(record[key] != paired[key] for key in
                              ("prompt_token_sha256", "ordered_image_sha256", "messages_sha256", "request_sampling")):
                raise RuntimeError(f"Paired Student inputs or sampling differ for {qid}")
            if finish == "repetition_abort" and not record["repetition_evidence"]:
                raise RuntimeError("Team repetition guard aborted without evidence")
            save(output, generated, condition, "generations", record)
            publish()
            print(f"SAVED {condition} {qid} {finish} tokens={len(tokens)} "
                  f"blocked={violation_count} seconds={elapsed:.2f}", flush=True)
    finally:
        engine.close()


def save(output, storage, condition, filename, record):
    with (output / condition / f"{filename}.jsonl").open("a", encoding="utf-8") as handle:
        append_checkpoint(handle, record)
    storage[condition][record["question_id"]] = record


def blind_judge(run, old, gen):
    if gen["finish_reason"] == "repetition_abort":
        return dict(prediction=None, extracted=False, answer_correct=None, correct=False,
                    scoring_route="repetition_abort_policy", judge_skipped=True)
    task = task_for(dict(annotation=old["annotation"], result={"gen": gen["gen"]}))
    gold = old["annotation"]["answer"]
    judged = run(task)
    raw, finish = judged["raw"], judged["finish_reason"]
    judge_error = None
    try:
        if finish != "stop":
            raise ValueError("judge_output_incomplete")
        output = json.loads(raw)
        verdict = score(output, task, gold)
    except (ValueError, TypeError, KeyError, AttributeError) as error:
        judge_error = f"{type(error).__name__}: {error}"
        verdict = None
    if verdict is not None:
        pred = output["answer"]
        route, evidence = "team_judge_matched", None
    else:
        pred, reason, evidence = extract_terminal(task["candidate_response"], task["options"])
        route = f"terminal_rules_v1:{reason}"
        if pred is None and judge_error is not None:
            return dict(scoring_route="judge_error_pending", judge_error=judge_error, judge=judged,
                        fallback_route=route, evidence_quote=evidence)
    answer_correct = pred == gold if pred is not None else None
    return dict(prediction=pred, extracted=pred is not None, answer_correct=answer_correct,
                correct=answer_correct is True, scoring_route=route, judge_skipped=False,
                judge=judged, judge_error=judge_error, evidence_quote=evidence)


def grade(output, ids, examples, generated, judgments, config, digest, publish):
    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams

    pending = [(qid, c) for qid in ids for c in CONDITIONS if qid in generated[c] and qid not in judgments[c]]
    if not pending:
        return
    tokenizer = AutoTokenizer.from_pretrained(JUDGE, local_files_only=True)
    params = SamplingParams(**JUDGE_SAMPLING)
    sampling_check(params, JUDGE_SAMPLING, None)
    engine = None

    def run(task):
        nonlocal engine
        prompt = tokenizer.apply_chat_template(
            [{"role": "system", "content": JUDGE_SYSTEM},
             {"role": "user", "content": json.dumps(task, ensure_ascii=False)}],
            tokenize=False, add_generation_prompt=True, enable_thinking=False)
        size = len(tokenizer.encode(prompt, add_special_tokens=False))
        if size + JUDGE_SAMPLING["max_tokens"] > JUDGE_ENGINE["max_model_len"]:
            raise RuntimeError("Judge context budget exceeded")
        if engine is None:
            gpu_snapshot(output, "judge")
            engine = LLM(**config["judge_engine"])
            cfg = engine.llm_engine.vllm_config
            if cfg.model_config.max_model_len != 32768 or cfg.model_config.model != str(JUDGE):
                raise RuntimeError("Judge engine config mismatch")
        answer = engine.generate([prompt], params, use_tqdm=False)[0].outputs[0]
        return dict(raw=answer.text, finish_reason=answer.finish_reason, input_tokens=size)

    failures = []
    try:
        for qid, condition in pending:
            print(f"JUDGE {condition} {qid}", flush=True)
            value = blind_judge(run, examples[qid][0], generated[condition][qid])
            record = dict(value, question_id=qid, condition=condition, contract=digest)
            if value["scoring_route"] == "judge_error_pending":
                failures.append((condition, qid))
                with (output / "judge_failures.jsonl").open("a") as handle:
                    append_checkpoint(handle, record)
            else:
                save(output, judgments, condition, "judgments", record)
                publish()
    finally:
        if engine is not None:
            engine.llm_engine.engine_core.shutdown()
    if failures:
        raise RuntimeError(f"Unscored Judge failures, can resume: {failures}")


def smoke(output, generated, catalog, digest):
    by_condition = {c: {q: generated[c][q] for q in SMOKE} for c in CONDITIONS}
    if not any(r["blocked_token_matches"] for r in by_condition["baseline"].values()):
        raise RuntimeError("Smoke baseline did not exercise a blocked ID")
    checks = []
    for q in SMOKE:
        a, b = (by_condition[c][q] for c in CONDITIONS)
        assert a["prompt_token_sha256"] == b["prompt_token_sha256"]
        assert a["ordered_image_sha256"] == b["ordered_image_sha256"]
        assert a["request_sampling"] == b["request_sampling"]
        assert not a["mask_applied"] and b["mask_applied"]
        assert b["mask_id_sha256"] == catalog["blocked_ids_sha256"]
        observed = {r["id"] for r in catalog["blocked"]}
        assert not observed.intersection(b["generated_token_ids"])
        assert all(r["raw_response"] and (r["finish_reason"] != "repetition_abort" or r["repetition_evidence"])
                   for r in (a, b))
        checks.append(dict(question_id=q, same_input=True, same_sampling=True,
                           baseline_blocked_tokens=a["blocked_token_matches"], nowait_violations=0,
                           baseline_finish=a["finish_reason"], nowait_finish=b["finish_reason"],
                           repetition_abort_observed=any(r["finish_reason"] == "repetition_abort" for r in (a, b))))
    freeze(output / "smoke_report.json", dict(passed=True, contract=digest, ids=list(SMOKE),
                                            cpu=read_json(output / "cpu_validation.json"), gpu_checks=checks))


def main():
    from nowait_report import report

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("prepare", "smoke", "judge-smoke", "generate", "judge", "report"))
    parser.add_argument("--output", required=True, type=lambda p: Path(p).resolve())
    args = parser.parse_args()
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    with (output / ".checkpoint.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.stage == "report":
            report(output)
            return
        selected, examples, config, catalog = prepare(output)
        digest = contract_hash(config)
        with (output / "commands.log").open("a") as f:
            f.write(shlex.join([sys.executable, *sys.argv]) + "\n")
        ids = list(examples)
        for c in CONDITIONS:
            (output / c).mkdir(exist_ok=True)
        generated, judgments = ({c: indexed(output / c / f"{kind}.jsonl", repair=True)
                                 for c in CONDITIONS} for kind in ("generations", "judgments"))
        for c in CONDITIONS:
            if (set(generated[c]) - set(ids) or set(judgments[c]) - set(generated[c])
                    or any(r["condition"] != c or r["contract"] != digest
                           for r in [*generated[c].values(), *judgments[c].values()])):
                raise ValueError(f"{c} checkpoint contract changed")

        def publish():
            report(output, generated, judgments)

        try:
            if args.stage == "smoke":
                generate(output, SMOKE, examples, config, catalog, generated, digest, publish)
                smoke(output, generated, catalog, digest)
            elif args.stage in {"generate", "judge", "judge-smoke"}:
                if read_json(output / "smoke_report.json")["contract"] != digest:
                    raise RuntimeError("Smoke configuration differs")
                if args.stage == "generate":
                    generate(output, ids, examples, config, catalog, generated, digest, publish)
                else:
                    grade(output, SMOKE if args.stage == "judge-smoke" else ids,
                          examples, generated, judgments, config, digest, publish)
        finally:
            publish()


if __name__ == "__main__":
    main()
