"""Export an existing HF validation DatasetDict without network access.

Run with the OLD baseline Python, which already has datasets and Pillow.
This export is not claimed to be byte-equivalent to Qwen's MMMU_DEV_VAL.tsv.
"""
import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

SUBJECTS = set("""Accounting Agriculture Architecture_and_Engineering Art Art_Theory
Basic_Medical_Science Biology Chemistry Clinical_Medicine Computer_Science
Design Diagnostics_and_Laboratory_Medicine Economics Electronics Energy_and_Power
Finance Geography History Literature Manage Marketing Materials Math
Mechanical_Engineering Music Pharmacy Physics Psychology Public_Health Sociology""".split())


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def annotation(sample, subject):
    expected_prefix = f"validation_{subject}_"
    if not sample["id"].startswith(expected_prefix) or not re.fullmatch(r"[A-Za-z0-9_]+", sample["id"]):
        raise ValueError(f"Unexpected ID: {sample['id']}")
    row = dict(index=sample["id"], question=sample["question"], answer=sample["answer"],
               split="validation", category=subject, question_type=sample["question_type"])
    if row["question_type"] == "multiple-choice":
        options = sample["options"]
        options = ast.literal_eval(options) if isinstance(options, str) else options
        if not isinstance(options, list) or not 2 <= len(options) <= 26 or not all(isinstance(x, str) for x in options):
            raise ValueError("Invalid options")
        row.update({chr(65+i): value for i, value in enumerate(options)})
        if row["answer"] not in [chr(65+i) for i in range(len(options))]:
            raise ValueError("Invalid gold option")
    elif row["question_type"] != "open":
        raise ValueError("Unknown question type")
    text = row["question"] + "\n" + "\n".join(str(row.get(k, "")) for k in "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    refs = {int(x) for x in re.findall(r"<image\s+(\d+)>", text)}
    available = [i for i in range(1, 8) if sample.get(f"image_{i}") is not None]
    if not refs or not refs.issubset(available):
        raise ValueError(f"Invalid image references: {sample['id']}")
    if available != list(range(1, max(available)+1)):
        raise ValueError("Image index gaps require explicit review")
    return row, available


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    from datasets import load_from_disk
    data = load_from_disk(str(args.data_root))
    if set(data) != SUBJECTS or any(len(data[s]) != 30 for s in SUBJECTS):
        raise ValueError("Expected 30 subjects with 30 validation samples each")
    rows, seen, counts = [], set(), Counter()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    image_dir = args.output_dir / "images"
    image_dir.mkdir()
    for subject in sorted(data):
        for sample in data[subject]:
            row, available = annotation(sample, subject)
            if row["index"] in seen:
                raise ValueError("Duplicate sample ID")
            seen.add(row["index"])
            paths, hashes = [], []
            for number in available:
                path = image_dir / f"{row['index']}_{number}.png"
                sample[f"image_{number}"].convert("RGB").save(path, format="PNG")
                paths.append(path.relative_to(args.output_dir).as_posix())
                hashes.append(sha256(path))
            row.update(image_path=paths, image_sha256=hashes)
            rows.append(row)
            counts[row["question_type"]] += 1
    output = args.output_dir / "validation.jsonl"
    with output.open("x", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False)+"\n")
    provenance = dict(source="existing Hugging Face DatasetDict loaded from disk", count=len(rows),
                      question_types=dict(counts), source_path=str(args.data_root.resolve()),
                      fingerprints={s: data[s]._fingerprint for s in sorted(data)},
                      upstream_tsv_equivalence_verified=False,
                      revision_note="Local directory name is not proof of HF revision; no independent revision verification.",
                      image_policy="RGB PNG export in original image_N order; not upstream TSV JPEG export",
                      manifest_sha256=sha256(output))
    (args.output_dir / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    print(json.dumps(provenance, indent=2))
    print("Manifest:", output)


if __name__ == "__main__":
    main()
