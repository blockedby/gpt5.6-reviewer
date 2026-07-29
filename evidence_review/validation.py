"""Strict structural and policy validation for review contracts."""

from __future__ import annotations

import re
from typing import Any

BLOCKING_RELATIONSHIPS = {"introduced", "regression", "materially_worsened"}
VALID_RELATIONSHIPS = BLOCKING_RELATIONSHIPS | {"pre_existing", "unrelated"}
VALID_EVIDENCE_TYPES = {
    "static_proof",
    "existing_test",
    "runtime_artifact",
    "regression_test",
    "contract_test",
    "local_reproducer",
    "integration_check",
    "authorized_runtime_check",
}
VALID_VERIFICATION = {"not_required", "verified", "unproven"}
VALID_DISPOSITIONS = {"BLOCK", "FOLLOW_UP"}
VALID_VERDICTS = {"READY", "READY_WITH_FOLLOW_UPS", "NOT_READY"}
VALID_CLOSURE_STATUSES = {"fixed", "still_open", "regressed", "not_applicable"}

FINDING_ID_RE = re.compile(r"REV-(?:00[1-9]|0[1-9][0-9]|[1-9][0-9]{2,})\Z")

FINDING_REQUIRED = {
    "id",
    "title",
    "locations",
    "scenario",
    "expected",
    "actual",
    "evidence_type",
    "evidence",
    "impact",
    "confidence",
    "relationship",
    "verification_status",
    "disposition",
    "next_action",
    "retain_regression_test",
}
FINDING_ALLOWED = FINDING_REQUIRED | {"closure_condition"}
RESULT_REQUIRED = {"mode", "base_sha", "head_sha", "verdict", "findings", "summary"}
RESULT_ALLOWED = RESULT_REQUIRED | {"closure"}
REQUEST_REQUIRED = {
    "mode",
    "task",
    "base_sha",
    "head_sha",
    "authorized_checks",
    "forbidden_operations",
}
REQUEST_ALLOWED = REQUEST_REQUIRED | {
    "changed_paths",
    "prior_findings",
    "remediation_diff",
}


def _is_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _object_fields(
    value: Any,
    *,
    path: str,
    required: set[str],
    allowed: set[str],
    errors: list[str],
) -> bool:
    if not isinstance(value, dict):
        errors.append(f"{path} must be an object")
        return False

    for field in sorted(required - value.keys()):
        errors.append(f"{path}.{field} is required")
    for field in sorted(value.keys() - allowed):
        errors.append(f"{path}.{field} is not allowed")
    return True


def _nonempty_string(
    value: Any,
    *,
    path: str,
    errors: list[str],
    max_length: int | None = None,
    min_length: int = 1,
) -> bool:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{path} must be a nonempty string")
        return False
    if len(value) < min_length:
        errors.append(f"{path} must contain at least {min_length} characters")
        return False
    if max_length is not None and len(value) > max_length:
        errors.append(f"{path} must contain at most {max_length} characters")
        return False
    return True


def _string_list(value: Any, *, path: str, errors: list[str]) -> bool:
    if not isinstance(value, list):
        errors.append(f"{path} must be an array")
        return False
    valid = True
    for index, item in enumerate(value):
        if not _nonempty_string(item, path=f"{path}[{index}]", errors=errors):
            valid = False
    return valid


def _enum_string(
    value: Any,
    choices: set[str],
    *,
    path: str,
    errors: list[str],
) -> bool:
    if not isinstance(value, str) or value not in choices:
        errors.append(f"{path} must be one of: {', '.join(sorted(choices))}")
        return False
    return True


def expected_disposition(finding: dict[str, Any]) -> str | None:
    """Return the only final disposition allowed by the documented policy."""
    impact = finding["impact"]
    confidence = finding["confidence"]
    relationship = finding["relationship"]
    verification = finding["verification_status"]

    if impact == 1 or confidence < 50:
        return None

    if verification == "unproven":
        return "FOLLOW_UP" if impact >= 3 and confidence < 80 else None

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


def expected_verdict(findings: list[Any]) -> str:
    """Derive a verdict without crashing while invalid findings are reported."""
    dispositions = {
        finding.get("disposition")
        for finding in findings
        if isinstance(finding, dict)
    }
    if "BLOCK" in dispositions:
        return "NOT_READY"
    if "FOLLOW_UP" in dispositions:
        return "READY_WITH_FOLLOW_UPS"
    return "READY"


