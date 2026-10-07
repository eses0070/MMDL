import json
from pathlib import Path
import tempfile
import unittest

from checkpointing import append_checkpoint, atomic_json, contract_hash, load_checkpoint, summarize


class CheckpointTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.contract = {"selected_ids": ["a", "b"], "seed": 3407, "max_tokens": 32768}
        self.digest = contract_hash(self.contract)
        atomic_json(self.root / "run_config.json", {"checkpoint_contract_hash": self.digest})
        self.row = dict(question_id="a", checkpoint_contract_hash=self.digest,
                        result={"gen": "Answer: B"}, finish_reason="stop", generated_tokens=4,
                        elapsed_seconds=2, context_budget_limited=False)

    def append(self, row):
        with (self.root / "predictions.jsonl").open("a", encoding="utf-8") as handle:
            append_checkpoint(handle, row)

    def test_empty_resume(self):
        self.assertEqual(load_checkpoint(self.root, self.contract), [])

    def test_saved_resume(self):
        self.append(self.row)
        self.assertEqual(load_checkpoint(self.root, self.contract), [self.row])

    def test_changed_settings_rejected(self):
        with self.assertRaises(ValueError):
            load_checkpoint(self.root, dict(self.contract, max_tokens=8192))

    def test_duplicate_rejected(self):
        self.append(self.row)
        self.append(self.row)
        with self.assertRaises(ValueError):
            load_checkpoint(self.root, self.contract)

    def test_truncated_line_preserved(self):
        path = self.root / "predictions.jsonl"
        path.write_text('{"question_id":', encoding="utf-8")
        before = path.read_bytes()
        with self.assertRaises(ValueError):
            load_checkpoint(self.root, self.contract)
        self.assertEqual(path.read_bytes(), before)

    def test_old_format_rejected(self):
        atomic_json(self.root / "run_config.json", {"settings": {"seed": 3407}})
        with self.assertRaises(ValueError):
            load_checkpoint(self.root, self.contract)

    def test_summary(self):
        report = summarize([self.row], 900)
        self.assertFalse(report["complete"])
        self.assertEqual(report["mean_generated_tokens"], 4)
        self.assertEqual(report["mean_seconds_per_question"], 2)

    def test_atomic_json(self):
        path = self.root / "summary.json"
        atomic_json(path, {"completed": 1})
        atomic_json(path, {"completed": 2})
        self.assertEqual(json.loads(path.read_text())["completed"], 2)
        self.assertFalse(path.with_name("summary.json.tmp").exists())


if __name__ == "__main__":
    unittest.main()
