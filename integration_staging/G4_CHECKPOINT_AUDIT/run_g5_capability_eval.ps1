param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("S1", "S2", "S3")]
    [string]$Stage
)

$ErrorActionPreference = "Stop"

$P2 = "C:\Users\PC - NGHI\Desktop\Pipeline\P2"
$Manual = Join-Path $P2 "experiments\week2September\manual"
$Audit = Join-Path $P2 "integration_staging\G4_CHECKPOINT_AUDIT"

$OutRoot = Join-Path $Manual "reports\capability_g4_validation"
$LogDir = Join-Path $Audit "execution_logs"

$Evaluator = Join-Path $Manual "scripts\capability_eval.py"
$PreflightPath = Join-Path $Audit "g5_capability_preflight.json"

$GoldManifest = Join-Path $Manual "data\gold_vfinal\gold_vfinal_manifest.json"
$GoldLabels = Join-Path $Manual "data\gold_vfinal\supplement_annotations_vfinal.jsonl"
$Approval = Join-Path $Manual "data\gold_releases\vFinal_2026-11-16\gold_supplement_85_approved_review.csv"
$DevIds = Join-Path $Manual "splits\d_dev_ids.txt"
$Config = Join-Path $Manual "integration_staging\P1\config\experiment_config.json"
$CheckpointLog = Join-Path $Manual "runs\main\B4_seed13\checkpoint_log.jsonl"

$StageMap = @{
    "S1" = @{
        RunId = "B4_seed13_S1"
        Round = 1
        Checkpoint = Join-Path $Audit "extracted_checkpoints\B4_seed13\S1"
        Prediction = Join-Path $Manual "reports\p1p2_integration\derived_predictions\B4_seed13\eval_student_ckpt_001_dev_status.jsonl"
        TrainSet = Join-Path $Audit "original_train_sets\S1\train_set.json"
    }
    "S2" = @{
        RunId = "B4_seed13_S2"
        Round = 2
        Checkpoint = Join-Path $Audit "extracted_checkpoints\B4_seed13\S2"
        Prediction = Join-Path $Manual "reports\p1p2_integration\derived_predictions\B4_seed13\eval_student_ckpt_002_dev_status.jsonl"
        TrainSet = Join-Path $Audit "original_train_sets\S2\train_set.json"
    }
    "S3" = @{
        RunId = "B4_seed13_S3"
        Round = 3
        Checkpoint = Join-Path $Audit "extracted_checkpoints\B4_seed13\S3"
        Prediction = Join-Path $Manual "reports\p1p2_integration\derived_predictions\B4_seed13\eval_student_ckpt_003_dev_status.jsonl"
        TrainSet = Join-Path $Audit "original_train_sets\S3\train_set.json"
    }
}

$Spec = $StageMap[$Stage]
$RunDir = Join-Path $OutRoot $Spec.RunId

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogBase = "$($Spec.RunId)_$Timestamp"

$TranscriptLog = Join-Path $LogDir "$LogBase.transcript.log"
$PythonLog = Join-Path $LogDir "$LogBase.python.log"
$StatusFile = Join-Path $LogDir "$LogBase.status.json"

$StartedAt = Get-Date
$Timer = [System.Diagnostics.Stopwatch]::StartNew()

$ExitCode = 1
$StageStatus = "FAILED"
$ErrorMessage = $null
$TranscriptStarted = $false

