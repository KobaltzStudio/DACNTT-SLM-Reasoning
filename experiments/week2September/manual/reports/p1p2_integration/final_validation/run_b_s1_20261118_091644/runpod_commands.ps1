param(
    [Parameter(Mandatory = $true)][string]$Root,
    [string]$Python = 'C:\KLTN-SLM-Reasoning\.venv\Scripts\python.exe'
)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $Root
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) { throw 'Python interpreter not found' }
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
nvidia-smi --query-gpu=name,memory.total,memory.free,driver_version --format=csv
if ($LASTEXITCODE -ne 0) { throw "nvidia-smi exit $LASTEXITCODE" }
& $Python -B scripts/run_p1_p2.py --help
if ($LASTEXITCODE -ne 0) { throw "Controller help exit $LASTEXITCODE" }
& $Python -B scripts/run_p1p2_post_eval.py --help
if ($LASTEXITCODE -ne 0) { throw "Hook help exit $LASTEXITCODE" }
Get-FileHash -LiteralPath @('config/experiment_config.json','config/p1p2_method_registry.yaml','config/p1p2_unified_run.yaml','splits/d_dev_ids.txt')
# Reference only. Run after separately authorizing the corresponding scope.
# & $Python -B scripts/run_p1_p2.py --method P1P2 --seed 13 --round 1 --resume --dtype bf16 --micro-batch 1 --nll-batch 1 --eval-batch 1
# & $Python -B scripts/run_p1_p2.py --method P1-DEFICIT --seed 13 --from-checkpoint S1 --to-checkpoint S3 --resume --backend hf --dtype bf16 --micro-batch 1 --nll-batch 1 --eval-batch 1
