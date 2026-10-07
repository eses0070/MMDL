"""Generate provenance hashes and a portable archive without Git metadata."""
import hashlib
import json
from pathlib import Path
import zipfile

root = Path(__file__).resolve().parent
source = root / "upstream" / "evaluation" / "mmmu"
files = sorted(p for p in source.iterdir() if p.is_file())
(root / "source_hashes.json").write_text(json.dumps(
    {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}, indent=2), encoding="utf-8")
destination = root.parent / "MMDL-official-vllm.zip"
with zipfile.ZipFile(destination, "x", compression=zipfile.ZIP_DEFLATED) as archive:
    for p in list(root.glob("*.py")) + list(root.glob("*.md")) + [root / "requirements.txt", root / "source_hashes.json"] + files:
        archive.write(p, "MMDL-official-vllm/" + p.relative_to(root).as_posix())
    license_path = root / "upstream" / "LICENSE"
    if license_path.exists():
        archive.write(license_path, "MMDL-official-vllm/upstream/LICENSE")
with zipfile.ZipFile(destination) as archive:
    assert archive.testzip() is None
print(destination)
