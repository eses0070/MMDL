"""Read-only readiness check. No model downloads, installs, or training."""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys


PACKAGES = ("torch", "vllm", "transformers", "qwen-vl-utils", "Pillow",
            "huggingface-hub", "peft", "trl", "datasets")
EXPECTED = {"torch": "2.9.0", "vllm": "0.11.2", "transformers": "4.57.1",
            "qwen-vl-utils": "0.0.14"}


def package_versions():
    result = {}
    for name in PACKAGES:
        try:
            result[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            result[name] = None
    return result


def command(args):
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=30)
        return {"returncode": proc.returncode, "stdout": proc.stdout.strip(),
                "stderr": proc.stderr.strip()}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"returncode": None, "error": str(exc)}


def collect(skip_cuda=False):
    versions = package_versions()
    issues = []
    for name, expected in EXPECTED.items():
        actual = versions[name]
        if actual is None or actual.split("+")[0] != expected:
            issues.append(f"{name}: expected {expected}, found {actual}")
    for name in ("Pillow", "huggingface-hub"):
        if versions[name] is None:
            issues.append(f"Missing inference dependency: {name}")
    if platform.system() != "Linux":
        issues.append("The GPU smoke test is intended for the school Linux host/container.")
    shared = []
    for path in (Path("/shared_dir"), Path.home() / "shared_dir"):
        if path.is_dir():
            shared.append({"path": str(path.resolve()), "writable": os.access(path, os.W_OK),
                           "free_gib": round(shutil.disk_usage(path).free / 2**30, 2)})
    cuda = {"checked": False}
    if not skip_cuda:
        try:
            import torch
            cuda = {"checked": True, "available": torch.cuda.is_available(),
                    "runtime": torch.version.cuda}
            if cuda["available"]:
                cuda.update(gpu=torch.cuda.get_device_name(0),
                            bf16=torch.cuda.is_bf16_supported(),
                            calculation=(torch.ones(1, device="cuda") + 1).tolist())
                if not cuda["bf16"]:
                    issues.append("BF16 is required by this smoke configuration.")
            else:
                issues.append("CUDA is not available.")
        except Exception as exc:
            cuda = {"checked": True, "error": repr(exc)}
            issues.append("CUDA check failed.")
    pip_check = command([sys.executable, "-m", "pip", "check"])
    if pip_check["returncode"] != 0:
        issues.append("pip check did not pass; inspect its output.")
    return {"python": sys.version, "python_executable": sys.executable,
            "platform": platform.platform(), "cwd": str(Path.cwd()),
            "virtual_env": os.environ.get("VIRTUAL_ENV"), "packages": versions,
            "cuda": cuda, "pip_check": pip_check,
            "gpu_processes": command(["nvidia-smi", "--query-compute-apps=pid,process_name,used_memory",
                                      "--format=csv"]),
            "shared_directories": shared, "hf_home": os.environ.get("HF_HOME"),
            "issues": issues, "ready_for_gpu_smoke": not issues and not skip_cuda,
            "training_readiness": "Not checked. Teacher, data, and SFT/GSPO trainer are not configured."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-cuda", action="store_true", help="Metadata only; not a GPU readiness pass")
    args = parser.parse_args()
    report = collect(args.skip_cuda)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not report["issues"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
