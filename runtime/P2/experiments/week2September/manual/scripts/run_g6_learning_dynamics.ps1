param(
    [int]$ExpectedSidecars = 33,
    [string[]]$ExtraRoot = @()
)

$ErrorActionPreference = "Stop"

$Manual = "C:\Users\PC - NGHI\Desktop\Pipeline\P2\experiments\week2September\manual"
Set-Location -LiteralPath $Manual

$PythonCommand = Get-Command python -ErrorAction Stop
$Python = $PythonCommand.Source
$Builder = Join-Path $Manual "scripts\build_capability_learning_dynamics.py"
$Output = Join-Path $Manual "reports\p1p2_integration\final_validation"
$Log = Join-Path $Output "g6_learning_dynamics_console.txt"

if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw "ACTIVE_PYTHON_NOT_FOUND: $Python"
}
if (-not (Test-Path -LiteralPath $Builder -PathType Leaf)) {
    throw "G6_BUILDER_NOT_FOUND: $Builder"
}

$VenvCheck = & $Python -c "import sys; print('YES' if sys.prefix != sys.base_prefix else 'NO')"
if ($LASTEXITCODE -ne 0 -or $VenvCheck -ne "YES") {
    throw "PROJECT_VENV_NOT_ACTIVE"
}

Write-Host "PYTHON: $Python"
Write-Host "VENV: PASS"

& $Python -m py_compile $Builder
if ($LASTEXITCODE -ne 0) {
    throw "G6_BUILDER_COMPILE_FAILED"
}
Write-Host "COMPILE: PASS"

& $Python $Builder --help
if ($LASTEXITCODE -ne 0) {
    throw "G6_BUILDER_HELP_FAILED"
}
Write-Host "CLI_HELP: PASS"

New-Item -ItemType Directory -Force -Path $Output | Out-Null

$CanonicalFiles = @(
    "capability_learning_dynamics_seed13.csv",
    "capability_learning_dynamics_seed13.json",
    "capability_learning_dynamics_seed13.md",
    "capability_sidecar_inventory_seed13.json"
)
$ExistingCanonical = @(
    foreach ($Name in $CanonicalFiles) {
        $Path = Join-Path $Output $Name
        if (Test-Path -LiteralPath $Path -PathType Leaf) { $Path }
    }
)
if ($ExistingCanonical.Count -gt 0) {
    $ExistingCanonical | ForEach-Object { Write-Host "EXISTS: $_" }
    throw "G6_FINAL_OUTPUT_EXISTS_NO_OVERWRITE"
}

$BuilderArgs = @(
    $Builder,
    "--manual", $Manual,
    "--output", $Output,
    "--expected-sidecars", "$ExpectedSidecars"
)
foreach ($Root in $ExtraRoot) {
    $ResolvedRoot = [System.IO.Path]::GetFullPath($Root)
    if (-not (Test-Path -LiteralPath $ResolvedRoot -PathType Container)) {
        throw "G6_EXTRA_ROOT_NOT_FOUND: $ResolvedRoot"
    }
    $BuilderArgs += @("--extra-root", $ResolvedRoot)
}

Write-Host "`n=== BUILD G6 ==="
Write-Host "EXPECTED_SIDECARS: $ExpectedSidecars"
foreach ($Root in $ExtraRoot) { Write-Host "EXTRA_ROOT: $Root" }

$PreviousPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& $Python @BuilderArgs 2>&1 | Tee-Object -FilePath $Log
$BuildExit = $LASTEXITCODE
$ErrorActionPreference = $PreviousPreference

if ($BuildExit -eq 4) {
    Write-Warning "G6 is PARTIAL. Review g6_partial_learning_dynamics_seed13.md and g6_partial_sidecar_inventory_seed13.json."
    return
}
if ($BuildExit -ne 0) {
    throw "G6_BUILDER_FAILED_EXIT_$BuildExit. Inspect $Log."
}

foreach ($Name in $CanonicalFiles) {
    $Path = Join-Path $Output $Name
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "G6_OUTPUT_MISSING: $Path"
    }
}
foreach ($Name in @("capability_learning_dynamics_seed13.json", "capability_sidecar_inventory_seed13.json")) {
    Get-Content -LiteralPath (Join-Path $Output $Name) -Raw |
        ConvertFrom-Json -ErrorAction Stop | Out-Null
}

Get-ChildItem -LiteralPath $Output -File |
    Where-Object { $_.Name -in $CanonicalFiles -or $_.Name -eq "g6_learning_dynamics_console.txt" } |
    Select-Object Name, Length, LastWriteTime |
    Format-Table -AutoSize

Write-Host "G6_BUILDER_EXECUTION: PASS"
Write-Host "This PASS requires all 33+ sidecars to validate and the seed-13 method/checkpoint matrix to be complete."
