$ErrorActionPreference = "Stop"

$Root = "C:\Users\PC - NGHI\Desktop\Pipeline\P2\experiments\week2September\manual"
Set-Location $Root

$RelativeSources = @(
    "reports\p1p2_integration\checkpoint_inventory_audit",
    "reports\capability\g5_9_real_data_s0",
    "reports\p1p2_integration\source_review"
)

$SourceDirectories = @()

foreach ($RelativePath in $RelativeSources) {
    $FullPath = Join-Path $Root $RelativePath

    if (-not (Test-Path -LiteralPath $FullPath -PathType Container)) {
        throw "Missing required source directory: $FullPath"
    }

    $ResolvedPath = (Resolve-Path -LiteralPath $FullPath).Path
    $SourceDirectories += $ResolvedPath
}

$OutputDirectory = Join-Path $Root "reports\p1p2_integration"

if (-not (Test-Path -LiteralPath $OutputDirectory -PathType Container)) {
    New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
}

$Stamp = Get-Date -Format "yyyyMMdd_HHmmss_fff"

$FinalBundle = Join-Path $OutputDirectory "historical_g59_evidence_$Stamp.zip"
$PartialBundle = Join-Path $OutputDirectory "historical_g59_evidence_$Stamp.partial.zip"

if (Test-Path -LiteralPath $FinalBundle) {
    throw "Refusing to overwrite existing bundle: $FinalBundle"
}

if (Test-Path -LiteralPath $PartialBundle) {
    throw "Refusing to overwrite existing partial bundle: $PartialBundle"
}

$SourceFileCount = 0

foreach ($Directory in $SourceDirectories) {
    $Files = @(Get-ChildItem -LiteralPath $Directory -Recurse -File)
    $SourceFileCount += $Files.Count

    Write-Host "SOURCE=$Directory"
    Write-Host "SOURCE_FILES=$($Files.Count)"
}

if ($SourceFileCount -eq 0) {
    throw "All source directories are empty. Refusing to create an empty bundle."
}

try {
    Write-Host "`nARCHIVE_STEP=START"

    Compress-Archive `
        -Path $SourceDirectories `
        -DestinationPath $PartialBundle `
        -CompressionLevel Optimal `
        -ErrorAction Stop

    if (-not (Test-Path -LiteralPath $PartialBundle -PathType Leaf)) {
        throw "Compression returned without creating the partial archive."
    }

    $PartialInfo = Get-Item -LiteralPath $PartialBundle

    if ($PartialInfo.Length -le 0) {
        throw "Partial archive is empty."
    }

    Add-Type -AssemblyName System.IO.Compression.FileSystem

    $Archive = [System.IO.Compression.ZipFile]::OpenRead($PartialBundle)

    try {
        $EntryCount = $Archive.Entries.Count

        if ($EntryCount -le 0) {
            throw "ZIP archive contains no entries."
        }

        $ArchiveFileEntries = @(
            $Archive.Entries | Where-Object {
                -not [string]::IsNullOrEmpty($_.Name)
            }
        )

        if ($ArchiveFileEntries.Count -le 0) {
            throw "ZIP archive contains no files."
        }

        Write-Host "ZIP_VALIDATION=PASS"
        Write-Host "ZIP_ENTRIES=$EntryCount"
        Write-Host "ZIP_FILE_ENTRIES=$($ArchiveFileEntries.Count)"
    }
    finally {
        $Archive.Dispose()
    }

    Move-Item `
        -LiteralPath $PartialBundle `
        -Destination $FinalBundle `
        -ErrorAction Stop

    if (-not (Test-Path -LiteralPath $FinalBundle -PathType Leaf)) {
        throw "Final archive is missing after publication."
    }

    $FinalInfo = Get-Item -LiteralPath $FinalBundle

    if ($FinalInfo.Length -le 0) {
        throw "Final archive is empty."
    }

    $Hash = (Get-FileHash -LiteralPath $FinalBundle -Algorithm SHA256).Hash

    if ([string]::IsNullOrWhiteSpace($Hash)) {
        throw "SHA256 calculation returned an empty value."
    }

    Write-Host "`nHISTORICAL_G59_BUNDLE=CREATED"
    Write-Host "INCLUDED_DIRECTORIES=$($SourceDirectories.Count)"
    Write-Host "SOURCE_FILES=$SourceFileCount"
    Write-Host "BUNDLE_SIZE_BYTES=$($FinalInfo.Length)"
    Write-Host "BUNDLE=$FinalBundle"
    Write-Host "BUNDLE_SHA256=$Hash"
}
catch {
    Write-Host "`nHISTORICAL_G59_BUNDLE=FAILED"
    Write-Host "ERROR=$($_.Exception.Message)"

    if (Test-Path -LiteralPath $PartialBundle -PathType Leaf) {
        Write-Host "PARTIAL_ARCHIVE=$PartialBundle"
        Write-Host "PARTIAL_ARCHIVE_PRESERVED=True"
    }

    throw
}
