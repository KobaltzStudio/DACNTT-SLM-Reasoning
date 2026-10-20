# Task 5: Báo cáo smoke test S_0 → S_1 trên D_dev

Ngày chạy: 2026-10-19 (Google Colab). Ngày viết báo cáo: 2026-10-20.
Dữ liệu gốc: `reports/task5/smoke_test/results/`. Notebook đã chạy: `reports/task5/smoke_test/result_smoke_test.ipynb`.

Smoke test **không phải kết quả chính**: không dùng D_test, không so sánh các phương pháp B0–B5. Mục đích là trả lời 3 câu hỏi trước thí nghiệm chính: Student có học được từ Teacher không, các tham số tạm I3/I4/I5 có hợp lý không, và chi phí chạy thực tế là bao nhiêu.

---

## 1. Kết luận

- **Student học được từ trajectory của Teacher.** Sau 1 vòng LoRA trên 200 trajectory, accuracy trên D_dev tăng 10,6–11,8 điểm %, vượt xa ngưỡng đã chốt trước (≥ 2 điểm % hoặc McNemar p < 0,1), và kết quả hai seed gần nhau (lệch 1,2 điểm %).
- **Quyết định: `keep`.** Giữ nguyên `n_round = 200`, `beta_round = 45.426`, `lr = 2e-4`, batch hiệu dụng 8, 1 epoch. Không có tham số nào đổi, nên không cần config v2.
- **Khoảng 40% mức tăng đến từ việc học định dạng.** Nếu bỏ qua định dạng, accuracy tăng khoảng 6,8 điểm % (vẫn có ý nghĩa thống kê). Xem mục 4.1.
- **I4 (probe b = 7) chưa được kiểm tra** trong smoke test vì không chạy probe L_emp. Giữ trạng thái tạm, chốt ở mục 2.2 (`Task.md`) khi đo L_emp (xác nhận 2026-10-20).

## 2. Cấu hình đã chạy

| Mục | Giá trị |
|---|---|
| Student | `Qwen/Qwen2.5-1.5B-Instruct`, revision `989aa7980e4cf806f80c7fef2b1adb7bc71aa306` |
| Config | `experiment_config.json` v1, SHA-256 `ba200e09…66c774` (trùng với file trong repo) |
| Phần cứng | Tesla T4, 15 GB VRAM (Colab) |
| dtype | bfloat16 (torch báo `is_bf16_supported() = True` trên T4) |
| Thư viện | torch 2.11.0+cu130, transformers 5.15.0, peft 0.20.0, accelerate 1.14.0, scipy 1.17.1. Đầy đủ: `smoke_test/results/environment_colab.txt` |
| Đánh giá | D_dev 500 câu, greedy, tối đa 512 token, chấm bằng `answer_utils.py`, batch 32 |
| Huấn luyện | LoRA r = 16, alpha = 32, completion-only loss, lr 2e-4, micro-batch 4 × grad-accum 2 = 8, 1 epoch = 25 step, gradient checkpointing, 18,46 triệu tham số huấn luyện |
| Tập huấn luyện | 200 trajectory chọn ngẫu nhiên từ 480 trajectory hợp lệ của pool sơ bộ (`random.Random(seed).sample(sorted(trajectory_id), 200)`) |
| Seed | 13 và 42 |
| NLL | Tính trên cả 480 trajectory tại S_0 và S_1 của mỗi seed, batch 8 |

### Điểm lệch so với config

