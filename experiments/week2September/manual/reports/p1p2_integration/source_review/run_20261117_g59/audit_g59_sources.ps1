$ErrorActionPreference = "Stop"

$Root = "C:\Users\PC - NGHI\Desktop\Pipeline\P2\experiments\week2September\manual"
$OutDir = Join-Path $Root "reports\p1p2_integration\source_review\run_20261117_g59"

$Targets = @(
    "capability_eval.py",
    "test_capability_eval.py",
    "checkpoint_prediction_inventory.json",
    "student_capability_input_inventory.json",
    "student_eval_source_inspection.json",
    "B4_seed13_checkpoint_inventory.json",
    "17Nov_checkpoint_pipeline_status.md"
)

$ExcludedDirectories = @(
    ".venv",
    "__pycache__",
    ".git",
    "node_modules"
)

$Found = [System.Collections.Generic.List[object]]::new()

$Files = Get-ChildItem -LiteralPath $Root -File -Recurse -ErrorAction SilentlyContinue |
    Where-Object {
        $Full = $_.FullName
        $Skip = $false
        foreach ($DirName in $ExcludedDirectories) {
            if ($Full -match "[\\/]$([regex]::Escape($DirName))[\\/]") {
                $Skip = $true
            }
        }
        (-not $Skip) -and ($Targets -contains $_.Name)
    }

foreach ($File in $Files) {
    $Hash = (Get-FileHash -LiteralPath $File.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    $Record = [ordered]@{
        name = $File.Name
        path = $File.FullName
        relative_path = $File.FullName.Substring($Root.Length).TrimStart('\')
        size_bytes = $File.Length
        sha256 = $Hash
        last_write_time = $File.LastWriteTime.ToString("o")
        json_parse = "NOT_APPLICABLE"
        json_root_keys = @()
        json_array_counts = @{}
    }

    if ($File.Extension -eq ".json") {
        try {
            $Json = Get-Content -LiteralPath $File.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
            $Record.json_parse = "PASS"
            if ($Json -is [System.Management.Automation.PSCustomObject]) {
                $Record.json_root_keys = @($Json.PSObject.Properties.Name)
                foreach ($Property in $Json.PSObject.Properties) {
                    if ($Property.Value -is [array]) {
                        $Record.json_array_counts[$Property.Name] = $Property.Value.Count
                    }
                }
            }
            elseif ($Json -is [array]) {
                $Record.json_array_counts["ROOT"] = $Json.Count
            }
        }
        catch {
            $Record.json_parse = "FAIL: $($_.Exception.Message)"
        }
    }

    $Found.Add([pscustomobject]$Record)
}

$AuditDir = Join-Path $Root "reports\p1p2_integration\checkpoint_inventory_audit\schema_alias_audit\run_20261117_110254"
$AuditFiles = @()

if (Test-Path -LiteralPath $AuditDir -PathType Container) {
    $AuditFiles = Get-ChildItem -LiteralPath $AuditDir -File -Recurse |
        ForEach-Object {
            [pscustomobject]@{
                path = $_.FullName
                relative_path = $_.FullName.Substring($Root.Length).TrimStart('\')
                size_bytes = $_.Length
                sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
            }
        }
}

$ExpectedBundleHashes = @{
    "capability_eval.py" = "db62d84497eda50baf73025387db6db7be6dc314ee8cc1b5c0346a1150cfa47d"
    "test_capability_eval.py" = "65f069a3129d4ba5d69a173c11f3b01e5e83e637c2d09cf67c9a809d5dd437a0"
    "checkpoint_prediction_inventory.json" = "b50711647090dc8102124ea472e9fec43f5a1787d11f8dd89de582fb0a4f1c97"
    "student_capability_input_inventory.json" = "8b131a2da02bc90fb62972271daed66a62ec922a7fa4be87041f313e19fb655b"
    "student_eval_source_inspection.json" = "9b5cab123730436ce14e688696647e0b89f2b1debfb0dfe11c988d0174a3035c"
}

$HashComparison = foreach ($Item in $Found) {
    $Expected = $ExpectedBundleHashes[$Item.name]
    if ($Expected) {
        [pscustomobject]@{
            name = $Item.name
            relative_path = $Item.relative_path
            bundle_sha256 = $Expected
            repository_sha256 = $Item.sha256
            comparison = if ($Expected -eq $Item.sha256) { "MATCH" } else { "DIFFERENT" }
        }
    }
}

$Report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    repository_root = $Root
    source_files = @($Found)
    source_file_count = $Found.Count
    schema_alias_audit_directory = $AuditDir
    schema_alias_audit_directory_exists = (Test-Path -LiteralPath $AuditDir -PathType Container)
    schema_alias_audit_files = @($AuditFiles)
    schema_alias_audit_file_count = @($AuditFiles).Count
    bundle_hash_comparison = @($HashComparison)
}

$JsonPath = Join-Path $OutDir "g59_source_inventory.json"
$CsvPath = Join-Path $OutDir "g59_source_inventory.csv"
$AuditCsvPath = Join-Path $OutDir "g59_schema_alias_audit_files.csv"
$HashCsvPath = Join-Path $OutDir "g59_bundle_hash_comparison.csv"

$Report | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $JsonPath -Encoding UTF8
@($Found) | Export-Csv -LiteralPath $CsvPath -NoTypeInformation -Encoding UTF8
@($AuditFiles) | Export-Csv -LiteralPath $AuditCsvPath -NoTypeInformation -Encoding UTF8
@($HashComparison) | Export-Csv -LiteralPath $HashCsvPath -NoTypeInformation -Encoding UTF8

Write-Host ""
Write-Host "=== G5.9 SOURCE INVENTORY ==="
Write-Host "Repository: $Root"
Write-Host "Matched source/audit files: $($Found.Count)"
$Found | Select-Object name, relative_path, size_bytes, sha256, json_parse | Format-Table -AutoSize

Write-Host ""
Write-Host "=== SCHEMA / ALIAS AUDIT ==="
Write-Host "Directory exists: $(Test-Path -LiteralPath $AuditDir -PathType Container)"
Write-Host "Audit files: $(@($AuditFiles).Count)"
$AuditFiles | Format-Table -AutoSize

Write-Host ""
Write-Host "=== SOURCE BUNDLE HASH COMPARISON ==="
@($HashComparison) | Format-Table -AutoSize

Write-Host ""
Write-Host "Reports written:"
Write-Host $JsonPath
Write-Host $CsvPath
Write-Host $AuditCsvPath
Write-Host $HashCsvPath
