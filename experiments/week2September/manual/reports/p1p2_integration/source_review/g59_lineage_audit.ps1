$ErrorActionPreference = "Stop"

$P2 = "C:\Users\PC - NGHI\Desktop\Pipeline\P2\experiments\week2September\manual"
Set-Location -LiteralPath $P2

$Derived = Join-Path $P2 "reports\p1p2_integration\derived_predictions\B4_seed13"
$ManifestPath = Join-Path $Derived "adapter_manifest.json"
$MainZip = Join-Path $P2 "runs\main\main.zip"
$DDevPath = Join-Path $P2 "splits\d_dev_ids.txt"
$ModelRoot = Join-Path $P2 "models\task7"

foreach ($Required in @($MainZip, $DDevPath, $ManifestPath)) {
    if (-not (Test-Path -LiteralPath $Required -PathType Leaf)) {
        throw "Required input missing: $Required"
    }
}

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$OutDir = Join-Path $P2 "reports\p1p2_integration\source_review\run_g59_lineage_audit_$Timestamp"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$ReportPath = Join-Path $OutDir "g59_lineage_audit.txt"
$Lines = [System.Collections.Generic.List[string]]::new()

function Add-Line {
    param([string]$Value)
    [void]$script:Lines.Add($Value)
}

function Read-ZipText {
    param($Entry)

    $Stream = $Entry.Open()
    try {
        $Reader = [System.IO.StreamReader]::new($Stream)
        try {
            return $Reader.ReadToEnd()
        }
        finally {
            $Reader.Dispose()
        }
    }
    finally {
        $Stream.Dispose()
    }
}

function Get-JsonlIndex {
    param([string]$Path)

    $Map = [System.Collections.Generic.Dictionary[string,string]]::new(
        [System.StringComparer]::Ordinal
    )
    $StatusMap = [System.Collections.Generic.Dictionary[string,string]]::new(
        [System.StringComparer]::Ordinal
    )

    $Rows = 0
    $Malformed = 0
    $MissingId = 0
    $Duplicates = 0

    foreach ($RawLine in Get-Content -LiteralPath $Path) {
        if ([string]::IsNullOrWhiteSpace($RawLine)) {
            continue
        }

        $Rows++

        try {
            $Record = $RawLine | ConvertFrom-Json -ErrorAction Stop
            $Id = [string]$Record.problem_id

            if ([string]::IsNullOrWhiteSpace($Id)) {
                $MissingId++
                continue
            }

            $Canonical = [ordered]@{}
            foreach ($Property in ($Record.PSObject.Properties | Sort-Object Name)) {
                $Canonical[$Property.Name] = $Property.Value
            }

            $CanonicalJson = ConvertTo-Json -InputObject $Canonical -Depth 100 -Compress

            if ($Map.ContainsKey($Id)) {
                $Duplicates++
            }

            $Map[$Id] = $CanonicalJson
            $StatusMap[$Id] = [string]$Record.status
        }
        catch {
            $Malformed++
        }
    }

    return [PSCustomObject]@{
        Rows = $Rows
        Unique = $Map.Count
        Malformed = $Malformed
        MissingId = $MissingId
        Duplicates = $Duplicates
        Map = $Map
        StatusMap = $StatusMap
    }
}

