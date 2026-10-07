import unittest
import run


class RunnerTests(unittest.TestCase):
    def row(self):
        return {"annotation": {"question": "pick", "A": "first", "B": "second", "answer": "B"},
                "result": {"gen": "second"}}

    def test_gold_hidden_mc(self):
        task = run.task_for(self.row())
        self.assertNotIn("accepted_answers", task)
        self.assertEqual(task["kind"], "multiple-choice")

    def test_open(self):
        row = self.row()
        row["annotation"].update(A=None, B=None, answer="['2', 'two']")
        self.assertEqual(run.task_for(row)["accepted_answers"], ["2", "two"])

    def test_matched(self):
        self.assertTrue(run.score({"status": "matched", "answer": "B", "reason": "match"}, run.task_for(self.row()), "B"))

    def test_uncertain(self):
        self.assertIsNone(run.score({"status": "uncertain", "answer": None, "reason": "absent"}, run.task_for(self.row()), "B"))

    def test_invalid(self):
        with self.assertRaises(ValueError):
            run.score({"status": "matched", "answer": "Z", "reason": "bad"}, run.task_for(self.row()), "B")

    def test_settings(self):
        self.assertEqual(run.SETTINGS["seed"], 3407)
        self.assertEqual(run.SETTINGS["max_pixels"], 5120*28*28)
        self.assertEqual(run.SETTINGS["max_tokens"], 32768)


if __name__ == "__main__":
    unittest.main()
