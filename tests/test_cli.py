import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from pilot.core import oracle
from pilot.data import ROOT


class CLITests(unittest.TestCase):
    def run_cli(self, *args, input=None):
        return subprocess.run([sys.executable, "-m", "pilot", *args],
                              cwd=ROOT, capture_output=True, text=True, input=input)

    def test_export_score_and_overwrite_protection(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "run"
            exported = self.run_cli("export", "--out", str(out))
            self.assertEqual(exported.returncode, 0, exported.stderr)
            cases = json.loads((out / "cases.evaluator-only.json").read_text())
            responses = out / "responses.jsonl"
            responses.write_text("\n".join(json.dumps({"case_id": c["case_id"],
                "choice": oracle(c["options"], c["budget"])[0]}) for c in cases))
            scored = self.run_cli("score", "--cases", str(out / "cases.evaluator-only.json"),
                                 "--responses", str(responses), "--model-id", "test-oracle-NOT-LLM")
            self.assertEqual(scored.returncode, 0, scored.stderr)
            self.assertEqual(json.loads(scored.stdout)["metrics"]["optimal_rate_all"], 1)
            self.assertNotEqual(self.run_cli("export", "--out", str(out)).returncode, 0)

    def test_interactive_questionnaire_and_common_heldout_grid(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "answers.json"
            run = self.run_cli("elicit", "--out", str(out), input="y\n" * 10)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(json.loads(out.read_text())["candidates"], [100])
        run = self.run_cli("demo")
        self.assertEqual(run.returncode, 0, run.stderr)
        result = json.loads(run.stdout)
        self.assertEqual({r["heldout_judgments"] for r in result["elicitation"]}, {10100})
        self.assertIn("NOT_LLM", result["evidence_type"])


if __name__ == "__main__":
    unittest.main()
