from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest

from evidence_review.validation import (
    validate_review_request,
    validate_review_result,
)

ROOT = Path(__file__).parents[1]
EXAMPLES = ROOT / "examples"


class ExamplesAndEntrypointsTests(unittest.TestCase):
    def load(self, name: str):
        return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))

    def test_all_json_examples_are_valid_and_cross_check(self):
        initial_request = self.load("initial-review-request.json")
        initial_result = self.load("initial-review-output.json")
        closure_request = self.load("closure-review-request.json")
        closure_result = self.load("closure-review-output.json")

        self.assertEqual(validate_review_request(initial_request), [])
        self.assertEqual(validate_review_result(initial_result, initial_request), [])
        self.assertEqual(validate_review_request(closure_request), [])
        self.assertEqual(validate_review_result(closure_result, closure_request), [])

    def test_all_schema_files_are_well_formed_json(self):
        schema_files = sorted((ROOT / "schemas").glob("*.schema.json"))
        self.assertEqual(
            [path.name for path in schema_files],
            [
                "finding.schema.json",
                "review-request.schema.json",
                "review-result.schema.json",
            ],
        )
        for path in schema_files:
            with self.subTest(path=path.name):
                schema = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(
                    schema["$schema"],
                    "https://json-schema.org/draft/2020-12/schema",
                )

    def test_module_entrypoint_validates_example(self):
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "evidence_review",
                "validate-result",
                "examples/closure-review-output.json",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("valid closure review", completed.stdout)

    def test_compatibility_script_validates_example(self):
        completed = subprocess.run(
            [
                sys.executable,
                "scripts/review_policy.py",
                "examples/initial-review-output.json",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("valid initial review", completed.stdout)

    def test_console_entrypoint_is_declared(self):
        project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn(
            'evidence-review = "evidence_review.cli:main"',
            project,
        )
        self.assertIn("dependencies = []", project)


if __name__ == "__main__":
    unittest.main()