1. **Bỏ `n_cap = 1`.** Pool sơ bộ chỉ có 98 câu, ít hơn `n_round = 200`. Kết quả là 200 trajectory trải trên 88 câu (seed 13, tối đa 4 trajectory/câu) và 92 câu (seed 42, tối đa 5 trajectory/câu). Trong thí nghiệm chính, mỗi câu chỉ góp 1 trajectory, nên dữ liệu đa dạng hơn smoke test.
2. **Chọn theo số lượng, không theo ngân sách token.** Số token trajectory thực tế là 44.263 (seed 13) và 47.467 (seed 42), so với `beta_round = 45.426`. Seed 42 vượt ngân sách 4,5%. Xem mục 5.
3. **bf16 trên T4.** T4 không có bf16 gốc. Phép so sánh vẫn hợp lệ vì S_0 và S_1 cùng dtype, nhưng thời gian đo được có thể chậm hơn so với GPU có bf16 thật (L4, A100).

## 3. Kết quả

### 3.1. Accuracy trên D_dev (metric chính của smoke test)

| | Seed 13 | Seed 42 |
|---|---|---|
| Accuracy S_0 → S_1 | 0,712 → **0,830** | 0,712 → **0,818** |
| Δ | +11,8 điểm % | +10,6 điểm % |
| Sai → đúng / đúng → sai | 89 / 30 | 84 / 31 |
| McNemar (exact) p | 5,7 × 10⁻⁸ | 8,0 × 10⁻⁷ |
| Tỉ lệ đúng định dạng S_0 → S_1 | 0,916 → 0,996 | 0,916 → 0,966 |
| Độ dài output trung bình (token) | 238,5 → 211,1 | 238,5 → 247,3 |
| Số câu chạm 512 token | 9 → 2 | 9 → 9 |
| Quyết định tự động | keep (có cảnh báo định dạng) | keep |

Chi tiết trạng thái từng câu tại S_0: 356 `valid`, 102 `invalid_answer`, 42 `invalid_format`. Tại S_1: 415 / 83 / 2 (seed 13) và 409 / 74 / 17 (seed 42).

### 3.2. Loss huấn luyện

| | Seed 13 | Seed 42 |
|---|---|---|
| Loss step đầu → step cuối | 0,225 → 0,189 | 0,235 → 0,208 |
| Loss lớn nhất | 0,295 | 0,287 |
| Xu hướng | giảm | giảm |

Loss giảm ổn định, không dao động bất thường, nên không có lý do giảm learning rate.

### 3.3. NLL và L_proxy (exploratory)

| | Seed 13 | Seed 42 |
|---|---|---|
| Spearman ℓ(S_0), ℓ(S_1), toàn pool (480) | 0,857 | 0,869 |
| Spearman, nhóm đã huấn luyện (200) | 0,902 | 0,888 |
| Spearman, nhóm chưa huấn luyện (280) | 0,944 | 0,950 |
| Δℓ trung bình, nhóm đã huấn luyện | −0,091 | −0,087 |
| Δℓ trung bình, nhóm chưa huấn luyện | −0,036 | −0,036 |
| ℓ\* (median): S_0 → S_1 | 0,233 → 0,169 | 0,233 → 0,174 |
| σ (IQR/1,349): S_0 → S_1 | 0,072 → 0,071 | 0,072 → 0,073 |
| Spearman L_proxy(S_0), L_proxy(S_1) | 0,575 | 0,646 |
| Jaccard top-200 theo L_proxy | 0,439 | 0,509 |

## 4. Diễn giải và lưu ý

### 4.1. Học định dạng chiếm một phần mức tăng

Tại S_0 có 42 câu (8,4%) sai định dạng `REASONING:` / `ANSWER:`. Một phần trong số đó có số cuối đúng, nên được tính đúng ngay khi Student học được định dạng.

| | Seed 13 | Seed 42 |
|---|---|---|
| Accuracy lỏng S_0 → S_1 (chỉ lấy số cuối, bỏ qua định dạng) | 0,762 → 0,830 | 0,762 → 0,830 |
| Sai → đúng theo cách chấm chính thức | 89 | 84 |
| … trong đó S_0 sai định dạng nhưng số cuối đã đúng | 21 | 17 |
| Sai → đúng / đúng → sai theo accuracy lỏng | 68 / 34 | 68 / 34 |
| McNemar (exact) p theo accuracy lỏng | 9,9 × 10⁻⁴ | 9,9 × 10⁻⁴ |

