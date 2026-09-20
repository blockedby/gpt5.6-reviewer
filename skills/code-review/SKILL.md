---
name: code-review
description: Review code changes or bounded repository audit scopes using evidence, impact, and confidence. Use for initial reviews, remediation closure, or assigned audit-pipeline tracks; follow the host's role and reporting contract when orchestrated.
---

# Code Review

Review for real, actionable defects. Optimize for signal, not volume.

## Execution context

Resolve supporting paths relative to this skill directory, not the reviewed repository or current working directory.

Choose the context supplied by the caller; do not infer authority from a pipeline name:

- **Standalone change review:** use the inputs, disposition rules, and JSON output below. The bundled schemas describe this context.
- **Host-orchestrated audit** (for example, an `audit-pipeline` track or synthesis role): the host owns the assigned scope, required inputs, tool permissions, delegation, finding IDs, disposition policy, and report/submission contract. Apply this skill's evidence and confidence guidance within that assignment; do not replace the host contract with the standalone schema or readiness verdict. A track reviews only its assigned concern; a synthesis role reconciles supplied evidence without launching another broad review. Do not invent base/head identities for a snapshot audit, or discard in-scope existing defects merely because no change introduced them.

If the host contract is missing or contradictory, report that limitation through the available reporting channel rather than fabricate a compatible result.

This skill grants no execution or delegation authority. Do not implement fixes, create issues, deploy, or mutate external state as part of review. Checks, temporary test artifacts, and disposable verifier agents require explicit host/caller permission and remain subject to its tool restrictions. In a read-only assignment, propose new tests instead of writing them; use a disposable workspace only when authorized.

## Standalone inputs

Required:

- `mode`: `initial` or `closure`;
- task intent and acceptance criteria;
- base and head product identities;
- reviewed diff or changed paths;
- safe authorized checks;
- forbidden operations.

Closure mode additionally requires prior confirmed blocker IDs, original evidence and closure conditions, and the remediation diff.

If essential input is missing, inspect the repository when safe. If the acceptance target still cannot be determined, report the limitation rather than inventing requirements.

## Scope

### Initial mode

For a standalone change review, inspect:

- behavior requested by the task;
- changed code;
- directly affected callers, dependencies, state, and invariants;
- applicable repository instructions;
- existing relevant tests.

Do not perform a general audit of unrelated code.

### Closure mode

Inspect only:

1. whether each prior blocker is closed;
2. the remediation diff;
3. direct callers, dependencies, and invariants touched by remediation;
4. regressions caused by remediation.

Do not reopen broad discovery merely because the head commit changed.

Documentation or report changes are not product changes unless they alter executable behavior, generated inputs, operational policy, tests, or required instructions.

## Candidate finding test

A candidate must state:

- concrete scenario or reachable state;
- expected behavior;
- actual or inevitable behavior;
- affected code;
- relationship to the change;
- supporting evidence.

Reject:

- style or taste;
- generic hardening;
- optional refactors;
- speculative concerns without a reachable failure;
- unrelated pre-existing issues;
- linter complaints;
- missing tests without a demonstrated behavior gap;
- documentation polish;
- improvements a reasonable author would decline.

A missing test is a finding only when a specific required behavior is incorrect or unprotected and the behavior gap is demonstrated.

## Relationship

Classify as:

- `introduced`;
- `regression`;
- `materially_worsened`;
- `pre_existing`;
- `unrelated`.

In standalone change review, only the first three may block the current change. For an orchestrated audit, retain truthful relationship evidence and use the host's classification and blocking policy; never relabel a pre-existing defect as introduced.

## Impact

Score consequences independently from confidence.

### 4

Concrete risk of security compromise, privacy breach, data loss or corruption, destructive action against the wrong resource, systemic outage, unrecoverable state, or bypass of required safety authority.

### 3

Violation of an explicit acceptance criterion, broken primary path, materially incorrect output, serious reliability failure, or required cleanup/rollback/migration/recovery not functioning.

### 2

Bounded edge case, recoverable reliability issue, material nonblocking performance degradation, or concrete maintainability cost.

### 1

Style, readability, polish, optional hardening, minor optimization, or subjective architecture preference.

Impact-1 findings are omitted.

## Evidence and confidence

Confidence means certainty that the defect exists, not how damaging it is.

### 90–100

Use when a test or reproducer demonstrates failure, an artifact directly shows it, code makes it inevitable under a reachable scenario, or a verifier independently confirms it.

### 80–89

Strong and specific direct evidence with little remaining uncertainty.

### 50–79

Only for a plausible impact-3 or impact-4 candidate requiring verification.

