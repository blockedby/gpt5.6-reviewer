import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "review_policy.py"
SPEC = importlib.util.spec_from_file_location("review_policy", MODULE_PATH)
review_policy = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(review_policy)


def finding(**overrides):
    value = {
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
    }
    value.update(overrides)
    return value


class ReviewPolicyTests(unittest.TestCase):
    def test_confirmed_serious_introduced_finding_blocks(self):
        self.assertEqual(review_policy.expected_disposition(finding()), "BLOCK")

    def test_confirmed_impact_two_is_follow_up(self):
        item = finding(impact=2, disposition="FOLLOW_UP")
        self.assertEqual(review_policy.expected_disposition(item), "FOLLOW_UP")
        self.assertEqual(review_policy.validate_finding(item), [])

    def test_preexisting_serious_does_not_block_current_change(self):
        item = finding(relationship="pre_existing", disposition="FOLLOW_UP")
        self.assertEqual(review_policy.expected_disposition(item), "FOLLOW_UP")
        self.assertEqual(review_policy.validate_finding(item), [])

    def test_low_confidence_candidate_must_not_reach_final_output(self):
        item = finding(confidence=70)
        self.assertIsNone(review_policy.expected_disposition(item))
        self.assertTrue(any("should not appear" in e for e in review_policy.validate_finding(item)))

    def test_unproven_serious_runtime_concern_is_follow_up(self):
        item = finding(
            confidence=65,
            verification_status="unproven",
            evidence_type="authorized_runtime_check",
            disposition="FOLLOW_UP",
            evidence="Only an authorized staging deploy can resolve this.",
        )
        self.assertEqual(review_policy.expected_disposition(item), "FOLLOW_UP")
        self.assertEqual(review_policy.validate_finding(item), [])

    def test_impact_one_is_omitted(self):
        self.assertIsNone(review_policy.expected_disposition(finding(impact=1)))

    def test_verdicts(self):
        self.assertEqual(review_policy.expected_verdict([finding()]), "NOT_READY")
        self.assertEqual(
            review_policy.expected_verdict([finding(impact=2, disposition="FOLLOW_UP")]),
            "READY_WITH_FOLLOW_UPS",
        )
        self.assertEqual(review_policy.expected_verdict([]), "READY")


if __name__ == "__main__":
    unittest.main()
