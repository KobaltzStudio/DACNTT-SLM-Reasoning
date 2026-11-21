# Task 6: Báo cáo pool trajectory chính thức (pool v1)

Ngày sinh: 2026-10-21 (RunPod, NVIDIA L4). Ngày viết báo cáo: 2026-10-22.
Quyết định: `task6_decisions.md` (T6-1 đến T6-6, schema v2). Các bước chạy: `Instruction_task6.md` (thư mục gốc repo).
Số liệu gốc: `reports/task6/` và `trajectory/pool/pool_v1_manifest.json`. Mọi con số trong báo cáo đều được tính từ các file này.

---

## 1. Kết luận

- **Pool v1 đạt yêu cầu: 4.353 trajectory valid thuộc 1.032 bài**, vượt ngưỡng ≥ 1.000 bài (T6-1), nên không cần sinh thêm khối 100 bài.
- **Không rò rỉ dữ liệu đánh giá:** không bài nào thuộc D_dev, D_test hay danh sách near-duplicate; câu hỏi không trùng nguyên văn và không chung 13-gram với D_dev/D_test.
- **vLLM tương đương HF:** trên cùng 500 lượt sinh của batch_100, tỉ lệ valid lệch −0,8 điểm %, độ dài lệch +0,2% (ngưỡng đặt trước: 5 điểm % và 10%).
- **68 bài bị loại (6,2%) theo T6-3**, nằm trong khoảng dự kiến [1,6%; 11,3%]. Gần một nửa (32 bài) bị loại vì định dạng hoặc độ dài, không phải vì Teacher giải sai.
- **invalid_format 13,3% chủ yếu là lệch định dạng:** 68% số trajectory này có số cuối đúng. Không do vLLM và không khác giữa batch_100 với bài mới.
- **Lời giải dài hơn pool sơ bộ 8,2%** (245,8 so với 227,13 token Student). `beta_round` giữ nguyên theo I3, nên mỗi vòng chứa trung bình khoảng 185 thay vì 200 trajectory.
- **Ratio chỉ xuất hiện ở 19 bài**, không đủ để phân tích riêng theo capability.

## 2. Thiết lập

| Mục | Giá trị |
|---|---|
| Teacher | `Qwen/Qwen2.5-3B-Instruct`, revision `aa8e72537993ba99e69dfaafa59ed015b17504d1`, bf16 |
| Prompt | prompt v1 (`REASONING:` / `ANSWER:`), chat template Qwen |
| Lấy mẫu | K = 5, T = 0,7, top_p 0,8, top_k 20, repetition_penalty 1,05, tối đa 512 token, dừng ở `[151643, 151645]` |
| Seed | `20261009 + problem_index × 5 + k`, một seed cho mỗi trajectory |
| Bài | 1.100 bài D_pool: 100 bài batch_100 (index 0–99) + 1.000 bài mới (index 100–1.099), lấy theo thứ tự xáo 6.868 bài ứng viên với seed 20261021 |
| Input | `trajectory/pool/pool_v1_input.jsonl`, SHA-256 `60f7c38e…` |
| Backend | vLLM 0.32.0, torch 2.13.0+cu130, `VLLM_ENABLE_V1_MULTIPROCESSING=0` |
| Phần cứng | NVIDIA L4 (RunPod, EUR-IS-1), network volume cho venv, cache model và kết quả |
| Config | `experiment_config.json` v1, SHA-256 `7c5aa72d…` (giống nhau ở cả hai bước) |
| Thời gian sinh | Bước A 68,5 giây (500 lượt), Bước B 499,3 giây (5.000 lượt), chưa tính thời gian nạp model |

Bước B chạy trên pod khác pod Bước A, vì pod cũ mất GPU. Image mới thiếu gói `sniffio`, đã cài bổ sung. vLLM và torch nằm trong venv trên network volume nên giữ đúng phiên bản.

## 3. Quy trình

1. **Kiểm tra tương đương (Bước A):** sinh lại 100 bài batch_100 bằng vLLM, so với lần sinh đầu bằng HF (`scripts/compare_vllm_hf.py`).
2. **Sinh bài mới (Bước B):** `scripts/generate_teacher_vllm.py --start-index 100 --end-index 1100`. Mỗi trajectory được chấm ngay bằng `answer_utils` (I1).
3. **Kiểm tra rò rỉ:** `scripts/check_pool_leak.py`.
4. **Gán C(τ):** extractor rules v2 trên toàn bộ output (`--source raw`, T6-6).
5. **Lọc và validate:** `scripts/build_pool_verified.py`. Một trajectory vào pool khi được chấm lại là valid, có C(τ) và qua `schemas/teacher_trajectory_schema_v2.json`.
6. **Thống kê:** `scripts/pool_stats.py`, `scripts/measure_pool_tokens.py`.

## 4. Kết quả

### 4.1. Kiểm tra tương đương vLLM và HF (batch_100, 500 lượt)

