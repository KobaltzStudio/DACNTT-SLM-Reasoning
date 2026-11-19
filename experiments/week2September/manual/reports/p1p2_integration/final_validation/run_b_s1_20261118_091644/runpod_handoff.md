# Bàn giao hoàn tất P1 P2 trên RunPod

**G9 NOT RUN / DELEGATED.** Người vận hành cần xác minh môi trường Linux, đường dẫn tương thích và các fingerprint trước khi thực thi. Các lệnh dưới đây là hợp đồng CLI đã kiểm tra trên Windows.

## Chuẩn bị môi trường và staging

1. Tạo volume lưu bền vững và đặt checkout/staging tại `/workspace/Pipeline/P2/experiments/week2September/manual`. Đặt `MANUAL_ROOT` đến thư mục này và chạy từ đó. Giữ `scripts/`, `config/`, `trajectory/`, `data/`, `splits/`, `runs/`, `models/` và `reports/` đúng vị trí tương đối như tại Windows.
2. Dùng Python 3.11 và môi trường cô lập. Đối chiếu `../../../requirements-lock.txt` với image và marker hệ điều hành trước khi cài. Runtime Windows đã xác minh dùng torch `2.13.0+cu126`, transformers `5.15.0`, peft `0.20.0`, accelerate `1.14.0`, PyYAML `6.0.3`, safetensors `0.8.0`, matplotlib `3.11.2`. Dùng wheel tương thích Linux/CUDA và driver. Lệnh cài trong môi trường đã chốt là `python -m pip install -r ../../../requirements-lock.txt`, sau đó `python -m pip check`. Nếu torch wheel đã khóa không có cho image đích, dừng để thống nhất runtime tương thích thay vì tự sửa lockfile.
3. Kiểm tra `nvidia-smi`, BF16 và VRAM thực tế bằng `bash runpod_commands.sh preflight`. Dùng GPU BF16 còn đủ VRAM cho max-length probe. Windows probe 1.024 token dùng khoảng 6,36 GiB reserved, Run A S1 thực tế khoảng 7,52 GiB. Chọn volume đủ cho model cache, adapter, predictions, logs và sidecars. Kiểm tra khả năng atomic filesystem publication trên volume.
4. Stage Student `Qwen/Qwen2.5-1.5B-Instruct` đúng revision `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`, tokenizer cùng revision và model weights. Sau staging, giữ `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1` và chọn `HF_HOME` trỏ đến cache đã kiểm tra.
5. Kiểm tra `sha256sum -c /path/to/runpod_sha256sums_v2.txt` từ `MANUAL_ROOT`. Chuyển dữ liệu bằng công cụ giữ nguyên bytes, gồm CRLF/BOM. Giữ cả tập gốc và công bố checksum của bản staging. Khi chạy ở host khác, xử lý blocker trong [portability audit](runpod_portability_audit.md) trước khi bật lệnh thực thi.

Tập staging gồm GSM8K train dùng để đọc D_dev, ID D_test dùng riêng để chặn leakage trong pool, verified pool và token table, Gold/split, reference S0, sidecar S0, Round 1 train set và selection logs, hai capability state S0, NLL S0 của P1P2, toàn bộ Run A S1/S2 đã bảo toàn và Run B S1. Dùng manifest để xác định file cụ thể. Các figure/G6/G7 còn cần B4/B5 lịch sử, gồm nguồn prediction dẫn xuất đã xác minh của B4 S1.

## Lệnh sau khi được phê duyệt riêng

Đây là lệnh tương lai. Chạy thêm `--dry-run` trước từng lệnh thực thi, kiểm tra phương pháp, round, phạm vi dữ liệu và trạng thái tái sử dụng. Các flags BF16/micro-batch/NLL-batch/eval-batch và HF backend giữ tương thích với intent evaluation đã ghi tại Windows.

