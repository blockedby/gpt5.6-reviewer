# Live Codex integration verification

Tested Codex CLI 0.154.0 on Linux against the adapter/skill at commit `6f7c15f`.
The runtime selected `gpt-6-astra` for both parent and child; the adapter does not
pin that model. Desktop GUI behavior was not tested.

## Setup

- Disposable Git repository with the full skill at `.agents/skills/code-review/`,
  the adapter at `.codex/agents/evidence-reviewer.toml`, and `.codex/config.toml`.
- Separate temporary `CODEX_HOME`, with the fixture registered as trusted in its
  `config.toml`. Existing authentication was referenced, not copied or published.
- Normal, non-ephemeral `codex exec` session, multi-agent enabled, parent sandbox
  explicitly selected. No permanent user/project configuration was changed.
- Two fixture commits: `total_price` initially multiplies unit price by quantity;
  the reviewed commit replaces multiplication with addition.
- Parent instructed to delegate exactly one review to the discovered
  `evidence_reviewer` type, not substitute a built-in agent, and return its
  standalone JSON result. No fixes, network operations, or further delegation
  were authorized.

## Observed results

| Check | Result |
| --- | --- |
| Custom role discovery and spawn | Session trace records `spawn_agent` with `agent_type: evidence_reviewer`; child thread metadata records that role and the parent ID. |
| Installed skill loaded | Child tool trace reads the installed `SKILL.md` and bundled result/finding schemas. |
| Concrete regression detected | Child reproduces base result 30 versus head result 13 for inputs 10 and 3. |
| Standalone contract | `python -m evidence_review validate-result <result.json>` accepts the report with verdict `NOT_READY` and one blocker. |
| Model inheritance | Parent and child thread metadata report the same model. |
| File preservation | Before/after hashes of all non-Git fixture files match. |
| Read-only parent | Both parent and child runtime policies allow root reads and restrict network, with no write entries. |
| Writable-parent control | Child inherits workspace/tmp write entries despite the adapter's `sandbox_mode = "read-only"`; fixture files nevertheless remain unchanged. |
| Cleanup | Temporary fixture and Codex home removed after each run; sanitized results summarized here, raw local traces not committed. |

## Compatibility findings

1. Project-local config was disabled when the fixture was not trusted in the
   loaded user config. Supplying a trust value as a CLI override did not activate
   it in this test. Use normal Codex workspace trust, not a bypass.
2. Explicit role registration in an ephemeral session reached spawning but failed
   with `no thread with id`. Normal sessions in a temporary Codex home worked.
3. **The adapter's sandbox setting did not narrow a writable parent's runtime
   permissions on this version.** TOML parsing and an unchanged working tree do
   not prove sandbox enforcement. Start the parent read-only for read-only review.

These are bounded smoke-test results, not universal compatibility guarantees or
proof that arbitrary prompts cannot cause writes. There was no write-attempt
probe: sandbox conclusions are based on recorded effective runtime policies.
The config/unit tests check syntax and requested settings, not runtime enforcement.