def _validate_location(value: Any, *, path: str) -> list[str]:
    errors: list[str] = []
    if not _object_fields(
        value,
        path=path,
        required={"path"},
        allowed={"path", "start_line", "end_line"},
        errors=errors,
    ):
        return errors

    if "path" in value:
        _nonempty_string(value["path"], path=f"{path}.path", errors=errors)

    has_start = "start_line" in value
    has_end = "end_line" in value
    if has_start != has_end:
        errors.append(
            f"{path}.start_line and {path}.end_line must be supplied together"
        )

    for field in ("start_line", "end_line"):
        if field in value and (
            not _is_integer(value[field]) or value[field] < 1
        ):
            errors.append(f"{path}.{field} must be an integer of at least 1")

    if (
        has_start
        and has_end
        and _is_integer(value["start_line"])
        and _is_integer(value["end_line"])
        and value["start_line"] > value["end_line"]
    ):
        errors.append(f"{path}.start_line must not exceed {path}.end_line")
    return errors


def validate_finding(finding: Any, *, path: str = "finding") -> list[str]:
    """Validate one complete final finding."""
    errors: list[str] = []
    if not _object_fields(
        finding,
        path=path,
        required=FINDING_REQUIRED,
        allowed=FINDING_ALLOWED,
        errors=errors,
    ):
        return errors

    if "id" in finding:
        finding_id = finding["id"]
        if not isinstance(finding_id, str) or FINDING_ID_RE.fullmatch(finding_id) is None:
            errors.append(
                f"{path}.id must match a positive canonical ID such as REV-001"
            )

    for field in (
        "scenario",
        "expected",
        "actual",
        "evidence",
        "next_action",
    ):
        if field in finding:
            _nonempty_string(finding[field], path=f"{path}.{field}", errors=errors)
    if "title" in finding:
        _nonempty_string(
            finding["title"],
            path=f"{path}.title",
            errors=errors,
            max_length=120,
        )
    if "closure_condition" in finding:
        _nonempty_string(
            finding["closure_condition"],
            path=f"{path}.closure_condition",
            errors=errors,
        )

    if "locations" in finding:
        locations = finding["locations"]
        if not isinstance(locations, list) or not locations:
            errors.append(f"{path}.locations must be a nonempty array")
        else:
            for index, location in enumerate(locations):
                errors.extend(
                    _validate_location(location, path=f"{path}.locations[{index}]")
                )

    if "impact" in finding and (
        not _is_integer(finding["impact"]) or finding["impact"] not in {1, 2, 3, 4}
    ):
        errors.append(f"{path}.impact must be an integer from 1 through 4")
    if "confidence" in finding and (
        not _is_integer(finding["confidence"])
        or not 0 <= finding["confidence"] <= 100
    ):
        errors.append(f"{path}.confidence must be an integer from 0 through 100")

    enum_fields = (
        ("relationship", VALID_RELATIONSHIPS),
        ("evidence_type", VALID_EVIDENCE_TYPES),
        ("verification_status", VALID_VERIFICATION),
        ("disposition", VALID_DISPOSITIONS),
    )
    enums_valid = True
    for field, choices in enum_fields:
        if field in finding and not _enum_string(
            finding[field],
            choices,
            path=f"{path}.{field}",
            errors=errors,
        ):
            enums_valid = False

    if "retain_regression_test" in finding and not isinstance(
        finding["retain_regression_test"], bool
    ):
        errors.append(f"{path}.retain_regression_test must be a boolean")

    disposition = finding.get("disposition")
    if disposition == "BLOCK" and (
        "closure_condition" not in finding
        or not isinstance(finding.get("closure_condition"), str)
        or not finding["closure_condition"].strip()
    ):
        errors.append(f"{path}.closure_condition is required for BLOCK")

    policy_fields_valid = (
        _is_integer(finding.get("impact"))
        and _is_integer(finding.get("confidence"))
        and finding.get("impact") in {1, 2, 3, 4}
        and 0 <= finding.get("confidence", -1) <= 100
        and isinstance(finding.get("relationship"), str)
        and finding.get("relationship") in VALID_RELATIONSHIPS
        and isinstance(finding.get("verification_status"), str)
        and finding.get("verification_status") in VALID_VERIFICATION
        and isinstance(disposition, str)
        and disposition in VALID_DISPOSITIONS
    )
    if policy_fields_valid and enums_valid:
        expected = expected_disposition(finding)
        if expected is None:
            errors.append(f"{path} must be omitted from a final result under policy")
        elif disposition != expected:
            errors.append(
                f"{path}.disposition {disposition!r} does not match policy "
                f"disposition {expected!r}"
            )
    return errors


