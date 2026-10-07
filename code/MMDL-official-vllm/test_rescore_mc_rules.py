import copy
import unittest

from rescore_mc_rules import extract_terminal, rescore


class RuleTests(unittest.TestCase):
    def test_terminal_formats(self):
        for text in ("Answer: B", "### Final Answer: **B. $7**", "B", "The correct answer is B."):
            self.assertEqual(extract_terminal(text, {"A": "$6", "B": "$7"})[0], "B")

    def test_no_guess_or_intermediate(self):
        for text in ("Perhaps the answer is B", "Answer: B\nBut wait, let me recalculate.",
                     "Total variable costs = $7", "Answer: B because it is correct", "Answer: Z",
                     "Answer: B. $6", "", "Option B is $7"):
            self.assertIsNone(extract_terminal(text, {"A": "$6", "B": "$7"})[0])

    def test_does_not_use_gold_or_change_original(self):
        source = dict(question_id="x", correct=None, gold="A", task=dict(
            question="q", kind="multiple-choice", options={"A": "one", "B": "two"},
            candidate_response="Answer: B"))
        retry = dict(copy.deepcopy(source), correct=True, prediction="A")
        before = copy.deepcopy(source)
        rows, audit, report = rescore([source], [retry])
        self.assertEqual(source, before)
        self.assertFalse(rows[0]["correct"])
        self.assertEqual(rows[0]["prediction"], "B")
        self.assertIsNone(rows[0]["reasoning_correct"])

    def test_missing_answer_policy(self):
        source = dict(question_id="x", correct=None, gold="A", task=dict(
            question="q", kind="multiple-choice", options={"A": "one", "B": "two"},
            candidate_response="Still calculating"))
        rows, _, _ = rescore([source], [copy.deepcopy(source)])
        self.assertFalse(rows[0]["correct"])
        self.assertIsNone(rows[0]["answer_correct"])

    def test_partial_retry_rejected(self):
        source = dict(question_id="x", correct=None, task={"kind": "multiple-choice"})
        with self.assertRaises(ValueError):
            rescore([source], [])


if __name__ == "__main__":
    unittest.main()
