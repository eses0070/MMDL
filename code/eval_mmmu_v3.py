"""Single-GPU MMMU validation evaluation; defaults to a five-question smoke run."""

import argparse
import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import re
import subprocess
import time

MODEL_REVISION = "ebb281ec70b05090aa6165b016eac8ec08e71b17"
DATA_REVISION = "98e6ac0cb9b7b2cd2c991b85a50762edc4aedc68"
SUBJECTS = """Accounting Agriculture Architecture_and_Engineering Art Art_Theory
Basic_Medical_Science Biology Chemistry Clinical_Medicine Computer_Science
Design Diagnostics_and_Laboratory_Medicine Economics Electronics Energy_and_Power
Finance Geography History Literature Manage Marketing Materials Math
Mechanical_Engineering Music Pharmacy Physics Psychology Public_Health Sociology""".split()
IMAGE_MARKER = re.compile(r"<image\s+(\d+)>")
MC_INSTRUCTION = (
    "Select the single best choice. Respond with exactly one line in the format "
    "'Answer: X', where X is the option letter. Do not include an explanation."
)
OPEN_INSTRUCTION = (
    "Solve the problem. End your response with a separate line 'Answer: X', "
    "where X is your concise final answer."
)


def build_prompt(sample):
    """Do not include gold answers or explanations in the input."""
    kind = sample["question_type"]
    if kind == "multiple-choice":
        options = sample["options"]
        if isinstance(options, str):
            options = ast.literal_eval(options)
        if not isinstance(options, list) or not 2 <= len(options) <= 26:
            raise ValueError(f"Invalid options: {sample['id']}")
        choices = "\n".join(f"{chr(65 + i)}. {value}" for i, value in enumerate(options))
        return f"{sample['question']}\n\nChoices:\n{choices}\n\n{MC_INSTRUCTION}", options
    if kind != "open":
        raise ValueError(f"Unsupported question type: {kind}")
    return f"{sample['question']}\n\n{OPEN_INSTRUCTION}", []


def build_content(sample, prompt):
    """Keep image references in both questions and answer options in order."""
    content, images, image_keys = [], [], []
    cursor = 0
    for match in IMAGE_MARKER.finditer(prompt):
        if match.start() > cursor:
            content.append({"type": "text", "text": prompt[cursor:match.start()]})
        key = f"image_{match.group(1)}"
        image = sample.get(key)
        if image is None:
            raise ValueError(f"{sample['id']}: missing referenced {key}")
        content.append({"type": "image"})
        images.append(image.convert("RGB"))
        image_keys.append(key)
        cursor = match.end()
    if cursor < len(prompt):
        content.append({"type": "text", "text": prompt[cursor:]})
    if not images and any(sample.get(f"image_{i}") is not None for i in range(1, 8)):
        raise ValueError(f"{sample['id']}: images exist but no image references were found")
    return content, images, image_keys


def final_answer(response):
    clean = response.replace("**", "").replace("`", "")
    matches = re.findall(r"(?im)^[ \t]*(?:final[ \t]+)?answer[ \t]*:[ \t]*([^\r\n]+)", clean)
    return (matches[-1].strip(), "answer_line") if matches else (None, "missing_answer_line")


def parse_choice(response, count):
    candidate, method = final_answer(response)
    if candidate is None:
        candidate, method = response.strip(), "bare_letter"
        pattern = r"\(?([A-Z])\)?[.!]?"
    else:
        pattern = r"\(?([A-Z])\)?(?:[.\s,:-].*)?"
    match = re.fullmatch(pattern, candidate, re.IGNORECASE)
    if not match:
        return None, "parse_failure"
    letter = match.group(1).upper()
    if letter not in [chr(65 + i) for i in range(count)]:
        return None, "invalid_choice"
    return letter, method


def normalize_open(value):
    text = str(value).strip().casefold().replace("\u2212", "-")
    text = re.sub(r"\s+", " ", text).strip().rstrip(".")
    number = text.replace(",", "")
    if re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?", number):
        return round(float(number), 2)
    return text


