# Cleanup approval plan — Phase E

**Staging hygiene PASS. ORIGINAL_REPOSITORY_CLEANUP=PENDING_APPROVAL.** Recounted the same 4,919-file census scope with no additions/removals in that scope. All 596 previously known manual-path references still exist. All 65 ZIP SHA values match. Rehashed all 735 P1 manual.zip members and their extracted copies; all matched. The independent package has no ZIP, bytecode, `__pycache__`, temporary files, baseline backup files or historical D_test output artifacts. The original layout remains canonical; `p1p2_unified` is an independent staging container.

The exact candidates for a possible future bytecode-only action are in CLEANUP_BYTECODE_CANDIDATES.csv. The 213 untracked, regenerable file records include size, SHA-256, source path and current source SHA. They total 2,356,666 bytes. No ZIP, source, report, checkpoint, Gold, frozen config, split, prediction, summary, NLL, adapter, log, sidecar or lineage file is in this candidate list. Keep the 65 ZIP archives; matched contents do not establish that archived container metadata can be discarded.

## Future approval and rollback

Request approval of the exact CSV digest and reviewed scope before any real cleanup. Prefer leaving the candidates in place because the verified package already excludes them. If approved, first revalidate Git, active processes and package/protected SHA. Reserve a fresh backup root separate from the repository. Back up each candidate as a regular file with its relative path and verify the recorded SHA on the copy before accepting any deletion instruction.

The following PowerShell preview is documentation only. It constrains paths under the named workspace and previews individual files. Run the preview and compare all rows before requesting a separate destructive command. Do not use recursive deletion or Git clean.

```powershell
$Root = 'C:\Users\PC - NGHI\Desktop\Pipeline'
$List = 'C:/Users/PC - NGHI/Desktop/Pipeline/P2/experiments/week2September/manual/reports/p1p2_integration/final_validation/pre_runpod_release_20261119_011425/CLEANUP_BYTECODE_CANDIDATES.csv'
$Prefix = (Resolve-Path -LiteralPath $Root).Path.TrimEnd('\') + '\'
$Candidates = Import-Csv -LiteralPath $List
foreach ($Item in $Candidates) {
    $Resolved = (Resolve-Path -LiteralPath (Join-Path $Root $Item.workspace_relative)).Path
    $File = Get-Item -LiteralPath $Resolved -Force
    if (-not $Resolved.StartsWith($Prefix, [StringComparison]::OrdinalIgnoreCase) -or
        $File.Extension -ne '.pyc' -or $File.Directory.Name -ne '__pycache__' -or
        ($File.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw "Unexpected candidate: $Resolved"
    }
    if ((Get-FileHash -LiteralPath $Resolved -Algorithm SHA256).Hash -ne $Item.sha256) {
        throw "SHA mismatch: $Resolved"
    }
    Remove-Item -LiteralPath $Resolved -WhatIf
}
```

Rollback from the verified backup list into an isolated restore directory. Verify item SHA and source ownership; restore the original path only under separate approval and only if the original location is absent. If the original path has different content, stop. Recheck the protected fingerprints and Git before subsequent work. No destructive action, move, rename, backup copy or restore was carried out in this audit.
