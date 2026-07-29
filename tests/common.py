from __future__ import annotations

from copy import deepcopy
from typing import Any


def finding(**overrides: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "id": "REV-001",
        "title": "Wrong resource is deleted",
        "locations": [{"path": "cleanup.py", "start_line": 10, "end_line": 20}],
        "scenario": "A mutable tag changes after validation.",
        "expected": "Only the validated image is removed.",
        "actual": "The image referenced by the changed tag is removed.",
        "evidence_type": "static_proof",
        "evidence": "The code validates tag identity and later removes by tag.",
        "impact": 4,
        "confidence": 95,
        "relationship": "introduced",
        "verification_status": "not_required",
        "disposition": "BLOCK",
        "next_action": "Remove by immutable image ID.",
        "retain_regression_test": True,
        "closure_condition": "Cleanup removes only the validated immutable ID.",
    }
    value.update(overrides)
    return value


def follow_up(**overrides: Any) -> dict[str, Any]:
    value = finding(
        id="REV-002",
        impact=2,
        disposition="FOLLOW_UP",
    )
    value.pop("closure_condition")
    value.update(overrides)
    return value


def initial_request(**overrides: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "mode": "initial",
        "task": "Delete only the validated immutable resource.",
        "base_sha": "1111111",
        "head_sha": "2222222",
        "changed_paths": ["cleanup.py"],
        "authorized_checks": ["run focused tests"],
        "forbidden_operations": ["production mutation"],
    }
    value.update(overrides)
    return value


def review_result(
    *,
    findings: list[dict[str, Any]] | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    result_findings = deepcopy(findings if findings is not None else [finding()])
    verdict = (
        "NOT_READY"
        if any(item["disposition"] == "BLOCK" for item in result_findings)
        else (
            "READY_WITH_FOLLOW_UPS"
            if result_findings
            else "READY"
        )
    )
    value: dict[str, Any] = {
        "mode": "initial",
        "base_sha": "1111111",
        "head_sha": "2222222",
        "verdict": verdict,
        "findings": result_findings,
        "summary": "Review completed with evidence.",
    }
    value.update(overrides)
    return value


def closure_request(**overrides: Any) -> dict[str, Any]:
    value = initial_request(
        mode="closure",
        prior_findings=[finding()],
        remediation_diff="diff --git a/cleanup.py b/cleanup.py\n",
    )
    value.update(overrides)
    return value


def closure_result(
    *,
    findings: list[dict[str, Any]] | None = None,
    closure: list[dict[str, Any]] | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    value = review_result(
        findings=[] if findings is None else findings,
        mode="closure",
        closure=(
            [
                {
                    "id": "REV-001",
                    "status": "fixed",
                    "evidence": "The focused reproducer now passes.",
                }
            ]
            if closure is None
            else closure
        ),
    )
    value.update(overrides)
    return value
