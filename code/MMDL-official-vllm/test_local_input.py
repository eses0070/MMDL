import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from export_local_mmmu import annotation, SUBJECTS
from local_input import load_local


class ExportTests(unittest.TestCase):
    def sample(self):
        return dict(id="validation_Accounting_1", question="<image 1> Choose.",
                    options="['first', '<image 2> second']", answer="B",
                    question_type="multiple-choice", image_1=object(), image_2=object())

    def test_options_and_image_order(self):
        row, images = annotation(self.sample(), "Accounting")
        self.assertEqual(images, [1, 2])
        self.assertEqual(row["B"], "<image 2> second")
        self.assertEqual(row["answer"], "B")

    def test_missing_reference_rejected(self):
        sample = self.sample()
        sample["image_2"] = None
        with self.assertRaises(ValueError):
            annotation(sample, "Accounting")

    def test_gap_rejected(self):
        sample = self.sample()
        sample.update(image_2=None, image_3=object(), options=["first", "second"])
        with self.assertRaises(ValueError):
            annotation(sample, "Accounting")

    def test_open_no_choices(self):
        sample = self.sample()
        sample.update(question_type="open", answer="['2', 'two']")
        row, _ = annotation(sample, "Accounting")
        self.assertNotIn("A", row)


class LoaderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        (self.root / "image.png").write_bytes(b"fixture")
        digest = hashlib.sha256(b"fixture").hexdigest()
        self.rows = [dict(index=f"validation_{s}_{i}", category=s, split="validation",
                          image_path=["image.png"], image_sha256=[digest])
                     for s in sorted(SUBJECTS) for i in range(30)]

    def save(self):
        path = self.root / "validation.jsonl"
        path.write_text("\n".join(json.dumps(r) for r in self.rows), encoding="utf-8")
        (self.root / "provenance.json").write_text(json.dumps({
            "manifest_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}), encoding="utf-8")
        return path

    def test_valid(self):
        rows, _ = load_local(self.save())
        self.assertEqual(len(rows), 900)
        self.assertTrue(Path(rows[0]["image_path"][0]).is_absolute())

    def test_duplicate(self):
        self.rows[1]["index"] = self.rows[0]["index"]
        with self.assertRaises(ValueError):
            load_local(self.save())

    def test_changed_image(self):
        path = self.save()
        (self.root / "image.png").write_bytes(b"modified")
        with self.assertRaises(ValueError):
            load_local(path)

    def test_escape(self):
        self.rows[0]["image_path"] = ["../outside.png"]
        with self.assertRaises(ValueError):
            load_local(self.save())

    def test_changed_manifest(self):
        path = self.save()
        path.write_text("{}", encoding="utf-8")
        with self.assertRaises(ValueError):
            load_local(path)


if __name__ == "__main__":
    unittest.main()
