# Task 5: Các quyết định đã đưa ra và lý do

Ngày: 2026-10-14.
Phạm vi: các quyết định cần chốt trước khi freeze (`task5_todo.txt`).
Trạng thái: config v1 không còn TBD (`--frozen` PASS). Thay đổi sau freeze phải tạo config version mới kèm lý do.

Nhãn nguồn:
- [README CŨ]: lấy từ `readme.md` gốc trước commit 3f7dce4 (`git show 3f7dce4^:readme.md`), có ghi mục.
- [NHÓM]: nhóm chốt ngày 2026-10-14.
- [TÍNH]: tính từ dữ liệu trong repo.


## A. Môi trường

| # | Quyết định | Nguồn |
|---|---|---|
| 3 | Tạo `.venv` ở gốc repo, cài theo `requirements.txt` | [NHÓM] |

Ghi chú [TÍNH]: `requirements.txt` mã hóa UTF-16 (pip freeze trên Windows), chứa `torch==2.13.0+cu126` (cần `--extra-index-url https://download.pytorch.org/whl/cu126`) và **không có `jsonschema`** dù các script validate cần. Đồng bộ requirements thuộc Task 8.

## B. Split

| # | Quyết định | Nguồn |
|---|---|---|
| 4 | D_test = GSM8K test chính thức (1319 bài) | [NHÓM], khớp [README CŨ] 13.1 |
| 5 | batch_100 bắt buộc vào D_pool | [NHÓM] |
| 6 | Supplement 85 bài vào D_dev | [NHÓM] |
| 7 | N_dev = 500 = 85 supplement + 415 lấy ngẫu nhiên từ GSM8K train còn lại | [NHÓM] |
| 8 | split_seed = 363636 | [NHÓM] |
| 9 | Near-duplicate: 13-gram overlap giữa D_pool và D_dev/D_test; bài bị gắn cờ loại khỏi D_pool | [NHÓM]; [README CŨ] 13.1 chỉ nói "n-gram overlap" |

Hệ quả của #7: D_dev **không stratify** theo capability ngoài 85 bài supplement (README cũ 13.1 viết "should be stratified"). Số bài theo capability chỉ báo cáo được trên phần có nhãn thủ công; phần còn lại ghi là giới hạn.

## C. Lịch train và budget

| # | Quyết định | Nguồn |
|---|---|---|
| 11 | M = 3 (S_0 … S_3) | [NHÓM]; [README CŨ] 5.1 ghi "for example M = 3" |
| 12 | beta_round = n_round × L̄ (L̄ = độ dài token trung bình của trajectory đã verify). Chưa chốt số. Pool phải lớn hơn khoảng 3–5 lần n_round | [NHÓM]; đơn vị token theo [README CŨ] 11.1 |
| 13 | Chỉ đo L_emp tại S_0, theo nhóm độ dài, để kiểm tra proxy. b chốt sau smoke test, thử từ 50 step | [NHÓM] |
| 14 | LoRA r=16, alpha=32, lr 2e-4, 1 epoch/vòng, max_seq_len 1024. Giá trị mặc định phổ biến, **chưa tune**; nếu tune chỉ trên D_dev | [NHÓM] |
| 15 | Chạy chính thức trên cloud; GPU 3050 Ti 4GB chỉ smoke test (QLoRA) | [NHÓM] |

Ghi chú #12 [TÍNH]: pool sơ bộ có 480 trajectory valid trên **98 bài** (không phải 100: `gsm8k_train_00029`, `gsm8k_train_00056` không có trajectory valid). Tổng `token_length` (token Teacher sinh, chưa gồm prompt) = 109.501, trung bình 228.1, trung vị 215.5, min 76, max 485. Với n_cap = 1, mỗi vòng chọn tối đa 98 trajectory → Task 6 phải mở rộng pool.

## D. Seed

| # | Quyết định | Nguồn |
|---|---|---|
| 16 | training_seeds = [13, 42, 2026]; thêm 2 seed nếu đủ tài nguyên. Giá trị tùy ý | [NHÓM]; số lượng ≥ 3 theo [README CŨ] 13.2 |
| 17 | data_order_seed = training_seed, ghi riêng trong config | [NHÓM] |

## E. Selection

