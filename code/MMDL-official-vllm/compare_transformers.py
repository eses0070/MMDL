"""Replay one saved vLLM input with Transformers; not a bitwise equivalence test."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import time


def read_case(path, question_id):
    matches = [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines()
               if line.strip()]
    matches = [row for row in matches if row["question_id"] == question_id]
    if len(matches) != 1:
        raise ValueError(f"Expected one matching record, found {len(matches)}")
    return matches[0]


def settings_for(row, config):
    settings = config["checkpoint_contract"]["generation"]
    if settings["repetition_penalty"] != 1.0:
        raise ValueError("This comparison supports repetition_penalty=1 only")
    if settings["max_tokens"] != row["max_new_tokens"]:
        raise ValueError("Record and config token budgets disagree")
    return dict(settings)


class OutputPresencePenalty:
    """Subtract once for each token seen in the generated suffix, not the prompt."""
    def __init__(self, prompt_length, penalty):
        self.prompt_length = prompt_length
        self.penalty = penalty

    def __call__(self, input_ids, scores):
        for batch in range(input_ids.shape[0]):
            seen = input_ids[batch, self.prompt_length:].unique()
            scores[batch, seen] -= self.penalty
        return scores


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--predictions", type=Path, required=True)
    p.add_argument("--question-id", default="validation_Accounting_5")
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    row = read_case(args.predictions, args.question_id)
    config_path = args.predictions.parent / "run_config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    settings = settings_for(row, config)
    model_path = Path(config["model_snapshot"])
    if not (model_path / "config.json").is_file():
        raise ValueError(f"Original model snapshot is unavailable: {model_path}")
    image_hashes = {}
    for message in row["messages"]:
        for item in message["content"]:
            if item["type"] == "image":
                path = Path(item["image"])
                image_hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
            elif item["type"] != "text":
                raise ValueError("Only saved image/text messages are supported")
    metadata = dict(question_id=args.question_id, settings=settings,
        model_snapshot=str(model_path), messages=row["messages"], image_sha256=image_hashes,
        source_predictions_sha256=hashlib.sha256(args.predictions.read_bytes()).hexdigest(),
        source_config_sha256=hashlib.sha256(config_path.read_bytes()).hexdigest(),
        source_metrics={k: row.get(k) for k in
            ("input_tokens", "generated_tokens", "finish_reason", "elapsed_seconds")},
        backend="Transformers / SDPA / BF16 / CUDA", seed=row["request_seed"],
        limitations=["Same seed does not imply identical sampling across backends",
            "Presence penalty uses a custom output-only logits processor",
            "Attention kernels, sampling implementations and image processing paths may differ",
            "No judge, no timeout, no repeat cutoff; generation budget inherited from saved run"])
    if args.dry_run:
        print(json.dumps(metadata, ensure_ascii=False, indent=2))
        return

    import torch
    from transformers import (AutoProcessor, GenerationConfig, LogitsProcessorList,
        Qwen3VLForConditionalGeneration, TextStreamer, set_seed)
    from qwen_vl_utils import process_vision_info

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required; no CPU fallback")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    metadata["environment"] = {name: importlib.metadata.version(name)
                               for name in ("torch", "transformers", "qwen-vl-utils")}
    save(args.output_dir / "run_config.json", metadata)
    processor = AutoProcessor.from_pretrained(model_path, local_files_only=True)
    text = processor.apply_chat_template(row["messages"], tokenize=False, add_generation_prompt=True)
    images, videos, video_kwargs = process_vision_info(row["messages"],
        image_patch_size=processor.image_processor.patch_size,
        return_video_kwargs=True, return_video_metadata=True)
    if videos is not None:
        raise ValueError("Video input is not supported by this comparison")
    inputs = processor(text=[text], images=images, padding=True, return_tensors="pt", **video_kwargs)
    prompt_length = inputs.input_ids.shape[1]
    metadata.update(input_tokens=prompt_length,
        image_grid_thw=inputs.image_grid_thw.tolist(),
        resized_image_sizes=[list(im.size) for im in images],
        rendered_prompt=text,
        prompt_token_ids=inputs.input_ids[0].tolist())
    if prompt_length != row["input_tokens"]:
        print(f"WARNING: input token count differs: Transformers={prompt_length}, vLLM={row['input_tokens']}", flush=True)
    context_limit = config["engine_args"]["max_model_len"]
    if prompt_length + settings["max_tokens"] > context_limit:
        raise ValueError("Requested generation exceeds the original context budget")
    print("Loading the original snapshot on CUDA in BF16...", flush=True)
    model = Qwen3VLForConditionalGeneration.from_pretrained(model_path,
        local_files_only=True, dtype=torch.bfloat16, device_map="cuda:0",
        attn_implementation="sdpa").eval()
    eos = model.generation_config.eos_token_id
    if eos is None:
        eos = processor.tokenizer.eos_token_id
    if eos is None:
        raise ValueError("No EOS token configured")
    generation = GenerationConfig(do_sample=True, num_beams=1,
        max_new_tokens=settings["max_tokens"], temperature=settings["temperature"],
        top_p=settings["top_p"], top_k=settings["top_k"], repetition_penalty=1.0,
        eos_token_id=eos, pad_token_id=processor.tokenizer.pad_token_id,
        bos_token_id=processor.tokenizer.bos_token_id, use_cache=True)
    metadata["generation_config"] = generation.to_dict()
    save(args.output_dir / "run_config.json", metadata)
    inputs = inputs.to("cuda:0")
    set_seed(row["request_seed"])
    torch.cuda.synchronize()
    started = time.perf_counter()
    print("Generating one answer (live text follows)...", flush=True)
    with torch.inference_mode():
        output = model.generate(**inputs, generation_config=generation,
            logits_processor=LogitsProcessorList([
                OutputPresencePenalty(prompt_length, settings["presence_penalty"])]),
            streamer=TextStreamer(processor.tokenizer, skip_prompt=True, skip_special_tokens=True))
    torch.cuda.synchronize()
    elapsed = time.perf_counter() - started
    ids = output[0, prompt_length:].tolist()
    raw = processor.tokenizer.decode(ids, skip_special_tokens=True)
    eos_ids = eos if isinstance(eos, list) else [eos]
    stopped = bool(ids and ids[-1] in eos_ids)
    result = dict(question_id=args.question_id, messages=row["messages"],
        annotation=row["annotation"], result={"gen_raw": raw, "gen": raw.split("</think>")[-1].strip()},
        generated_tokens=len(ids), input_tokens=prompt_length,
        finish_reason="stop" if stopped else "length",
        elapsed_generation_seconds=elapsed, scoring="pending")
    save(args.output_dir / "prediction.json", result)
    summary = {k: v for k, v in result.items() if k not in ("messages", "annotation", "result")}
    summary["source_vllm_metrics"] = metadata["source_metrics"]
    summary["timing_note"] = "TF measures generate only; original vLLM timing also included input preparation"
    save(args.output_dir / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
