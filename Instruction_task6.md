# Hướng dẫn Task 6: Sinh pool chính thức bằng vLLM trên RunPod

Thuộc: `Task.md` mục 1.1. Quyết định: `experiments/week2September/manual/task6_decisions.md` (T6-1 đến T6-5, đã chốt 2026-10-21).
Ngày soạn: 2026-10-21.

Mục tiêu: sinh K = 5 lời giải của Teacher Qwen2.5-3B-Instruct cho 1.100 bài (100 bài batch_100 ở index 0–99 + 1.000 bài mới ở index 100–1.099), tổng 5.500 lượt sinh, bằng vLLM trên GPU có bf16. Trước khi sinh bài mới, kiểm tra vLLM cho kết quả tương đương lần sinh đầu bằng HF trên batch_100.

---

## 1. Các file

Trong `experiments/week2September/manual/`:

| File | Vai trò |
|---|---|
| `scripts/make_pool_input.py` | Xáo 6.868 bài ứng viên (seed 20261021), tạo `trajectory/pool/pool_v1_input.jsonl` (1.100 dòng) và manifest SHA-256. **Đã chạy ở máy local**, chỉ chạy lại khi cần thêm khối 100 bài. |
| `scripts/generate_teacher_vllm.py` | Sinh bằng vLLM: prompt v1, tham số lấy mẫu tường minh (T 0,7, top_p 0,8, top_k 20, repetition_penalty 1,05, 512 token), seed riêng cho từng trajectory theo công thức trong config, chạy theo khoảng index, ghi nối tiếp và chạy tiếp được khi bị ngắt, chấm bằng `answer_utils`. |
| `scripts/compare_vllm_hf.py` | Kiểm tra tương đương trên batch_100: tỉ lệ valid lệch ≤ 5 điểm %, độ dài trung bình lời giải valid lệch ≤ 10%. Thoát với mã 0 (PASS) hoặc 1 (FAIL). |
| `scripts/setup_pod.sh` | Chuẩn bị pod: kích hoạt venv trên `/workspace` (tạo và cài vLLM nếu chưa có), đặt `HF_HOME`, bật lịch xử lý tất định của vLLM, in phiên bản và kiểm tra bf16. |

Kết quả sinh ra:
- `trajectory/pool/pool_v1_teacher_raw.jsonl`: toàn bộ 5.500 trajectory (raw, cả valid lẫn không valid).
- `trajectory/pool/pool_v1_teacher_raw.jsonl.run_<start>_<end>.json`: tóm tắt mỗi lần chạy (thời gian, tham số, phiên bản, hash input và config).
- `reports/task6/parity_vllm_hf.json`: kết quả kiểm tra tương đương.

Không file nào của pool sơ bộ (`batch_100_*`) bị ghi đè.

---

## 2. Kết nối pod

Pod: `tz1k71joq490o0` (NVIDIA L4, EUR-IS-1, $0,59/giờ), network volume `0q3rshkad1` gắn tại `/workspace`.

Nếu pod đang dừng, bấm **Start** trong console rồi lấy lệnh SSH mới ở nút **Connect** (IP và cổng đổi sau mỗi lần Start). Dạng lệnh:
```bash
ssh root@<IP> -p <PORT> -i ~/.ssh/runpod_ed25519
```
Trong các lệnh dưới đây, thay `<IP>` và `<PORT>` bằng giá trị hiện tại.

---

## 3. Đưa project lên pod (chạy ở máy local)

Repo trên GitHub là private, nên chép thẳng thư mục `manual/` (khoảng 20 MB) bằng `rsync`, không cần token GitHub trên pod:
```bash
cd ~/Desktop/Code/DACNTT-SLM-Reasoning/experiments/week2September
rsync -avz --no-owner --no-group --exclude '__pycache__' -e "ssh -p <PORT> -i ~/.ssh/runpod_ed25519" \
    manual/ root@<IP>:/workspace/manual/
```
`--no-owner --no-group` là bắt buộc: network volume của RunPod không cho đổi chủ sở hữu file, thiếu hai cờ này `rsync` báo hàng loạt lỗi `chown ... Operation not permitted` (file vẫn được chép). Kiểm tra trên pod: `sha256sum /workspace/manual/trajectory/pool/pool_v1_input.jsonl` phải bắt đầu bằng `60f7c38e`.

Chạy lại lệnh này mỗi khi sửa script ở máy local. `rsync` không xoá file trên pod, nên kết quả đã sinh trên pod không bị ảnh hưởng.

---

## 4. Chuẩn bị môi trường (trên pod, mỗi lần Start lại pod)

```bash
cd /workspace/manual
source scripts/setup_pod.sh
```
Dòng in ra phải có `gpu NVIDIA L4 | bf16 True | vllm ...`. Nếu thấy `STOP: this GPU has no bf16` thì không chạy tiếp (T6-5 không cho chạy vLLM bằng fp16).

**Ghi lại dòng phiên bản** (vLLM, torch, transformers) để đưa vào báo cáo pool.

Kiểm tra nhanh không cần GPU (dựng prompt và seed cho 2 trajectory đầu):
```bash
python scripts/generate_teacher_vllm.py --start-index 0 --end-index 1 --dry-run
```
Seed của `gsm8k_train_00000_traj_001` phải là `20261009`, `stop_token_ids=[151643, 151645]`.