def validate_review_request(request: Any) -> list[str]:
    """Validate an initial or closure review request."""
    errors: list[str] = []
    if not _object_fields(
        request,
        path="request",
        required=REQUEST_REQUIRED,
        allowed=REQUEST_ALLOWED,
        errors=errors,
    ):
        return errors

    mode_valid = False
    if "mode" in request:
        mode_valid = _enum_string(
            request["mode"],
            {"initial", "closure"},
            path="request.mode",
            errors=errors,
        )

    if "task" in request:
        _nonempty_string(request["task"], path="request.task", errors=errors)
    for field in ("base_sha", "head_sha"):
        if field in request:
            _nonempty_string(
                request[field],
                path=f"request.{field}",
                errors=errors,
                min_length=7,
            )
    for field in ("changed_paths", "authorized_checks", "forbidden_operations"):
        if field in request:
            _string_list(request[field], path=f"request.{field}", errors=errors)

    mode = request.get("mode") if mode_valid else None
    if mode == "initial":
        for field in ("prior_findings", "remediation_diff"):
            if field in request:
                errors.append(f"request.{field} is not allowed in initial mode")

    if mode == "closure":
        if "prior_findings" not in request:
            errors.append("request.prior_findings is required in closure mode")
        if "remediation_diff" not in request:
            errors.append("request.remediation_diff is required in closure mode")

    prior_findings = request.get("prior_findings")
    if "prior_findings" in request:
        if not isinstance(prior_findings, list) or not prior_findings:
            errors.append("request.prior_findings must be a nonempty array")
        else:
            seen: set[str] = set()
            for index, finding in enumerate(prior_findings):
                finding_path = f"request.prior_findings[{index}]"
                errors.extend(validate_finding(finding, path=finding_path))
                if isinstance(finding, dict):
                    finding_id = finding.get("id")
                    if isinstance(finding_id, str):
                        if finding_id in seen:
                            errors.append(
                                f"request.prior_findings has duplicate id {finding_id}"
                            )
                        seen.add(finding_id)
                    if finding.get("disposition") != "BLOCK":
                        errors.append(f"{finding_path}.disposition must be BLOCK")

    if "remediation_diff" in request:
        _nonempty_string(
            request["remediation_diff"],
            path="request.remediation_diff",
            errors=errors,
        )
    return errors


def _validate_closure_entry(value: Any, *, path: str) -> list[str]:
    errors: list[str] = []
    if not _object_fields(
        value,
        path=path,
        required={"id", "status", "evidence"},
        allowed={"id", "status", "evidence"},
        errors=errors,
    ):
        return errors
    if "id" in value and (
        not isinstance(value["id"], str)
        or FINDING_ID_RE.fullmatch(value["id"]) is None
    ):
        errors.append(
            f"{path}.id must match a positive canonical ID such as REV-001"
        )
    if "status" in value:
        _enum_string(
            value["status"],
            VALID_CLOSURE_STATUSES,
            path=f"{path}.status",
            errors=errors,
        )
    if "evidence" in value:
        _nonempty_string(value["evidence"], path=f"{path}.evidence", errors=errors)
    return errors