Phần cải thiện không do định dạng khoảng +6,8 điểm %, vẫn rõ và có ý nghĩa thống kê, nên quyết định `keep` không đổi. Tuy vậy:

- Hiệu ứng học định dạng giống nhau cho mọi phương pháp ở vòng 1, nên không làm lệch so sánh B5 với B4, nhưng làm phồng con số "Student học được bao nhiêu".
- **Đề xuất:** thêm accuracy lỏng làm metric phụ trong `analysis_plan.md` trước khi chạy thí nghiệm chính.
- Ngưỡng cảnh báo trong `analyze_smoke_test.py` là ≥ 5 điểm %. Seed 42 đổi đúng 5,0 điểm % (0,916 → 0,966) nhưng không bị cảnh báo do sai số dấu phẩy động (0,04999…). Không ảnh hưởng kết luận, chỉ cần biết khi đọc bảng tự động.

### 4.2. NLL giảm một phần do cơ học

Nhóm trajectory đã được huấn luyện giảm NLL nhiều gấp khoảng 2,5 lần nhóm chưa huấn luyện. Đây là hiệu ứng ghi nhớ dữ liệu đã học, không phải thay đổi learnability. Nhóm chưa huấn luyện vẫn giảm NLL (khoảng −0,036), tức Student thay đổi chung chứ không chỉ nhớ dữ liệu.

Thứ hạng NLL gần như giữ nguyên (Spearman 0,86–0,95), nhưng thứ hạng L_proxy thay đổi nhiều hơn hẳn (Spearman 0,58–0,65, chỉ khoảng một nửa top-200 trùng nhau). Lý do là L_proxy đo khoảng cách tới tâm dải ℓ\*, mà ℓ\* dịch xuống khoảng 0,06 trong khi σ gần như giữ nguyên. Vì vậy các trajectory ở rìa dải đổi vị trí nhiều.

Đây là tín hiệu ban đầu ủng hộ giả thuyết H, nhưng **chưa diễn giải được khi chưa có ρ_noise**. Đề xuất:
- Đo ρ_noise (mục 2.2 `Task.md`) trước khi sinh pool chính thức.
- Đưa phân tích H trên nhóm trajectory **chưa được chọn huấn luyện** vào `analysis_plan.md` như phân tích chính, thay vì để exploratory (mục 2.4 `Task.md`).

### 4.3. Trần accuracy

S_1 đạt 0,82–0,83 sau 1 vòng. Nếu accuracy của Teacher trên D_dev chỉ cao hơn S_0 khoảng 16 điểm % (khoảng 0,87), vòng 2–3 còn rất ít chỗ để tăng và khác biệt B5 so với B4 dễ bị ép về null. Smoke test **chưa đo accuracy của Teacher trên D_dev**. Đề xuất đo trước khi sinh pool chính thức (Task 6), vì sau đó gần như không đổi được cặp mô hình.

## 5. Chi phí đo được

| Việc | Thời gian (T4, bf16) | VRAM tối đa |
|---|---|---|
| Đánh giá 500 câu D_dev | 1.399 giây (23 phút, seed 13), 1.682 giây (28 phút, seed 42) | 4,07 GB |
| Huấn luyện 1 vòng (200 trajectory, 25 step) | 499 giây (seed 13), 509 giây (seed 42), khoảng 8,5 phút | 6,13–6,46 GB |
| NLL 480 trajectory | 377–378 giây, khoảng 6,3 phút (khoảng 1,27 trajectory/giây) | 6,18 GB |

Thời gian đánh giá S_0 không đo được: lần chạy cuối ghi `elapsed_seconds_this_run = 0.0` vì chạy tiếp từ kết quả đã có. Dùng thời gian của S_1 thay thế, vì cùng model và cùng thiết lập sinh.

