# Evidence-Driven Code Review

Evidence-Driven Code Review provides strict JSON contracts and deterministic
routing for an agent review loop.

> A change is ready when no sufficiently important, sufficiently supported
> defects remain.

The Python package enforces requests, results, blocker routing, and closure
handoffs. It does **not** invoke an LLM: the surrounding agent harness supplies
the independent reviewer described by `agents/code-reviewer.md` and
`skills/code-review/SKILL.md`.

## Agent skill

Install the portable skill with the skills.sh CLI:

```bash
npx skills add blockedby/gpt5.6-reviewer --skill code-review
```

`skills/code-review/SKILL.md` is the discoverable entry point. Its directory
includes the verifier prompt and JSON schemas, so installing the skill does not
require copying this repository's `agents/`, root `schemas/`, or Python package.
The skill targets current SOTA coding models; delegated verification additionally
requires a host that supports and explicitly permits subagents.

Use it for standalone change reviews or bounded, host-orchestrated audits such
as `audit-pipeline`. Standalone reviews use this repository's JSON contract;
orchestrated roles use the host's scope, permissions, and reporting contract.
A single audit track does not start its own review loop or declare the entire
review ready. See [execution context](skills/code-review/SKILL.md#execution-context).

`agents/code-reviewer.md` is an optional repository-local agent wrapper, not a
separately installable skill. The Python CLI below is optional, installed
separately, and validates standalone change-review results, not arbitrary host
audit reports.

### Codex desktop, CLI, and IDE

The skill works in local Codex clients. On the machine running Codex, install
`skills/code-review/` under `~/.agents/skills/code-review/` for personal use or
`.agents/skills/code-review/` in a project. Copy the **whole directory**, including
schemas and `agents/openai.yaml`. Existing installations should be updated
intentionally rather than overwritten blindly. Codex supports symlinked skill
directories too; restart the client if discovery has not refreshed.

For a separate read-only reviewer, also copy
[`agents/codex/evidence-reviewer.toml`](agents/codex/evidence-reviewer.toml) to
`~/.codex/agents/evidence-reviewer.toml` (personal) or
`.codex/agents/evidence-reviewer.toml` (project). The adapter requires the
installed `code-review` skill; it does not bundle or install it. The skills.sh
command installs the skill, **not** this separate custom-agent adapter.

Ask Codex:

> Delegate an independent review to evidence_reviewer. Review this branch
> against main for the following task and acceptance criteria: … Do not modify
> code. Pass the comparison identities and permitted read-only checks to the
> reviewer, and summarize its findings and evidence gaps.

Replace `main` with the actual target branch. For a standalone JSON review,
explicitly request the skill's standalone contract and provide its required
inputs. For a partial review, supply the assigned concern and report format.

The adapter inherits the parent's model and reasoning configuration and sets
`sandbox_mode = "read-only"`. Tests requiring writes may therefore be unavailable;
the reviewer reports that limitation rather than weakening the sandbox.
Subagent use depends on client version and host permissions.
`agents/openai.yaml` supplies skill UI metadata; it is **not** a subagent definition.
The Markdown wrapper remains available for other harnesses.

See OpenAI's [skills documentation](https://developers.openai.com/codex/skills)
and [custom subagent documentation](https://developers.openai.com/codex/subagents).
These files do not install anything into your local Codex configuration by themselves.

## Standalone policy

Confidence measures whether a defect exists. Impact measures its consequence.
The blocking predicate is unchanged:

```python
blocking = (
    confidence >= 80
    and impact >= 3
    and relationship in {
        "introduced",
        "regression",
        "materially_worsened",
    }
    and verification_status in {"verified", "not_required"}
)
```

Confirmed impact-2 findings, confirmed serious pre-existing findings, and
important unproven runtime checks at confidence 50–79 are follow-ups under the
canonical policy. Impact-1, confidence-below-50, disproved, and ordinary
unresolved candidates must not appear in final results.

The derived verdict is:

- `NOT_READY` when any finding is `BLOCK`;
- `READY_WITH_FOLLOW_UPS` when no blocker and at least one `FOLLOW_UP` remain;
- `READY` when no findings remain.

Only `BLOCK` findings go back to the implementation owner. A closure review
checks those exact findings, the remediation diff, touched invariants, and
regressions caused by remediation; it is not another broad audit.

## Python CLI installation

Python 3.10 or newer is required. Runtime and tests use only the standard
library.

```bash
python -m pip install .
evidence-review --help
```

For repository development, installation is optional:

```bash
python -m evidence_review --help
```

The two entry points run the same CLI.

## Commands

All generated JSON is stable, UTF-8, pretty-printed, and key-sorted.
Input uses strict JSON: duplicate object keys and nonstandard constants such as
`NaN` and `Infinity` are rejected. Generation commands write to stdout by
default. `--output PATH` atomically replaces an explicit file. An input path of
`-` reads stdin; only one input in a multi-input command may use stdin.

### Create an initial request

```bash
evidence-review new-request \
  --task "Implement immutable image import" \
  --base-sha 163f0e08 \
  --head-sha 5b0ce7ea \
  --changed-path scripts/local/prebuild-release-images.sh \
  --authorized-check "run focused contract tests" \
  --forbidden-operation "real deploy" \
  --output request.json
```

`--changed-path`, `--authorized-check`, and `--forbidden-operation` are
repeatable. Their order is preserved.

### Validate contracts

```bash
evidence-review validate-request request.json
evidence-review validate-result result.json
evidence-review validate-result result.json --request request.json
```

Cross-validation requires `mode`, `base_sha`, and `head_sha` to equal the
request. In closure mode, closure entry IDs must exactly equal the prior blocker
IDs.

### Route a result

```bash
evidence-review route result.json
```

For `NOT_READY`, output contains `action: "remediate"` and only the full
`BLOCK` findings. For `READY` and `READY_WITH_FOLLOW_UPS`, output contains
`action: "finish"` and the verdict.

### Prepare closure

```bash
evidence-review prepare-closure \
  --request request.json \
  --result result.json \
  --head-sha dbb01214 \
  --remediation-diff-file remediation.diff \
  --authorized-check "run focused archive identity contract test" \
  --forbidden-operation "real deploy" \
  --output closure-request.json
```

The prior request and result are validated and cross-checked first. The result
must contain at least one blocker. The generated request:

- copies every full `BLOCK` finding without rewriting evidence or closure
  conditions;
- sets `base_sha` to the previous result's `head_sha`;
- sets `head_sha` to the supplied remediated SHA;
- embeds the remediation diff file content;
- carries the original task and optional changed paths;
- uses exactly the repeatable authorized/forbidden values supplied to this
  command.

## JSON contracts

`schemas/review-request.schema.json`, `schemas/finding.schema.json`, and
`schemas/review-result.schema.json` document standalone structural contracts.
These root schemas are canonical; identical copies are bundled under
`skills/code-review/schemas/` for portable installation. Update both together;
packaging tests check equality and isolated reference resolution. The Python
validator additionally enforces cross-object and policy rules that JSON Schema
cannot conveniently express.

### Request

Every request requires:

```json
{
  "mode": "initial",
  "task": "Requested behavior and acceptance criteria",
  "base_sha": "163f0e08",
  "head_sha": "5b0ce7ea",
  "changed_paths": [],
  "authorized_checks": [],
  "forbidden_operations": []
}
```

`changed_paths` is optional. Closure mode additionally requires a nonempty
`prior_findings` array containing full, policy-valid `BLOCK` finding objects,
and a nonempty `remediation_diff` string. Those fields are forbidden in initial
mode.

### Finding

Finding IDs are positive canonical values such as `REV-001` (never `REV-000`)
and are unique within a result or closure request. All documented strings and
locations are nonempty. A location
may contain only `path`, or a complete positive `start_line`/`end_line` pair
where start does not exceed end. Every blocker has a nonempty
`closure_condition`.

Disposition must match the policy predicate. Unknown fields are rejected at
every object level.

### Result

Every result has `mode`, `base_sha`, `head_sha`, a findings-derived `verdict`,
`findings`, and a nonempty `summary`. Initial results cannot contain `closure`.
Closure results require it.

The closure array is nonempty and its IDs are unique. `still_open` and
`regressed` entries require a `BLOCK` finding with the same ID. `fixed` and
`not_applicable` entries cannot retain any same-ID finding. With a request
supplied, closure IDs must exactly match all prior blocker IDs.

See `examples/initial-review-request.json`,
`examples/initial-review-output.json`, `examples/closure-review-request.json`,
and `examples/closure-review-output.json`.

## Exit codes

- `0`: command succeeded and any validated data is valid;
- `1`: structurally or policy-invalid data;
- `2`: CLI usage, file I/O, or JSON decoding error.

Errors are written to stderr with a stable `ERROR:` prefix. `argparse` usage
errors also return 2.

## Compatibility validator

The original one-argument result checker remains available and delegates to the
package validator:

```bash
python scripts/review_policy.py examples/initial-review-output.json
```

## Development checks

```bash
python -m unittest discover -s tests -v
python -m evidence_review validate-request examples/initial-review-request.json
python -m evidence_review validate-result \
  examples/initial-review-output.json \
  --request examples/initial-review-request.json
python scripts/review_policy.py examples/closure-review-output.json
```

## Repository layout

```text
.
├── AGENTS.md
├── README.md
├── agents/code-reviewer.md
├── evidence_review/
├── skills/code-review/
├── schemas/
├── scripts/review_policy.py
├── examples/
├── tests/
└── pyproject.toml
```

## Deliberate non-features

This repository does not invoke reviewers, modify product code, deploy, mutate
production, create issues, implement a workflow DSL, automatically downgrade
severity, or trigger broad re-audits after remediation.
