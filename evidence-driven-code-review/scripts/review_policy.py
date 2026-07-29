#!/usr/bin/env python3
"""Validate final evidence-driven review outputs using the standard library."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

BLOCKING_RELATIONSHIPS = {"introduced", "regression", "materially_worsened"}
VALID_RELATIONSHIPS = BLOCKING_RELATIONSHIPS | {"pre_existing", "unrelated"}
VALID_EVIDENCE_TYPES = {
    "static_proof", "existing_test", "runtime_artifact", "regression_test",
    "contract_test", "local_reproducer", "integration_check",
    "authorized_runtime_check",
}
VALID_VERIFICATION = {"not_required", "verified", "unproven"}
VALID_DISPOSITIONS = {"BLOCK", "FOLLOW_UP"}
VALID_VERDICTS = {"READY", "READY_WITH_FOLLOW_UPS", "NOT_READY"}


def expected_disposition(finding: dict[str, Any]) -> str | None:
    impact = finding["impact"]
    confidence = finding["confidence"]
    relationship = finding["relationship"]
    verification = finding["verification_status"]

    if impact == 1 or confidence < 50:
        return None

    if verification == "unproven":
        return "FOLLOW_UP" if impact >= 3 else None

    if (
        confidence >= 80
        and impact >= 3
        and relationship in BLOCKING_RELATIONSHIPS
        and verification in {"verified", "not_required"}
    ):
        return "BLOCK"

    if confidence >= 80 and impact >= 2:
        return "FOLLOW_UP"

    return None


def validate_finding(finding: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "id", "title", "locations", "scenario", "expected", "actual",
        "evidence_type", "evidence", "impact", "confidence", "relationship",
        "verification_status", "disposition", "next_action",
        "retain_regression_test",
    }
    missing = sorted(required - finding.keys())
    if missing:
        return [f"missing fields: {', '.join(missing)}"]

    if not isinstance(finding["id"], str) or not finding["id"].startswith("REV-"):
        errors.append("id must start with REV-")
    if finding["impact"] not in {1, 2, 3, 4}:
        errors.append("impact must be 1..4")
    if not isinstance(finding["confidence"], int) or not 0 <= finding["confidence"] <= 100:
        errors.append("confidence must be an integer from 0 to 100")
    if finding["relationship"] not in VALID_RELATIONSHIPS:
        errors.append(f"invalid relationship: {finding['relationship']}")
    if finding["evidence_type"] not in VALID_EVIDENCE_TYPES:
        errors.append(f"invalid evidence_type: {finding['evidence_type']}")
    if finding["verification_status"] not in VALID_VERIFICATION:
        errors.append(f"invalid verification_status: {finding['verification_status']}")
    if finding["disposition"] not in VALID_DISPOSITIONS:
        errors.append(f"invalid disposition: {finding['disposition']}")
    for name in ("title","scenario","expected","actual","evidence","next_action"):
        if not isinstance(finding[name], str) or not finding[name].strip():
            errors.append(f"{name} must be non-empty")
    if not isinstance(finding["locations"], list) or not finding["locations"]:
        errors.append("locations must be a non-empty list")

    expected = expected_disposition(finding)
    if expected is None:
        errors.append("finding should not appear in final output under the policy")
    elif finding["disposition"] != expected:
        errors.append(f"disposition {finding['disposition']} does not match expected {expected}")

    return errors


def expected_verdict(findings: list[dict[str, Any]]) -> str:
    if any(f.get("disposition") == "BLOCK" for f in findings):
        return "NOT_READY"
    if any(f.get("disposition") == "FOLLOW_UP" for f in findings):
        return "READY_WITH_FOLLOW_UPS"
    return "READY"


def validate_review(review: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in ("mode","base_sha","head_sha","verdict","findings","summary"):
        if field not in review:
            errors.append(f"missing top-level field: {field}")
    if errors:
        return errors

    if review["mode"] not in {"initial","closure"}:
        errors.append("mode must be initial or closure")
    if review["verdict"] not in VALID_VERDICTS:
        errors.append(f"invalid verdict: {review['verdict']}")
    if not isinstance(review["findings"], list):
        return errors + ["findings must be a list"]

    ids: set[str] = set()
    for index, finding in enumerate(review["findings"]):
        for error in validate_finding(finding):
            errors.append(f"findings[{index}] {error}")
        finding_id = finding.get("id")
        if finding_id in ids:
            errors.append(f"duplicate finding id: {finding_id}")
        ids.add(finding_id)

    calculated = expected_verdict(review["findings"])
    if review["verdict"] != calculated:
        errors.append(f"verdict {review['verdict']} does not match calculated {calculated}")

    if review["mode"] == "closure" and "closure" not in review:
        errors.append("closure mode requires a closure array")

    return errors


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"usage: {argv[0]} REVIEW.json", file=sys.stderr)
        return 2

    path = Path(argv[1])
    try:
        review = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        print(f"cannot read {path}: {exc}", file=sys.stderr)
        return 2

    errors = validate_review(review)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"valid {review['mode']} review: {review['verdict']} ({len(review['findings'])} findings)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