Ước tính thô cho thí nghiệm chính trên T4 (HF `generate`, chưa tối ưu):
- Đánh giá: khoảng 87.000 lượt sinh ≈ 174 lần × 25 phút ≈ **70–80 giờ GPU**. Đây là phần tốn nhất. Chuyển sang vLLM sẽ giảm đáng kể.
- NLL cho pool khoảng 5.000 trajectory: khoảng 65 phút mỗi checkpoint.
- Huấn luyện: khoảng 8,5 phút mỗi vòng, không đáng kể.

Thông tin này dùng cho mục 0.2 (`Task.md`, thuê máy chủ cloud).

**Ngân sách token:** smoke test chọn 200 trajectory theo số lượng, nên số token thực tế dao động −2,6% đến +4,5% so với `beta_round`. Trong thí nghiệm chính, script chọn dữ liệu phải dừng theo ngân sách token (`beta_round`), không theo số lượng. Nếu không, phương pháp ưu tiên lời giải dài sẽ được huấn luyện nhiều token hơn và so sánh không còn cùng ngân sách.

## 6. Trạng thái I3, I4, I5 sau smoke test

| Mục | Giá trị | Trạng thái đề xuất | Căn cứ |
|---|---|---|---|
| I3: `n_round`, `beta_round` | 200; 45.426 token/vòng | **Đã chốt sau smoke test** | Accuracy tăng rõ ở cả hai seed sau 1 vòng |
| I4: probe `b` | 7 step (nhóm G = 50 trajectory) | **Giữ tạm, chốt ở mục 2.2** | Smoke test không chạy probe L_emp. Kiểm tra khi đo L_emp (mục 2.2) |
| I5: hyperparameters | r = 16, alpha = 32, lr 2e-4, batch 8, 1 epoch | **Đã chốt sau smoke test** | Loss giảm ổn định, không dao động, hai seed nhất quán |

## 7. Việc tiếp theo

1. ~~Xác nhận trạng thái I4~~: giữ tạm (2026-10-20).
2. ~~Cập nhật `task5_decisions.md`~~ (đã thêm mục J, 2026-10-20). ~~Trường `status` trong `experiment_config.json`, rồi chạy `validate_experiment_config.py --frozen` và tạo lại `reports/task5/SHA256SUMS_task5.txt`~~ (xong 2026-10-20, 33/33 OK).
3. ~~Cập nhật `task5_changelog.txt`, `README.txt` và `Task.md` mục 0.1~~ (đã cập nhật 2026-10-20).
4. Trước Task 6: đo accuracy của Teacher trên D_dev (mục 4.3) và ρ_noise (mục 4.2). Bổ sung accuracy lỏng, phân tích H trên nhóm chưa huấn luyện và quy tắc chọn theo ngân sách token vào analysis plan hoặc config v2.

## 8. Danh sách file

Trong `reports/task5/smoke_test/results/`:

| File | Nội dung |
|---|---|
| `eval_S0_dev.jsonl`, `eval_S1_dev_seed{13,42}.jsonl` (+ `.summary.json`) | Kết quả đánh giá từng câu và tóm tắt |
| `train_set_seed{13,42}.json` | 200 `trajectory_id` dùng để huấn luyện, kèm quy tắc chọn và điểm lệch |
| `train_log_seed{13,42}.json` | Loss từng step, số token, thời gian, VRAM, hash config |
| `nll_pool_S0.jsonl`, `nll_pool_S1_seed{13,42}.jsonl` (+ `.summary.json`) | NLL chuẩn hoá theo độ dài cho 480 trajectory |
| `smoke_analysis.json`, `smoke_analysis.md` | Phân tích tự động (`analyze_smoke_test.py`); chạy lại ở local cho kết quả trùng khớp |
| `environment_colab.txt` | Phiên bản thư viện trên Colab |

Adapter LoRA (`student_ckpt_001_smoke_seed{13,42}`) lưu trên Drive, không đưa vào repo.