---

## 5. Bước A: kiểm tra tương đương trên batch_100 (500 lượt sinh)

Chạy ở chế độ nền để không mất khi ngắt SSH:
```bash
nohup python scripts/generate_teacher_vllm.py --start-index 0 --end-index 100 \
    > /workspace/gen_0_100.log 2>&1 &
tail -f /workspace/gen_0_100.log        # Ctrl+C chỉ thoát xem log, không dừng tiến trình
```
Lần đầu sẽ tải model khoảng 6 GB vào `/workspace/hf`. Khi log báo `[gen] 500/500` là xong.

So sánh với lần sinh đầu bằng HF:
```bash
python scripts/compare_vllm_hf.py
```

- **PASS:** sang Bước B.
- **FAIL:** **không** sinh bài mới. Giữ nguyên file, chép `reports/task6/parity_vllm_hf.json` và log về để nhóm xem xét (tham số lấy mẫu, phiên bản vLLM). Không sửa ngưỡng sau khi đã thấy kết quả.

---

## 6. Bước B: sinh 1.000 bài mới (5.000 lượt sinh)

```bash
nohup python scripts/generate_teacher_vllm.py --start-index 100 --end-index 1100 \
    > /workspace/gen_100_1100.log 2>&1 &
tail -f /workspace/gen_100_1100.log
```
Nếu bị ngắt (pod dừng, hết tiền...), chạy lại **đúng lệnh đó**: các trajectory đã có trong file được bỏ qua.

Đếm nhanh khi xong:
```bash
python - <<'EOF'
import json, collections
rows = [json.loads(l) for l in open("trajectory/pool/pool_v1_teacher_raw.jsonl")]
st = collections.Counter(r["metadata"]["verification_status"] for r in rows)
ok = {r["problem_id"] for r in rows if r["metadata"]["verification_status"] == "valid"}
print(len(rows), "trajectory", dict(st), "| bài có ít nhất 1 lời giải đúng:", len(ok))
EOF
```
Cần **5.500 trajectory** và **≥ 1.000 bài có ít nhất 1 lời giải đúng**. Nếu thiếu, xem mục 8.

---

## 7. Mang kết quả về và dừng pod

Ở máy local:
```bash
cd ~/Desktop/Code/DACNTT-SLM-Reasoning/experiments/week2September
rsync -avz --no-owner --no-group -e "ssh -p <PORT> -i ~/.ssh/runpod_ed25519" \
    root@<IP>:/workspace/manual/trajectory/pool/ manual/trajectory/pool/
rsync -avz --no-owner --no-group -e "ssh -p <PORT> -i ~/.ssh/runpod_ed25519" \
    root@<IP>:/workspace/manual/reports/task6/ manual/reports/task6/
rsync -avz --no-owner --no-group -e "ssh -p <PORT> -i ~/.ssh/runpod_ed25519" \
    root@<IP>:/workspace/gen_*.log manual/reports/task6/
```
Kiểm tra file về đủ (`wc -l manual/trajectory/pool/pool_v1_teacher_raw.jsonl` = 5500) rồi **Stop pod** trong console. Network volume vẫn giữ venv, cache model và bản sao kết quả.

---

## 8. Nếu thiếu bài có lời giải đúng (T6-1)

Thêm khối 100 bài tiếp theo trong thứ tự đã xáo, lặp đến khi đủ:
```bash
# máy local: mở rộng file input (file cũ phải là tiền tố, script tự kiểm tra)
python scripts/make_pool_input.py --n-new 1100
# đưa lên pod (mục 3), rồi trên pod:
python scripts/generate_teacher_vllm.py --start-index 1100 --end-index 1200
```
Không chọn lại hay bỏ bài theo nội dung.

---

## 9. Sau khi có pool (làm ở máy local, sẽ có hướng dẫn riêng)

1. Kiểm tra không bài nào thuộc D_dev/D_test, mỗi bài đủ K = 5 trajectory.
2. Chạy capability extractor (rules v2) để có C(τ); validate theo `schemas/teacher_trajectory_schema.json`.
3. Thống kê: số bài, valid / invalid_answer / invalid_format, bài bị loại (T6-3), phân bố capability và token.
4. Tạo `trajectory/pool/pool_v1_verified.jsonl` (chỉ trajectory valid của các bài eligible), manifest SHA-256 và `reports/task6/pool_report.md`.
5. Cập nhật `Task.md`, `README.txt` và commit.

---

## 10. Chi phí và lưu ý

- Pod tính **$0,59/giờ** khi đang chạy, kể cả lúc không làm gì. Dừng pod ngay sau mục 7.
- Network volume tính phí theo tháng đến khi bị xoá, kể cả khi pod đã dừng.
- Hết tiền thì RunPod tự dừng pod; dữ liệu trên `/workspace` vẫn còn, chạy lại lệnh sinh để tiếp tục.
- vLLM chỉ đảm bảo tái lập trên cùng phần cứng và cùng phiên bản, nên giữ nguyên GPU (L4) và phiên bản vLLM cho cả Bước A và Bước B.
