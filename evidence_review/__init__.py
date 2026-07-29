"""Dependency-free contracts for evidence-driven code review."""

from .validation import (
    expected_disposition,
    expected_verdict,
    validate_finding,
    validate_review_request,
    validate_review_result,
)

__all__ = [
    "expected_disposition",
    "expected_verdict",
    "validate_finding",
    "validate_review_request",
    "validate_review_result",
]

__version__ = "0.2.0"
