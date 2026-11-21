# Final P1/P2 unified handoff

**HANDOFF_WORKSPACE_READY=PASS for local handoff.** The separate root is `C:\Users\PC - NGHI\Desktop\Pipeline\P1P2-Unified`. The nested `runtime/` is the byte-identical sealed private intake. The independent `github/` candidate is separate from the original P2 Git worktree, runtime, research evidence and external cache.

| Acceptance gate | Status / evidence |
|---|---|
| WINDOWS_CPU_TESTS | PASS, 103/103 from copied runtime in 31.931 seconds and 7/7 deployment fixtures, exit 0. |
| SOURCE_IMPORT_CLOSURE | PASS, 22 active modules and retained history, validated via AST closure and the runtime suite. |
| RUNPOD_STAGING_INTEGRITY | PASS, all 658 files and 575,403,394 bytes match sealed source and manifest; actual Windows plans 0/0/4/16. |
| GITHUB_PUBLICATION_AUDIT | BLOCKED on license and ownership. 57 technical candidates, zero public datasets or weights, static secret/path/link checks PASS. |
| LINUX_CPU_VALIDATION | PENDING, real host acceptance and Linux preflight receipt needed. |
| RUNPOD_GPU_EXECUTION | NOT_RUN, approved single scopes only. |
| G6/G7/G8 | PARTIAL. File copies are existing observed seed-13 evidence. |
| D_TEST_EXECUTION / G9 | NOT_RUN / DELEGATED. D_test requires G7 FINAL, independent SHA and separate approval. |
| Original cleanup | PENDING_APPROVAL; original research paths remain in place. |

## Inventory and size

The runtime carries 22 active source modules plus 166 historical scripts, 14 test-directory files, 13 config files, 11 frozen input/pool/Gold files and 8 split files. It includes 6 adapter weight files (A/B verified stages plus archived G4), 36 other checkpoint support files, 43 D_dev prediction-class files, 8 NLL-class files and 331 remaining runtime or provenance files. The private analysis copy contains 23 files, including seven PNG and seven paired CSV. File roles are listed explicitly in the inventories. B2–B5 baseline source and CLI are present; end-to-end runtime support for that matrix has not been established.

The upload allowlist has **681 files** (658 runtime and 23 tools/docs/checksum entries). The seven external Student files sum to **3,098,955,668 bytes** and are not copied into this workspace. Private-only material includes adapters, datasets, predictions, NLL, figures, lineage and evidence. Total logical workspace size was **593,478,834 bytes** before the final inventories/report/seal. The final exact byte count including generated indices and recovery is reported by `python -B recovery/finalize_workspace.py verify`.

- [Source inventory](../manifests/source_inventory.csv)
- [Artifact inventory](../manifests/artifact_inventory.csv)
- [Copy provenance](../manifests/source_to_handoff_mapping.csv)
- [GitHub inclusion](../manifests/github_inclusion_manifest.csv)
- [RunPod and external cache inclusion](../manifests/runpod_inclusion_manifest.csv)
- [Workspace SHA index](../manifests/SHA256SUMS.txt)

## Evidence and boundaries

A S1 PASS 416/500, A S2 complete 26-step adapter and 75/500 D_dev observations, A S3 pending. B S1 PASS 406/500, B S2/S3 pending. A S2 planned only D_dev/log/hook/state. B S2/S3 planned NLL S1/S2 with the same exact adapters used as the LoRA parents. No stage, training, inference, NLL, D_test, GPU job or upload was performed. Baseline settings and observed outputs are preserved. Future graph direction/annotation, transfer and ablation work is [PROPOSED](../future_research/README.md).

Acceptance ran `python -B -m unittest discover -s tests -v` independently at the copied manual root and workspace root, `python -B deployment/ops.py plans`, offline cache validation, and Git Bash syntax checks for ten wrappers plus a source-no-op check. SHA validation matched all 52 protected originals after testing; original Git HEAD remains `a26f420b0b4203890c2d86be1d3852a645aeb65d` on `codex/controller-dryrun-fix` with inherited 12 tracked modifications and untracked work. Original diff check exit 0. No local Git initialization, remote update, commit or publication occurred. [Test evidence](evidence/runtime_unittest.log) · [Deployment fixtures](evidence/deployment_unittest.log) · [Scope evidence](evidence/round_scope.log) · [Original integrity](evidence/closing_original.log).

No missing mandatory local inputs were observed. Linux wheel/driver, permissions and actual CPU tests are pending. Current rights and license uncertainty blocks publication. Use the [GitHub approval instructions](GITHUB_PUBLICATION.md), [RunPod operator handoff](HANDOFF_FOR_RUNPOD_OPERATOR.md), and [scope checklist](FINAL_RELEASE_CHECKLIST.md). Recovery starts at [NEXT_SESSION_START_HERE](NEXT_SESSION_HANDOFF.md).
