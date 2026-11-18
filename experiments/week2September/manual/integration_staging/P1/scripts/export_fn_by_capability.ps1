param(
    [Parameter(Mandatory=$true)]
    [string]$InputCsv,

    [Parameter(Mandatory=$true)]
    [string]$OutputDir
)

if (-not (Test-Path $InputCsv)) {
    throw "Input CSV not found: $InputCsv"
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$CapabilityList = @(
    "multiplication",
    "addition",
    "subtraction",
    "division",
    "ratio"
)

$Rows = Import-Csv $InputCsv

foreach ($Capability in $CapabilityList) {
    $Selected = @(
        $Rows | Where-Object {
            $Missing = @(
                ConvertFrom-Json $_.v3_false_negatives
            )

            $Missing -contains $Capability
        }
    )

    $OutputFile = Join-Path $OutputDir "fn_$Capability.csv"

    $Selected |
        Select-Object `
            problem_id,
            question,
            gold_capabilities,
            v3_predictions,
            v3_false_negatives,
            review_notes,
            solution_trace_available |
        Export-Csv `
            $OutputFile `
            -NoTypeInformation `
            -Encoding UTF8

    Write-Host "$Capability : $($Selected.Count) records -> $OutputFile"
}
