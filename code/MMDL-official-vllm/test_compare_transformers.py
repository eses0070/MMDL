import json
from pathlib import Path
import tempfile
import unittest
from compare_transformers import read_case, settings_for, OutputPresencePenalty


class CompareTests(unittest.TestCase):
    def test_selection_and_duplicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rows.jsonl"
            row = json.dumps({"question_id": "target"})
            path.write_text(row, encoding="utf-8")
            self.assertEqual(read_case(path, "target")["question_id"], "target")
            with self.assertRaises(ValueError):
                read_case(path, "missing")
            path.write_text(row + "\n" + row, encoding="utf-8")
            with self.assertRaises(ValueError):
                read_case(path, "target")

    def test_budget_and_penalty_validation(self):
        config = {"checkpoint_contract": {"generation": {"max_tokens": 8192, "repetition_penalty": 1.0}}}
        self.assertEqual(settings_for({"max_new_tokens": 8192}, config)["max_tokens"], 8192)
        with self.assertRaises(ValueError):
            settings_for({"max_new_tokens": 32768}, config)
        config["checkpoint_contract"]["generation"]["repetition_penalty"] = 1.1
        with self.assertRaises(ValueError):
            settings_for({"max_new_tokens": 8192}, config)

    def test_presence_output_only_once(self):
        try:
            import torch
        except ImportError:
            self.skipTest("torch is not installed in this CPU test environment")
        processor = OutputPresencePenalty(2, 1.5)
        scores = torch.zeros(1, 8)
        actual = processor(torch.tensor([[1, 2, 3, 3, 4]]), scores)
        self.assertEqual(actual.tolist(), [[0, 0, 0, -1.5, -1.5, 0, 0, 0]])
        self.assertEqual(processor(torch.tensor([[1, 2]]), torch.zeros(1, 8)).sum().item(), 0)


if __name__ == "__main__":
    unittest.main()
