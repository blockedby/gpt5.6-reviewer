#!/usr/bin/env python3
"""Backwards-compatible one-argument review-result validator."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# Direct execution sets sys.path[0] to scripts/, so make the repository package
# importable without requiring installation first.
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from evidence_review.io import InputError, read_json  # noqa: E402
from evidence_review.validation import (  # noqa: E402,F401
    BLOCKING_RELATIONSHIPS,
    VALID_DISPOSITIONS,
    VALID_EVIDENCE_TYPES,
    VALID_RELATIONSHIPS,
    VALID_VERDICTS,
    VALID_VERIFICATION,
    expected_disposition,
    expected_verdict,
    validate_finding,
    validate_review,
)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"usage: {argv[0]} REVIEW.json", file=sys.stderr)
        return 2

    try:
        review: Any = read_json(argv[1])
    except InputError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    errors = validate_review(review)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(
        f"valid {review['mode']} review: {review['verdict']} "
        f"({len(review['findings'])} findings)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
