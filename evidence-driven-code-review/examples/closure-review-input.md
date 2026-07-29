# Closure review input

```yaml
mode: closure
task: Close REV-001 without changing release-gate scope.
base_sha: 5b0ce7ea
head_sha: dbb01214
prior_findings:
  - id: REV-001
    closure_condition: >
      The substitution test can no longer make imported bytes differ from
      validated bytes.
authorized_checks:
  - inspect remediation diff
  - run focused archive identity contract test
  - inspect direct loader call path
forbidden_operations:
  - broad repository audit
  - real deploy
  - destructive Docker cleanup
```