| # | Quyết định | Nguồn |
|---|---|---|
| 18 | ell*_t = median, sigma_t = IQR / 1.349 (trên pool eligible tại S_t) | [README CŨ] 9.1 |
| 19 | alpha = 0.5, ghi "chưa tune"; nếu đủ tài nguyên tune trên D_dev với {0.25, 0.5, 0.75}. Chỉ ảnh hưởng B6 | [NHÓM]; [README CŨ] 16.1 yêu cầu tune trên D_dev |
| 20 | n_cap = 1 | [NHÓM]; [README CŨ] 16.1 ví dụ |
| 21 | r = 50% | [NHÓM], dẫn TiC-LM (ACL 2025, arXiv 2504.02107) |
| 22 | Cho phép chọn lại trajectory ở các vòng sau; mỗi vòng giữ n_cap; không giới hạn tổng | [NHÓM] |
| 23 | Hòa điểm: xếp theo trajectory_id | [NHÓM] |
| 24 | B3 = trajectory đúng ngắn nhất mỗi bài (xem dưới) | [NHÓM] |

Ghi chú #21:
- Các trang tóm tắt TiC-LM xác nhận bài dùng "fixed-ratio replay of older data", nhưng **chưa xác nhận con số 50%**; cần đối chiếu toàn văn. TiC-LM là continual pretraining trên web data theo thời gian, khác bối cảnh ở đây (cùng GSM8K, khác capability).
- Phạm vi áp dụng r còn mở (xem "Còn mở").

Chi tiết #24 (B3):
1. Chỉ lấy trajectory đúng (`verification_status == valid`), chấm bằng hàm verify đã thống nhất.
2. Mỗi bài chọn 1 trajectory ngắn nhất, đếm token bằng tokenizer của Student; hòa thì trajectory_id nhỏ nhất.
3. Nếu tổng token vượt beta_round: xáo thứ tự **bài** bằng seed (giống B2), lấy dần tới khi đủ budget.
4. Tính một lần, dùng nguyên tập cho cả 3 vòng.

Lý do không dùng `scripts/select_traces_automatically.py` [TÍNH]: dùng skill gap của Student (không phải heuristic bề mặt), chọn Top-2 toàn pool, đường dẫn và schema của dữ liệu 50x5 cũ.

## F. Đánh giá và phân tích

| # | Quyết định | Nguồn |
|---|---|---|
| 25 | prompt_version v1 = cùng prompt template với `scripts/generate_teacher_trajectories_batch.py` | [NHÓM] |
| 26 | Eval greedy, max_new_tokens = 512 | [NHÓM]; [README CŨ] 10.1 |
| 28 | Đánh giá D_test ở mọi checkpoint S_0 … S_3; mọi quyết định chỉ dựa trên D_dev | [NHÓM]; [README CŨ] 10.1, 13.1 |
| 29 | Bắt buộc: B0, B2, B3, B4, B5. Nên có: ablation "dynamic with shuffled scores". Nếu đủ tài nguyên: B1, B6 | [NHÓM]; ablation theo [README CŨ] 16.2 |
| 30 | Trong một seed: McNemar. Qua các seed: trung bình chênh lệch paired + 95% CI. alpha = 0.05 | [NHÓM]; [README CŨ] 19.1 |

## G. Dọn dẹp

| # | Quyết định | Trạng thái |
|---|---|---|
| 31 | Sửa `config/proposal2_trajectory_protocol.md` bị lặp | XONG 2026-10-14: giữ dòng 1–106 + `}` đóng JSON; đã diff, hai nửa giống hệt nhau. (Dấu `}` ở đầu dòng 107 cũ là dấu đóng JSON của nửa đầu, không phải dấu thừa.) |

## H. Kết quả chạy (2026-10-14)

**Môi trường** [TÍNH]: `.venv` (Python 3.14.6): torch 2.13.0+cu126 (CUDA khả dụng), transformers 5.15.0, datasets 5.0.1, jsonschema 4.26.0 (cài thêm, không có trong requirements.txt).

**GSM8K test** [TÍNH]: `scripts/download_gsm8k_test.py` → `data/raw/gsm8k_test.jsonl`, 1319 bài, `openai/gsm8k` main test, revision `740312add88f781978c0658806c59bc2815b9866`, sha256 `96ec83f9…`. Kiểm tra thêm: 7473 record của `gsm8k_train.jsonl` khớp HF train ở cùng revision (0 khác biệt về question/ground_truth theo source_index).

**Split** [TÍNH]: `scripts/create_splits.py` → `splits/`.

