from __future__ import annotations

from io import StringIO
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from evidence_review.cli import main
from evidence_review.validation import validate_review_request
from evidence_review.workflow import prepare_closure_request
from tests.common import (
    closure_request,
    closure_result,
    finding,
    follow_up,
    initial_request,
    review_result,
)

ROOT = Path(__file__).parents[1]


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


class CliTests(unittest.TestCase):
    def run_cli(self, args, *, stdin_text=""):
        stdout = StringIO()
        stderr = StringIO()
        code = main(
            args,
            stdin=StringIO(stdin_text),
            stdout=stdout,
            stderr=stderr,
        )
        return code, stdout.getvalue(), stderr.getvalue()

    def test_new_request_repeated_arguments_and_deterministic_stdout(self):
        args = [
            "new-request",
            "--task",
            "Review the requested change.",
            "--base",
            "1111111",
            "--head",
            "2222222",
            "--changed-path",
            "one.py",
            "--changed-path",
            "two.py",
            "--authorized-check",
            "run unit tests",
            "--forbidden-operation",
            "deploy",
        ]
        first = self.run_cli(args)
        second = self.run_cli(args)
        self.assertEqual(first, second)
        code, stdout, stderr = first
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        request = json.loads(stdout)
        self.assertEqual(request["changed_paths"], ["one.py", "two.py"])
        self.assertEqual(request["authorized_checks"], ["run unit tests"])
        self.assertEqual(validate_review_request(request), [])

    def test_new_request_atomically_replaces_explicit_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "request.json"
            output.write_text("old", encoding="utf-8")
            code, stdout, stderr = self.run_cli(
                [
                    "new-request",
                    "--task",
                    "Review the requested change.",
                    "--base-sha",
                    "1111111",
                    "--head-sha",
                    "2222222",
                    "--output",
                    str(output),
                ]
            )
            self.assertEqual((code, stdout, stderr), (0, "", ""))
            self.assertEqual(json.loads(output.read_text()), initial_request(
                task="Review the requested change.",
                changed_paths=[],
                authorized_checks=[],
                forbidden_operations=[],
            ))
            self.assertEqual(list(Path(directory).glob("*.tmp")), [])

    def test_validate_request_and_result(self):
        code, stdout, stderr = self.run_cli(
            ["validate-request", str(ROOT / "examples/initial-review-request.json")]
        )
        self.assertEqual(code, 0)
        self.assertIn("valid initial review request", stdout)
        self.assertEqual(stderr, "")

        code, stdout, stderr = self.run_cli(
            [
                "validate-result",
                str(ROOT / "examples/initial-review-output.json"),
                "--request",
                str(ROOT / "examples/initial-review-request.json"),
            ]
        )
        self.assertEqual(code, 0)
        self.assertIn("NOT_READY", stdout)
        self.assertEqual(stderr, "")

    def test_route_returns_only_block_findings(self):
        with tempfile.TemporaryDirectory() as directory:
            result_path = Path(directory) / "result.json"
            write_json(
                result_path,
                review_result(findings=[finding(), follow_up()]),
            )
            code, stdout, stderr = self.run_cli(["route", str(result_path)])
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        route = json.loads(stdout)
        self.assertEqual(route["action"], "remediate")
        self.assertEqual([item["id"] for item in route["blocking_findings"]], ["REV-001"])
        self.assertNotIn("REV-002", stdout)

    def test_route_ready_finishes_without_findings(self):
        code, stdout, stderr = self.run_cli(
            ["route", str(ROOT / "examples/closure-review-output.json")]
        )
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(
            json.loads(stdout),
            {"action": "finish", "verdict": "READY"},
        )

    def test_route_reads_stdin(self):
        result_text = (ROOT / "examples/closure-review-output.json").read_text()
        code, stdout, stderr = self.run_cli(["route", "-"], stdin_text=result_text)
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(json.loads(stdout)["action"], "finish")

    def test_prepare_closure_preserves_full_block_and_diff(self):
        request = json.loads(
            (ROOT / "examples/initial-review-request.json").read_text()
        )
        result = json.loads(
            (ROOT / "examples/initial-review-output.json").read_text()
        )
        with tempfile.TemporaryDirectory() as directory:
            request_path = Path(directory) / "request.json"
            result_path = Path(directory) / "result.json"
            diff_path = Path(directory) / "remediation.diff"
            write_json(request_path, request)
            write_json(result_path, result)
            diff_text = "diff --git a/x b/x\n+fixed\n"
            diff_path.write_text(diff_text, encoding="utf-8")

            code, stdout, stderr = self.run_cli(
                [
                    "prepare-closure",
                    "--request",
                    str(request_path),
                    "--result",
                    str(result_path),
                    "--head-sha",
                    "3333333",
                    "--remediation-diff-file",
                    str(diff_path),
                    "--authorized-check",
                    "run focused reproducer",
                    "--forbidden-operation",
                    "deploy",
                ]
            )

        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        closure = json.loads(stdout)
        blocker = next(
            item for item in result["findings"] if item["disposition"] == "BLOCK"
        )
        self.assertEqual(closure["prior_findings"], [blocker])
        self.assertEqual(
            closure["prior_findings"][0]["closure_condition"],
            blocker["closure_condition"],
        )
        self.assertEqual(closure["base_sha"], result["head_sha"])
        self.assertEqual(closure["head_sha"], "3333333")
        self.assertEqual(closure["remediation_diff"], diff_text)
        self.assertEqual(closure["authorized_checks"], ["run focused reproducer"])
        self.assertEqual(closure["forbidden_operations"], ["deploy"])
        self.assertEqual(validate_review_request(closure), [])

    def test_repeated_closure_preserves_original_blocker_object(self):
        original = finding()
        request = closure_request(prior_findings=[original])
        current = finding(
            evidence="New evidence that must not replace the original handoff.",
            closure_condition="A rewritten condition that must not replace the original.",
        )
        result = closure_result(
            findings=[current],
            closure=[
                {
                    "id": "REV-001",
                    "status": "still_open",
                    "evidence": "The original reproducer still fails.",
                }
            ],
        )
        prepared = prepare_closure_request(
            request=request,
            result=result,
            head_sha="3333333",
            remediation_diff="diff\n",
            authorized_checks=[],
            forbidden_operations=[],
        )
        self.assertEqual(prepared["prior_findings"], [original])

    def test_prepare_closure_rejects_result_without_blockers(self):
        with tempfile.TemporaryDirectory() as directory:
            request_path = Path(directory) / "request.json"
            result_path = Path(directory) / "result.json"
            diff_path = Path(directory) / "diff"
            write_json(request_path, initial_request())
            write_json(result_path, review_result(findings=[]))
            diff_path.write_text("diff\n", encoding="utf-8")
            code, stdout, stderr = self.run_cli(
                [
                    "prepare-closure",
                    "--request",
                    str(request_path),
                    "--result",
                    str(result_path),
                    "--head-sha",
                    "3333333",
                    "--remediation-diff-file",
                    str(diff_path),
                ]
            )
        self.assertEqual(code, 1)
        self.assertEqual(stdout, "")
        self.assertIn("no BLOCK findings", stderr)

    def test_prepare_closure_rejects_multiple_stdin_inputs(self):
        code, stdout, stderr = self.run_cli(
            [
                "prepare-closure",
                "--request",
                "-",
                "--result",
                str(ROOT / "examples/initial-review-output.json"),
                "--head-sha",
                "3333333",
                "--remediation-diff-file",
                "-",
            ],
            stdin_text="{}",
        )
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertIn("only one", stderr)

    def test_invalid_policy_data_returns_one(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            write_json(path, initial_request(extra=True))
            code, stdout, stderr = self.run_cli(["validate-request", str(path)])
        self.assertEqual(code, 1)
        self.assertEqual(stdout, "")
        self.assertIn("ERROR:", stderr)

    def test_malformed_json_and_missing_file_return_two(self):
        with tempfile.TemporaryDirectory() as directory:
            malformed = Path(directory) / "malformed.json"
            malformed.write_text("{broken", encoding="utf-8")
            code, stdout, stderr = self.run_cli(
                ["validate-result", str(malformed)]
            )
            self.assertEqual(code, 2)
            self.assertEqual(stdout, "")
            self.assertIn("cannot parse JSON", stderr)

            missing = Path(directory) / "missing.json"
            code, stdout, stderr = self.run_cli(["route", str(missing)])
            self.assertEqual(code, 2)
            self.assertEqual(stdout, "")
            self.assertIn("cannot read", stderr)

    def test_duplicate_keys_and_nonstandard_numbers_return_two(self):
        with tempfile.TemporaryDirectory() as directory:
            duplicate = Path(directory) / "duplicate.json"
            duplicate.write_text(
                '{"mode":"initial","mode":"closure"}',
                encoding="utf-8",
            )
            code, stdout, stderr = self.run_cli(
                ["validate-request", str(duplicate)]
            )
            self.assertEqual(code, 2)
            self.assertEqual(stdout, "")
            self.assertIn("duplicate object key 'mode'", stderr)

            nonstandard = Path(directory) / "nonstandard.json"
            nonstandard.write_text('{"confidence":NaN}', encoding="utf-8")
            code, stdout, stderr = self.run_cli(
                ["validate-result", str(nonstandard)]
            )
            self.assertEqual(code, 2)
            self.assertEqual(stdout, "")
            self.assertIn("non-standard numeric constant NaN", stderr)

    def test_usage_error_returns_two(self):
        completed = subprocess.run(
            [sys.executable, "-m", "evidence_review", "new-request"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("usage:", completed.stderr)


if __name__ == "__main__":
    unittest.main()