```bash
export MANUAL_ROOT=/workspace/Pipeline/P2/experiments/week2September/manual
cd "$MANUAL_ROOT"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1

# Run A chỉ nối tiếp đánh giá S2.
python -B scripts/run_p1_p2.py --method P1-DEFICIT --seed 13 --round 2 \
  --resume --backend hf --dtype bf16 --micro-batch 1 --nll-batch 1 --eval-batch 1

# Run A tiếp tục S2 và S3 từ S1 đã xác minh.
python -B scripts/run_p1_p2.py --method P1-DEFICIT --seed 13 --from-checkpoint S1 --to-checkpoint S3 \
  --resume --backend hf --dtype bf16 --micro-batch 1 --nll-batch 1 --eval-batch 1

# Run B kiểm tra/tái sử dụng đúng S1, hoặc chạy S1 nếu thiếu và phạm vi này được phép.
python -B scripts/run_p1_p2.py --method P1P2 --seed 13 --round 1 \
  --resume --backend hf --dtype bf16 --micro-batch 1 --nll-batch 1 --eval-batch 1

# Run B toàn bộ S1 đến S3. Resume phải nhận ra S1 đã hoàn tất nếu đã stage.
python -B scripts/run_p1_p2.py --method P1P2 --seed 13 --rounds all \
  --resume --backend hf --dtype bf16 --micro-batch 1 --nll-batch 1 --eval-batch 1

# Run B chỉ nối tiếp S2 và S3 từ S1.
python -B scripts/run_p1_p2.py --method P1P2 --seed 13 --from-checkpoint S1 --to-checkpoint S3 \
  --resume --backend hf --dtype bf16 --micro-batch 1 --nll-batch 1 --eval-batch 1
```

Ở seed 42 hoặc 2026, thay `--seed` sau khi xác minh hay tạo đầu vào cho đúng seed và được duyệt từng phạm vi. Chọn `--round 1` để thử một checkpoint. Không tái dùng train set, state hoặc NLL của seed 13 dưới danh tính khác.

## Artifact và dựng lại phân tích

Mỗi checkpoint sau khi hoàn tất phải có train set, selection log, train log, adapter config/weights, prediction D_dev 500 ID, summary, intent, checkpoint-log row, Gold sidecar 85 ID với bảy capability, và capability state. Controller tự gọi hook; kiểm tra CLI bằng `python -B scripts/run_p1p2_post_eval.py --help` và chạy controller `--dry-run --resume` để xác nhận không còn stage. Duyệt hook và state trong log trước khi chuyển checkpoint tiếp theo.

```bash
python -B scripts/build_capability_learning_dynamics.py --manual .
python -B scripts/select_checkpoint_on_dev.py --manual-root .
python -B scripts/build_p1p2_analysis_figures.py --manual-root . --preflight
python -B scripts/build_p1p2_analysis_figures.py --manual-root .
```

Để xem dữ liệu đang có, G7 có `--partial --output NEW_REPORT_DIR` và G8 có `--allow-partial --output NEW_FIGURE_DIR`. Chạy bản đầy đủ vào namespace chưa tồn tại hoặc thư mục version mới. Xác minh manifest PNG/CSV và pool/sidecar source SHA-256. Khóa chọn checkpoint trên 415 D_dev_select ID trước bất kỳ D_test nào. Bản handoff này không cho phép chạy D_test.

## Điều kiện nghiệm thu của người vận hành

- [ ] Xác minh image, driver, phiên bản thư viện, BF16, cache revision, VRAM và disk.
- [ ] Đối chiếu manifest, path mapping và dry-run trên Linux. Kiểm tra một checkpoint đã hoàn thành có zero pending stages khi resume.
- [ ] Xác nhận phạm vi mới đã được người có thẩm quyền phê duyệt riêng.
- [ ] Với lỗi subprocess, giữ lock/artifact và log để kiểm tra. Xác minh chủ lock đã thoát trước khi xử lý. Không ghi đè adapter dở dang hoặc sửa hash để cho qua.
- [ ] Sau mỗi checkpoint, lưu artifacts nguyên byte trên volume, tải về theo đúng relative paths, kiểm tra lại SHA-256 và xác minh lineage.
- [ ] Bàn giao GPU/driver, source version, lệnh, thời gian, exit code, hashes và bằng chứng resume Linux. Chỉ khi đó mới đánh giá G9.