def validate_review_result(result: Any, request: Any | None = None) -> list[str]:
    """Validate a final result, optionally against its exact request."""
    errors: list[str] = []
    if not _object_fields(
        result,
        path="result",
        required=RESULT_REQUIRED,
        allowed=RESULT_ALLOWED,
        errors=errors,
    ):
        if request is not None:
            errors.extend(
                f"cross-check {error}" for error in validate_review_request(request)
            )
        return errors

    mode_valid = False
    if "mode" in result:
        mode_valid = _enum_string(
            result["mode"],
            {"initial", "closure"},
            path="result.mode",
            errors=errors,
        )
    if "verdict" in result:
        _enum_string(
            result["verdict"],
            VALID_VERDICTS,
            path="result.verdict",
            errors=errors,
        )
    for field in ("base_sha", "head_sha"):
        if field in result:
            _nonempty_string(
                result[field],
                path=f"result.{field}",
                errors=errors,
                min_length=7,
            )
    if "summary" in result:
        _nonempty_string(
            result["summary"],
            path="result.summary",
            errors=errors,
            max_length=500,
        )

    finding_ids: set[str] = set()
    block_ids: set[str] = set()
    findings = result.get("findings")
    if not isinstance(findings, list):
        if "findings" in result:
            errors.append("result.findings must be an array")
    else:
        for index, finding in enumerate(findings):
            finding_path = f"result.findings[{index}]"
            errors.extend(validate_finding(finding, path=finding_path))
            if isinstance(finding, dict):
                finding_id = finding.get("id")
                if isinstance(finding_id, str):
                    if finding_id in finding_ids:
                        errors.append(f"result.findings has duplicate id {finding_id}")
                    finding_ids.add(finding_id)
                    if finding.get("disposition") == "BLOCK":
                        block_ids.add(finding_id)

        if (
            isinstance(result.get("verdict"), str)
            and result.get("verdict") in VALID_VERDICTS
        ):
            calculated = expected_verdict(findings)
            if result["verdict"] != calculated:
                errors.append(
                    f"result.verdict {result['verdict']!r} does not match "
                    f"findings-derived verdict {calculated!r}"
                )

    mode = result.get("mode") if mode_valid else None
    if mode == "initial" and "closure" in result:
        errors.append("result.closure is not allowed in initial mode")
    if mode == "closure" and "closure" not in result:
        errors.append("result.closure is required in closure mode")

    closure_ids: set[str] = set()
    closure = result.get("closure")
    if "closure" in result:
        if not isinstance(closure, list):
            errors.append("result.closure must be an array")
        elif not closure:
            errors.append("result.closure must be a nonempty array")
        else:
            for index, entry in enumerate(closure):
                entry_path = f"result.closure[{index}]"
                errors.extend(_validate_closure_entry(entry, path=entry_path))
                if not isinstance(entry, dict):
                    continue
                closure_id = entry.get("id")
                if isinstance(closure_id, str):
                    if closure_id in closure_ids:
                        errors.append(f"result.closure has duplicate id {closure_id}")
                    closure_ids.add(closure_id)
                status = entry.get("status")
                if (
                    isinstance(closure_id, str)
                    and isinstance(status, str)
                    and status in {"still_open", "regressed"}
                    and closure_id not in block_ids
                ):
                    errors.append(
                        f"{entry_path} status {status!r} requires a BLOCK "
                        f"finding with id {closure_id}"
                    )
                if (
                    isinstance(closure_id, str)
                    and isinstance(status, str)
                    and status in {"fixed", "not_applicable"}
                    and closure_id in finding_ids
                ):
                    errors.append(
                        f"{entry_path} status {status!r} cannot retain a "
                        f"finding with id {closure_id}"
                    )

    if request is not None:
        request_errors = validate_review_request(request)
        errors.extend(f"cross-check {error}" for error in request_errors)
        if not request_errors:
            for field in ("mode", "base_sha", "head_sha"):
                if result.get(field) != request.get(field):
                    errors.append(
                        f"cross-check result.{field} must equal request.{field}"
                    )
            if request.get("mode") == "closure" and isinstance(closure, list):
                prior_ids = {
                    finding["id"]
                    for finding in request["prior_findings"]
                    if isinstance(finding, dict) and isinstance(finding.get("id"), str)
                }
                if closure_ids != prior_ids:
                    missing = sorted(prior_ids - closure_ids)
                    unexpected = sorted(closure_ids - prior_ids)
                    details: list[str] = []
                    if missing:
                        details.append(f"missing {', '.join(missing)}")
                    if unexpected:
                        details.append(f"unexpected {', '.join(unexpected)}")
                    errors.append(
                        "cross-check result.closure ids must exactly match "
                        f"request.prior_findings ids ({'; '.join(details)})"
                    )
    return errors


# Backwards-compatible name used by scripts/review_policy.py and older callers.
validate_review = validate_review_result