| | HF (lần sinh đầu) | vLLM |
|---|---|---|
| valid | 406 (81,2%) | 402 (80,4%) |
| invalid_format | 59 | 59 |
| invalid_answer | 35 | 39 |
| Bài không có lời giải đúng | 5 | 6 |
| Độ dài trung bình lời giải valid (token Teacher) | 236,8 | 237,2 |

Lệch tỉ lệ valid −0,8 điểm %, lệch độ dài +0,2%: **PASS** (`parity_vllm_hf.json`). Khác biệt đã biết: 23/100 câu hỏi của lần sinh HF khác bản chuẩn hoá chỉ ở khoảng trắng.

### 4.2. Trạng thái 5.500 trajectory

| | valid | invalid_format | invalid_answer |
|---|---|---|---|
| batch_100 (500) | 402 | 59 | 39 |
| Bài mới (5.000) | 3.953 | 671 | 376 |
| **Tổng (5.500)** | **4.355 (79,2%)** | **730 (13,3%)** | **415 (7,5%)** |

Mọi bài đủ K = 5, `trajectory_id` không trùng, seed và ID khớp công thức ở cả 5.500 dòng; trạng thái chấm lại khớp trạng thái đã lưu ở 5.500/5.500 dòng.

Số trajectory trong pool v1 trên mỗi bài:

| Số trajectory | 0 (bị loại) | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| Số bài | 68 | 53 | 62 | 115 | 179 | 623 |

Ngoài 1.145 trajectory không valid, có thêm 2 trajectory valid bị loại vì C(τ) rỗng (lời giải đại số và phép cộng viết bằng lời mà rules v2 không bắt được). Hai bài này vẫn còn 4 trajectory. Từng trajectory bị loại được ghi kèm lý do trong `pool_v1_excluded.jsonl`.

### 4.3. Kiểm tra rò rỉ

| Kiểm tra | Kết quả |
|---|---|
| File split khớp hash trong `split_manifest.json` | Khớp |
| Bài không thuộc D_pool / thuộc D_dev / thuộc D_test / thuộc near-duplicate | 0 / 0 / 0 / 0 |
| Câu hỏi hoặc đáp án khác `gsm8k_train.jsonl` | 0 |
| Trùng nguyên văn với D_dev/D_test (không phân biệt hoa thường, dấu câu) | 0 |
| Chung 13-gram với D_dev/D_test | 0 |

Đối chứng: cùng hàm phát hiện được 5/5 near-duplicate đã loại khi chia split và 50/50 câu D_dev (`leak_check.json`).

### 4.4. 68 bài bị loại (T6-3)

- 6 bài batch_100, 62 bài mới.
- 14 bài sai đáp án cả 5 lần; 54 bài có ít nhất 1 trajectory invalid_format.
- **32 bài có ít nhất 1 trajectory đúng số cuối** nếu chấm nới (chỉ để chẩn đoán, không đổi cách chấm).
- Lời giải các bài này dài hơn hẳn: trung bình 371 token Teacher, so với 268 của toàn bộ 5.500 trajectory.

Danh sách từng bài: `pool_stats.json`, mục `excluded_problems`.

### 4.5. Phân bố capability (4.353 trajectory)

| Capability | Theo trajectory | Theo bài (1.032 bài, có ở ít nhất 1 trajectory) |
|---|---|---|
| multiplication | 3.483 (80,0%) | 855 (82,9%) |
| addition | 2.800 (64,3%) | 720 (69,8%) |
| subtraction | 2.202 (50,6%) | 579 (56,1%) |
| division | 1.775 (40,8%) | 492 (47,7%) |
| fraction | 829 (19,0%) | 224 (21,7%) |
| percentage | 525 (12,1%) | 128 (12,4%) |
| ratio | 37 (0,8%) | 19 (1,8%) |

- Số capability mỗi trajectory: 1 → 342, 2 → 1.741, 3 → 1.463, 4 → 610, 5 → 184, 6 → 13.
- Tổ hợp thường gặp nhất: addition+multiplication (675), addition+subtraction+multiplication (408), addition+subtraction (307).
- 311 bài có các trajectory với C(τ) khác nhau, tức cùng một bài có nhiều cách giải dùng capability khác nhau.

C(τ) lấy từ toàn bộ output thay vì phần sau `REASONING:` (T6-6). Trên gold v2 của batch_100, cách này giữ nguyên hoặc tăng nhẹ F1 ở mọi capability, trừ fraction giảm từ 0,941 xuống 0,936 (`extractor_source_batch100.csv`).

### 4.6. Độ dài (tokenizer Student, Qwen2.5-1.5B-Instruct @989aa79)

| | Trung bình | Trung vị | IQR | Min–max |
|---|---|---|---|---|
| Response | 245,8 | 232 | 187–288 | 79–512 |
| Prompt + response | 376,1 | 361 | 309–427 | 181–698 |
| Lời giải ngắn nhất mỗi bài (B3) | 215,6 | 203 | 164–249 | 79–496 |

