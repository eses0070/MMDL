"""CPU checks for no-download preview and output preservation."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("smoke_vllm.py")


class SmokeCLI(unittest.TestCase):
    def invoke(self, *args):
        return subprocess.run([sys.executable, "-B", str(SCRIPT), *args],
                              capture_output=True, text=True, timeout=10)

    def test_dry_run_has_no_download_or_output_side_effect(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "new_run"
            result = self.invoke("--dry-run", "--limit", "2", "--output-dir", str(output))
            self.assertEqual(result.returncode, 0, result.stderr)
            config = json.loads(result.stdout)
            self.assertEqual(config["cases"], ["red", "blue"])
            self.assertFalse(output.exists())

    def test_existing_output_is_rejected_before_loading_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "keep.txt"
            marker.write_text("existing result", encoding="utf-8")
            result = self.invoke("--output-dir", directory)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("already exists", result.stderr)
            self.assertEqual(marker.read_text(encoding="utf-8"), "existing result")
            self.assertEqual(len(list(Path(directory).iterdir())), 1)

    def test_missing_output_and_out_of_range_limit_are_rejected(self):
        self.assertNotEqual(self.invoke().returncode, 0)
        self.assertNotEqual(self.invoke("--dry-run", "--limit", "0").returncode, 0)


if __name__ == "__main__":
    unittest.main()
