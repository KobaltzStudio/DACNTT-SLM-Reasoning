$ErrorActionPreference = "Stop"

$P2 = "C:\Users\PC - NGHI\Desktop\Pipeline\P2\experiments\week2September\manual"
Set-Location -LiteralPath $P2

$MainZip = Join-Path $P2 "runs\main\main.zip"
$DevIdsPath = Join-Path $P2 "splits\d_dev_ids.txt"

if (-not (Test-Path -LiteralPath $MainZip -PathType Leaf)) {
    throw "Missing main archive: $MainZip"
}

if (-not (Test-Path -LiteralPath $DevIdsPath -PathType Leaf)) {
    throw "Missing D_dev ID file: $DevIdsPath"
}

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$OutDir = Join-Path $P2 "reports\p1p2_integration\source_review\run_g59_prediction_discovery_$Timestamp"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$ReportPath = Join-Path $OutDir "g59_prediction_source_discovery.txt"

$Lines = [System.Collections.Generic.List[string]]::new()

function Add-Line {
    param([string]$Value)
    [void]$script:Lines.Add($Value)
}

function Get-JsonlAudit {
    param(
        [string[]]$RawLines,
        [System.Collections.Generic.HashSet[string]]$ExpectedIds
    )

    $Seen = [System.Collections.Generic.HashSet[string]]::new()
    $Rows = 0
    $Missing = 0
    $Malformed = 0
    $Valid = 0
    $InvalidAnswer = 0
    $InvalidFormat = 0
    $OtherStatus = 0

    foreach ($RawLine in $RawLines) {
        if ([string]::IsNullOrWhiteSpace($RawLine)) {
            continue
        }

        $Rows++

        try {
            $Record = $RawLine | ConvertFrom-Json -ErrorAction Stop
            $Id = [string]$Record.problem_id
            $Status = [string]$Record.status

            if ([string]::IsNullOrWhiteSpace($Id)) {
                $Missing++
            }
            else {
                [void]$Seen.Add($Id)
            }

            switch ($Status) {
                "valid" { $Valid++ }
                "invalid_answer" { $InvalidAnswer++ }
                "invalid_format" { $InvalidFormat++ }
                default { $OtherStatus++ }
            }
        }
        catch {
            $Malformed++
        }
    }

    $MissingExpected = 0
    $Unexpected = 0

    if ($null -ne $ExpectedIds) {
        foreach ($Id in $ExpectedIds) {
            if (-not $Seen.Contains($Id)) {
                $MissingExpected++
            }
        }

        foreach ($Id in $Seen) {
            if (-not $ExpectedIds.Contains($Id)) {
                $Unexpected++
            }
        }
    }

    return [PSCustomObject]@{
        Rows = $Rows
        UniqueIds = $Seen.Count
        MissingIds = $Missing
        Malformed = $Malformed
        Valid = $Valid
        InvalidAnswer = $InvalidAnswer
        InvalidFormat = $InvalidFormat
        OtherStatus = $OtherStatus
        MissingExpectedIds = $MissingExpected
        UnexpectedIds = $Unexpected
    }
}

function Get-ZipEntryLines {
    param($Entry)

    $Stream = $Entry.Open()
    try {
        $Reader = [System.IO.StreamReader]::new($Stream)
        try {
            $Content = $Reader.ReadToEnd()
            return ,([string[]]($Content -split "`r?`n"))
        }
        finally {
            $Reader.Dispose()
        }
    }
    finally {
        $Stream.Dispose()
    }
}

$ExpectedIds = [System.Collections.Generic.HashSet[string]]::new(
    [System.StringComparer]::Ordinal
)

foreach ($IdLine in Get-Content -LiteralPath $DevIdsPath) {
    $Id = $IdLine.Trim()
    if (-not [string]::IsNullOrWhiteSpace($Id)) {
        [void]$ExpectedIds.Add($Id)
    }
}

Add-Line "G5.9 PREDICTION SOURCE DISCOVERY"
Add-Line "Repository: $P2"
Add-Line "Generated: $(Get-Date -Format o)"
Add-Line "Main archive: $MainZip"
Add-Line "Main archive SHA256: $((Get-FileHash -LiteralPath $MainZip -Algorithm SHA256).Hash)"
Add-Line "D_dev file: $DevIdsPath"
Add-Line "D_dev unique IDs: $($ExpectedIds.Count)"
Add-Line ""

