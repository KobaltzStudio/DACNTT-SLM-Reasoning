# RunPod handoff cập nhật

**G9 NOT RUN / DELEGATED.** Đây là hướng dẫn cho người vận hành Linux. Cần xác minh và phê duyệt riêng trước từng job. Phiên hiện tại chỉ chạy CPU Windows.

## Chuẩn bị và xác minh

1. Stage trên volume bền vững. Dùng `/workspace/Pipeline/P2/experiments/week2September/manual` làm cwd. Giữ cùng relative paths cho `scripts`, `tests`, `config`, `data`, `trajectory`, `splits`, `runs`, `models`, `reports` và archive G4 ngoài manual. Chuyển đúng file theo hai manifest bên dưới. Giữ bytes, BOM/CRLF, filenames và nguồn Windows. Tránh checkout đổi newline cho artifact đã ký. Tập chuyển hiện tại khoảng 572 MB chưa gồm cache và output.
2. Dùng Python 3.11 và wheel Linux x86_64 đúng driver/CUDA theo `P2/requirements-lock.txt`. Windows đã xác minh torch 2.13.0+cu126, transformers 5.15.0, peft 0.20.0, accelerate 1.14.0, PyYAML 6.0.3, safetensors 0.8.0, matplotlib 3.11.2. Bảng đầy đủ trong `runpod_transfer_verification_sealed.json`. Kiểm `python -m pip check`; wheel/driver bất tương thích cần xử lý trước khi chạy.
3. Stage Student `Qwen/Qwen2.5-1.5B-Instruct` đúng revision `989aa7980e4cf806f80c7fef2b1adb7bc71aa306` cùng tokenizer. SHA weights đã ghi `dd924a11b4c220f385b51ffa522daea7c9f3d850e31b162bb5661df483c6d3ee`. Đặt `HF_HOME` đến cache đã xác minh, giữ hub/Transformers offline. Kiểm tra cache có đủ blob khi dùng symlink.
4. Kiểm BF16, `nvidia-smi`, free VRAM, disk, khả năng hardlink/atomic publish cùng filesystem và quyền tạo lock. Evidence cũ ghi probe 1024 tokens khoảng 6,36 GiB reserved và A S1 khoảng 7,52 GiB. Chọn GPU có dư VRAM so với mốc S1, cân nhắc GPU 16 GiB để tránh sát giới hạn. Phê duyệt riêng nếu cần GPU probe. Giữ optimizer, max length, seed, effective batch, dtype và học LoRA theo protocol.

Đặt `EVIDENCE_DIR` là thư mục chứa hai manifest đã chuyển và `HF_HOME` là model cache. Mỗi manifest phải chạy kiểm từ đúng base.

```bash
set -euo pipefail
export MANUAL_ROOT=/workspace/Pipeline/P2/experiments/week2September/manual
export LEGACY_WINDOWS_ROOT='C:\Users\PC - NGHI\Desktop\Pipeline\P2\experiments\week2September\manual'
: "${EVIDENCE_DIR:?set the directory containing the two SHA manifests}"
: "${HF_HOME:?set the verified model cache}"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
cd "$MANUAL_ROOT"
sha256sum -c "$EVIDENCE_DIR/runpod_sha256sums_sealed.txt"
(cd ../../.. && sha256sum -c "$EVIDENCE_DIR/runpod_p2_sha256sums_sealed.txt")
python --version
python -m pip check
python -B scripts/run_p1_p2.py --help
python -B scripts/run_p1p2_post_eval.py --help

common=(--manual-root "$MANUAL_ROOT" --legacy-windows-root "$LEGACY_WINDOWS_ROOT" --seed 13
        --resume --backend hf --dtype bf16 --micro-batch 1 --nll-batch 1 --eval-batch 1)

CUDA_VISIBLE_DEVICES='' python -B -m unittest discover -s tests -v
CUDA_VISIBLE_DEVICES='' python -B scripts/run_p1_p2.py "${common[@]}" --method P1-DEFICIT --round 1 --dry-run
CUDA_VISIBLE_DEVICES='' python -B scripts/run_p1_p2.py "${common[@]}" --method P1P2 --round 1 --dry-run
CUDA_VISIBLE_DEVICES='' python -B scripts/run_p1_p2.py "${common[@]}" --method P1-DEFICIT --round 2 --dry-run
CUDA_VISIBLE_DEVICES='' python -B scripts/run_p1_p2.py "${common[@]}" --method P1P2 --from-checkpoint S1 --to-checkpoint S3 --dry-run
```

