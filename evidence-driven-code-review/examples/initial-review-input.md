# Initial review input

```yaml
mode: initial
task: >
  Prebuild ten immutable Docker images, import them only after all outputs are
  valid, run integration shards against those exact images, and clean up only
  resources owned by this run.
base_sha: 163f0e08
head_sha: 5b0ce7ea
authorized_checks:
  - read source and git diff
  - run focused shell contract tests
  - use a fake docker CLI wrapper
  - inspect generated manifests
forbidden_operations:
  - real deploy
  - production mutation
  - destructive daemon cleanup
  - broad image builds solely for review
```
