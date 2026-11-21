# Release checklist

- [x] Keep GitHub candidate separate from P2 and the private artifact bundle.
- [x] Audit exact source closure, file allowlist and secret/path/binary exclusion.
- [x] Document the source-only suite and the sealed-bundle-dependent tests.
- [ ] Obtain rights-holder approval for original and derivative source, third-party notices, and the redacted paths/checksums.
- [ ] Review and approve the staged diff before committing the first release.
- [ ] Verify the approved GitHub remote URL and approve the actual push.
- [ ] Use the separately authorized private bundle and cache on the target Linux host; verify Linux CPU before any live job.

The release manifest omits its own digest from the content table to avoid a circular SHA. The manifest itself has a Git blob ID in the final index. See [audit evidence](PRE_PUSH_AUDIT.md) and [RunPod workflow](GITHUB_TO_RUNPOD_WORKFLOW.md).
