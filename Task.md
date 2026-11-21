# Task: các việc cần làm tiếp theo

Cập nhật: 2026-11-02. Pipeline Task 7 đã viết và chạy pilot local (`done.md`); việc tiếp theo là chạy thử trên L4. Tiến độ ước tính ở dòng này chưa đánh giá lại. Task 1-6 xong (I4 giữ tạm). Smoke test S_0 → S_1: Student học được từ Teacher (+10,6 đến +11,8 điểm % trên D_dev), giữ nguyên tham số. Đo Teacher trên D_dev: 0,886, giữ cặp 3B → 1.5B. Task 6 xong: pool v1 `pool_v1_verified.jsonl` 4.353 trajectory / 1.032 bài (sinh bằng vLLM trên L4), báo cáo `reports/task6/pool_report.md`.

Nguồn: `BaoCaoTienDoTuan4.txt`, `experiments/week2September/manual/README.txt` (mục 0), `task4_todo.txt`, `task5_todo.txt`, `task7_decisions.md`, `config/experiment_config.json`, `analysis_plan.md`. File này chưa gồm yêu cầu riêng của khoa và giảng viên hướng dẫn.

Ký hiệu: `[ ]` chưa làm, `[~]` đang làm / làm một phần, `[!]` bị chặn.

---

## Ưu tiên 0: Việc quyết định hướng đi (làm ngay)

### 0.1. Smoke test S_0 → S_1 trên D_dev (thuộc Task 5, chốt I3/I4/I5)
- [x] Chốt cách làm (2026-10-19): 200 trajectory (chỉ bỏ `n_cap` trong smoke test), ngưỡng ≥ 2 điểm % hoặc McNemar p < 0,1, seed 13 và 42, NLL pool, chạy trên Colab.
- [x] Viết script và notebook Colab, chạy thử pipeline bằng Qwen2.5-0.5B (xem `Instruction_0.1.md` mục 13).
- [x] **Chạy trên Colab** (2026-10-19, Tesla T4, bf16) và mang kết quả về `reports/task5/smoke_test/results/`. Chạy lại `analyze_smoke_test.py` ở local: trùng khớp.
- [x] Đánh giá S_0 trên D_dev (500 câu, greedy, max 512 token): accuracy 0,712, đúng định dạng 0,916. Thời gian S_0 không đo được (lần chạy cuối là chạy tiếp); dùng thời gian S_1: 23–28 phút / 500 câu.
- [x] Huấn luyện 1 vòng LoRA trên 200 trajectory chọn ngẫu nhiên từ pool sơ bộ (seed 13 và 42): 25 step, khoảng 8,5 phút, loss giảm.
- [x] Đánh giá lại trên D_dev: 0,830 (seed 13), 0,818 (seed 42). Không dùng D_test.
- [x] Quyết định theo kết quả: **`keep`**. Accuracy thay đổi rõ (McNemar p < 1e-6), loss giảm ổn định. I3, I5 đã chốt; **I4 (`b = 7`) giữ tạm**, chốt ở mục 2.2 vì smoke test không chạy probe L_emp.
- [x] ~~Tạo config v2~~: không cần, không đổi giá trị nào.
- [x] Viết `reports/task5/smoke_test_report.md`, thêm mục J vào `task5_decisions.md`.
- [x] Cập nhật trường `status` trong `experiment_config.json` (I3, I5 đã chốt; I4 tạm; không đổi giá trị), `--frozen` PASS, tạo lại `reports/task5/SHA256SUMS_task5.txt`: 33/33 OK (chỉ đổi hash của config và `task5_decisions.md`).
- [x] Cập nhật `task5_changelog.txt` (mục 7), `task5_todo.txt` và dòng trạng thái Task 5 trong `README.txt`.

Lưu ý từ smoke test (chi tiết: `smoke_test_report.md` mục 4):
- Khoảng 40% mức tăng là do học định dạng; accuracy lỏng chỉ tăng +6,8 điểm % (vẫn có ý nghĩa, p ≈ 0,001).
- S_1 đã đạt 0,82–0,83 sau 1 vòng. ~~Cần đo accuracy của Teacher 3B trên D_dev~~ **Đã đo (2026-10-20): Teacher 0,886, hơn S_1 trung bình 6,2 điểm % (ngưỡng đặt trước ≥ 5 điểm %) → GIỮ cặp Teacher Qwen2.5-3B → Student Qwen2.5-1.5B.** Rủi ro: chỉ còn khoảng 55/500 câu Teacher đúng mà S_1 sai, khác biệt B5 so với B4 có thể nhỏ. Chi tiết: `task5_decisions.md` mục K, `smoke_test_report.md` mục 4.3.