def numeric_value(value):
    """Evaluate a small arithmetic grammar, never Python eval or arbitrary code."""
    text = str(value).strip().replace("\u2212", "-").replace(",", "")
    text = text.replace("\\(", "").replace("\\)", "").strip("$")
    text = re.sub(r"\\(?:d?frac)\{([+-]?[\d.]+)\}\{([+-]?[\d.]+)\}", r"(\1/\2)", text)
    text = re.sub(r"\\sqrt\{([\d.]+)\}", r"sqrt(\1)", text)
    text = re.sub(r"\u221a([\d.]+)", r"sqrt(\1)", text)
    text = re.sub(r"(?<=[\d)])(?=sqrt\()", "*", text)
    text = text.replace("^", "**")
    if len(text) > 128:
        return None

    def calculate(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            result = float(node.value)
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            result = calculate(node.operand) * (-1 if isinstance(node.op, ast.USub) else 1)
        elif isinstance(node, ast.BinOp):
            left, right = calculate(node.left), calculate(node.right)
            if isinstance(node.op, ast.Add):
                result = left + right
            elif isinstance(node.op, ast.Sub):
                result = left - right
            elif isinstance(node.op, ast.Mult):
                result = left * right
            elif isinstance(node.op, ast.Div):
                result = left / right
            elif isinstance(node.op, ast.Pow) and abs(right) <= 10:
                result = left ** right
            else:
                raise ValueError("Unsupported operator")
        elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
              and node.func.id == "sqrt" and len(node.args) == 1 and not node.keywords):
            result = math.sqrt(calculate(node.args[0]))
        else:
            raise ValueError("Unsupported expression")
        if not isinstance(result, (int, float)) or not math.isfinite(result) or abs(result) > 1e100:
            raise ValueError("Out of range")
        return result

    try:
        tree = ast.parse(text.strip(), mode="eval")
        if len(list(ast.walk(tree))) > 64:
            return None
        return calculate(tree.body)
    except (SyntaxError, ValueError, TypeError, ArithmeticError, RecursionError):
        return None


def open_answer_matches(prediction, gold):
    pred, target = normalize_open(prediction), normalize_open(gold)
    if pred == target:
        return True
    target_number = numeric_value(gold)
    if target_number is not None:
        candidate = str(prediction).strip().rstrip(".")
        # Strip only documented suffixes; do not extract numbers from reasoning.
        candidate = re.sub(
            r"\s+(?:U|F|unfavou?rable|favou?rable|USD|dollars?|V|A|W|Hz|ohms?|\u03a9|k\u03a9|g|kg|m|cm|mm|s)\s*$",
            "", candidate, flags=re.IGNORECASE,
        )
        result = numeric_value(candidate)
        return result is not None and round(result, 2) == round(target_number, 2)
    # Word-boundary matching is restricted to short, non-negated final answers.
    if isinstance(pred, str) and isinstance(target, str) and len(target) >= 3:
        if (len(pred.split()) <= 6 and "?" not in pred
                and not re.search(r"\b(?:not|no|except|rather|or)\b", pred)):
            return re.search(r"(?<!\w)" + re.escape(target) + r"(?!\w)", pred) is not None
    return False


def score_response(response, sample, options):
    gold = sample["answer"]
    if isinstance(gold, str) and gold.lstrip().startswith("["):
        try:
            parsed = ast.literal_eval(gold)
            if isinstance(parsed, list):
                gold = parsed
        except (SyntaxError, ValueError):
            pass
    answers = gold if isinstance(gold, list) else [gold]
    if sample["question_type"] == "multiple-choice":
        pred, method = parse_choice(response, len(options))
        correct = pred is not None and pred in [str(x).strip().upper() for x in answers]
    else:
        pred, method = final_answer(response)
        if pred is None and len(response.strip().splitlines()) == 1:
            pred, method = response.strip() or None, "single_line"
        correct = pred is not None and any(open_answer_matches(pred, x) for x in answers)
    return {"prediction": pred, "parser_method": method, "parse_failure": pred is None,
            "correct": bool(correct)}


def select_examples(data, limit, question_type="all"):
    if set(data) != set(SUBJECTS):
        raise ValueError("Expected exactly the 30 required subject configs")
    seen = set()
    for subject in SUBJECTS:
        ids = list(data[subject]["id"])
        if len(ids) != 30 or len(set(ids)) != 30 or seen.intersection(ids):
            raise ValueError(f"Wrong count or duplicate IDs: {subject}")
        seen.update(ids)
    # Round-robin keeps a small run spread over subjects and stable in a full run.
    selected = [(subject, i) for i in range(30) for subject in SUBJECTS]
    if question_type != "all":
        selected = [(s, i) for s, i in selected if data[s]["question_type"][i] == question_type]
    return selected if limit == 0 else selected[:limit]


