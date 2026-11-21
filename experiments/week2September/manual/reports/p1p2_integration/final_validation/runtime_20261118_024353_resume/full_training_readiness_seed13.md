# Full LoRA training readiness — seed 13

**Ready for an authorization decision. Full training remains NOT RUN.** Windows dry-run, fixture orchestration and the bounded real-Student LoRA smoke are separate checks. The smoke does not establish runtime throughput, full-length peak VRAM, scientific accuracy or the production S1–S3 artifacts.

- The two Round 1 selection pairs and shared S0 are available and pass controller preflight. P1-DEFICIT dispatches no NLL. P1P2 uses the already verified S0 NLL for Round 1 and plans fresh S1 and S2 NLL for Rounds 2 and 3. The frozen alpha is 0.5.
- The fixture controller uses a real capability hook and state subprocess. Synthetic NLL, selection, training and D_dev substitute for expensive model subprocesses. The fixture verified S1–S3 parent adapter lineage, exact resume, post-hook state, collision handling and safe retry where outputs were absent or provided a valid evaluation prefix.
- A process interruption that leaves a partial adapter, incomplete NLL pair, corrupt fingerprint or uncertain lock requires manual inspection. Preserve the artifact. A stuck lock must be verified against the original controller process and its write activity before clearing it. No automatic stale-lock removal is implemented.
- The B4 S1 mismatch resolves to the existing derived prediction that exactly matches sidecar SHA-256. G7 still cannot select all checkpoints because the six new predictions and sidecars are absent. G6 and G8 likewise depend on these artifacts. RunPod remains delegated.

## Windows commands

Use this PowerShell block to set the verified working directory and interpreter.

```powershell
$ErrorActionPreference = 'Stop'
$Root = 'C:\Users\PC - NGHI\Desktop\Pipeline\P2\experiments\week2September\manual'
$Python = 'C:\KLTN-SLM-Reasoning\.venv\Scripts\python.exe'
Set-Location -LiteralPath $Root
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
function Invoke-PipelinePython {
    & $Python @args
    if ($LASTEXITCODE -ne 0) { throw "Python exited $LASTEXITCODE" }
}
```

Only after explicit authorization:

```powershell
Invoke-PipelinePython -B scripts/run_p1_p2.py --method P1-DEFICIT --seed 13 --rounds all --resume --dtype bf16 --micro-batch 1 --nll-batch 1 --eval-batch 1
# Validate Run A before launching Run B.
Invoke-PipelinePython -B scripts/run_p1_p2.py --method P1-DEFICIT --seed 13 --rounds all --resume --dry-run --dtype bf16 --micro-batch 1 --nll-batch 1 --eval-batch 1
Invoke-PipelinePython -B scripts/run_p1_p2.py --method P1P2 --seed 13 --rounds all --resume --dtype bf16 --micro-batch 1 --nll-batch 1 --eval-batch 1
# Use this range instead of all rounds when S1 already exists and is verified.
Invoke-PipelinePython -B scripts/run_p1_p2.py --method P1P2 --seed 13 --from-checkpoint S1 --to-checkpoint S3 --resume --dtype bf16 --micro-batch 1 --nll-batch 1 --eval-batch 1
```

After the required S1–S3 artifacts are present:

```powershell
Invoke-PipelinePython -B scripts/build_capability_learning_dynamics.py --manual $Root
Invoke-PipelinePython -B scripts/select_checkpoint_on_dev.py --manual-root $Root
Invoke-PipelinePython -B scripts/build_p1p2_analysis_figures.py --manual-root $Root --preflight
Invoke-PipelinePython -B scripts/build_p1p2_analysis_figures.py --manual-root $Root
```