Add-Line ("=" * 100)
Add-Line "1. DERIVED_PREDICTIONS DIRECTORIES"
Add-Line ("=" * 100)

$ExcludedPattern = '\\(\.venv|node_modules|__pycache__|\.git)\\'

$DerivedDirs = @(
    Get-ChildItem -LiteralPath $P2 -Directory -Recurse -Force -ErrorAction SilentlyContinue |
    Where-Object {
        $_.Name -eq "derived_predictions" -and
        $_.FullName -notmatch $ExcludedPattern
    } |
    Sort-Object FullName
)

Add-Line "DERIVED_DIRECTORY_COUNT: $($DerivedDirs.Count)"

foreach ($Dir in $DerivedDirs) {
    Add-Line ""
    Add-Line "DIRECTORY: $($Dir.FullName)"

    $Files = @(
        Get-ChildItem -LiteralPath $Dir.FullName -File -Recurse -Force |
        Where-Object { $_.Extension -in @(".jsonl", ".json") } |
        Sort-Object FullName
    )

    Add-Line "JSON_FILE_COUNT: $($Files.Count)"

    foreach ($File in $Files) {
        $Hash = (Get-FileHash -LiteralPath $File.FullName -Algorithm SHA256).Hash
        Add-Line "FILE: $($File.FullName)"
        Add-Line "SIZE: $($File.Length)"
        Add-Line "SHA256: $Hash"

        if ($File.Extension -eq ".jsonl") {
            $RawLines = @(Get-Content -LiteralPath $File.FullName)
            $Audit = Get-JsonlAudit -RawLines $RawLines -ExpectedIds $ExpectedIds

            Add-Line (
                "AUDIT: ROWS={0}; UNIQUE={1}; MISSING={2}; MALFORMED={3}; VALID={4}; INVALID_ANSWER={5}; INVALID_FORMAT={6}; OTHER_STATUS={7}; MISSING_DDEV={8}; UNEXPECTED={9}" -f
                $Audit.Rows,
                $Audit.UniqueIds,
                $Audit.MissingIds,
                $Audit.Malformed,
                $Audit.Valid,
                $Audit.InvalidAnswer,
                $Audit.InvalidFormat,
                $Audit.OtherStatus,
                $Audit.MissingExpectedIds,
                $Audit.UnexpectedIds
            )
        }

        Add-Line ""
    }
}

Add-Line ""
Add-Line ("=" * 100)
Add-Line "2. MAIN.ZIP EVAL_DEV MEMBERS"
Add-Line ("=" * 100)

$Archive = [System.IO.Compression.ZipFile]::OpenRead($MainZip)

