# Handoff controller P1/P2 seed 13

Checkout nguồn là `C:\Users\PC - NGHI\Desktop\Pipeline\P2\experiments\week2September\manual` trên branch `codex/controller-dryrun-fix`. Kết quả bên dưới bao gồm diff cục bộ. Build lại từ đúng source đã kiểm tra trước khi chuyển máy.

## Đầu vào và môi trường

- Python 3.11.9 tại `C:\KLTN-SLM-Reasoning\.venv\Scripts\python.exe`. Runtime đã quan sát gồm torch 2.13.0+cu126, transformers 5.15.0, peft 0.20.0, accelerate 1.14.0 và PyYAML 6.0.3. Dùng `P2/requirements-lock.txt` của repo làm manifest. Kiểm tra wheel CUDA và driver trên host đích.
- Dùng pinned Student `Qwen/Qwen2.5-1.5B-Instruct@989aa7980e4cf806f80c7fef2b1adb7bc71aa306`. Cache Windows đã có config, tokenizer và model.safetensors của revision này. Teacher `Qwen/Qwen2.5-3B-Instruct` đã cung cấp trajectory trong pool đông cứng. Không cần chạy Teacher để thực thi controller.
- Mang theo `config/experiment_config.json`, `config/p1p2_method_registry.yaml`, `config/p1p2_unified_run.yaml`, verified pool và token table kèm summary, các split manifest và Gold đầu vào. Dùng trường `verified_inputs` trong báo cáo dry-run để đối chiếu SHA-256 của dữ liệu và cấu hình chính.
- Giữ shared S0 tại `runs/main/S0`, sidecar tại `reports/capability/g5_9_real_data_s0/SHARED_seed0_S0`, cùng S0 reference tại `reports/p1p2_integration/source_review/s0_base_model_reference.json`. S0 dùng Student base và SHA-256 prediction `49eb7c7f0d76bbb707b62446a265387f6ca5f0418572953f02383de7eb9ca77c`.
- Round 1 seed 13 đã được tiếp nhận từ hai cặp train set/selection log hiện có. Các record này và một số artifact cũ chứa đường dẫn Windows tuyệt đối. Khi chuyển host cần xác minh các tham chiếu state, NLL, pool và adapter trước khi tái sử dụng. Giữ nguyên bản nguồn để đối chiếu; không đổi hash của bản gốc.

## Runtime và artifact

Từ thư mục `manual`, CLI lập kế hoạch S1 đến S3 theo checkpoint. `--from-checkpoint S1 --to-checkpoint S3` xác minh S1 và xử lý S2, S3. S1 bắt đầu từ base LoRA. S2 và S3 dùng `--init-adapter` từ checkpoint trước. P1-DEFICIT chỉ dùng capability state. P1P2 dùng NLL S0, S1 và S2 tương ứng với ba lượt selection, với alpha 0.5. Mỗi lượt đánh giá D_dev trước khi chạy hook Gold và dựng capability state.

Run, model và report dùng `runs/p1p2_integration`, `models/p1p2_integration` và `reports/p1p2_integration`. Seed ngoài 13, 42 và 2026 dùng hậu tố `_custom`. Mỗi phương pháp có checkpoint log nối thêm record. Provenance gồm hash của adapter, train set, selection log, train log, D_dev intent/prediction và fingerprint sidecar. Nếu dừng giữa stage, chạy lại đúng method, seed, batch và dtype với `--resume`. Nếu còn lock sau khi process bị chấm dứt, xác minh không còn process sở hữu lock trước khi xử lý lock. Nếu checkpoint hoặc prediction có provenance thiếu hoặc không khớp, bảo toàn artifact và xử lý nguồn lỗi trước khi resume.

RTX 4060 Laptop có 8188 MiB VRAM, driver 610.78, CUDA 12.6 khả dụng qua PyTorch, và khoảng 102 GB dung lượng trống tại thời điểm audit. Cấu hình nghiên cứu giữ LoRA, bf16, sequence length 1024, effective batch 8 và gradient checkpointing. Nếu cần giảm peak VRAM sau khi được phép thử, micro-batch 1 cho accumulation 8. Peak VRAM, train step và save/load adapter của pipeline này chưa được xác minh bằng chạy thực tế.

## Windows PowerShell

```powershell
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath 'C:\Users\PC - NGHI\Desktop\Pipeline\P2\experiments\week2September\manual'
$py = 'C:\KLTN-SLM-Reasoning\.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $py -PathType Leaf)) { throw "Python missing: $py" }
function Invoke-PipelinePython {
    & $py @args
    if ($LASTEXITCODE -ne 0) { throw "Python failed ($LASTEXITCODE): $args" }
}
Invoke-PipelinePython -m compileall -q scripts tests
Invoke-PipelinePython -B -m unittest discover -s tests -v
Invoke-PipelinePython -B scripts/run_p1_p2.py --method P1-DEFICIT --seed 13 --rounds all --dry-run
Invoke-PipelinePython -B scripts/run_p1_p2.py --method P1P2 --seed 13 --rounds all --dry-run
Invoke-PipelinePython -B scripts/run_p1_p2.py --methods P1-DEFICIT P1P2 --seeds 13 --rounds all --dry-run
Invoke-PipelinePython -B -c "import torch; assert torch.cuda.is_available() and torch.cuda.is_bf16_supported(); print(torch.__version__, torch.version.cuda, torch.cuda.get_device_properties(0))"
```

Chỉ chạy ba lệnh sau khi có phê duyệt training và đã xác nhận cache model cùng tài nguyên runtime. Giữ cùng tùy chọn khi resume.

```powershell
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
Invoke-PipelinePython -B scripts/run_p1_p2.py --method P1-DEFICIT --seed 13 --rounds all --resume --dtype bf16 --micro-batch 1 --nll-batch 1 --eval-batch 1
Invoke-PipelinePython -B scripts/run_p1_p2.py --method P1P2 --seed 13 --rounds all --resume --dtype bf16 --micro-batch 1 --nll-batch 1 --eval-batch 1
```

Validation sau training dùng cùng CLI và các tùy chọn runtime, thêm `--dry-run` để kiểm tra lại artifact. Với RunPod, chọn interpreter Linux, chạy ba dry-run với cùng dữ liệu, đối chiếu `verified_inputs` và đường dẫn được dựng trong plan. Handoff còn cần xác minh migration tham chiếu artifact cũ, runtime Linux và VRAM thực đo. Chưa có bằng chứng RunPod execution.