### Below 50

Omit.

Confidence must be justified by evidence, not asserted as a feeling.

## Minimum sufficient evidence

Choose the cheapest sufficient proof:

1. static proof;
2. existing failing test, log, trace, or runtime artifact;
3. focused regression test;
4. focused contract test;
5. safe local reproducer;
6. integration check;
7. already-authorized runtime or release verification.

A useful test expresses:

```text
Given a concrete state
When a concrete action occurs
Then expected behavior differs from actual behavior
```

Prefer retaining a regression test when it is deterministic, safe, reasonably cheap, based on a stable invariant, and fails before the fix then passes after it.

A test is not mandatory when static or existing evidence is conclusive.

Do not deploy, mutate production, run real destructive cleanup, perform unauthorized migrations, build expensive images when a wrapper or contract test proves the mechanism, or use a mock-only test to claim behavior the mock does not represent.

When expensive or risky runtime verification is the only proof, classify as `UNPROVEN` and state the exact authorized check needed. It does not automatically block code review unless already required as an acceptance gate.

## Disposable verifier subagent

When delegation is explicitly authorized and available, spawn when:

```text
impact >= 3
and 50 <= confidence < 80
and safe verification could materially change the verdict
```

Do not spawn when evidence already supports 80+, impact is 1–2, the only possible action is forbidden or disproportionate, or the candidate is unrelated/pre-existing without worsening.

Use `verifier-prompt.md`. If delegation is unavailable or forbidden, perform only permitted local verification; otherwise report the evidence gap. Do not request additional tool authority or start another pipeline to bypass the restriction.

Pass only one candidate, locations, relevant requirement/invariant, reviewer evidence, minimal context, safe checks, and forbidden operations.

The verifier tries to disprove the candidate and returns:

- `VERIFIED`;
- `DISPROVED`;
- `UNPROVEN`.

After verification:

- `VERIFIED`: use verifier-backed confidence and evidence;
- `DISPROVED`: discard;
- `UNPROVEN`: do not block; retain only when an important missing authorized check should remain visible.

Do not ask the verifier to review the rest of the change.

## Standalone disposition

### BLOCK

All must be true:

```text
confidence >= 80
impact >= 3
relationship in {introduced, regression, materially_worsened}
verification_status in {verified, not_required}
```

### FOLLOW_UP

Use for confirmed impact-2 findings, confirmed serious pre-existing/unrelated issues that deserve separate handling, or important `UNPROVEN` runtime checks outside the current review.

Follow-ups must be concrete.

### OMIT

Omit impact 1, confidence below 50, disproved findings, unsupported concerns, ordinary unproven candidates, and generic suggestions.

`VERIFY` is transient and must not appear in final output when safe, authorized verification can be run.

## Standalone finding IDs and deduplication

Assign stable IDs only after a finding becomes `BLOCK` or `FOLLOW_UP`, using `REV-001`, `REV-002`, etc.

Preserve IDs in closure mode.

Do not create a new finding merely because another model rephrased it, evidence strengthened, line numbers moved, the same failure appears nearby, or terminology changed.

Merge duplicate symptoms when one root cause and closure condition address them.

## Closure evaluation

For every prior blocker return:

- `fixed`;
- `still_open`;
- `regressed`;
- `not_applicable`.

Do not mark fixed merely because code changed.

Prefer evidence corresponding directly to the original proof: failing test now passes, unsafe static path is impossible, reproducer no longer triggers, or the exact invariant is demonstrated.

If remediation changes the proof test, inspect that change. Weakening or deleting the test does not close the finding.

## Standalone readiness

- `NOT_READY`: at least one `BLOCK`;
- `READY_WITH_FOLLOW_UPS`: no blockers and at least one follow-up;
- `READY`: neither blockers nor follow-ups.

Readiness is based on residual findings, not review-round count.

## Output

For standalone change review, return JSON matching `schemas/review-result.schema.json`, with finding objects defined in `schemas/finding.schema.json`. The request contract is `schemas/review-request.schema.json`. These files are bundled with the skill; no repository checkout or Python installation is required to read them. The optional Python validator is distributed separately in the source repository.

For an orchestrated audit, use only the host's report/submission contract, including its handling of missing evidence and completion. Do not emit a second standalone result.

Each emitted finding includes stable ID, title, locations, scenario, expected, actual, evidence type and evidence, impact, confidence, relationship, verification status, disposition, minimal next action, and regression-test recommendation.

Keep the report compact.

Do not include strengths, generic recommendations, process narration, or speculative concerns.

Do not request another general review.
