import asyncio
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from checkpointing import atomic_json, append_checkpoint, contract_hash, load_checkpoint, summarize
from repetition_guard import POLICY, RepetitionGuard, aborted_judgment, replay
from streaming_guard import guarded_generate

PHRASE = " ".join("word" + chr(97+i//26) + chr(97+i%26) for i in range(40))


class DetectorTests(unittest.TestCase):
    def test_repeated_long_phrase(self):
        guard = RepetitionGuard()
        self.assertIsNone(guard.check((PHRASE + " ")*8, 1024))
        evidence = guard.check((PHRASE + " ")*12, 1152)
        self.assertIsNotNone(evidence)
        self.assertGreaterEqual(evidence["occurrences"], 4)

    def test_below_minimum_and_short_recheck(self):
        guard = RepetitionGuard()
        self.assertIsNone(guard.check((PHRASE + " ")*10, 512))
        self.assertIsNone(guard.check((PHRASE + " ")*2, 1024))

    def test_numbers_and_tables_not_sufficient(self):
        guard = RepetitionGuard()
        for count in (1024, 1152, 1280):
            self.assertIsNone(guard.check("1 2 3 4 5 6 7 8 9 10 "*count, count))

    def test_unique_long_text(self):
        self.assertFalse(replay(" ".join(f"unique{i}" for i in range(3000)))["detected"])

    def test_old_loop_not_reconfirmed_without_new_occurrence(self):
        guard = RepetitionGuard()
        text = (PHRASE + " ")*8
        self.assertIsNone(guard.check(text, 1024))
        self.assertIsNone(guard.check(text + " finally answer is B", 1152))

    def test_fresh_guard_per_request(self):
        for _ in range(2):
            self.assertIsNone(RepetitionGuard().check((PHRASE + " ")*8, 1024))

    def test_abort_policy_ignores_partial_answer(self):
        row = dict(question_id="x", annotation={"answer": "B"},
                   result={"gen_raw": "Answer: B"}, finish_reason="repetition_abort")
        verdict = aborted_judgment(row)
        self.assertIsNone(verdict["prediction"])
        self.assertIs(verdict["correct"], False)
        self.assertTrue(verdict["judge_skipped"])
        self.assertIsNone(aborted_judgment(dict(row, finish_reason="stop")))

    def test_abort_checkpoint_and_denominator(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = {"selected_ids": ["x"], "repetition_policy": POLICY}
            digest = contract_hash(contract)
            atomic_json(root / "run_config.json", {"checkpoint_contract_hash": digest})
            row = dict(question_id="x", result={"gen": "", "gen_raw": "Answer: B"},
                       prediction=None, correct=False, judge_skipped=True,
                       repetition_evidence={"reason": "loop"}, finish_reason="repetition_abort",
                       generated_tokens=1200, checkpoint_contract_hash=digest)
            with (root / "predictions.jsonl").open("w", encoding="utf-8") as f:
                append_checkpoint(f, row)
            self.assertEqual(len(load_checkpoint(root, contract)), 1)
            report = summarize([row], 1)
            self.assertTrue(report["complete"])
            self.assertEqual(report["repetition_aborted"], 1)
            with self.assertRaises(ValueError):
                load_checkpoint(root, dict(contract, repetition_policy={"enabled": False}))
            row["prediction"] = "B"
            with (root / "predictions.jsonl").open("w", encoding="utf-8") as f:
                append_checkpoint(f, row)
            with self.assertRaises(ValueError):
                load_checkpoint(root, contract)


class FakeEngine:
    def __init__(self, outputs, fail=False):
        self.outputs = outputs
        self.aborts = []
        self.closed = 0
        self.fail = fail

    async def generate(self, prompt, params, request_id):
        try:
            for output in self.outputs:
                yield output
            if self.fail:
                raise RuntimeError("mock engine failure")
        finally:
            self.closed += 1

    async def abort(self, request_id):
        self.aborts.append(request_id)


def output(text, tokens, finished=False, reason=None):
    return SimpleNamespace(finished=finished, prompt_token_ids=[1, 2], outputs=[
        SimpleNamespace(text=text, token_ids=list(range(tokens)), finish_reason=reason)])


class StreamTests(unittest.IsolatedAsyncioTestCase):
    async def test_abort_then_next_request(self):
        engine = FakeEngine([output((PHRASE+" ")*8, 1024), output((PHRASE+" ")*12, 1152)])
        result = await guarded_generate(engine, {}, None, "one", RepetitionGuard())
        self.assertEqual(result.outputs[0].finish_reason, "repetition_abort")
        self.assertEqual(engine.aborts, ["one"])
        self.assertEqual(engine.closed, 1)
        engine.outputs = [output("Answer: B", 4, True, "stop")]
        result = await guarded_generate(engine, {}, None, "two", RepetitionGuard())
        self.assertEqual(result.outputs[0].finish_reason, "stop")
        self.assertEqual(engine.aborts, ["one"])

    async def test_natural_end_not_retroactively_aborted(self):
        engine = FakeEngine([output((PHRASE+" ")*8, 1024),
                             output((PHRASE+" ")*12, 1152, True, "length")])
        result = await guarded_generate(engine, {}, None, "one", RepetitionGuard())
        self.assertEqual(result.outputs[0].finish_reason, "length")
        self.assertEqual(engine.aborts, [])

    async def test_failure_cancels_and_propagates(self):
        engine = FakeEngine([output("hello", 1)], fail=True)
        with self.assertRaises(RuntimeError):
            await guarded_generate(engine, {}, None, "one", RepetitionGuard())
        self.assertEqual(engine.aborts, ["one"])
        self.assertEqual(engine.closed, 1)

    async def test_cancellation_aborts(self):
        class BlockingEngine(FakeEngine):
            async def generate(self, prompt, params, request_id):
                try:
                    await asyncio.sleep(100)
                    yield output("never", 1)
                finally:
                    self.closed += 1
        engine = BlockingEngine([])
        task = asyncio.create_task(guarded_generate(engine, {}, None, "one", RepetitionGuard()))
        await asyncio.sleep(0)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(engine.aborts, ["one"])
        self.assertEqual(engine.closed, 1)


class JudgeIntegrationTests(unittest.TestCase):
    def test_mixed_results_skip_aborted_and_keep_denominator(self):
        import run
        calls = []
        class Tokenizer:
            def apply_chat_template(self, *args, **kwargs):
                return "prompt"
            def encode(self, *args, **kwargs):
                return [1]
        class Engine:
            def __init__(self, **kwargs):
                pass
            def generate(self, *args, **kwargs):
                calls.append(1)
                return [SimpleNamespace(outputs=[SimpleNamespace(
                    text='{"status":"matched","answer":"B","reason":"explicit"}', finish_reason="stop")])]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "predictions.jsonl"
            annotation = {"question": "test", "answer": "B", "A": "one", "B": "two"}
            rows = [dict(question_id="abort", annotation=annotation,
                         result={"gen": "", "gen_raw": "Answer: B"}, finish_reason="repetition_abort"),
                    dict(question_id="normal", annotation=annotation,
                         result={"gen": "Answer: B"}, finish_reason="stop")]
            path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
            args = SimpleNamespace(predictions=path, limit=0, judge_model="mock", judge_context=32768)
            modules = {"transformers": SimpleNamespace(AutoTokenizer=SimpleNamespace(from_pretrained=lambda p: Tokenizer())),
                       "vllm": SimpleNamespace(LLM=Engine, SamplingParams=lambda **kw: kw)}
            with patch.dict("sys.modules", modules), patch.object(run, "snapshot", return_value="mock"):
                run.judge(args, root, {})
            report = json.loads((root / "summary.json").read_text())
            self.assertEqual(len(calls), 1)
            self.assertEqual(report["completed"], 2)
            self.assertEqual(report["accuracy_pct"], 50)
            self.assertEqual(report["repetition_aborted"], 1)
            saved = [json.loads(line) for line in (root / "judgments.jsonl").read_text().splitlines()]
            self.assertFalse(saved[0]["correct"])
            self.assertTrue(saved[0]["judge_skipped"])


if __name__ == "__main__":
    unittest.main()