### 0.2. Thuê máy chủ cloud (Task 9)
Số liệu đo trên T4 (smoke test): đánh giá 500 câu 23–28 phút, huấn luyện 1 vòng khoảng 8,5 phút, NLL khoảng 1,27 trajectory/giây. Ước tính phần đánh giá của thí nghiệm chính khoảng 70–80 giờ GPU T4 nếu dùng HF `generate`; nên chuyển sang vLLM.
- [~] Chọn nhà cung cấp, ước tính chi phí theo khối lượng: khoảng 4.500 lượt sinh Teacher và khoảng 87.000 lượt sinh để đánh giá. Đã chọn RunPod L4 ($0,59/giờ, Task 6); chi phí thí nghiệm chính chờ đo thời gian trên L4.
- [x] Chạy thành công một job thử (sinh trajectory hoặc đánh giá) trên cloud: sinh pool v1 bằng vLLM trên L4 (Task 6).
- [~] Có cơ chế lưu checkpoint, chạy tiếp khi bị ngắt, và sao lưu kết quả về repo/lưu trữ chung: `run_experiment.py` chạy tiếp được; kết quả nằm trên network volume và rsync về thủ công.
- [ ] Xóa pod cũ `jfs0rhsawcq0fd` (có API key dạng văn bản thuần) và đổi API key RunPod, nếu chưa làm.

---

## Ưu tiên 1: Dữ liệu và độ tin cậy nhãn

### 1.1. Pool trajectory chính thức (Task 6)
- [x] Chốt các quyết định của Task 6 (2026-10-21): `experiments/week2September/manual/task6_decisions.md`. 1.000 câu mới (thiếu thì thêm khối 100 câu theo thứ tự đã xáo), bài mới bắt đầu từ index 100, loại câu không có lời giải đúng, **sinh lại cả 100 bài batch_100** (98 trajectory của pool sơ bộ dùng prompt khác prompt v1 và seed ngoài quy tắc), sinh bằng vLLM (bf16, tham số lấy mẫu khớp HF).
- [x] Viết script sinh bằng vLLM, script kiểm tra tương đương, `setup_pod.sh` và `Instruction_task6.md`; tạo thứ tự xáo 6.868 bài và `pool_v1_input.jsonl` (1.100 dòng) kèm manifest SHA-256 (2026-10-21).
- [x] Chuẩn bị GPU có bf16: pod RunPod `tz1k71joq490o0` (L4, EUR-IS-1, $0,59/giờ), network volume `0q3rshkad1` (40 GB) tại `/workspace` (2026-10-21).
- [x] Chạy 100 bài batch_100 bằng vLLM 0.32.0 trên L4 (500 lượt, 68 giây) và kiểm tra tương đương với lần sinh đầu bằng HF (2026-10-21): **PASS**. Valid 402/500 (80,4%) so với 406/500 (81,2%), lệch −0,8 điểm %; độ dài valid trung bình 237,2 so với 236,8 token, lệch +0,2%. Báo cáo: `reports/task6/parity_vllm_hf.json`.
- [x] Sinh trajectory cho 1.100 câu (100 batch_100 + 1.000 câu mới) × K = 5 = 5.500 lượt sinh, giữ nguyên seed rule trong config (2026-10-21, vLLM 0.32.0, L4, 499 giây cho 5.000 lượt bài mới). Kết quả `trajectory/pool/pool_v1_teacher_raw.jsonl`: 5.500 dòng, đủ K = 5 cho mọi bài, seed và ID đúng quy tắc; valid 4.355 (79,2%), invalid_format 730 (13,3%), invalid_answer 415 (7,5%); 168 trajectory chạm 512 token. **1.032 bài có ít nhất 1 lời giải đúng (≥ 1.000), không cần thêm khối 100 bài**; 68 bài bị loại theo T6-3 (6,2%).
- [x] ~~Tái sử dụng pool sơ bộ~~: thay bằng sinh lại cả batch_100 (T6-4). Không ghi đè file raw cũ.
- [x] Chấm đáp án bằng `scripts/answer_utils.py` (đã chốt ở Task 5, I1): chấm ngay khi sinh, lưu ở `metadata.verification_status`.
- [x] Validate toàn bộ trajectory: tạo `schemas/teacher_trajectory_schema_v2.json` (v1 cấm `question`/`raw_generation` cần cho huấn luyện), `pool_v1_verified.jsonl` 4.353 trajectory / 1.032 bài eligible, 0 lỗi schema; kiểm tra rò rỉ D_dev/D_test PASS; C(τ) từ extractor rules v2 trên toàn bộ output (T6-6) (2026-10-21).
- [x] Thống kê (trạng thái, 68 bài bị loại, capability, token theo tokenizer Student, phân tích invalid_format 13,3%) và báo cáo `reports/task6/pool_report.md`; `student_common.load_pool` trỏ sang `pool_v1_verified.jsonl`, smoke test vẫn tái lập được với pool sơ bộ (2026-10-22). Lưu ý cho Task 7: response trung bình 245,8 token (cao hơn L̄ 8,2%), ratio chỉ 19 bài; nên báo cáo kèm accuracy chấm nới.
- [x] Chốt quy tắc cho các câu không có lời giải đúng nào sau K lần sinh: **loại** khỏi eligible, giữ trong raw và báo cáo (T6-3).
- [x] ~~Nếu không đủ tài nguyên cho 1.000 câu: giảm `n_round`~~: không cần, pool có 1.032 bài eligible.

