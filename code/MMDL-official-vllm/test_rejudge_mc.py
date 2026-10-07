import copy
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from rejudge_mc import (apply_result, eligible, merge_rows, read_rows, schema_for,
                        summary, task_for, validate_extraction)


def row():
    return dict(question_id="one", correct=None, error="invalid_judge_output", gold="C",
        finish_reason="stop", raw_judge_response='{"answer":"C. 16%"}',
        task=dict(kind="multiple-choice", question="Find the return.",
                  options={"A": "14%", "B": "15%", "C": "16%"},
                  candidate_response="My final answer is C. 16%."))


def answer(letter="C", quote="My final answer is C. 16%."):
    return dict(status="matched", answer=letter, evidence_quote=quote, reason="explicit final answer")


class ExtractionTests(unittest.TestCase):
    def test_select_unresolved_only(self):
        r = row()
        self.assertTrue(eligible(r))
        for value in (True, False):
            self.assertFalse(eligible(dict(r, correct=value)))
        self.assertFalse(eligible(dict(r, error="repetition_abort")))
        self.assertFalse(eligible(dict(r, judge_skipped=True)))
        r["task"]["kind"] = "open"
        self.assertFalse(eligible(r))

    def test_gold_and_previous_judge_not_in_task(self):
        r = row()
        r["task"]["gold"] = "SECRET"
        r["task"]["accepted_answers"] = ["SECRET"]
        self.assertEqual(set(task_for(r)), {"question", "options", "candidate_response"})
        self.assertNotIn("SECRET", json.dumps(task_for(r)))
        original_task = task_for(r)
        r["gold"] = "A"
        self.assertEqual(task_for(r), original_task)

    def test_schema_limits_keys_and_allows_abstention(self):
        schema = schema_for(task_for(row()))
        self.assertEqual(schema["properties"]["answer"]["enum"], ["A", "B", "C", None])
        self.assertEqual(schema["properties"]["status"]["enum"], ["matched", "uncertain"])
        self.assertFalse(schema["additionalProperties"])

    def test_extract_then_compare(self):
        r = row()
        before = copy.deepcopy(r)
        new = apply_result(r, json.dumps(answer()), "stop", 10)
        self.assertTrue(new["correct"])
        self.assertEqual(new["prediction"], "C")
        self.assertNotIn("error", new)
        self.assertEqual(new["previous_judge"]["error"], "invalid_judge_output")
        self.assertEqual(r, before)

    def test_wrong_choice_still_extracted(self):
        r = row()
        r["gold"] = "A"
        new = apply_result(r, json.dumps(answer()), "stop", 10)
        self.assertFalse(new["correct"])
        self.assertEqual(new["prediction"], "C")

    def test_out_of_range_and_content_not_allowed(self):
        for letter in ("D", "C. 16%", "16%", None, ["C"]):
            with self.assertRaises(ValueError):
                validate_extraction(answer(letter), task_for(row()))

    def test_correctness_status_rejected(self):
        for status in ("correct", "incorrect"):
            with self.assertRaises(ValueError):
                validate_extraction(dict(answer(), status=status), task_for(row()))

    def test_diagram_label_maps_to_option_key(self):
        r = row()
        r["task"]["options"] = {"A": "E", "B": "B", "C": "C", "D": "A"}
        r["task"]["candidate_response"] = "The diagram region is E."
        r["gold"] = "A"
        new = apply_result(r, json.dumps(answer("A", "The diagram region is E.")), "stop", 10)
        self.assertTrue(new["correct"])
        with self.assertRaises(ValueError):
            validate_extraction(answer("E", "The diagram region is E."), task_for(r))

    def test_fabricated_evidence_rejected(self):
        new = apply_result(row(), json.dumps(answer(quote="Final answer: C")), "stop", 10)
        self.assertIsNone(new["correct"])
        self.assertEqual(new["error"], "evidence_not_in_candidate")

    def test_uncertain_not_forced_to_an_option(self):
        value = dict(status="uncertain", answer=None, evidence_quote="", reason="no conclusion")
        self.assertIsNone(validate_extraction(value, task_for(row())))
        with self.assertRaises(ValueError):
            validate_extraction(dict(value, answer="C"), task_for(row()))
        self.assertIsNone(apply_result(row(), json.dumps(value), "stop", 10)["correct"])

    def test_invalid_truncated_context(self):
        for raw, stop in (("not json", "stop"), (json.dumps(answer()), "length"), ("[]", "stop")):
            self.assertIsNone(apply_result(row(), raw, stop, 10)["correct"])
        new = apply_result(row(), None, None, 40000, "context_budget_exceeded")
        self.assertEqual(new["error"], "context_budget_exceeded")

    def test_merge_keeps_other_rows_and_denominator(self):
        aborted = dict(question_id="abort", correct=False, error="repetition_abort")
        resolved = dict(row(), question_id="resolved", correct=True)
        original = [aborted, row(), resolved]
        retry = apply_result(row(), json.dumps(answer()), "stop", 10)
        merged = merge_rows(original, [retry])
        self.assertEqual(merged[0], aborted)
        self.assertEqual(merged[2], resolved)
        report = summary(merged, [retry], 1)
        self.assertEqual(report["completed"], 3)
        self.assertEqual(report["correct"], 2)
        self.assertEqual(report["repetition_aborted"], 1)
        self.assertEqual(report["remaining_unretried"], 0)

    def test_illegal_retries_rejected(self):
        original = [row()]
        retry = apply_result(row(), json.dumps(answer()), "stop", 10)
        for retries in ([retry, retry], [dict(retry, gold="A")], [dict(retry, question_id="missing")]):
            with self.assertRaises(ValueError):
                merge_rows(original, retries)

    def test_input_duplicate_ids_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "judgments.jsonl"
            text = json.dumps(row())
            path.write_text(text+"\n"+text+"\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                read_rows(path)


class IntegrationTests(unittest.TestCase):
    def test_pipeline_preserves_source_and_uses_constraints(self):
        import rejudge_mc
        captured = []
        class Tokenizer:
            def apply_chat_template(self, messages, **kwargs):
                task = json.loads(messages[1]["content"])
                self_task = set(task)
                if self_task != {"question", "options", "candidate_response"}:
                    raise AssertionError("Unexpected judge input")
                return "prompt"
            def encode(self, *args, **kwargs):
                return [1, 2]
        class Engine:
            def __init__(self, **kwargs):
                pass
            def generate(self, prompts, sampling_params, **kwargs):
                captured.append(sampling_params)
                return [SimpleNamespace(outputs=[SimpleNamespace(text=json.dumps(answer()), finish_reason="stop")])]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model = root / "model"
            model.mkdir()
            (model / "config.json").write_text("{}", encoding="utf-8")
            source = root / "judgments.jsonl"
            original = [row(), dict(row(), question_id="resolved", correct=False),
                        dict(question_id="abort", correct=False, error="repetition_abort")]
            source.write_text("\n".join(json.dumps(r) for r in original), encoding="utf-8")
            before = source.read_bytes()
            out = root / "repair"
            modules = {
                "transformers": SimpleNamespace(AutoTokenizer=SimpleNamespace(from_pretrained=lambda _: Tokenizer())),
                "vllm": SimpleNamespace(LLM=Engine, SamplingParams=lambda **kwargs: kwargs),
                "vllm.sampling_params": SimpleNamespace(StructuredOutputsParams=lambda **kwargs: kwargs)}
            argv = ["rejudge_mc.py", "--judgments", str(source), "--judge-model", str(model), "--output-dir", str(out)]
            with patch.dict("sys.modules", modules), patch("sys.argv", argv), patch.dict("os.environ"), \
                    patch.object(rejudge_mc.importlib.metadata, "version", return_value="0.11.2"):
                rejudge_mc.main()
            self.assertEqual(source.read_bytes(), before)
            self.assertEqual(len(captured), 1)
            schema = captured[0]["structured_outputs"]["json"]
            self.assertEqual(schema["properties"]["answer"]["enum"], ["A", "B", "C", None])
            merged = read_rows(out / "judgments.jsonl")
            self.assertTrue(merged[0]["correct"])
            self.assertEqual(merged[1:], original[1:])
            report = json.loads((out / "summary.json").read_text())
            self.assertEqual(report["completed"], 3)
            self.assertEqual(report["retried"], 1)
            self.assertEqual(report["repetition_aborted"], 1)


if __name__ == "__main__":
    unittest.main()