function Compare-Predictions {
    param(
        [string]$Label,
        [string]$DerivedPath,
        [string]$ArchiveEntryName,
        $Archive
    )

    Add-Line ""
    Add-Line "COMPARISON: $Label"
    Add-Line "DERIVED_PATH: $DerivedPath"
    Add-Line "ARCHIVE_ENTRY: $ArchiveEntryName"

    if (-not (Test-Path -LiteralPath $DerivedPath -PathType Leaf)) {
        Add-Line "RESULT: DERIVED_FILE_MISSING"
        return
    }

    $Entry = $Archive.GetEntry($ArchiveEntryName)
    if ($null -eq $Entry) {
        Add-Line "RESULT: ARCHIVE_ENTRY_MISSING"
        return
    }

    $DerivedHash = (Get-FileHash -LiteralPath $DerivedPath -Algorithm SHA256).Hash.ToLowerInvariant()

    $Stream = $Entry.Open()
    try {
        $SHA = [System.Security.Cryptography.SHA256]::Create()
        try {
            $Bytes = $SHA.ComputeHash($Stream)
            $ArchiveHash = [System.BitConverter]::ToString($Bytes).Replace("-", "").ToLowerInvariant()
        }
        finally {
            $SHA.Dispose()
        }
    }
    finally {
        $Stream.Dispose()
    }

    Add-Line "DERIVED_SHA256: $DerivedHash"
    Add-Line "ARCHIVE_SHA256: $ArchiveHash"
    Add-Line "BYTE_IDENTICAL: $($DerivedHash -eq $ArchiveHash)"

    $DerivedIndex = Get-JsonlIndex -Path $DerivedPath

    $ArchiveText = Read-ZipText -Entry $Entry
    $ArchiveTemp = Join-Path $OutDir ("archive_compare_" + [guid]::NewGuid().ToString("N") + ".jsonl")

    try {
        [System.IO.File]::WriteAllText(
            $ArchiveTemp,
            $ArchiveText,
            [System.Text.UTF8Encoding]::new($false)
        )

        $ArchiveIndex = Get-JsonlIndex -Path $ArchiveTemp

        $MissingInArchive = 0
        $MissingInDerived = 0
        $RecordDifferences = 0
        $StatusDifferences = 0

        foreach ($Id in $DerivedIndex.Map.Keys) {
            if (-not $ArchiveIndex.Map.ContainsKey($Id)) {
                $MissingInArchive++
            }
            else {
                if ($DerivedIndex.Map[$Id] -ne $ArchiveIndex.Map[$Id]) {
                    $RecordDifferences++
                }

                if ($DerivedIndex.StatusMap[$Id] -ne $ArchiveIndex.StatusMap[$Id]) {
                    $StatusDifferences++
                }
            }
        }

        foreach ($Id in $ArchiveIndex.Map.Keys) {
            if (-not $DerivedIndex.Map.ContainsKey($Id)) {
                $MissingInDerived++
            }
        }

        Add-Line "DERIVED_ROWS: $($DerivedIndex.Rows)"
        Add-Line "DERIVED_UNIQUE: $($DerivedIndex.Unique)"
        Add-Line "DERIVED_MALFORMED: $($DerivedIndex.Malformed)"
        Add-Line "DERIVED_DUPLICATES: $($DerivedIndex.Duplicates)"
        Add-Line "ARCHIVE_ROWS: $($ArchiveIndex.Rows)"
        Add-Line "ARCHIVE_UNIQUE: $($ArchiveIndex.Unique)"
        Add-Line "ARCHIVE_MALFORMED: $($ArchiveIndex.Malformed)"
        Add-Line "ARCHIVE_DUPLICATES: $($ArchiveIndex.Duplicates)"
        Add-Line "MISSING_IN_ARCHIVE: $MissingInArchive"
        Add-Line "MISSING_IN_DERIVED: $MissingInDerived"
        Add-Line "FULL_RECORD_DIFFERENCES: $RecordDifferences"
        Add-Line "STATUS_DIFFERENCES: $StatusDifferences"
    }
    finally {
        if (Test-Path -LiteralPath $ArchiveTemp) {
            Remove-Item -LiteralPath $ArchiveTemp -Force
        }
    }
}

Add-Line "G5.9 CHECKPOINT / PREDICTION LINEAGE AUDIT"
Add-Line "Generated: $(Get-Date -Format o)"
Add-Line "Repository: $P2"
Add-Line "Main ZIP SHA256: $((Get-FileHash -LiteralPath $MainZip -Algorithm SHA256).Hash)"
Add-Line ""

Add-Line ("=" * 100)
Add-Line "1. DERIVED ADAPTER MANIFEST"
Add-Line ("=" * 100)

$ManifestHash = (Get-FileHash -LiteralPath $ManifestPath -Algorithm SHA256).Hash
Add-Line "MANIFEST_PATH: $ManifestPath"
Add-Line "MANIFEST_SHA256: $ManifestHash"

$ManifestText = Get-Content -LiteralPath $ManifestPath -Raw
try {
    $ManifestObject = $ManifestText | ConvertFrom-Json -ErrorAction Stop
    $ManifestPretty = ConvertTo-Json -InputObject $ManifestObject -Depth 100
    foreach ($Line in ($ManifestPretty -split "`r?`n")) {
        Add-Line $Line
    }
}
catch {
    Add-Line "MANIFEST_JSON_PARSE_ERROR: $($_.Exception.Message)"
    Add-Line $ManifestText
}

