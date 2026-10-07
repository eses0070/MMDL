import ast
import copy
import unittest

import run
from checkpointing import contract_hash


class CotTests(unittest.TestCase):
    def messages(self):
        return [{"role": "user", "content": [
            {"type": "image", "image": "example.png", "max_pixels": 4014080},
            {"type": "text", "text": "Question: example\nOptions:\nA. one\nB. two"}]}]

    def test_exact_upstream_suffix(self):
        tree = ast.parse((run.UPSTREAM / "run_mmmu.py").read_text(encoding="utf-8"))
        matches = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant)
                   and isinstance(n.value, str)
                   and n.value.startswith(" If you are uncertain or the problem is too complex")]
        self.assertEqual(matches, [run.OFFICIAL_COT_PROMPT])

    def test_disabled_unchanged(self):
        messages = self.messages()
        original = copy.deepcopy(messages)
        self.assertEqual(run.apply_cot(messages, False), original)

    def test_only_text_suffix_changes(self):
        messages = self.messages()
        original = copy.deepcopy(messages)
        run.apply_cot(messages, True)
        self.assertEqual(messages[0]["content"][0], original[0]["content"][0])
        self.assertEqual(messages[0]["content"][-1]["text"],
                         original[0]["content"][-1]["text"] + run.OFFICIAL_COT_PROMPT)

    def test_contract_distinguishes_prompt(self):
        self.assertNotEqual(contract_hash({"prompt_protocol": {"use_cot": False}}),
                            contract_hash({"prompt_protocol": {"use_cot": True}}))


if __name__ == "__main__":
    unittest.main()
