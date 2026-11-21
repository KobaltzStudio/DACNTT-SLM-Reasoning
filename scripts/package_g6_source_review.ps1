$ErrorActionPreference = "Stop"

try {
    $Root = Split-Path -Parent $PSScriptRoot

    $ExpectedRunner = Join-Path $Root "scripts\run_experiment.py"
    if (-not (Test-Path -LiteralPath $ExpectedRunner -PathType Leaf)) {
        throw "Project root validation failed. Expected file not found: $ExpectedRunner"
    }

    $ReportRoot = Join-Path $Root "reports\p1p2_integration"
    $SidecarRoot = Join-Path $Root "reports\capability\g5_9_historical_20261117"
    $OutDir = Join-Path $ReportRoot "source_review"

    $G6Input = Join-Path $ReportRoot "g6_input_audit\run_20261117_1730"
    $G6Token = Join-Path $ReportRoot "g6_token_audit\run_20261117_1800"

    $Package1 = @(
        (Join-Path $G6Input "g6_input_audit.json"),
        (Join-Path $G6Input "g6_input_audit.md"),
        (Join-Path $G6Token "g6_token_audit.json"),
        (Join-Path $G6Token "g6_token_audit.md"),
        (Join-Path $Root "scripts\p1p2_capability_state.py")
    )

    $Package2 = @(
        (Join-Path $Root "scripts\selection.py"),
        (Join-Path $Root "scripts\learnability.py"),
        (Join-Path $Root "scripts\build_pool_tokens.py"),
        (Join-Path $Root "integration_staging\P1\scripts\build_capability_learning_curves.py")
    )

    $Package3 = @(
        (Join-Path $SidecarRoot "B2_seed13_S1\capability_metrics.csv"),
        (Join-Path $SidecarRoot "B2_seed13_S1\capability_metrics.jsonl"),
        (Join-Path $SidecarRoot "B2_seed13_S1\capability_manifest.json"),
        (Join-Path $SidecarRoot "B4_seed13_S1\capability_metrics.csv"),
        (Join-Path $SidecarRoot "B4_seed13_S1\capability_metrics.jsonl"),
        (Join-Path $SidecarRoot "B4_seed13_S1\capability_manifest.json"),
        (Join-Path $SidecarRoot "B4_seed13_S2\capability_metrics.csv"),
        (Join-Path $SidecarRoot "B4_seed13_S2\capability_metrics.jsonl"),
        (Join-Path $SidecarRoot "B4_seed13_S2\capability_manifest.json"),
        (Join-Path $SidecarRoot "B4_seed13_S3\capability_metrics.csv"),
        (Join-Path $SidecarRoot "B4_seed13_S3\capability_metrics.jsonl"),
        (Join-Path $SidecarRoot "B4_seed13_S3\capability_manifest.json"),
        (Join-Path $SidecarRoot "B5_seed13_S1\capability_metrics.csv"),
        (Join-Path $SidecarRoot "B5_seed13_S1\capability_metrics.jsonl"),
        (Join-Path $SidecarRoot "B5_seed13_S1\capability_manifest.json")
    )

    $Packages = @(
        @{ Name = "g6_part1_audit_state.zip"; Files = $Package1 },
        @{ Name = "g6_part2_algorithms.zip"; Files = $Package2 },
        @{ Name = "g6_part3_sidecar_samples.zip"; Files = $Package3 }
    )

    # Validate every input before creating any ZIP.
    $AllMissing = @()

    foreach ($Package in $Packages) {
        foreach ($File in $Package.Files) {
            if (-not (Test-Path -LiteralPath $File -PathType Leaf)) {
                $AllMissing += $File
            }
        }
    }

    if ($AllMissing.Count -gt 0) {
        Write-Host "PACKAGING_INPUT_VALIDATION=FAIL"
        Write-Host "MISSING_FILE_COUNT=$($AllMissing.Count)"
        foreach ($MissingFile in $AllMissing) {
            Write-Host "MISSING: $MissingFile"
        }
        throw "Input validation failed. No ZIP creation was started."
    }

    New-Item -ItemType Directory -Path $OutDir -Force | Out-Null

    # Refuse to overwrite any previous output or partial archive.
    foreach ($Package in $Packages) {
        $FinalPath = Join-Path $OutDir $Package.Name
        $PartialPath = $FinalPath + ".partial"

        if (Test-Path -LiteralPath $FinalPath) {
            throw "Output already exists; refusing to overwrite: $FinalPath"
        }

        if (Test-Path -LiteralPath $PartialPath) {
            throw "Partial archive already exists; inspect before retrying: $PartialPath"
        }
    }

    $Created = @()

    foreach ($Package in $Packages) {
        $FinalPath = Join-Path $OutDir $Package.Name
        $PartialPath = $FinalPath + ".partial"
        $Stage = Join-Path $OutDir ($Package.Name + ".staging")

        if (Test-Path -LiteralPath $Stage) {
            throw "Staging directory already exists; inspect before retrying: $Stage"
        }

        New-Item -ItemType Directory -Path $Stage | Out-Null

        foreach ($File in $Package.Files) {
            # PowerShell 5.1-compatible relative path calculation.
            $Relative = $File.Substring($Root.Length)
            $Relative = $Relative.TrimStart([char[]]@('\', '/'))

            $Destination = Join-Path $Stage $Relative
            $DestinationDir = Split-Path -Parent $Destination

            New-Item -ItemType Directory -Path $DestinationDir -Force | Out-Null
            Copy-Item -LiteralPath $File -Destination $Destination
        }

        Compress-Archive `
            -Path (Join-Path $Stage "*") `
            -DestinationPath $PartialPath `
            -CompressionLevel Optimal

        if (-not (Test-Path -LiteralPath $PartialPath -PathType Leaf)) {
            throw "Compression did not produce the expected archive: $PartialPath"
        }

        $PartialSize = (Get-Item -LiteralPath $PartialPath).Length
        if ($PartialSize -le 0) {
            throw "Archive is empty: $PartialPath"
        }

        Move-Item -LiteralPath $PartialPath -Destination $FinalPath

        if (-not (Test-Path -LiteralPath $FinalPath -PathType Leaf)) {
            throw "Final archive publication failed: $FinalPath"
        }

        $Hash = (Get-FileHash -LiteralPath $FinalPath -Algorithm SHA256).Hash
        $Size = (Get-Item -LiteralPath $FinalPath).Length

        $Created += [PSCustomObject]@{
            Name = $Package.Name
            Path = $FinalPath
            Files = $Package.Files.Count
            SizeBytes = $Size
            SHA256 = $Hash
        }

        Remove-Item -LiteralPath $Stage -Recurse -Force
    }

    Write-Host ""
    Write-Host "G6_SOURCE_PACKAGING=PASS"
    foreach ($Item in $Created) {
        Write-Host ""
        Write-Host "CREATED: $($Item.Path)"
        Write-Host "FILES: $($Item.Files)"
        Write-Host "SIZE_BYTES: $($Item.SizeBytes)"
        Write-Host "SHA256: $($Item.SHA256)"
    }

    Write-Host ""
    Write-Host "S0_INCLUDED=NO"
    Write-Host "S0_NOTE=Will locate the actual S0 sidecar after inspecting the real capability directory structure."
}
catch {
    Write-Host ""
    Write-Host "G6_SOURCE_PACKAGING=FAIL"
    Write-Host "ERROR: $($_.Exception.Message)"
    exit 1
}