def summarize(rows, expected, elapsed):
    counts, hits = Counter(), Counter()
    for row in rows:
        counts[row["subject"]] += 1
        hits[row["subject"]] += row["correct"]
    subjects = {s: {"count": counts[s], "correct": hits[s],
                    "accuracy_pct": 100 * hits[s] / counts[s]} for s in counts}
    full = len(rows) == 900 and len(counts) == 30 and all(n == 30 for n in counts.values())
    return {
        "completed": len(rows), "expected": expected, "is_full_900": full,
        "accuracy_pct": 100 * sum(hits.values()) / len(rows) if rows else None,
        "macro_accuracy_pct": sum(v["accuracy_pct"] for v in subjects.values()) / 30 if full else None,
        "parse_failures": sum(r["parse_failure"] for r in rows),
        "length_limited": sum(r["finish_reason"] == "length" for r in rows),
        "elapsed_seconds_including_load": elapsed,
        "subjects": subjects,
    }


def presence_processor(torch, base_class, prompt_length, penalty):
    class OutputPresencePenalty(base_class):
        def __call__(self, input_ids, scores):
            for row in range(input_ids.shape[0]):
                seen = torch.unique(input_ids[row, prompt_length:])
                scores[row, seen] -= penalty
            return scores
    return OutputPresencePenalty()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model_path", default="Qwen/Qwen3-VL-4B-Instruct")
    parser.add_argument("--data_root", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=5, help="0 = all selected questions; default = 5")
    parser.add_argument("--question_type", choices=["all", "open", "multiple-choice"], default="all",
                        help="Filter only for diagnostic runs; use all for submission")
    parser.add_argument("--max_new_tokens", type=int, default=2048)
    parser.add_argument("--open_max_new_tokens", type=int, default=8192,
                        help="Separate output budget for open questions (default: 8192)")
    parser.add_argument("--min_pixels", type=int, default=4096)
    parser.add_argument("--max_pixels", type=int, default=1048576)
    args = parser.parse_args()
    if not 0 <= args.limit <= 900 or min(args.max_new_tokens, args.open_max_new_tokens) < 1:
        parser.error("limit must be 0..900 and both output budgets must be positive")
    if not 0 < args.min_pixels <= args.max_pixels:
        parser.error("Require 0 < min_pixels <= max_pixels")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        parser.error("Output directory is not empty; choose a new directory to preserve prior results")

    import torch
    import transformers
    from datasets import load_from_disk
    from transformers import (AutoProcessor, GenerationConfig, LogitsProcessor,
                              LogitsProcessorList, Qwen3VLForConditionalGeneration, set_seed)

    if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():
        raise RuntimeError("A CUDA GPU with BF16 support is required")
    data = load_from_disk(str(args.data_root))
    selected = select_examples(data, args.limit, args.question_type)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    recipe = dict(do_sample=True, temperature=0.7, top_p=0.8, top_k=20,
                  repetition_penalty=1.0, presence_penalty=1.5, seed=3407)
    metadata = {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "arguments": {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
        "model_revision": MODEL_REVISION, "expected_dataset_revision": DATA_REVISION,
        "dataset_provenance_note": "Local export loaded; fingerprints recorded, original HF revision not independently verifiable.",
        "dataset_fingerprints": {s: data[s]._fingerprint for s in SUBJECTS},
        "recipe": recipe, "seed_policy": "Reset seed=3407 before each question; batch size 1",
        "recipe_source": "https://github.com/QwenLM/Qwen3-VL#evaluation-reproduction",
        "mc_prompt_template": "{question}\n\nChoices:\n{lettered_options}\n\n" + MC_INSTRUCTION,
        "open_prompt_template": "{question}\n\n" + OPEN_INSTRUCTION,
        "pipeline_version": 3,
        "output_budget_policy": "open_max_new_tokens for open questions; max_new_tokens for multiple-choice",
        "parser": "Custom final-answer parser v2; see IMPROVEMENTS.md; not official MMMU scoring",
        "dtype": "bfloat16", "attention": "sdpa", "gpu": torch.cuda.get_device_name(0),
        "total_vram_gib": torch.cuda.get_device_properties(0).total_memory / 2**30,
        "torch_cuda": torch.version.cuda, "transformers": transformers.__version__,
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "planned_ids": [data[s]["id"][i] for s, i in selected],
    }
    try:
        metadata["nvidia_smi"] = subprocess.check_output(["nvidia-smi"], text=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        metadata["nvidia_smi"] = str(exc)
    write_json(args.output_dir / "run_config.json", metadata)
    packages = sorted(f"{d.metadata['Name']}=={d.version}" for d in importlib.metadata.distributions())
    (args.output_dir / "environment.txt").write_text("\n".join(packages) + "\n", encoding="utf-8")

    started = time.perf_counter()
    torch.cuda.reset_peak_memory_stats()
    print(f"Loading model; selected {len(selected)} questions", flush=True)
    processor = AutoProcessor.from_pretrained(
        args.model_path, revision=MODEL_REVISION, local_files_only=True)
    model = Qwen3VLForConditionalGeneration.from_pretrained(
        args.model_path, revision=MODEL_REVISION, local_files_only=True,
        dtype=torch.bfloat16, device_map={"": 0}, attn_implementation="sdpa").eval()
    config = GenerationConfig(
        do_sample=True, temperature=0.7, top_p=0.8, top_k=20, repetition_penalty=1.0,
        max_new_tokens=args.max_new_tokens, use_cache=True,
        eos_token_id=model.generation_config.eos_token_id,
        pad_token_id=model.generation_config.pad_token_id,
        bos_token_id=model.generation_config.bos_token_id,
    )
    write_json(args.output_dir / "generation_config.json", config.to_dict())
    eos = config.eos_token_id
    eos_ids = set(eos if isinstance(eos, list) else [eos])
    results = []
    with (args.output_dir / "predictions.jsonl").open("w", encoding="utf-8") as handle:
        for position, (subject, index) in enumerate(selected, 1):
            sample = data[subject][index]
            try:
                prompt, options = build_prompt(sample)
                content, images, image_keys = build_content(sample, prompt)
                messages = [{"role": "user", "content": content}]
                rendered = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                question_started = time.perf_counter()
                inputs = processor(
                    text=[rendered], images=images or None, return_tensors="pt",
                    min_pixels=args.min_pixels, max_pixels=args.max_pixels,
                ).to("cuda")
                input_length = inputs["input_ids"].shape[1]
                set_seed(3407)
                penalty = presence_processor(torch, LogitsProcessor, input_length, 1.5)
                output_budget = args.open_max_new_tokens if sample["question_type"] == "open" else args.max_new_tokens
                with torch.inference_mode():
                    generated = model.generate(
                        **inputs, generation_config=config,
                        max_new_tokens=output_budget,
                        logits_processor=LogitsProcessorList([penalty]))
                torch.cuda.synchronize()
                ids = generated[0, input_length:].tolist()
                response = processor.decode(ids, skip_special_tokens=True)
                row = {
                    "id": sample["id"], "subject": subject, "question_type": sample["question_type"],
                    "prompt": prompt, "rendered_prompt": rendered, "image_keys": image_keys,
                    "image_sizes": [list(im.size) for im in images],
                    "image_grid_thw": inputs["image_grid_thw"].tolist() if images else [],
                    "input_tokens": input_length, "generated_tokens": len(ids),
                    "max_new_tokens": output_budget,
                    "finish_reason": "eos" if ids and ids[-1] in eos_ids else "length",
                    "response": response, "gold": sample["answer"],
                    "elapsed_seconds": time.perf_counter() - question_started,
                    **score_response(response, sample, options),
                }
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                handle.flush()
                results.append(row)
                print(f"[{position}/{len(selected)}] {sample['id']} "
                      f"pred={row['prediction']} gold={sample['answer']} "
                      f"correct={row['correct']} tokens={len(ids)} stop={row['finish_reason']}", flush=True)
                if args.limit != 0:
                    print(response, "\n", flush=True)
                del inputs, generated
            except Exception as exc:
                write_json(args.output_dir / "error.json", {"id": sample["id"], "error": repr(exc)})
                raise
            summary = summarize(results, len(selected), time.perf_counter() - started)
            summary["torch_peak_allocated_gib"] = torch.cuda.max_memory_allocated() / 2**30
            summary["torch_peak_reserved_gib"] = torch.cuda.max_memory_reserved() / 2**30
            write_json(args.output_dir / "summary.json", summary)

    lines = ["| Subject | Count | Correct | Accuracy (%) |", "|---|---:|---:|---:|"]
    for subject, values in summary["subjects"].items():
        lines.append(f"| {subject} | {values['count']} | {values['correct']} | {values['accuracy_pct']:.2f} |")
    label = "Overall (macro average)" if summary["is_full_900"] else "SMOKE TEST ONLY (micro average)"
    accuracy = summary["macro_accuracy_pct"] if summary["is_full_900"] else summary["accuracy_pct"]
    lines.append(f"| {label} | {len(results)} | {sum(r['correct'] for r in results)} | {accuracy:.2f} |")
    (args.output_dir / "scores.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)
    print(f"Results: {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