### 1.2. Annotation (phần còn lại của Task 4)
- [!] Xác minh người annotate thứ hai (A2) có làm độc lập không (A1/A2 trùng 30/30). Nếu không: annotate lại theo `guideline_v3.md` mà không xem nhãn A1, rồi tính lại kappa.
- [ ] Gán nhãn lần hai cho một phần trong 85 câu bổ sung để đo độ đồng thuận trên ratio, percentage, fraction.
- [ ] Ghi các giới hạn còn lại vào báo cáo nếu không khắc phục được.

### 1.3. Bộ trích xuất capability
- [ ] Giảm nhận nhầm division (khoảng 49 trajectory dạng "một phần của N" viết thành N / k). Có thể cần thêm ngữ cảnh đề bài vào luật.
- [ ] Đánh giá được ratio (batch 100 không có câu ratio; dùng các câu bổ sung).
- [ ] Thử extractor trên lời giải của Student, không chỉ của Teacher.
- [ ] Mọi thay đổi luật thì tạo `capability_rules_v3.json`, không sửa bản cũ, và lưu report riêng.

---

## Ưu tiên 2: Thí nghiệm chính (Task 7 trở đi)

### 2.1. Cài đặt pipeline
- [x] Chốt quy tắc phân tích và lịch chọn của B3, B4 trước khi chạy (2026-11-01): `task7_decisions.md`, config v2, `analysis_plan.md` v2. Scripts bên dưới phải cài theo các quy tắc này.
- [x] Script tính `L_proxy` (NLL chuẩn hoá theo độ dài, dải Gauss với ℓ* = median, σ = IQR/1.349) cho toàn pool tại mỗi checkpoint: `scripts/learnability.py` (2026-11-01).
- [x] Script chọn dữ liệu theo đúng `analysis_plan.md`: `n_cap = 1`, tie-break theo `trajectory_id`, ghi log theo `selection_log_schema.json`. **Dừng theo ngân sách token `beta_round`, không theo số lượng** (smoke test chọn theo số lượng đã lệch tới +4,5%): `scripts/selection.py`, `select_round.py`, `build_pool_tokens.py`, test `test_selection.py` (2026-11-01).
- [x] Cài đặt các phương pháp bắt buộc: B0, B2, B3, B4, B5, và ablation `shuffled_scores` (2026-11-01). Tuỳ chọn B1, B6: chưa cài.
- [x] Script huấn luyện LoRA theo config (completion-only loss, giữ adapter qua các vòng, khởi tạo lại optimizer mỗi vòng): `train_round.py` có sẵn, đã chạy nối 3 vòng trong pilot.
- [~] Script đánh giá (greedy, `answer_utils.py`), ghi accuracy tổng, accuracy theo capability, tỉ lệ đúng định dạng, độ dài output: `eval_student.py` thêm D_test, chấm nới, capability (85 bài có nhãn), backend vLLM. **Backend vLLM chưa chạy thử**; đối chiếu bằng `compare_eval_backends.py` trên pod.
- [x] Orchestrator chạy một phương pháp, một seed, chạy tiếp khi bị ngắt, dùng lại S_1 giữa B4 và B5: `scripts/run_experiment.py` (2026-11-01).
- [x] Pilot pipeline trên máy local (Qwen2.5-0.5B, pool 60 bài, backend HF): đủ 6 phương pháp và L_emp chạy hết, chỉ để kiểm tra pipeline (2026-11-01). Chi tiết: `done.md`.
- [ ] Chạy thử trên L4 với model thật: đo thời gian từ `runs/.../timing.jsonl`, đối chiếu vLLM với HF, tách khỏi kết quả chính.
- [ ] Xác nhận 3 quy ước cài đặt và việc giữ hay bỏ ablation (`done.md`, mục 4); ghi thành T7-9 trong `task7_decisions.md` và tạo lại manifest Task 7.
- [ ] **Quyết định trước khi chạy chính:** có thêm biến thể chọn theo ℓ cao / ℓ thấp không (`notes/formula_review.md`, mục A2). Hiện chưa có bằng chứng "vùng giữa" tốt hơn hai đầu. Nếu thêm: ghi quyết định mới, cài vào `selection.py`, tính thêm chi phí GPU.
- [ ] Viết script phân tích cho mọi mục ở 3.1, thử trên dữ liệu pilot trước khi có kết quả chính.
- [ ] Commit theo hai đợt: đợt chốt v2 trước, pipeline sau, để giữ bằng chứng quy tắc được chốt trước khi có số liệu. Dọn các file đã xóa trong git; không đưa `diagrams/.$file_relationships.drawio.bkp` vào commit.