| Split | Số bài |
|---|---|
| D_pool | 6968 (gồm 100/100 bài batch_100) |
| D_dev | 500 = 85 supplement + 415 ngẫu nhiên (seed 363636) |
| D_test | 1319 |
| Bị loại do near-duplicate 13-gram | 5 |

`scripts/validate_splits.py`: PASS 31/31 check. Chạy lại 3 lần với PYTHONHASHSEED khác nhau: hash 4 file output giống hệt. Script từ chối ghi đè `splits/`.
`split_manifest.json` sha256 `8bac2c8d43eae6df53b63f97f353ed6006551f44d5562b74941455301fec09a3` (đã điền vào config).

5 bài near-duplicate (đọc tay từng cặp):
| D_pool | Trùng với | Đánh giá |
|---|---|---|
| gsm8k_train_01401 | gsm8k_test_00602 | cùng khuôn ("travels N miles in 3 hours… additional hours"), khác số |
| gsm8k_train_05199 | gsm8k_test_00602 | như trên |
| gsm8k_train_01779 | gsm8k_train_04791 (D_dev) | bài ngược (cookie jar) |
| gsm8k_train_05217 | gsm8k_train_00779 (D_dev) | bài ngược (soccer camp) |
| gsm8k_train_00501 | gsm8k_test_00581 | **ca biên**: chung 1 câu mô tả phim, câu hỏi khác. Vẫn loại theo quy tắc #9 |

**Revision model** [TÍNH]: HF `Qwen/Qwen2.5-3B-Instruct` sha `aa8e725…`, `Qwen/Qwen2.5-1.5B-Instruct` sha `989aa79…`; cả hai repo sửa lần cuối 2024-09-25. Teacher không ghi revision lúc sinh; vì repo không đổi từ 2024-09-25, nếu tải từ HF main thì revision là `aa8e725`. Student ghim `989aa79`. Đã điền vào config kèm ghi chú.

**Token của pool dưới tokenizer Student** [TÍNH] (`scripts/measure_pool_tokens.py` → `reports/task5/pool_token_stats.json`, 480 trajectory valid, 98 bài):
| | Tổng | Trung bình | Trung vị | Min | Max |
|---|---|---|---|---|---|
| Response | 109.022 | 227.1 | 215 | 75 | 484 |
| Prompt + response (chat template) | 172.606 | 359.6 | 348 | 186 | 633 |
| B3 (ngắn nhất mỗi bài, response) | 16.957 | 173.0 | 168.5 | 75 | 352 |
- `token_length` của Teacher = response + 1 ở 478/480 trajectory (nhiều khả năng là token kết thúc), nên tokenizer 3B và 1.5B cho cùng kết quả trên pool này.
- Max 633 < max_seq_len 1024.

**Answer extractor/verifier ứng viên** [TÍNH]: `scripts/answer_utils.py`: tách REASONING/ANSWER (cùng regex với script generate), lấy **số cuối**, chuẩn hóa **Decimal**. `scripts/test_answer_utils.py`: 12/12 unit case; tái tạo đúng 480 valid / 20 invalid_answer (0 lệch). Trạng thái: **đề xuất, chưa chốt**.
Ghi chú: gsm8k_train_00056 có cả 5 trajectory ra 600 trong khi ground truth 50; Task 4 đã ghi nhãn 50 là lỗi có sẵn trong lời giải gốc GSM8K. Giữ nguyên, bài này không có trajectory valid.

**Schema/config** [TÍNH]:
- `validate_selection_log.py`: ví dụ hợp lệ PASS 4/4; ví dụ sai FAIL 4/4 đúng lỗi đã cài.
- `validate_experiment_config.py`: PASS (draft); `--frozen` FAIL vì còn 13 TBD (đúng mong đợi).

**Manifest** [TÍNH]: `reports/task5/SHA256SUMS_task5.txt` (split, config, schema, analysis plan, dữ liệu nguồn, pool, script). Kiểm tra: `sha256sum -c reports/task5/SHA256SUMS_task5.txt` tại `manual/`. Phải tạo lại khi freeze.

## I. Đề xuất để freeze (2026-10-14)

Trạng thái duyệt (nhóm, 2026-10-14):
| Mã | Trạng thái |
|---|---|
| I1, I2, I6, I7, I8 | **ĐÃ CHỐT** |
| I3, I4, I5 | **CHƯA CHỐT, chờ smoke test** trên D_dev (README.txt mục 0, Task 5 "Còn lại"). Giá trị dưới đây là giá trị tạm trong config v1; nếu smoke test cho kết quả khác thì đổi bằng config v2 kèm lý do, trước thí nghiệm chính |

