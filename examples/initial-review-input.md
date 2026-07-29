# Initial review input

The machine-readable initial request is
[`initial-review-request.json`](initial-review-request.json).

Create an equivalent request with:

```bash
python -m evidence_review new-request \
  --task "Prebuild ten immutable Docker images, import them only after all outputs are valid, run integration shards against those exact images, and clean up only resources owned by this run." \
  --base-sha 163f0e08 \
  --head-sha 5b0ce7ea \
  --changed-path scripts/local/prebuild-release-images.sh \
  --changed-path scripts/local/recovery_journal.py \
  --authorized-check "read source and git diff" \
  --forbidden-operation "real deploy"
```
