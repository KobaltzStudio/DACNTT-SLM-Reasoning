[CmdletBinding()]
param(
    [string]$Manual = 'C:\Users\PC - NGHI\Desktop\Pipeline\P2\experiments\week2September\manual'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

if (-not (Test-Path -LiteralPath $Manual -PathType Container)) {
    throw "MANUAL_ROOT_NOT_FOUND: $Manual"
}

$ReportRoot = Join-Path $Manual 'reports\p1p2_integration\source_review\seed13_artifact_audit'
New-Item -ItemType Directory -Force -Path $ReportRoot | Out-Null
$Stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$JsonOut = Join-Path $ReportRoot "seed13_artifact_audit_$Stamp.json"
$CsvOut = Join-Path $ReportRoot "seed13_artifact_audit_$Stamp.csv"
$TextOut = Join-Path $ReportRoot "seed13_artifact_audit_$Stamp.txt"

function Get-ManifestRows {
    param([string]$Root, [string]$Label)
    $rows = [System.Collections.Generic.List[object]]::new()
    if (-not (Test-Path -LiteralPath $Root -PathType Container)) {
        return $rows
    }
    $manifests = @(Get-ChildItem -LiteralPath $Root -Filter 'student_capability_evaluation_manifest.json' -File -Recurse -ErrorAction SilentlyContinue)
    foreach ($file in $manifests) {
        $obj = $null
        $parseStatus = 'OK'
        try {
            $obj = Get-Content -LiteralPath $file.FullName -Raw | ConvertFrom-Json -ErrorAction Stop
        }
        catch {
            $parseStatus = 'JSON_ERROR: ' + $_.Exception.Message
        }
        $method = $null
        $seed = $null
        $round = $null
        $checkpoint = $null
        $runId = $null
        $checkpointHash = $null
        $predictionHash = $null
        $goldPolicy = $null
        if ($null -ne $obj) {
            $method = $obj.method
            $seed = $obj.seed
            $round = $obj.round
            $checkpoint = $obj.checkpoint
            $runId = $obj.run_id
            $goldPolicy = $obj.gold_policy
            if ($null -ne $obj.input_hashes) {
                $checkpointHash = $obj.input_hashes.checkpoint
                $predictionHash = $obj.input_hashes.dev_predictions
            }
        }
        $rows.Add([pscustomobject]@{
            root_label = $Label
            sidecar_dir = $file.DirectoryName
            manifest_path = $file.FullName
            parse_status = $parseStatus
            method = $method
            seed = $seed
            round = $round
            checkpoint = $checkpoint
            run_id = $runId
            checkpoint_hash = $checkpointHash
            prediction_hash = $predictionHash
            gold_policy = $goldPolicy
        })
    }
    return $rows
}

function Get-FileInventory {
    param([string]$Root, [string]$Label)
    $rows = [System.Collections.Generic.List[object]]::new()
    if (-not (Test-Path -LiteralPath $Root -PathType Container)) {
        $rows.Add([pscustomobject]@{ root_label=$Label; root=$Root; relative_path=''; name=''; length=$null; kind='ROOT_MISSING' })
        return $rows
    }
    $files = @(Get-ChildItem -LiteralPath $Root -File -Recurse -ErrorAction SilentlyContinue)
    foreach ($file in $files) {
        $relative = $file.FullName.Substring($Root.TrimEnd('\').Length).TrimStart('\')
        $kind = 'OTHER'
        if ($file.Name -eq 'eval_dev.jsonl') { $kind = 'DEV_PREDICTION' }
        if ($file.Name -match '^(train_set|selection_log|checkpoint_log|train_log|run_manifest|input_fingerprint|student_capability_evaluation_manifest)') { $kind = 'LINEAGE_OR_SELECTION' }
        if ($file.Name -match '^(nll|ell|learnability).*(json|jsonl|csv)$') { $kind = 'NLL_OR_LEARNABILITY' }
        if ($file.Name -match '^(adapter_model|model|pytorch_model|model\.safetensors)') { $kind = 'MODEL_WEIGHT' }
        $rows.Add([pscustomobject]@{
            root_label = $Label
            root = $Root
            relative_path = $relative
            name = $file.Name
            length = $file.Length
            kind = $kind
        })
    }
    return $rows
}

$ManifestRows = [System.Collections.Generic.List[object]]::new()
$ManifestRoots = @(
    [pscustomobject]@{ Label='G5_9_REAL_DATA_S0'; Path=(Join-Path $Manual 'reports\capability\g5_9_real_data_s0') },
    [pscustomobject]@{ Label='G5_9_HISTORICAL'; Path=(Join-Path $Manual 'reports\capability\g5_9_historical_20261117') },
    [pscustomobject]@{ Label='G4_VALIDATION'; Path=(Join-Path $Manual 'reports\capability_g4_validation') },
    [pscustomobject]@{ Label='P1P2_CAPABILITY_STATE'; Path=(Join-Path $Manual 'reports\p1p2_integration\capability_state') }
)
foreach ($root in $ManifestRoots) {
    $found = Get-ManifestRows -Root $root.Path -Label $root.Label
    foreach ($row in $found) { $ManifestRows.Add($row) }
}

$ArtifactRows = [System.Collections.Generic.List[object]]::new()
$ArtifactRoots = @(
    [pscustomobject]@{ Label='P1_DEFICIT_RUN'; Path=(Join-Path $Manual 'runs\p1p2_integration\P1-DEFICIT_seed13') },
    [pscustomobject]@{ Label='P1P2_RUN'; Path=(Join-Path $Manual 'runs\p1p2_integration\P1P2_seed13') },
    [pscustomobject]@{ Label='P1_DEFICIT_MODEL'; Path=(Join-Path $Manual 'models\p1p2_integration\P1-DEFICIT_seed13') },
    [pscustomobject]@{ Label='P1P2_MODEL'; Path=(Join-Path $Manual 'models\p1p2_integration\P1P2_seed13') },
    [pscustomobject]@{ Label='P1_STAGING'; Path=(Join-Path $Manual 'integration_staging\P1') },
    [pscustomobject]@{ Label='TASK7_MODEL_REFERENCE_READ_ONLY'; Path=(Join-Path $Manual 'models\task7') }
)
foreach ($root in $ArtifactRoots) {
    $found = Get-FileInventory -Root $root.Path -Label $root.Label
    foreach ($row in $found) { $ArtifactRows.Add($row) }
}

$ManifestArray = @($ManifestRows.ToArray())
$ArtifactArray = @($ArtifactRows.ToArray())
$RawCount = $ManifestArray.Count
$LogicalGroups = @($ManifestArray | Where-Object { $_.parse_status -eq 'OK' } | Group-Object { '{0}|{1}|{2}|{3}' -f $_.method,$_.seed,$_.round,$_.checkpoint })
$DuplicateGroups = @($LogicalGroups | Where-Object { $_.Count -gt 1 })
$P1Rows = @($ManifestArray | Where-Object { $_.method -in @('P1-DEFICIT','P1P2') -and [string]$_.seed -eq '13' })
$P1RunFiles = @($ArtifactArray | Where-Object { $_.root_label -in @('P1_DEFICIT_RUN','P1P2_RUN') })
$P1ModelFiles = @($ArtifactArray | Where-Object { $_.root_label -in @('P1_DEFICIT_MODEL','P1P2_MODEL') })

$Summary = [ordered]@{
    generated_at = (Get-Date).ToString('o')
    manual_root = $Manual
    raw_manifest_count_across_roots = $RawCount
    logical_checkpoint_group_count = $LogicalGroups.Count
    duplicate_logical_group_count = $DuplicateGroups.Count
    duplicate_logical_groups = @(
        foreach ($group in $DuplicateGroups) {
            [pscustomobject]@{
                logical_key = $group.Name
                count = $group.Count
                entries = @($group.Group | Select-Object root_label,sidecar_dir,checkpoint_hash,prediction_hash)
            }
        }
    )
    p1_seed13_sidecars = $P1Rows
    p1_run_files = $P1RunFiles
    p1_model_files = $P1ModelFiles
    all_manifest_rows = $ManifestArray
    all_artifact_files = $ArtifactArray
}

$Summary | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $JsonOut -Encoding UTF8
$ManifestArray | Export-Csv -LiteralPath $CsvOut -NoTypeInformation -Encoding UTF8
$lines = [System.Collections.Generic.List[string]]::new()
$lines.Add("MANUAL_ROOT: $Manual")
$lines.Add("RAW_MANIFEST_COUNT: $RawCount")
$lines.Add("LOGICAL_CHECKPOINT_GROUP_COUNT: $($LogicalGroups.Count)")
$lines.Add("DUPLICATE_LOGICAL_GROUP_COUNT: $($DuplicateGroups.Count)")
$lines.Add('')
$lines.Add('=== P1 SEED 13 SIDECARS ===')
foreach ($row in $P1Rows) {
    $lines.Add(("{0} S{1} | {2} | {3}" -f $row.method,$row.round,$row.sidecar_dir,$row.checkpoint_hash))
}
$lines.Add('')
$lines.Add('=== P1 RUN FILES ===')
foreach ($row in $P1RunFiles) { $lines.Add(("{0} | {1} | {2}" -f $row.root_label,$row.relative_path,$row.length)) }
$lines.Add('')
$lines.Add('=== P1 MODEL FILES ===')
foreach ($row in $P1ModelFiles) { $lines.Add(("{0} | {1} | {2}" -f $row.root_label,$row.relative_path,$row.length)) }
$lines.Add('')
$lines.Add("JSON_REPORT: $JsonOut")
$lines.Add("CSV_REPORT: $CsvOut")
$lines | Set-Content -LiteralPath $TextOut -Encoding UTF8

Write-Host "RAW_MANIFEST_COUNT: $RawCount"
Write-Host "LOGICAL_CHECKPOINT_GROUP_COUNT: $($LogicalGroups.Count)"
Write-Host "DUPLICATE_LOGICAL_GROUP_COUNT: $($DuplicateGroups.Count)"
Write-Host "P1_SEED13_SIDECAR_COUNT: $($P1Rows.Count)"
Write-Host "P1_RUN_FILE_COUNT: $($P1RunFiles.Count)"
Write-Host "P1_MODEL_FILE_COUNT: $($P1ModelFiles.Count)"
Write-Host "AUDIT_JSON: $JsonOut"
Write-Host "AUDIT_CSV: $CsvOut"
Write-Host "AUDIT_TEXT: $TextOut"
Write-Host 'AUDIT_STATUS: COMPLETE_READ_ONLY'
