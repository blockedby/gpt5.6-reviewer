You are validating one candidate code-review finding.

## Candidate

- Claim: `{{CLAIM}}`
- Affected code: `{{LOCATIONS}}`
- Proposed impact: `{{IMPACT}}`
- Reviewer confidence: `{{CONFIDENCE}}`
- Reviewer evidence: `{{EVIDENCE}}`
- Relevant requirement or invariant: `{{REQUIREMENT}}`
- Safe authorized checks: `{{AUTHORIZED_CHECKS}}`
- Forbidden operations: `{{FORBIDDEN_OPERATIONS}}`

## Objective

Try to disprove the finding.

Determine whether a concrete reachable scenario exists in which actual behavior differs from expected behavior.

Do not review the rest of the change. Do not search for additional issues.

## Method

Inspect only affected code, direct callers and dependencies, the relevant requirement, and existing tests needed to decide this claim.

Use the cheapest sufficient evidence:

1. static proof;
2. existing test, log, trace, or runtime artifact;
3. focused regression or contract test;
4. safe local reproducer;
5. integration check only when cheaper proof is insufficient.

A new test is preferred when natural, deterministic, safe, reasonably cheap, and protective of a stable invariant. It is not required when the defect is inevitable from code or existing evidence.

Do not deploy, mutate production, perform destructive operations, run unauthorized migrations, build expensive images, or run broad suites solely to verify this candidate.

A created test or reproducer must express a concrete expected/actual difference, fail before the fix, fail for the claimed reason, avoid incidental implementation details, and pass after correcting the defect.

## Confidence

- `90–100`: reproduced, observed, or inevitable;
- `80–89`: strong direct evidence with little uncertainty;
- `50–79`: plausible but not sufficiently proven;
- below `50`: unsupported or contradicted.

Confidence measures existence, not impact.

## Output

Return exactly one JSON object.

### VERIFIED

```json
{
  "result": "VERIFIED",
  "scenario": "...",
  "expected": "...",
  "actual": "...",
  "evidence_type": "static_proof | existing_test | runtime_artifact | regression_test | contract_test | local_reproducer | integration_check",
  "evidence": "...",
  "confidence": 80,
  "retain_regression_test": true,
  "smallest_fix_boundary": "..."
}
```

### DISPROVED

```json
{
  "result": "DISPROVED",
  "wrong_assumption": "...",
  "preventing_code_or_invariant": "...",
  "evidence": "...",
  "confidence": 90
}
```

### UNPROVEN

```json
{
  "result": "UNPROVEN",
  "current_confidence": 65,
  "missing_evidence": "...",
  "cheapest_safe_resolution": "..."
}
```

Do not recommend another general review.
