# GitHub strategy and approval checklist

**GITHUB_PUBLICATION_AUDIT=BLOCKED on ownership and licensing.** The technical audit covers the isolated `github/` candidate and its exact allowlist. No repository-level LICENSE or equivalent source redistribution grant was found in the audited source trees. Before publishing, obtain owner approval for original code and disclosure of the redacted release path/metadata, and inventory third-party notices. Prefer MIT for original code only if all rights holders approve and third-party terms are compatible; otherwise select approved terms or remove conflicting files. No license was assigned in this handoff. Frozen inputs, Gold, splits, outputs and weights stay private pending individual permission.

| Git strategy | Assessment |
|---|---|
| Independent repo rooted at `github/` | Recommended. Enforces a small reviewed publication tree; record original P2 HEAD and SHA in private provenance. |
| Put handoff under P2 | Adds publication risk by collocating private material and old history. |
| Release/export branch | Can preserve tracked history, but requires a stronger historical purge review and branch approval. |

After approval, stage the exact allowlist and inspect the diff. Suggested commit structure is one reviewed initial release covering source, docs, tests and deployment. Dependent research artifacts stay outside Git. These commands were not executed.

```powershell
Set-Location -LiteralPath '<handoff-root>/github'
git init -b main
git add --pathspec-from-file=manifests/public_files.txt
git diff --cached --check
git diff --cached --stat
git status --short
# After explicit approval of the staged diff and license:
git commit -m "Release reviewed P1/P2 unified handoff source"
# With a separately approved remote URL:
git remote add origin '<approved-GitHub-repository-URL>'
git remote -v
# Publish only after a separate push approval:
git push -u origin main
```

Candidate docs and lock files are usable with an approved separately delivered release. On license approval, update the reviewed allowlist and repeat the technical audit before staging anything.
