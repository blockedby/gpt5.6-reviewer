"""Command-line interface for evidence-driven review contracts."""

from __future__ import annotations

import argparse
import sys
from typing import Any, Sequence, TextIO

from .io import InputError, read_json, read_text, write_json
from .validation import validate_review_request, validate_review_result
from .workflow import new_initial_request, prepare_closure_request, route_result


def _add_output_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-o",
        "--output",
        metavar="PATH",
        help="write JSON atomically to PATH instead of stdout; use - for stdout",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="evidence-review",
        description="Build, validate, and route evidence-driven review JSON.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    new_request = subparsers.add_parser(
        "new-request",
        help="create an initial review request",
    )
    new_request.add_argument("--task", required=True)
    new_request.add_argument("--base-sha", "--base", dest="base_sha", required=True)
    new_request.add_argument("--head-sha", "--head", dest="head_sha", required=True)
    new_request.add_argument(
        "--changed-path",
        action="append",
        default=[],
        metavar="PATH",
    )
    new_request.add_argument(
        "--authorized-check",
        action="append",
        default=[],
        metavar="CHECK",
    )
    new_request.add_argument(
        "--forbidden-operation",
        action="append",
        default=[],
        metavar="OPERATION",
    )
    _add_output_argument(new_request)

    validate_request = subparsers.add_parser(
        "validate-request",
        help="validate a review request",
    )
    validate_request.add_argument("request", metavar="REQUEST")

    validate_result = subparsers.add_parser(
        "validate-result",
        help="validate a review result",
    )
    validate_result.add_argument("result", metavar="RESULT")
    validate_result.add_argument(
        "--request",
        metavar="REQUEST",
        help="cross-check result identity and closure IDs against a request",
    )

    route = subparsers.add_parser(
        "route",
        help="emit the machine routing decision for a valid result",
    )
    route.add_argument("result", metavar="RESULT")
    _add_output_argument(route)

    closure = subparsers.add_parser(
        "prepare-closure",
        help="create a closure request from the prior request and result",
    )
    closure.add_argument("--request", required=True, metavar="REQUEST")
    closure.add_argument("--result", required=True, metavar="RESULT")
    closure.add_argument("--head-sha", "--head", dest="head_sha", required=True)
    closure.add_argument(
        "--remediation-diff-file",
        required=True,
        metavar="PATH",
    )
    closure.add_argument(
        "--authorized-check",
        action="append",
        default=[],
        metavar="CHECK",
    )
    closure.add_argument(
        "--forbidden-operation",
        action="append",
        default=[],
        metavar="OPERATION",
    )
    _add_output_argument(closure)
    return parser


def _report_errors(errors: list[str], *, stderr: TextIO) -> int:
    for error in errors:
        print(f"ERROR: {error}", file=stderr)
    return 1


def _require_object(value: Any, label: str) -> tuple[dict[str, Any] | None, list[str]]:
    if not isinstance(value, dict):
        return None, [f"{label} must be a JSON object"]
    return value, []


def _run(
    args: argparse.Namespace,
    *,
    stdin: TextIO,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    if args.command == "new-request":
        request = new_initial_request(
            task=args.task,
            base_sha=args.base_sha,
            head_sha=args.head_sha,
            changed_paths=args.changed_path,
            authorized_checks=args.authorized_check,
            forbidden_operations=args.forbidden_operation,
        )
        errors = validate_review_request(request)
        if errors:
            return _report_errors(errors, stderr=stderr)
        write_json(request, args.output, stdout=stdout)
        return 0

    if args.command == "validate-request":
        raw_request = read_json(args.request, stdin=stdin)
        request, errors = _require_object(raw_request, "request")
        if errors:
            return _report_errors(errors, stderr=stderr)
        assert request is not None
        errors = validate_review_request(request)
        if errors:
            return _report_errors(errors, stderr=stderr)
        print(f"valid {request['mode']} review request", file=stdout)
        return 0

    if args.command == "validate-result":
        raw_result = read_json(args.result, stdin=stdin)
        result, errors = _require_object(raw_result, "result")
        if errors:
            return _report_errors(errors, stderr=stderr)
        request: dict[str, Any] | None = None
        if args.request is not None:
            if args.result == "-" and args.request == "-":
                raise InputError("result and request cannot both read from stdin")
            raw_request = read_json(args.request, stdin=stdin)
            request, request_shape_errors = _require_object(raw_request, "request")
            if request_shape_errors:
                return _report_errors(request_shape_errors, stderr=stderr)
        assert result is not None
        errors = validate_review_result(result, request)
        if errors:
            return _report_errors(errors, stderr=stderr)
        print(
            f"valid {result['mode']} review: {result['verdict']} "
            f"({len(result['findings'])} findings)",
            file=stdout,
        )
        return 0

    if args.command == "route":
        raw_result = read_json(args.result, stdin=stdin)
        result, errors = _require_object(raw_result, "result")
        if errors:
            return _report_errors(errors, stderr=stderr)
        assert result is not None
        errors = validate_review_result(result)
        if errors:
            return _report_errors(errors, stderr=stderr)
        write_json(route_result(result), args.output, stdout=stdout)
        return 0

    if args.command == "prepare-closure":
        stdin_inputs = [
            value
            for value in (
                args.request,
                args.result,
                args.remediation_diff_file,
            )
            if value == "-"
        ]
        if len(stdin_inputs) > 1:
            raise InputError(
                "only one of request, result, and remediation diff may read from stdin"
            )
        raw_request = read_json(args.request, stdin=stdin)
        raw_result = read_json(args.result, stdin=stdin)
        request, errors = _require_object(raw_request, "request")
        if errors:
            return _report_errors(errors, stderr=stderr)
        result, errors = _require_object(raw_result, "result")
        if errors:
            return _report_errors(errors, stderr=stderr)
        assert request is not None
        assert result is not None
        errors = validate_review_result(result, request)
        if errors:
            return _report_errors(errors, stderr=stderr)
        blockers = [
            finding
            for finding in result["findings"]
            if finding["disposition"] == "BLOCK"
        ]
        if not blockers:
            return _report_errors(
                ["result has no BLOCK findings to prepare for closure"],
                stderr=stderr,
            )
        remediation_diff = read_text(args.remediation_diff_file, stdin=stdin)
        closure_request = prepare_closure_request(
            request=request,
            result=result,
            head_sha=args.head_sha,
            remediation_diff=remediation_diff,
            authorized_checks=args.authorized_check,
            forbidden_operations=args.forbidden_operation,
        )
        errors = validate_review_request(closure_request)
        if errors:
            return _report_errors(errors, stderr=stderr)
        write_json(closure_request, args.output, stdout=stdout)
        return 0

    raise AssertionError(f"unhandled command {args.command}")


def main(
    argv: Sequence[str] | None = None,
    *,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """Run the CLI and return its documented process exit code."""
    input_stream = stdin if stdin is not None else sys.stdin
    output_stream = stdout if stdout is not None else sys.stdout
    error_stream = stderr if stderr is not None else sys.stderr
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        return _run(
            args,
            stdin=input_stream,
            stdout=output_stream,
            stderr=error_stream,
        )
    except InputError as exc:
        print(f"ERROR: {exc}", file=error_stream)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
