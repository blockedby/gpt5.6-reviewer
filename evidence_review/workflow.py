"""Pure builders and routing decisions for the review workflow."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def new_initial_request(
    *,
    task: str,
    base_sha: str,
    head_sha: str,
    changed_paths: list[str],
    authorized_checks: list[str],
    forbidden_operations: list[str],
) -> dict[str, Any]:
    """Build an initial review request."""
    return {
        "mode": "initial",
        "task": task,
        "base_sha": base_sha,
        "head_sha": head_sha,
        "changed_paths": list(changed_paths),
        "authorized_checks": list(authorized_checks),
        "forbidden_operations": list(forbidden_operations),
    }


def route_result(result: dict[str, Any]) -> dict[str, Any]:
    """Return the owner-routing instruction for a valid result."""
    if result["verdict"] == "NOT_READY":
        return {
            "action": "remediate",
            "blocking_findings": [
                deepcopy(finding)
                for finding in result["findings"]
                if finding["disposition"] == "BLOCK"
            ],
        }
    return {
        "action": "finish",
        "verdict": result["verdict"],
    }


def prepare_closure_request(
    *,
    request: dict[str, Any],
    result: dict[str, Any],
    head_sha: str,
    remediation_diff: str,
    authorized_checks: list[str],
    forbidden_operations: list[str],
) -> dict[str, Any]:
    """Build the next closure request from a valid request/result pair."""
    original_blockers = {
        finding["id"]: finding
        for finding in request.get("prior_findings", [])
        if finding.get("disposition") == "BLOCK"
    }
    closure_request: dict[str, Any] = {
        "mode": "closure",
        "task": request["task"],
        "base_sha": result["head_sha"],
        "head_sha": head_sha,
        "authorized_checks": list(authorized_checks),
        "forbidden_operations": list(forbidden_operations),
        "prior_findings": [
            deepcopy(original_blockers.get(finding["id"], finding))
            for finding in result["findings"]
            if finding["disposition"] == "BLOCK"
        ],
        "remediation_diff": remediation_diff,
    }
    if "changed_paths" in request:
        closure_request["changed_paths"] = deepcopy(request["changed_paths"])
    return closure_request