Add-Line ""
Add-Line ("=" * 100)
Add-Line "2. DERIVED PREDICTION VS MAIN.ZIP"
Add-Line ("=" * 100)

$Archive = [System.IO.Compression.ZipFile]::OpenRead($MainZip)

try {
    $Pairs = @(
        @{
            Label = "B4 seed13 S1 / checkpoint 001"
            Derived = Join-Path $Derived "eval_student_ckpt_001_dev_status.jsonl"
            Archive = "B4_seed13/S1/eval_dev.jsonl"
        },
        @{
            Label = "B4 seed13 S2 / checkpoint 002"
            Derived = Join-Path $Derived "eval_student_ckpt_002_dev_status.jsonl"
            Archive = "B4_seed13/S2/eval_dev.jsonl"
        },
        @{
            Label = "B4 seed13 S3 / checkpoint 003"
            Derived = Join-Path $Derived "eval_student_ckpt_003_dev_status.jsonl"
            Archive = "B4_seed13/S3/eval_dev.jsonl"
        }
    )

    foreach ($Pair in $Pairs) {
        Compare-Predictions `
            -Label $Pair.Label `
            -DerivedPath $Pair.Derived `
            -ArchiveEntryName $Pair.Archive `
            -Archive $Archive
    }

    Add-Line ""
    Add-Line ("=" * 100)
    Add-Line "3. B4 SEED13 ARCHIVE METADATA AND MARKERS"
    Add-Line ("=" * 100)

    $B4Entries = @(
        $Archive.Entries |
        Where-Object {
            $_.FullName -match '^B4_seed13/' -and
            (
                $_.FullName -match '\.done/' -or
                $_.FullName -match 'train|checkpoint|lineage|config|manifest|summary|marker'
            )
        } |
        Sort-Object FullName
    )

    Add-Line "B4_METADATA_ENTRY_COUNT: $($B4Entries.Count)"

    foreach ($Entry in $B4Entries) {
        Add-Line ""
        Add-Line "ENTRY: $($Entry.FullName)"
        Add-Line "SIZE: $($Entry.Length)"

        $IsReadable = (
            $Entry.FullName -match '\.(json|txt|yaml|yml|log|jsonl)$' -and
            $Entry.Length -le 2000000 -and
            $Entry.FullName -notmatch 'eval_dev\.jsonl$'
        )

        if ($IsReadable) {
            $Content = Read-ZipText -Entry $Entry
            Add-Line "CONTENT_BEGIN"
            foreach ($Line in ($Content -split "`r?`n")) {
                Add-Line $Line
            }
            Add-Line "CONTENT_END"
        }
    }

    Add-Line ""
    Add-Line ("=" * 100)
    Add-Line "4. S0 EVALUATION METADATA"
    Add-Line ("=" * 100)

    $S0Entries = @(
        $Archive.Entries |
        Where-Object {
            $_.FullName -match '^S0/' -and
            (
                $_.FullName -match '\.done/' -or
                $_.FullName -match 'summary|config|manifest|marker'
            )
        } |
        Sort-Object FullName
    )

    Add-Line "S0_METADATA_ENTRY_COUNT: $($S0Entries.Count)"

    foreach ($Entry in $S0Entries) {
        Add-Line ""
        Add-Line "ENTRY: $($Entry.FullName)"
        Add-Line "SIZE: $($Entry.Length)"

        if ($Entry.Length -le 2000000) {
            $Content = Read-ZipText -Entry $Entry
            Add-Line "CONTENT_BEGIN"
            foreach ($Line in ($Content -split "`r?`n")) {
                Add-Line $Line
            }
            Add-Line "CONTENT_END"
        }
    }

    $S0Prediction = $Archive.GetEntry("S0/eval_dev.jsonl")

    if ($null -ne $S0Prediction) {
        Add-Line ""
        Add-Line "S0 PREDICTION COVERAGE"

        $S0Text = Read-ZipText -Entry $S0Prediction
        $S0Temp = Join-Path $OutDir "s0_archive_eval_dev_audit.jsonl"

        [System.IO.File]::WriteAllText(
            $S0Temp,
            $S0Text,
            [System.Text.UTF8Encoding]::new($false)
        )

        $ExpectedIds = [System.Collections.Generic.HashSet[string]]::new(
            [System.StringComparer]::Ordinal
        )

        foreach ($IdLine in Get-Content -LiteralPath $DDevPath) {
            $Id = $IdLine.Trim()
            if (-not [string]::IsNullOrWhiteSpace($Id)) {
                [void]$ExpectedIds.Add($Id)
            }
        }

        $S0Index = Get-JsonlIndex -Path $S0Temp
        $Missing = 0
        $Unexpected = 0

        foreach ($Id in $ExpectedIds) {
            if (-not $S0Index.Map.ContainsKey($Id)) {
                $Missing++
            }
        }

        foreach ($Id in $S0Index.Map.Keys) {
            if (-not $ExpectedIds.Contains($Id)) {
                $Unexpected++
            }
        }

        Add-Line "D_DEV_UNIQUE: $($ExpectedIds.Count)"
        Add-Line "S0_ROWS: $($S0Index.Rows)"
        Add-Line "S0_UNIQUE: $($S0Index.Unique)"
        Add-Line "S0_MALFORMED: $($S0Index.Malformed)"
        Add-Line "S0_MISSING_ID: $($S0Index.MissingId)"
        Add-Line "S0_DUPLICATES: $($S0Index.Duplicates)"
        Add-Line "S0_MISSING_DDEV: $Missing"
        Add-Line "S0_UNEXPECTED: $Unexpected"
    }
    else {
        Add-Line "S0_EVAL_DEV_MEMBER_MISSING"
    }
}
finally {
    $Archive.Dispose()
}

