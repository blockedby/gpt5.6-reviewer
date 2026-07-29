# Evidence-Driven Code Review

A small review workflow for long-running coding agents working on large codebases.

> A change is ready when no sufficiently important, sufficiently supported defects remain.

The workflow does not stop because an arbitrary number of review rounds elapsed. It also does not force every review concern into the current task.

## Components

```text
implementation owner
        ↓
code-reviewer agent
        ↓
code-review skill
        ↓
uncertain serious candidate?
        ├─ no  → classify directly
        └─ yes → disposable verifier subagent
                         ↓
              VERIFIED / DISPROVED / UNPROVEN
        ↓
BLOCK / FOLLOW_UP / omit
        ↓
owner fixes BLOCK findings
        ↓
closure review of findings + remediation diff
        ↓
READY when no confirmed blockers remain
```

Permanent context stays small:

- `agents/code-reviewer.md` defines the reviewer role.
- `skills/code-review/SKILL.md` contains the canonical policy.
- `skills/code-review/verifier-prompt.md` is loaded only for one uncertain finding.
- JSON schemas and a small checker make outputs machine-readable.

## Core model

### Confidence

How certain are we that the defect exists?

| Score | Meaning |
|---:|---|
| 90–100 | Reproduced, observed, or inevitable from code |
| 80–89 | Strong direct evidence with little uncertainty |
| 50–79 | Plausible serious concern requiring verification |
| below 50 | Unsupported or contradicted; omit |

### Impact

How bad are the consequences if it exists?

| Impact | Meaning |
|---:|---|
| 4 | Security, privacy, data loss, corruption, destructive effects, systemic outage, lost recovery authority |
| 3 | Broken requirement or primary path, materially incorrect result, serious operational failure |
| 2 | Bounded edge case, recoverable reliability problem, material performance or maintenance cost |
| 1 | Style, polish, optional hardening, minor improvement |

### Blocking predicate

```python
blocking = (
    confidence >= 80
    and impact >= 3
    and relationship in {
        "introduced",
        "regression",
        "materially_worsened",
    }
)
```

Confirmed impact-2 findings become follow-ups. Impact-1 findings are omitted. Unproven findings do not block.

## Evidence policy

Every blocker must provide:

```text
scenario → expected behavior → actual behavior → evidence
```

Use the cheapest sufficient proof:

1. static proof;
2. existing failing test, log, trace, or runtime artifact;
3. focused regression test;
4. contract test;
5. safe local reproducer;
6. integration check;
7. already-authorized runtime verification.

A test is preferred when it is natural, deterministic, safe, and protects a stable invariant. It is not mandatory when the defect is already clear.

Do not deploy, mutate production, run destructive cleanup, perform a real migration, or build expensive images solely to prove a review hypothesis.

## Initial and closure review

Initial review examines the requested change, requirements, changed paths, direct dependencies, repository rules, and relevant tests.

Closure review examines only:

- closure of original blocker IDs;
- the remediation diff;
- direct dependencies and invariants touched by remediation;
- regressions caused by remediation.

Closure review is not a fresh broad audit.

## Layout

```text
.
├── AGENTS.md
├── README.md
├── agents/code-reviewer.md
├── skills/code-review/SKILL.md
├── skills/code-review/verifier-prompt.md
├── schemas/finding.schema.json
├── schemas/review-result.schema.json
├── scripts/review_policy.py
├── examples/
└── tests/test_review_policy.py
```

## Invocation input

```yaml
mode: initial | closure
task: requested behavior and acceptance criteria
base_sha: commit before reviewed work
head_sha: current product commit
changed_paths: optional path set
prior_findings: required in closure mode
authorized_checks: safe checks the reviewer may run
forbidden_operations: deploys, destructive actions, production writes, etc.
```

The reviewer returns JSON matching `schemas/review-result.schema.json`.

Final verdicts:

- `NOT_READY`: at least one `BLOCK`;
- `READY_WITH_FOLLOW_UPS`: no blockers, at least one follow-up;
- `READY`: no blockers or follow-ups.

## Validate

```bash
python scripts/review_policy.py examples/initial-review-output.json
python scripts/review_policy.py examples/closure-review-output.json
python -m unittest discover -s tests -v
```

## Orchestrator

```python
result = run_code_reviewer(...)

if result.verdict == "NOT_READY":
    run_owner_with(blocking_findings=result.blockers)
    run_code_reviewer(
        mode="closure",
        prior_findings=result.blockers,
        remediation_diff=...,
    )
else:
    finish()
```

The reviewer must not request another general review. The owner must not receive speculative candidates. The process continues only while a confirmed blocker remains.

A high external safety limit may protect against a broken runtime, but it is not a readiness rule.

## Deliberate non-features

This repository does not implement planning, task decomposition, issue creation, workflow DSLs, automatic deploys, automatic severity downgrades, or broad re-audits after every fix.