### 2.2. Đo nhiễu trước khi chạy so sánh
- [ ] Đo ρ_noise và ε trên các lần chạy B4 (cùng dữ liệu, khác seed) theo T7-6, T7-7; cần NLL của B4 tại S_1 và S_2 cho 3 seed.
- [~] Đo `L_emp` tại S_0 trên 5 nhóm theo độ dài token (50 trajectory/nhóm), tính tương quan Spearman với `L_proxy` để kiểm chứng proxy: `scripts/probe_lemp.py` đã có, chưa đo trên model thật.
- [ ] **Chốt I4 (probe `b = 7`)**: chạy thử 1–2 nhóm probe, so mức thay đổi với nhiễu giữa seed (1,2 điểm % ở smoke test). Tín hiệu quá nhỏ thì tăng `b` hoặc kích thước nhóm qua config v2. Cân nhắc dùng accuracy lỏng để loại hiệu ứng học định dạng.

### 2.3. Chạy thí nghiệm
- [ ] Vòng đầu S_0 → S_1 cho tất cả phương pháp, 3 seed (13, 42, 2026).
- [ ] Hoàn thành 3 vòng (S_0 → S_3). Chỉ đánh giá trên D_test tại các checkpoint đã định trước.
- [~] Ghi `beta_est` (chi phí ước lượng learnability) cạnh chi phí huấn luyện: `run_experiment.py` đã ghi vào `checkpoint_log.jsonl`, còn đưa vào báo cáo.
- [ ] Tạo manifest SHA-256 cho kết quả thí nghiệm chính và sao lưu về máy local, giống các Task trước.

