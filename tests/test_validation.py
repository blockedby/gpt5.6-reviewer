from __future__ import annotations

from copy import deepcopy
import unittest

from evidence_review.validation import (
    validate_finding,
    validate_review_request,
    validate_review_result,
)
from tests.common import (
    closure_request,
    closure_result,
    finding,
    follow_up,
    initial_request,
    review_result,
)


class FindingValidationTests(unittest.TestCase):
    def assertInvalid(self, value, fragment: str):
        errors = validate_finding(value)
        self.assertTrue(
            any(fragment in error for error in errors),
            f"{fragment!r} not found in {errors!r}",
        )

    def test_valid_block_and_follow_up(self):
        self.assertEqual(validate_finding(finding()), [])
        self.assertEqual(validate_finding(follow_up()), [])

    def test_id_must_match_exact_pattern(self):
        for invalid_id in (
            "REV-1",
            "REV-000",
            "REV-001-extra",
            "xREV-001",
            "REV-ABC",
        ):
            with self.subTest(invalid_id=invalid_id):
                self.assertInvalid(finding(id=invalid_id), "must match")

    def test_unknown_finding_and_location_fields_are_rejected(self):
        item = finding(extra=True)
        self.assertInvalid(item, ".extra is not allowed")
        item = finding(locations=[{"path": "x.py", "column": 2}])
        self.assertInvalid(item, ".column is not allowed")

    def test_nonempty_strings_and_locations_are_required(self):
        self.assertInvalid(finding(title=" \n"), "title must be a nonempty")
        self.assertInvalid(finding(locations=[]), "locations must be a nonempty")
        self.assertInvalid(finding(locations=[{"path": ""}]), "path must be a nonempty")

    def test_line_ranges_are_complete_positive_and_ordered(self):
        cases = (
            ([{"path": "x.py", "start_line": 3}], "supplied together"),
            (
                [{"path": "x.py", "start_line": 0, "end_line": 2}],
                "at least 1",
            ),
            (
                [{"path": "x.py", "start_line": 4, "end_line": 2}],
                "must not exceed",
            ),
            (
                [{"path": "x.py", "start_line": True, "end_line": 2}],
                "must be an integer",
            ),
        )
        for locations, fragment in cases:
            with self.subTest(locations=locations):
                self.assertInvalid(finding(locations=locations), fragment)

    def test_block_requires_nonempty_closure_condition(self):
        item = finding()
        item.pop("closure_condition")
        self.assertInvalid(item, "closure_condition is required")
        self.assertInvalid(
            finding(closure_condition=" "),
            "closure_condition must be a nonempty",
        )

    def test_disposition_cannot_weaken_blocking_predicate(self):
        item = finding(disposition="FOLLOW_UP")
        item.pop("closure_condition")
        self.assertInvalid(item, "does not match policy")

    def test_boolean_is_not_an_integer_score(self):
        self.assertInvalid(finding(confidence=True), "confidence must be an integer")

    def test_unproven_is_transient_at_confirmed_confidence(self):
        self.assertInvalid(
            finding(confidence=80, verification_status="unproven"),
            "must be omitted",
        )

    def test_malformed_enum_types_report_errors_without_crashing(self):
        self.assertInvalid(finding(relationship=[]), "relationship must be one of")


class RequestValidationTests(unittest.TestCase):
    def assertInvalid(self, value, fragment: str):
        errors = validate_review_request(value)
        self.assertTrue(
            any(fragment in error for error in errors),
            f"{fragment!r} not found in {errors!r}",
        )

    def test_initial_and_closure_requests_are_valid(self):
        self.assertEqual(validate_review_request(initial_request()), [])
        self.assertEqual(validate_review_request(closure_request()), [])

    def test_unknown_fields_and_blank_array_items_are_rejected(self):
        self.assertInvalid(initial_request(extra="x"), ".extra is not allowed")
        self.assertInvalid(
            initial_request(authorized_checks=[" "]),
            "authorized_checks[0] must be a nonempty",
        )

    def test_initial_request_rejects_closure_fields(self):
        self.assertInvalid(
            initial_request(prior_findings=[finding()]),
            "not allowed in initial mode",
        )

    def test_closure_requires_full_unique_blockers_and_diff(self):
        request = closure_request()
        request.pop("remediation_diff")
        self.assertInvalid(request, "remediation_diff is required")

        self.assertInvalid(
            closure_request(prior_findings=[finding(), finding()]),
            "duplicate id",
        )
        self.assertInvalid(
            closure_request(prior_findings=[follow_up()]),
            "disposition must be BLOCK",
        )


