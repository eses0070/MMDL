"""Three synthetic color images: vLLM execution check, NOT a benchmark or CoT experiment."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import time

from preflight import package_versions


MODEL = "Qwen/Qwen3-VL-4B-Instruct"
REVISION = "ebb281ec70b05090aa6165b016eac8ec08e71b17"
MIN_PIXELS, MAX_PIXELS = 1003520, 4014080
QUESTION = "What is the dominant color of the image? Reply with exactly one lowercase English word."
CASES = (("red", (255, 0, 0)), ("blue", (0, 0, 255)), ("green", (0, 255, 0)))


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--limit", type=int, choices=(1, 2, 3), default=3)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    config = dict(purpose="synthetic_execution_smoke_only", model=MODEL, revision=REVISION,
                  seed=3407, dtype="bfloat16", max_model_len=8192, max_new_tokens=64,
                  temperature=0.0, min_pixels=MIN_PIXELS, max_pixels=MAX_PIXELS,
                  max_num_seqs=1, tensor_parallel_size=1, gpu_memory_utilization=0.8,
                  enforce_eager=True, use_cot=False, repetition_guard=False,
                  prompt=QUESTION, cases=[c[0] for c in CASES[:args.limit]],
                  note="Short synthetic check; different context, sampling and prompt from the MMMU baseline.")
    if args.dry_run:
        print(json.dumps(config, ensure_ascii=False, indent=2))
        return 0
    if args.output_dir is None:
        parser.error("--output-dir is required for GPU execution")
    if args.output_dir.exists():
        parser.error("Output directory already exists. Choose a new directory; nothing was overwritten.")
    if platform.system() != "Linux":
        parser.error("Run the GPU test on the school Linux host/container.")
    # vLLM workers must not fork a process after the CUDA runtime has initialized.
    os.environ.setdefault("VLLM_WORKER_MULTIPROC_METHOD", "spawn")
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    config.update(created_utc=datetime.now(timezone.utc).isoformat(), packages=package_versions(),
                  python=sys.version, python_executable=sys.executable,
                  script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    write_json(output / "run_config.json", config)
    write_json(output / "summary.json", {"completed": 0, "expected": args.limit, "complete": False})
    started = time.perf_counter()
    rows = []
    try:
        import torch
        from huggingface_hub import snapshot_download
        from PIL import Image
        from qwen_vl_utils import process_vision_info
        from transformers import AutoProcessor
        from vllm import LLM, SamplingParams

        if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():
            raise RuntimeError("CUDA with BF16 support is required.")
        print(f"Preparing pinned model {MODEL}@{REVISION}. First use downloads weights.", flush=True)
        model_path = snapshot_download(MODEL, revision=REVISION,
                                       allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model", "*.jinja"])
        config.update(model_snapshot=model_path, gpu=torch.cuda.get_device_name(0),
                      torch_cuda_runtime=torch.version.cuda)
        write_json(output / "run_config.json", config)
        processor = AutoProcessor.from_pretrained(model_path)
        engine = LLM(model=model_path, dtype="bfloat16", seed=3407, tensor_parallel_size=1,
                     max_model_len=config["max_model_len"], max_num_seqs=1,
                     gpu_memory_utilization=0.8, enforce_eager=True,
                     limit_mm_per_prompt={"image": 1},
                     mm_processor_kwargs={"min_pixels": MIN_PIXELS, "max_pixels": MAX_PIXELS})
        params = SamplingParams(temperature=0.0, max_tokens=64, seed=3407)
        for number, (expected, rgb) in enumerate(CASES[:args.limit], 1):
            image_path = output / f"synthetic_{expected}.png"
            Image.new("RGB", (224, 224), rgb).save(image_path)
            messages = [{"role": "user", "content": [
                {"type": "image", "image": str(image_path),
                 "min_pixels": MIN_PIXELS, "max_pixels": MAX_PIXELS},
                {"type": "text", "text": QUESTION}]}]
            text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            images, _, video_kwargs = process_vision_info(
                messages, image_patch_size=processor.image_processor.patch_size,
                return_video_kwargs=True, return_video_metadata=True)
            request = {"prompt": text, "multi_modal_data": {"image": images},
                       "mm_processor_kwargs": video_kwargs}
            token_count = len(processor.tokenizer.encode(text, add_special_tokens=False))
            # vLLM expands image placeholders; this is a text-only preliminary count.
            if token_count + config["max_new_tokens"] > config["max_model_len"]:
                raise RuntimeError("Text prompt exceeds the smoke context budget.")
            begin = time.perf_counter()
            response = engine.generate([request], sampling_params=params, use_tqdm=False)[0]
            completion = response.outputs[0]
            answer = completion.text.strip().lower().strip(".! ")
            row = dict(id=f"synthetic_color_{number}", expected=expected, messages=messages,
                       raw_response=completion.text, parsed_color=answer,
                       color_check=completion.finish_reason == "stop" and answer == expected,
                       finish_reason=completion.finish_reason, generated_tokens=len(completion.token_ids),
                       input_tokens=len(response.prompt_token_ids or []),
                       generation_seconds=time.perf_counter() - begin)
            with (output / "predictions.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            rows.append(row)
            summary = dict(completed=len(rows), expected=args.limit, complete=len(rows) == args.limit,
                           color_checks_passed=sum(r["color_check"] for r in rows),
                           elapsed_seconds_including_load=time.perf_counter() - started,
                           scope="Synthetic execution check only. No training or benchmark scoring.")
            write_json(output / "summary.json", summary)
            print(f"[{number}/{args.limit}] expected={expected} output={completion.text!r} "
                  f"tokens={len(completion.token_ids)} finish={completion.finish_reason}", flush=True)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0 if all(r["color_check"] for r in rows) else 1
    except Exception as exc:
        write_json(output / "error.json", {"type": type(exc).__name__, "error": str(exc),
                                           "completed": len(rows)})
        raise


if __name__ == "__main__":
    raise SystemExit(main())