### 2.4. Kiểm soát hiệu ứng giả (đề xuất bổ sung, cần nhóm duyệt)
- [x] Phân tích riêng sự thay đổi `L_proxy` trên các trajectory **chưa từng được chọn huấn luyện**. Trajectory đã được học sẽ tự giảm NLL, nên đó là thay đổi cơ học, không phải learnability: đã chốt thành tập U (T7-6, T7-7), thực hiện ở mục 3.1.
- [ ] Biến thể chọn theo NLL cao / NLL thấp: chuyển thành việc phải quyết định ở mục 2.1.
- [ ] Cân nhắc thêm tập đánh giá độ bền (GSM-Plus hoặc GSM-Symbolic) vì GSM8K có thể đã bị nhiễm vào dữ liệu huấn luyện của Qwen2.5.
- [ ] Mọi bổ sung ở trên phải ghi là **exploratory** hoặc tạo config v2 trước khi chạy, không sửa phân tích chính sau khi đã thấy kết quả.

---

## Ưu tiên 3: Phân tích và Đề xuất 1

### 3.1. Phân tích thống kê (theo `analysis_plan.md`)
- [ ] So sánh chính B5 vs B4 trên D_test: McNemar trong từng seed, trung bình hiệu cặp + 95% CI giữa các seed.
- [ ] So sánh phụ: B4 vs B3, B4/B5 vs B2, B5 vs ablation (nếu giữ ablation).
- [ ] Accuracy chấm nới (T7-5): McNemar và CI qua seed cho B5 vs B4, luôn báo cáo cùng accuracy chặt và tỉ lệ đúng định dạng.
- [ ] Đọc thủ công nhóm `invalid_format` có `lenient_correct = True` trên D_test tại S_0 và S_3, tối đa 100 trường hợp mỗi checkpoint, để ước lượng tỉ lệ đúng nhầm (T7-5).
- [ ] Đo ε trên U: phân vị 95% của |L^a − L^b| tại S_1, kèm 2,77·s_w và CI bootstrap theo bài; báo cáo tỉ lệ vượt ε so với mốc 5% (T7-6).
- [ ] Kiểm định giả thuyết H (T7-4, T7-7): trên B4, S_0→S_1 và S_1→S_2, Δ^a = ρ_noise^a − ρ_change^a trên U, bootstrap theo cụm `problem_id` 10.000 lần. Ủng hộ H khi **mọi** seed có cận dưới một phía 95% của Δ^a > 0 và Δ^a ≥ 0,05.
- [ ] Thang đo của H (T7-7): quyết định trên L_proxy, báo cáo Δ trên thứ hạng ℓ kèm CI. Nếu L_proxy đạt mà ℓ không đạt, chỉ kết luận "thứ hạng theo khoảng cách tới trung vị thay đổi".
- [ ] Độ nhạy của H (T7-7): mốc √ρ_noise ở S_0→S_1, kiểm định Steiger, U bỏ các bài có trajectory đã train, lặp lại trên B2 (cần `--b2-nll`). Wilcoxon kèm effect size chỉ để mô tả.
- [ ] Độ nhạy của việc chọn với nhiễu: Jaccard giữa tập chọn vòng 2 của B5 ở các seed, so với mức ngẫu nhiên khoảng 0,02 (T7-8).
- [ ] Các chỉ số dynamic: Jaccard(B_t, B_{t+1}), tỉ lệ trajectory vào/ra dải, phân loại profile tăng/giảm/ổn định/không đơn điệu (profile chỉ mang tính mô tả).
- [ ] Hiệu quả: accuracy D_test theo số token đã train, diện tích dưới đường cong, `beta_est`.
- [ ] Proxy validity: Spearman giữa L_proxy trung bình theo nhóm và L_emp, kèm bootstrap CI; 5 nhóm nên chỉ mang tính mô tả.
- [ ] Hiệu chỉnh Holm-Bonferroni qua các baseline và các phân tích theo capability. Báo cáo effect size và CI cùng p-value; báo cáo kết quả null/âm chi tiết như kết quả dương.

### 3.2. Đề xuất 1
- [ ] Nhóm chốt phạm vi: chỉ làm đường cong học theo capability (rẻ, có sẵn từ đánh giá mỗi checkpoint), hay cả đồ thị transfer (cần huấn luyện can thiệp riêng cho từng capability, rất tốn tài nguyên).
- [ ] Dựng learning curve theo capability từ dữ liệu thật (thay dữ liệu giả lập trong `learning_dynamics/examples/`).
- [ ] Dựng capability graph từ checkpoint S_1 nếu giữ phần transfer.

---

## Ưu tiên 4: Tài liệu, môi trường, báo cáo (Task 8)