try {
    Start-Transcript -LiteralPath $TranscriptLog -Force | Out-Null
    $TranscriptStarted = $true

    Write-Host "========== G5 CAPABILITY EVALUATION =========="
    Write-Host "STAGE=$Stage"
    Write-Host "RUN_ID=$($Spec.RunId)"
    Write-Host "START_TIME=$($StartedAt.ToString('o'))"
    Write-Host "TRANSCRIPT_LOG=$TranscriptLog"
    Write-Host "PYTHON_LOG=$PythonLog"
    Write-Host "STATUS_FILE=$StatusFile"

    $RequiredFiles = @(
        $Evaluator,
        $PreflightPath,
        $GoldManifest,
        $GoldLabels,
        $Approval,
        $DevIds,
        $Config,
        $CheckpointLog,
        $Spec.Prediction,
        $Spec.TrainSet,
        (Join-Path $Spec.Checkpoint "adapter_model.safetensors"),
        (Join-Path $Spec.Checkpoint "adapter_config.json"),
        (Join-Path $Spec.Checkpoint "train_log.json")
    )

    foreach ($File in $RequiredFiles) {
        if (-not (Test-Path -LiteralPath $File -PathType Leaf)) {
            throw "REQUIRED_FILE_MISSING: $File"
        }
    }

    if (-not (Test-Path -LiteralPath $Spec.Checkpoint -PathType Container)) {
        throw "CHECKPOINT_DIRECTORY_MISSING: $($Spec.Checkpoint)"
    }

    $Preflight = Get-Content -LiteralPath $PreflightPath -Raw |
        ConvertFrom-Json

    if ($Preflight.status -ne "PASS") {
        throw "PREFLIGHT_NOT_PASS"
    }

    Write-Host "PREFLIGHT=PASS"
    Write-Host "INPUT_FILES=PASS"

    $Arguments = @(
        $Evaluator,
        "--run-id", $Spec.RunId,
        "--method", "B4",
        "--seed", "13",
        "--round", "$($Spec.Round)",
        "--checkpoint", $Spec.Checkpoint,
        "--dev-predictions", $Spec.Prediction,
        "--gold-manifest", $GoldManifest,
        "--gold-labels", $GoldLabels,
        "--approval-csv", $Approval,
        "--dev-ids", $DevIds,
        "--config", $Config,
        "--train-set", $Spec.TrainSet,
        "--train-log", (Join-Path $Spec.Checkpoint "train_log.json"),
        "--checkpoint-log", $CheckpointLog,
        "--out-root", $OutRoot
    )

    Write-Host "EVALUATOR_START=$(Get-Date -Format o)"

    # Capture Python stdout and stderr into a dedicated log.
    & python @Arguments *> $PythonLog
    $ExitCode = $LASTEXITCODE

    Write-Host "EVALUATOR_EXIT_CODE=$ExitCode"

    if (Test-Path -LiteralPath $PythonLog) {
        Write-Host "========== PYTHON OUTPUT =========="
        Get-Content -LiteralPath $PythonLog
    }

    if ($ExitCode -ne 0) {
        throw "PYTHON_EVALUATOR_EXITED_WITH_CODE_$ExitCode"
    }

    if (-not (Test-Path -LiteralPath $RunDir -PathType Container)) {
        throw "EXPECTED_RUN_DIRECTORY_NOT_CREATED: $RunDir"
    }

    $ExpectedOutputs = @(
        "capability_metrics.csv",
        "capability_metrics.jsonl",
        "checkpoint_lineage.json"
    )

    foreach ($Name in $ExpectedOutputs) {
        $OutputFile = Join-Path $RunDir $Name
        if (-not (Test-Path -LiteralPath $OutputFile -PathType Leaf)) {
            throw "EXPECTED_OUTPUT_MISSING: $OutputFile"
        }
    }

    # Validate that the lineage file is readable JSON.
    $LineagePath = Join-Path $RunDir "checkpoint_lineage.json"
    $null = Get-Content -LiteralPath $LineagePath -Raw |
        ConvertFrom-Json

    $StageStatus = "PASS"
    Write-Host "OUTPUT_FILES=PASS"
    Write-Host "LINEAGE_JSON_PARSE=PASS"
    Write-Host "STAGE_STATUS=PASS"
}
catch {
    $ErrorMessage = $_.Exception.Message
    $StageStatus = "FAILED"
    Write-Host "STAGE_STATUS=FAILED"
    Write-Host "ERROR=$ErrorMessage"
}
finally {
    $Timer.Stop()
    $EndedAt = Get-Date

    $Status = [ordered]@{
        stage = $Stage
        run_id = $Spec.RunId
        status = $StageStatus
        exit_code = if ($StageStatus -eq "PASS") { 0 } else { 1 }
        started_at = $StartedAt.ToString("o")
        ended_at = $EndedAt.ToString("o")
        elapsed_seconds = [math]::Round($Timer.Elapsed.TotalSeconds, 2)
        error = $ErrorMessage
        output_directory = $RunDir
        transcript_log = $TranscriptLog
        python_log = $PythonLog
    }

    $Status | ConvertTo-Json -Depth 5 |
        Set-Content -LiteralPath $StatusFile -Encoding UTF8

    Write-Host "END_TIME=$($EndedAt.ToString('o'))"
    Write-Host "ELAPSED_SECONDS=$([math]::Round($Timer.Elapsed.TotalSeconds, 2))"
    Write-Host "FINAL_STATUS=$StageStatus"
    Write-Host "STATUS_FILE=$StatusFile"

    if ($TranscriptStarted) {
        Stop-Transcript | Out-Null
    }
}

if ($StageStatus -eq "PASS") {
    exit 0
}
else {
    exit 1
}
