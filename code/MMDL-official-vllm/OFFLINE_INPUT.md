# Optional local validation input after TLS download failure

The server clock is synchronized but both requests and curl reject the download
endpoint's certificate as expired. Do not disable TLS verification or change time.
No verified byte-identical replacement TSV has been found. The adapter below is
an explicit alternative, not a silent mirror or a claim of full reproduction.

It reuses the previously saved HF MMMU validation dataset, retaining question text,
option order, IDs and image_N order. Images are exported as RGB PNG, not the
upstream TSV/JPEG pipeline. Equivalence to the Qwen TSV has NOT been verified.
This route makes the input comparable to the earlier HF baseline, but cannot
establish that all input differences from Qwen's reported evaluation are removed.
Prompt construction, resizing budgets, sampling settings and vLLM remain unchanged.

## Apply the small update

Transfer the files in MMDL-official-vllm-offline-fix.zip to the existing school
MMDL-official-vllm directory. Update run.py and add export_local_mmmu.py,
local_input.py, test_local_input.py and this document. Do not replace the venv,
upstream directory or source_hashes.json. No new packages are needed.

## Export using the existing OLD Python (not pip install)

From /home/user/mmdl/MMDL-official-vllm:

```bash
/home/user/mmdl/.venv/bin/python export_local_mmmu.py --data-root /home/user/mmdl/data/mmmu_val_98e6ac0cb9b7b2cd2c991b85a50762edc4aedc68 --output-dir data/local_validation
```

This only executes the old environment's datasets/Pillow; it does not change that
environment. It exports all 900 questions. A partial failed export is preserved;
use a new directory if retrying. Review count=900, question_types and fingerprints.

## Inference using the NEW active venv

```bash
python run.py infer --local-manifest data/local_validation/validation.jsonl --limit 3 --output-dir results/smoke3_local
```

Do not reuse results/smoke3, which already contains the failed run's metadata.
Keep official 128000 context initially. OOM/kernel issues are separate from TLS.
If needed, follow the explicit low-memory option in README and record the change.
This has not yet been GPU-tested here. No paid APIs or remote model runs occurred.

The exporter records dataset fingerprints and PNG checksums; the loader checks
900 unique IDs, 30 x 30 counts and checksums. These detect changes after export,
not authenticity of the original HF revision. Existing datasets/results stay intact.