### 4.1. Tài liệu
- [ ] Viết lại `readme.md`. Hiện file bị cụt, bắt đầu từ mục 5, mất phần giới thiệu sau commit 3f7dce4. Cần có: mục tiêu, hai đề xuất, cấu trúc thư mục, cách chạy, trỏ tới protocol và config.
- [ ] Gộp protocol Đề xuất 2 về một nguồn duy nhất (hiện rải rác ở `readme.md`, `proposal2_full_protocol.md`, `proposal2_trajectory_protocol.md`).
- [ ] Đánh dấu hoặc chuyển các kết quả cũ đã lỗi thời. Ví dụ `experiments/week2September/results/multi_trajectory_analysis.json` (single-shot 10%, do lỗi trích đáp án cũ) dễ bị trích nhầm.
- [ ] Sửa `week2_experimental_snapshot.txt` (đang chứa nguyên lệnh PowerShell `@" ... "@`).
- [ ] Bổ sung lệnh bash tương đương cho các hướng dẫn đang dùng PowerShell và đường dẫn `C:\`.

### 4.2. Môi trường
- [~] `requirements.txt` / `requirements-lock.txt`: đã chuyển sang UTF-8, thêm index PyTorch cu126, bổ sung `openai`, `jsonschema`, `matplotlib`, `scipy`, `bitsandbytes`, resolve được cho Windows/Linux với Python 3.11-3.14. **Còn lại:** cài thử trong venv sạch trên cả Windows và Linux, rồi chạy các script validate.
- [ ] Rà soát và bỏ các đường dẫn cố định chỉ chạy được trên máy cá nhân.

### 4.3. Tổng quan tài liệu và báo cáo
- [ ] Viết `papers/paper_analysis.md` (hiện rỗng). Cần so sánh với các công trình liên quan (learnability gap / mix distillation, chọn dữ liệu theo loss hoặc độ khó như IFD, LESS, RHO-1, curriculum) để xác định điểm mới.
- [ ] Tìm cơ sở tài liệu cho các ngưỡng đang chọn (n-gram = 13, retention r = 50%, dải median/IQR).
- [ ] Bắt đầu viết các phần đã ổn định của khoá luận: tổng quan, phương pháp, dữ liệu, thiết lập thực nghiệm.
- [ ] Viết chương kết quả và thảo luận của khoá luận, sau khi có phân tích 3.1.
- [ ] Viết bài báo. Giá trị config và kết quả chỉ đặt ở mục Experiments, không đặt ở Related Work hay Methodology.
- [ ] Rà lại BCGK và báo cáo tiến độ: `need_fix.txt`, `need_fix_BaoCaoTienDo2.txt` không còn trong thư mục gốc repo, cần xác nhận các lỗi đã sửa chưa.
- [ ] Làm slide và chuẩn bị bảo vệ.
- [ ] Đối chiếu file này với yêu cầu của khoa và giảng viên hướng dẫn.
- [ ] Ước lượng thời gian chạy, chia việc trong nhóm và lên lộ trình đến hạn nộp. **Chưa ghi hạn nộp trong file này.**

---

## Thứ tự gợi ý

Đã xong: smoke test (0.1), pool chính thức (1.1), chốt quy tắc và viết pipeline, pilot local (2.1).

1. Commit, xóa pod cũ và đổi API key (0.2, 2.1).
2. Chốt các quyết định còn mở ở 2.1: ablation, 3 quy ước cài đặt, biến thể ℓ cao / ℓ thấp.
3. Chạy thử trên L4 với model thật, đối chiếu vLLM với HF, ước tính chi phí (2.1).
4. Đo `L_emp`, chốt I4 (2.2). Nếu I4 đổi thì tạo config mới trước khi chạy chính.
5. Viết script phân tích và thử trên dữ liệu pilot (2.1).
6. Chạy thí nghiệm chính (2.3); đo ρ_noise và ε từ các lần chạy B4 (2.2).
7. Phân tích (3.1), rồi chương kết quả và bài báo (4.3).
8. Annotation, extractor, tài liệu (1.2, 1.3, 4.1, 4.2) và phần khoá luận đã ổn định làm xen kẽ khi chờ máy chạy.
