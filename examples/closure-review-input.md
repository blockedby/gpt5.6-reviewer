# Closure review input

The machine-readable closure request is
[`closure-review-request.json`](closure-review-request.json). It preserves the
complete original `REV-001` blocker, including its evidence and exact closure
condition, and embeds the remediation diff.

Closure requests should normally be generated rather than handwritten:

```bash
python -m evidence_review prepare-closure \
  --request initial-review-request.json \
  --result initial-review-output.json \
  --head-sha dbb01214 \
  --remediation-diff-file remediation.diff \
  --authorized-check "inspect remediation diff" \
  --authorized-check "run focused archive identity contract test" \
  --forbidden-operation "real deploy"
```