- Cao hơn `L̄ = 227,13` của pool sơ bộ 8,2%. Theo I3, `L̄` và `beta_round = 45.426` giữ nguyên (chỉ báo cáo, không đổi config).
- Mọi mẫu đều ngắn hơn `max_seq_len = 1024` của huấn luyện (dài nhất 698 token kể cả prompt).

### 4.7. invalid_format (730 trajectory, 13,3%)

| Nguyên nhân | Số lượng | Số cuối vẫn đúng |
|---|---|---|
| Thiếu dòng `REASONING:`, vẫn có `ANSWER:` | 403 | 352 |
| Bị cắt ở 512 token | 157 | 25 |
| `ANSWER:` đứng trước `REASONING:` | 76 | 45 |
| Chỉ có `\boxed{}` | 59 | 48 |
| Không có dòng đáp án | 18 | 12 |
| Nhãn đáp án có định dạng (`**ANSWER**:`) | 17 | 14 |
| **Tổng** | **730** | **496 (68%)** |

- **Không do vLLM:** trên cùng 500 lượt batch_100, HF và vLLM đều có 59 invalid_format.
- **Không khác giữa batch_100 và bài mới:** 11,8% so với 13,4%, kiểm định hai tỉ lệ p = 0,31.
- **Phần lớn là lệch định dạng:** nguyên nhân lớn nhất là Teacher bỏ dòng tiêu đề `REASONING:`, và 87% nhóm này vẫn ra đúng đáp án.
- **Bị cắt ở 512 token thì gần như sai thật** (25/157 đúng số cuối). Nhóm này chiếm 157/168 trajectory chạm giới hạn.
- 318 bài có ít nhất 1 trajectory invalid_format, phần lớn chỉ 1–2 trajectory.

Chấm nghiêm theo I1 vẫn giữ cho pool: Student chỉ học các output đúng định dạng prompt v1.

## 5. Hạn chế

- **Pool hơi lệch về bài ngắn và bài Teacher giữ đúng định dạng.** Khoảng 32/68 bài bị loại không phải vì Teacher không giải được. Nên báo cáo kèm accuracy chấm nới cho Teacher và Student (đã có trong kế hoạch cập nhật analysis plan).
- **C(τ) do luật trích xuất gán**, F1 0,86–0,96 trên gold batch_100 (ratio không đủ mẫu). Lời giải đại số hoặc phép tính viết bằng lời có thể bị bỏ sót.
- **Ratio quá hiếm** (19 bài), không đủ để kết luận riêng về capability này.
- **Tái lập của vLLM** chỉ được đảm bảo trên cùng phần cứng và phiên bản (L4, vLLM 0.32.0). Bước B chạy trên một pod khác nhưng cùng loại GPU và cùng venv.

## 6. File

| File | Nội dung |
|---|---|
| `trajectory/pool/pool_v1_teacher_raw.jsonl` | 5.500 output của Teacher (raw, mọi trạng thái) |
| `trajectory/pool/pool_v1_teacher_raw.jsonl.run_*.json` | Tóm tắt hai lần chạy (tham số, phiên bản, hash) |
| `trajectory/pool/pool_v1_capability_predictions.jsonl` | C(τ) kèm bằng chứng cho 4.355 trajectory valid |
| **`trajectory/pool/pool_v1_verified.jsonl`** | **Pool chính thức: 4.353 trajectory, 1.032 bài, schema v2.** SHA-256 `a982a8ef…` |
| `trajectory/pool/pool_v1_excluded.jsonl` | 1.147 trajectory bị loại, kèm lý do |
| `trajectory/pool/pool_v1_manifest.json` | Quy tắc, số đếm, SHA-256 của input và output |
| `schemas/teacher_trajectory_schema_v2.json` | Schema của pool (v1 giữ nguyên) |
| `reports/task6/parity_vllm_hf.json` | Kiểm tra tương đương |
| `reports/task6/leak_check.json` | Kiểm tra rò rỉ |
| `reports/task6/extractor_source_batch100.csv` | F1 của extractor theo nguồn văn bản |
| `reports/task6/pool_stats.json` | Trạng thái, bài bị loại, capability, invalid_format |
| `reports/task6/pool_token_stats.json` | Độ dài theo tokenizer Student |
| `reports/task6/gen_0_100.log`, `gen_100_1100.log` | Log sinh trên pod |

## 7. Chuyển sang Task 7

- `scripts/student_common.py` trỏ mặc định sang `pool_v1_verified.jsonl`. `load_pool()` kiểm tra cả D_dev lẫn D_test.
- `compute_nll.py` và `train_round.py` có thêm tham số `--pool`, đồng thời ghi đường dẫn và SHA-256 của pool vào kết quả.
- Smoke test của Task 5 vẫn tái lập được:
  - `select_smoke_train_set.py` cố định pool sơ bộ và tạo lại đúng hai train set seed 13 và 42.
  - `train_round.py` đọc pool ghi trong train set và kiểm tra hash.
  - Notebook `notebooks/smoke_test_colab.ipynb` truyền `--pool` của pool sơ bộ cho `compute_nll.py`.