class ResultValidationTests(unittest.TestCase):
    def assertInvalid(self, value, fragment: str, request=None):
        errors = validate_review_result(value, request)
        self.assertTrue(
            any(fragment in error for error in errors),
            f"{fragment!r} not found in {errors!r}",
        )

    def test_initial_and_closure_results_are_valid(self):
        self.assertEqual(validate_review_result(review_result()), [])
        self.assertEqual(validate_review_result(closure_result()), [])

    def test_unknown_fields_are_rejected_at_all_levels(self):
        self.assertInvalid(review_result(extra=True), ".extra is not allowed")
        result = closure_result()
        result["closure"][0]["extra"] = True
        self.assertInvalid(result, ".extra is not allowed")

    def test_finding_ids_and_closure_ids_are_unique(self):
        self.assertInvalid(
            review_result(findings=[finding(), finding()]),
            "findings has duplicate id",
        )
        self.assertInvalid(
            closure_result(
                closure=[
                    {"id": "REV-001", "status": "fixed", "evidence": "one"},
                    {"id": "REV-001", "status": "fixed", "evidence": "two"},
                ]
            ),
            "closure has duplicate id",
        )

    def test_verdict_is_derived_from_findings(self):
        self.assertInvalid(
            review_result(verdict="READY"),
            "findings-derived verdict",
        )

    def test_malformed_verdict_type_reports_error_without_crashing(self):
        self.assertInvalid(review_result(verdict=[]), "verdict must be one of")

    def test_non_object_finding_reports_error_without_crashing(self):
        result = review_result(findings=[], verdict="READY")
        result["findings"] = [None]
        self.assertInvalid(result, "result.findings[0] must be an object")

    def test_closure_presence_depends_on_mode(self):
        self.assertInvalid(
            review_result(closure=[]),
            "not allowed in initial mode",
        )
        result = closure_result()
        result.pop("closure")
        self.assertInvalid(result, "required in closure mode")
        self.assertInvalid(
            closure_result(closure=[]),
            "closure must be a nonempty array",
        )

    def test_open_status_requires_same_id_block(self):
        self.assertInvalid(
            closure_result(
                closure=[
                    {
                        "id": "REV-001",
                        "status": "still_open",
                        "evidence": "The reproducer still fails.",
                    }
                ]
            ),
            "requires a BLOCK finding",
        )

    def test_fixed_status_cannot_retain_same_id_finding(self):
        self.assertInvalid(
            closure_result(findings=[finding()]),
            "cannot retain a finding",
        )
        self.assertInvalid(
            closure_result(findings=[follow_up(id="REV-001")]),
            "cannot retain a finding",
        )

    def test_cross_check_identity_fields(self):
        request = initial_request()
        for field in ("mode", "base_sha", "head_sha"):
            result = review_result()
            result[field] = "closure" if field == "mode" else "9999999"
            if field == "mode":
                result["closure"] = []
            with self.subTest(field=field):
                self.assertInvalid(result, f"result.{field}", request)

    def test_cross_check_closure_ids_match_exactly(self):
        request = closure_request(prior_findings=[finding(), finding(id="REV-003")])
        result = closure_result()
        self.assertInvalid(result, "ids must exactly match", request)

        matching = deepcopy(result)
        matching["closure"].append(
            {
                "id": "REV-003",
                "status": "not_applicable",
                "evidence": "The second scenario cannot occur after the fix.",
            }
        )
        self.assertEqual(validate_review_result(matching, request), [])


if __name__ == "__main__":
    unittest.main()
