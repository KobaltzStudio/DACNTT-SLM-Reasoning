# Initial audit — PASS

The source worktree is the P2 Git root, branch `codex/controller-dryrun-fix`, HEAD `a26f420b0b4203890c2d86be1d3852a645aeb65d`. Existing tracked and untracked source was inventoried. Python 3.11.9 was confirmed from the approved venv. CIM and GPU query found no matching pipeline process; there were no controller locks.

Read the five original recovery files, guide, pre-release audit, Linux contract, deployment instructions and package/cache manifests. Rechecked 52 protected SHA values, all 655 payload SHA values plus three package indices, the staged/original P2 source correspondence, all 7 cache files, and guide/recovery integrity. Baseline strict D_dev A S1 416/500, A S2 75/500 without summary, B S1 406/500. Prior recorded Windows suite 103/103. The new root was absent and is outside the P2 worktree. The sealed copy remains the trust anchor.