try {
    $PredictionMembers = @(
        $Archive.Entries |
        Where-Object {
            $_.FullName -match '(^|/)eval_dev\.jsonl$'
        } |
        Sort-Object FullName
    )

    Add-Line "EVAL_DEV_MEMBER_COUNT: $($PredictionMembers.Count)"

    foreach ($Member in $PredictionMembers) {
        $Stream = $Member.Open()

        try {
            $SHA = [System.Security.Cryptography.SHA256]::Create()
            try {
                $HashBytes = $SHA.ComputeHash($Stream)
                $MemberHash = [System.BitConverter]::ToString($HashBytes).Replace("-", "").ToLowerInvariant()
            }
            finally {
                $SHA.Dispose()
            }
        }
        finally {
            $Stream.Dispose()
        }

        Add-Line "ZIP_MEMBER: $($Member.FullName)"
        Add-Line "SIZE: $($Member.Length)"
        Add-Line "SHA256: $MemberHash"

        if ($Member.FullName -eq "S0/eval_dev.jsonl") {
            $RawLines = @(Get-ZipEntryLines -Entry $Member)
            $Audit = Get-JsonlAudit -RawLines $RawLines -ExpectedIds $ExpectedIds

            Add-Line (
                "S0_AUDIT: ROWS={0}; UNIQUE={1}; MISSING={2}; MALFORMED={3}; VALID={4}; INVALID_ANSWER={5}; INVALID_FORMAT={6}; OTHER_STATUS={7}; MISSING_DDEV={8}; UNEXPECTED={9}" -f
                $Audit.Rows,
                $Audit.UniqueIds,
                $Audit.MissingIds,
                $Audit.Malformed,
                $Audit.Valid,
                $Audit.InvalidAnswer,
                $Audit.InvalidFormat,
                $Audit.OtherStatus,
                $Audit.MissingExpectedIds,
                $Audit.UnexpectedIds
            )
        }

        Add-Line ""
    }

    Add-Line ""
    Add-Line "3. S0 EVALUATION MARKERS"
    Add-Line ("=" * 100)

    $S0Markers = @(
        $Archive.Entries |
        Where-Object {
            $_.FullName -match '^S0/\.done/.*eval.*dev.*\.json$'
        }
    )

    Add-Line "S0_EVAL_MARKER_COUNT: $($S0Markers.Count)"

    foreach ($Marker in $S0Markers) {
        Add-Line "MARKER: $($Marker.FullName)"
        $RawLines = @(Get-ZipEntryLines -Entry $Marker)
        foreach ($Line in $RawLines) {
            Add-Line $Line
        }
        Add-Line ""
    }

    Add-Line ""
    Add-Line "4. S0 LOCAL CANDIDATES"
    Add-Line ("=" * 100)

    $S0Candidates = @(
        "runs\main\S0\eval_dev.jsonl",
        "reports\task5\smoke_test\results\eval_S0_dev.jsonl",
        "reports\task7\smoke\eval_S0_dev_10.jsonl"
    )

    foreach ($RelativePath in $S0Candidates) {
        $FullPath = Join-Path $P2 $RelativePath

        if (Test-Path -LiteralPath $FullPath -PathType Leaf) {
            $File = Get-Item -LiteralPath $FullPath
            $Hash = (Get-FileHash -LiteralPath $FullPath -Algorithm SHA256).Hash

            Add-Line "S0_CANDIDATE: $FullPath"
            Add-Line "SIZE: $($File.Length)"
            Add-Line "SHA256: $Hash"

            if ($File.Extension -eq ".jsonl") {
                $RawLines = @(Get-Content -LiteralPath $FullPath)
                $Audit = Get-JsonlAudit -RawLines $RawLines -ExpectedIds $ExpectedIds

                Add-Line (
                    "AUDIT: ROWS={0}; UNIQUE={1}; MISSING={2}; MALFORMED={3}; VALID={4}; INVALID_ANSWER={5}; INVALID_FORMAT={6}; OTHER_STATUS={7}; MISSING_DDEV={8}; UNEXPECTED={9}" -f
                    $Audit.Rows,
                    $Audit.UniqueIds,
                    $Audit.MissingIds,
                    $Audit.Malformed,
                    $Audit.Valid,
                    $Audit.InvalidAnswer,
                    $Audit.InvalidFormat,
                    $Audit.OtherStatus,
                    $Audit.MissingExpectedIds,
                    $Audit.UnexpectedIds
                )
            }
        }
        else {
            Add-Line "S0_CANDIDATE_MISSING: $FullPath"
        }

        Add-Line ""
    }
}
finally {
    $Archive.Dispose()
}

Add-Line ""
Add-Line ("=" * 100)
Add-Line "5. DISCOVERY SUMMARY"
Add-Line ("=" * 100)
Add-Line "D_dev unique IDs: $($ExpectedIds.Count)"
Add-Line "Derived directories found: $($DerivedDirs.Count)"
Add-Line "Archive eval_dev members: $($PredictionMembers.Count)"
Add-Line "No source files were modified."
Add-Line "No model training was executed."
Add-Line "No capability sidecar was executed."

if (Test-Path -LiteralPath $ReportPath) {
    throw "Refusing to overwrite report: $ReportPath"
}

$Lines | Set-Content -LiteralPath $ReportPath -Encoding UTF8

Write-Host ""
Write-Host "DISCOVERY REPORT CREATED:"
Write-Host $ReportPath
Write-Host ""
Write-Host "SIZE:"
(Get-Item -LiteralPath $ReportPath).Length
Write-Host ""
Write-Host "SHA256:"
(Get-FileHash -LiteralPath $ReportPath -Algorithm SHA256).Hash
Write-Host ""
Write-Host "=== REPORT PREVIEW ==="
Get-Content -LiteralPath $ReportPath -TotalCount 180