Add-Line ""
Add-Line ("=" * 100)
Add-Line "5. LOCAL B4 SEED13 PHYSICAL CHECKPOINT CANDIDATES"
Add-Line ("=" * 100)

if (Test-Path -LiteralPath $ModelRoot -PathType Container) {
    $CandidateFiles = @(
        Get-ChildItem -LiteralPath $ModelRoot -File -Recurse -Force -ErrorAction SilentlyContinue |
        Where-Object {
            $_.FullName -match 'B4.*seed.?13|seed.?13.*B4' -or
            $_.DirectoryName -match 'B4.*seed.?13|seed.?13.*B4'
        } |
        Where-Object {
            $_.Extension -in @(".zip", ".safetensors", ".json", ".bin")
        } |
        Sort-Object FullName
    )

    Add-Line "CHECKPOINT_CANDIDATE_COUNT: $($CandidateFiles.Count)"

    foreach ($File in $CandidateFiles) {
        Add-Line "FILE: $($File.FullName)"
        Add-Line "SIZE: $($File.Length)"

        if ($File.Extension -in @(".zip", ".safetensors", ".bin")) {
            Add-Line "SHA256: $((Get-FileHash -LiteralPath $File.FullName -Algorithm SHA256).Hash)"
        }
    }
}
else {
    Add-Line "MODEL_ROOT_MISSING: $ModelRoot"
}

Add-Line ""
Add-Line "6. AUDIT LIMITATIONS"
Add-Line "This audit compares prediction records and inspects available metadata."
Add-Line "A matching hash does not alone prove model/checkpoint provenance."
Add-Line "No model training was executed."
Add-Line "No capability sidecar was executed."
Add-Line "No protected source artifact was modified."

if (Test-Path -LiteralPath $ReportPath) {
    throw "Refusing to overwrite report: $ReportPath"
}

$Lines | Set-Content -LiteralPath $ReportPath -Encoding UTF8

Write-Host ""
Write-Host "LINEAGE AUDIT REPORT CREATED:"
Write-Host $ReportPath
Write-Host ""
Write-Host "SIZE:"
(Get-Item -LiteralPath $ReportPath).Length
Write-Host ""
Write-Host "SHA256:"
(Get-FileHash -LiteralPath $ReportPath -Algorithm SHA256).Hash
Write-Host ""
Write-Host "=== REPORT PREVIEW ==="
Get-Content -LiteralPath $ReportPath -TotalCount 220
