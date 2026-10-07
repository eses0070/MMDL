"""Validated local input adapter; never downloads data or evaluates text as code."""
from collections import Counter
import hashlib
import json
from pathlib import Path


def load_local(path):
    path = Path(path).resolve()
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    provenance = json.loads(path.with_name("provenance.json").read_text(encoding="utf-8"))
    if digest != provenance["manifest_sha256"]:
        raise ValueError("Local manifest checksum mismatch")
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    ids = [r["index"] for r in rows]
    counts = Counter(r["category"] for r in rows)
    if len(ids) != 900 or len(set(ids)) != 900 or len(counts) != 30 or set(counts.values()) != {30}:
        raise ValueError("Expected unique 900 IDs, 30 subjects x 30")
    for row in rows:
        if row["split"] != "validation":
            raise ValueError("Only validation is supported by the local adapter")
        paths, hashes = row["image_path"], row.pop("image_sha256")
        if not paths or len(paths) != len(hashes):
            raise ValueError("Image manifest mismatch")
        resolved = []
        for name, expected in zip(paths, hashes):
            image = (path.parent / name).resolve()
            if not image.is_relative_to(path.parent):
                raise ValueError("Image path outside export directory")
            if hashlib.sha256(image.read_bytes()).hexdigest() != expected:
                raise ValueError(f"Image checksum mismatch: {name}")
            resolved.append(str(image))
        row["image_path"] = resolved
    return rows, dict(provenance, manifest_sha256=digest)