Các giá trị dưới đây đã điền vào `config/experiment_config.json` để config không còn TBD (`validate_experiment_config.py --frozen`: PASS).

**I1 [ĐÃ CHỐT]. Answer extractor/verifier (#27, #27b)** → `scripts/answer_utils.py`; `invalid_format` tính là sai, tỉ lệ format compliance báo cáo riêng.
- Là hàm duy nhất tái tạo đúng trạng thái verify của pool (480/20); hai hàm cũ lệch 1 và 5 record (mục H).
- Dùng cùng regex REASONING/ANSWER với prompt v1, nên Teacher và Student được chấm như nhau.
- Tính `invalid_format` là sai vì README cũ §10.1 coi "format compliance (final answer extractable)" là metric phụ, tức không trích được đáp án thì không có đáp án.

**I2 [ĐÃ CHỐT]. Token budget đếm gì (#12b)** → chỉ đếm **token response** (có loss); token prompt bị mask khỏi loss và ghi log riêng.
- README cũ §11.1 chọn token làm đơn vị vì "a count-based budget silently gives long trajectories more training exposure". Exposure là số token được học (có gradient); token prompt không có gradient khi train completion-only.
- Prompt gần như giống nhau giữa các trajectory của cùng bài, nên nếu đếm prompt thì budget phạt các phương pháp chọn nhiều bài khác nhau, không liên quan tới độ dài lời giải.

**I3 [CHỜ SMOKE TEST]. n_round, beta_round (#12)** → n_round = 200; beta_round = round(200 × 227.13) = **45.426** token response/vòng; tổng 3 vòng 136.278. Yêu cầu kèm theo: pool chính thức ở Task 6 phải phủ **≥ 1000 bài**.
- Ràng buộc nhóm đã chốt (#12): pool ≥ 3–5 × n_round. Với n_cap = 1, số trajectory chọn được mỗi vòng ≤ số bài. Pool sơ bộ 98 bài chỉ cho n_round ≤ 32 (khoảng 7.300 token/vòng), quá nhỏ để thấy khác biệt giữa các phương pháp, nên dù chọn số nào Task 6 cũng phải mở rộng pool.
- Chi phí lớn nhất của thí nghiệm là **eval**, không phải train: 4 phương pháp × 3 seed × 4 checkpoint × (500 dev + 1319 test) ≈ 87.000 lần sinh greedy ≤ 512 token. Train 136K token/run là rẻ. Sinh pool 1000 bài × K=5 = 5.000 lần sinh, cũng nhỏ so với eval. Vì vậy tăng n_round không làm thí nghiệm đắt hơn đáng kể; giới hạn thực tế là kích thước pool.
- Chọn hệ số 5× (cận trên của 3–5×) để mỗi vòng chỉ chọn 20% số bài, selection có nhiều lựa chọn.
- L̄ cố định từ pool sơ bộ (227.13, đã hash). Nếu pool chính thức có L̄ khác, beta_round vẫn giữ nguyên số đã freeze.
- Rủi ro: 600 trajectory sau 3 vòng có thể vẫn làm accuracy thay đổi ít. Nếu smoke test cho thấy vậy, phải đổi bằng config v2 kèm lý do **trước** khi chạy thí nghiệm chính, không đổi sau khi thấy kết quả.

**I4 [CHỜ SMOKE TEST]. Probe budget b (#13)** → nhóm G = 50 trajectory (cận trên khoảng 20–50 của README cũ §9.1(b)); 5 nhóm theo ngũ phân vị độ dài token tại S_0, lấy mẫu với seed 363636; **b = ceil(50/8) = 7 step** (1 epoch).
- L_emp dùng để kiểm tra L_proxy có dự đoán được mức học trong **chính chế độ train của thí nghiệm** không. Chế độ đó là 1 epoch/vòng, batch 8, cùng lr. Train probe nhiều epoch hơn sẽ đo một chế độ khác (dễ overfit nhóm 50 trajectory).
- Rủi ro: tín hiệu có thể nhỏ hơn nhiễu, khi đó kiểm tra proxy validity cho kết quả không kết luận được. README cũ §19 yêu cầu giữ lại kết quả null.
- Thay cho giá trị "thử từ 50 step" ở #13: 50 step × batch 8 = 400 lượt trên nhóm 50 trajectory = 8 epoch.

**I5 [CHỜ SMOKE TEST]. Hyperparameters (#14)**: giữ r=16, alpha=32, lr 2e-4, 1 epoch/vòng, max_seq_len 1024 (nhóm đã chốt, #14), thêm:
| Tham số | Giá trị | Lý do |
|---|---|---|
| target modules | q,k,v,o,gate,up,down_proj (mọi lớp linear trừ lm_head; tên lấy từ config Qwen2.5-1.5B @989aa79) | QLoRA: "LoRA on all linear transformer block layers are required to match full finetuning performance" |
| lora_dropout | 0.1 | QLoRA Appendix: "LoRA dropout of 0.1 for models up to 13B" |
| lr scheduler | constant, không warmup | QLoRA: "we use a constant learning rate schedule"; mỗi vòng chỉ khoảng 45.426/227 ≈ 200 trajectory / batch 8 ≈ 25 step, lịch giảm dần sẽ làm các vòng không đồng nhất |
| optimizer | AdamW (`adamw_torch`), beta2 0.999, weight decay 0, max grad norm 0.3 | QLoRA Appendix (beta2, grad norm); AdamW là mặc định của trl/transformers |
| batch size | 8 (hiệu dụng) | khoảng 25 step/vòng; batch 16 như QLoRA chỉ còn khoảng 12 step |
| loss | completion-only | nhất quán với I2 |
| adapter qua các vòng | tiếp tục cùng adapter từ S_t; optimizer state khởi tạo lại mỗi vòng | đúng định nghĩa S_{t+1} = Train(S_t, B_t) (README cũ §5.1) |
| precision | bf16 | chạy cloud; smoke test cục bộ dùng QLoRA (#15) |

**I6 [ĐÃ CHỐT]. Seed**:
- B2: `random.Random(training_seed * 100 + round)`: khác nhau theo seed và vòng, không trùng giữa các seed {13, 42, 2026}.
- B3: thứ tự bài khi cắt theo budget dùng `training_seed`, cùng cách B2 lấy ngẫu nhiên (quyết định #24 bước 3). Với pool ≥ 1000 bài, tổng token của B3 (khoảng 1000 × 173 ≈ 173K) vượt beta_round 45.426, nên bước cắt chắc chắn xảy ra.
- Seed bổ sung [7, 77]: ghi trước để nếu đủ tài nguyên thì chạy, và khi chạy phải chạy cho mọi phương pháp. Giá trị tùy ý.

**I7 [ĐÃ CHỐT]. Phạm vi retention r (#21b)** → chỉ B6.
- So sánh chính B5 vs B4 phải chỉ khác ở việc tính lại learnability (README cũ §16.2). B4, B5 và ablation không dùng capability nên không có khái niệm "capability đã nắm" để áp quota.
- r = 50% đã đối chiếu toàn văn TiC-LM (arXiv 2504.02107, Sec. 5, 6.1): bài thử α_t = 1/t và α_t = 1/2, kết luận "α_t = 1/2 offers a better practical trade-off". Lưu ý bối cảnh: continual pretraining theo thời gian, khác bài toán này.

**I8 [ĐÃ CHỐT]. Khôi phục protocol (#32)** → `config/proposal2_full_protocol.md`: trích **nguyên văn** các mục §5.1, §9, §10.1, §11.1, §13.1–13.2, §16.1–16.2, §19–19.1 từ `3f7dce4^:readme.md`; đã diff, khớp 100%. Đầu file ghi nguồn và lệnh tái tạo.

## Còn mở

Trạng thái 2026-10-14: config v1 hết TBD (`--frozen` PASS).
- #1 **ĐÃ CHỐT**: nhóm xác nhận định nghĩa trong README cũ (`config/proposal2_full_protocol.md`) còn hiệu lực.
- I1, I2, I6, I7, I8 **ĐÃ CHỐT**.

Còn lại:
| # | Vấn đề | Ghi chú |
|---|---|---|
| I3, I4, I5 | Budget mỗi vòng, probe budget b, hyperparameters | Chờ smoke test trên D_dev |
| T6 | Task 6 phải tạo pool chính thức ≥ 1000 bài D_pool (điều kiện của I3) | Nếu không đủ tài nguyên: giảm n_round (sửa I3, config v2) |