Kỳ vọng A/B S1 có 0 bước. A S2 phải nhận 75 D_dev predictions đã xác minh, adapter S2 và log; chỉ còn eval, checkpoint log, hook và state. Run B S2/S3 phải lập NLL S1/S2 và đúng adapter cha. Kiểm số bước, tags, bytes và log; sai khác dừng trước khi chạy. Trên Linux có một test Windows-native được đánh dấu skip, các test mapping độc lập vẫn thực thi.

## Lệnh tương lai sau phê duyệt

Dùng `common` khai báo ở trên với đúng stage và file transcript riêng cho mỗi lệnh. Cần chạy một checkpoint trước và nghiệm thu đầy đủ. Dùng một process cho mỗi method/seed namespace.

```bash
# Run A S2 only, resume existing 75/500 predictions.
python -B scripts/run_p1_p2.py "${common[@]}" --method P1-DEFICIT --round 2

# Run A S3 only, after S2 passes and approval includes S3.
python -B scripts/run_p1_p2.py "${common[@]}" --method P1-DEFICIT --round 3

# Alternative approved Run A S2-S3 range, after validating the S1 prerequisite.
python -B scripts/run_p1_p2.py "${common[@]}" --method P1-DEFICIT --from-checkpoint S1 --to-checkpoint S3

# Run B S2-S3 range from verified S1.
python -B scripts/run_p1_p2.py "${common[@]}" --method P1P2 --from-checkpoint S1 --to-checkpoint S3

# Full range CLI only if specifically approved. It must reuse staged S1.
python -B scripts/run_p1_p2.py "${common[@]}" --method P1P2 --rounds all
```

Sau mỗi checkpoint lưu train set, selection log, train log, adapter weights/config, checkpoint-log row, D_dev 500/500 và summary/intent, Gold sidecar 85 ID / 7 capabilities, capability state. Kiểm runtime/memory, SHA và parent. Nếu output đã tồn tại nhưng thiếu provenance, giữ nguyên. Kiểm PID, time, GPU và lock owner trước khi cân nhắc recovery. Adapter dở dang, prefix thiếu newline, hash sai, OOM hoặc runtime gọi sai split đều phải dừng và lưu log. Chỉ tiếp tục evaluation S2 khi controller chứng minh có thể append trên prefix đúng. Không được xóa, truncate hoặc đổi frozen parameters để chạy qua lỗi.

Khi các checkpoint cần thiết hoàn tất, xuất G6/G7/G8 vào version mới của báo cáo. Dùng G6 mapped để kiểm tra adapter G4 và dấu vết gốc. G7 chỉ dùng D_dev_select. Handoff không cấp quyền D_test.

```bash
: "${NEW_REPORT_DIR:?set a new, unused reports directory}"
python -B scripts/build_capability_learning_dynamics.py --manual "$MANUAL_ROOT" \
  --legacy-windows-root "$LEGACY_WINDOWS_ROOT" --output "$NEW_REPORT_DIR/g6"
python -B scripts/select_checkpoint_on_dev.py --manual-root "$MANUAL_ROOT" --output "$NEW_REPORT_DIR/g7"
python -B scripts/build_p1p2_analysis_figures.py --manual-root "$MANUAL_ROOT" --preflight
python -B scripts/build_p1p2_analysis_figures.py --manual-root "$MANUAL_ROOT" --output "$NEW_REPORT_DIR/figures"
```

Khi cần bản partial, G7 dùng `--partial`, G8 `--allow-partial`. G6/G8 có thể trả exit 4 do coverage. Kiểm artifact manifest, seven CSV/PNG và source hashes. Bàn giao image/driver, log kiểm staging, lệnh, thời gian, exit, VRAM, SHA và provenance của kết quả theo checkpoint. G9 cần bằng chứng chạy thực tế từ người vận hành.
