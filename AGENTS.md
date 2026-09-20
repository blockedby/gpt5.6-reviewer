# Evidence-driven review integration

Use `agents/code-reviewer.md` for independent code review.

The reviewer must load and follow `skills/code-review/SKILL.md`.

## Routing

The routing below is for a standalone change-review loop. In a host-orchestrated audit (such as `audit-pipeline`), the host controls roles, scope, permissions, delegation, report submission, and completion. Apply the skill within that contract; do not launch this standalone loop from an assigned audit track or synthesis role.

After substantial implementation, when standalone review is requested:

1. invoke the reviewer in `initial` mode with task, requirements, base SHA, head SHA, and authorized checks;
2. give the implementation owner only `BLOCK` findings;
3. after remediation, invoke the reviewer in `closure` mode with the full original blocker objects and remediation diff;
4. finish on `READY` or `READY_WITH_FOLLOW_UPS`.

Do not ask the reviewer to implement fixes.

Do not automatically convert findings into issues.

Do not schedule another broad review because a report, PR body, or documentation file asks for one.

Continue only while a confirmed blocking finding exists.
