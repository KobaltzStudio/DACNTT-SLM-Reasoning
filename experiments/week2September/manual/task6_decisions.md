# Task 6: Các quyết định cho pool chính thức (đề xuất)

Ngày: 2026-10-21.
Phạm vi: các quyết định cần chốt **trước khi** sinh pool chính thức trên D_pool (`Task.md` mục 1.1, `README.txt` mục 6).
Trạng thái: **ĐÃ CHỐT (2026-10-21)** cả 5 quyết định T6-1 đến T6-5, theo đúng đề xuất bên dưới (xem bảng tóm tắt). Mọi thay đổi sau này phải ghi thêm mục mới kèm lý do, không sửa nội dung đã chốt.

Nhãn nguồn:
- [TÍNH]: tính từ dữ liệu trong repo (lệnh hoặc file nguồn ghi kèm).
- [THAM KHẢO]: tài liệu bên ngoài, danh sách ở mục 7.
- [SUY RA]: lập luận từ thiết kế đã chốt (config v1, `task5_decisions.md`, `analysis_plan.md`).
- [CONFIG]: giá trị đã đóng băng trong `config/experiment_config.json` v1.

Ràng buộc kế thừa từ Task 5 (không đổi trong tài liệu này):
- I3: pool chính thức phải phủ **≥ 1.000 bài** D_pool; `n_round = 200`, `n_cap = 1`, pool ≥ 5 × n_round [CONFIG; `task5_decisions.md` I3, #12].
- Teacher `Qwen/Qwen2.5-3B-Instruct` @aa8e725, K = 5, T = 0,7, tối đa 512 token, prompt v1 [CONFIG]. Giữ cặp mô hình (`task5_decisions.md` mục K).
- `generation_seed = 20261009 + problem_index × K + k`, `problem_index` = thứ tự dòng trong file input [CONFIG].
- Chấm đáp án bằng `scripts/answer_utils.py` (I1) [CONFIG].

---

## 0. Phát hiện khi chuẩn bị (ảnh hưởng tới các quyết định bên dưới)

Kiểm tra lại pool sơ bộ batch_100 bằng `answer_utils.py` [TÍNH]:

| File | Số trajectory | valid | invalid_format | invalid_answer | Bài không có lời giải đúng |
|---|---|---|---|---|---|
| `batch_100_teacher_raw.jsonl` (lần sinh đầu, seed đúng quy tắc 20261009–20261508) | 500 | 406 (81,2%) | 59 (11,8%) | 35 (7,0%) | **5/100** |
| `batch_100_teacher_verified.jsonl` (sau khi sinh lại) | 480 | 480 | 0 | 0 | 2/100 |

1. **98 trajectory không hợp lệ của batch_100 đã được sinh lại** bằng `regenerate_failed_trajectories*.py`, với seed lệch khỏi quy tắc (`seed + 100000 + index`, ví dụ 20361021) [TÍNH: 98 seed ngoài khoảng 20261009–20261508 trong `batch_100_teacher_raw_recovered_v2.jsonl`].
2. **Các lần sinh lại dùng prompt khác prompt v1.** `PROMPT_TEMPLATE` trong `regenerate_failed_trajectories_reviewed.py` thêm "Do not use Markdown headings", "In ANSWER, write only the final numeric answer"... trong khi config ghi prompt v1 = `generate_teacher_trajectories_batch.py:PROMPT_TEMPLATE` [TÍNH: so sánh hai template]. Trong 480 trajectory của pool sơ bộ, 78 trajectory đến từ các lần sinh lại này.
3. Vì vậy tỉ lệ 96% valid và "chỉ 2 bài không có lời giải đúng" của pool sơ bộ là **sau khi đã sinh lại có chọn lọc**. Tỉ lệ ở lần sinh đầu (đúng quy tắc, không sinh lại) là 81,2% trajectory valid và 5% bài không có lời giải đúng. Các ước lượng dưới đây dùng số của lần sinh đầu.
4. Trajectory invalid_format ở lần sinh đầu dài hơn hẳn (trung bình 386 token so với 238 token của trajectory valid; 21/59 chạm 512 token) và nhiều trường hợp dùng Markdown/LaTeX thay cho định dạng REASONING/ANSWER [TÍNH].
5. Qwen2.5-3B-Instruct có `generation_config` mặc định `top_p = 0.8`, `top_k = 20`, `repetition_penalty = 1.05` [THAM KHẢO R7]. Script sinh chỉ truyền `temperature`, nên HF `generate` **đã áp dụng ngầm** ba tham số này. Config v1 chỉ ghi `temperature = 0.7`.

Hệ quả: pool sơ bộ không phải là kết quả của đúng một quy trình (một prompt, một quy tắc seed, K = 5 lần sinh). Không ảnh hưởng tới Task 4 hay smoke test (đó là dữ liệu thăm dò và `L̄ = 227,13` đã đóng băng), nhưng ảnh hưởng tới việc tái sử dụng batch_100 trong pool chính thức (mục 4).

---

## 1. Chọn bao nhiêu câu mới và theo quy tắc nào

**T6-1 [ĐÃ CHỐT 2026-10-21]:**
- Ứng viên: D_pool trừ 100 bài batch_100, tức **6.868 bài** [TÍNH: `splits/d_pool_ids.txt` 6.968 dòng, batch_100 nằm trọn trong D_pool].
- Xáo trộn tất định: `random.Random(20261021).shuffle(sorted(ứng viên))`. Seed `pool_sample_seed = 20261021` (ngày chốt), khác `split_seed` và `generation_seed_base` để mỗi seed chỉ có một vai trò.
- Lấy **1.000 bài đầu tiên** của thứ tự đã xáo (không phải 920 như đề xuất trước đó, xem lý do).
- **Quy tắc bổ sung đặt trước:** sau khi chấm, nếu số bài có ít nhất 1 trajectory valid (toàn pool) < 1.000, lấy thêm **khối 100 bài tiếp theo** trong cùng thứ tự đã xáo, sinh và chấm, lặp đến khi đủ. Không chọn lại, không bỏ bài theo nội dung.
- Lưu toàn bộ thứ tự đã xáo (6.868 ID) vào `trajectory/pool/pool_v1_candidate_order.txt`, cùng SHA-256 trong manifest. Python version, seed và hash ghi trong manifest.

**Lý do:**
1. **Vì sao 1.000 chứ không phải 920 hay 900.** Với tỉ lệ bài không có lời giải đúng ở lần sinh đầu p₀ ≈ 5/100, khoảng tin cậy 95% Clopper–Pearson là [1,6%; 11,3%] [TÍNH; THAM KHẢO R5]. Số bài đủ điều kiện, tính cả 100 bài batch_100 (giả định 95 bài đủ điều kiện như lần sinh đầu) [TÍNH, phân phối nhị thức]:

   | Số bài mới | p₀ = 5% (ước lượng điểm) | p₀ = 11,3% (cận trên) |
   |---|---|---|
   | 920 | kỳ vọng 969; P(≥ 1.000) ≈ 0 | kỳ vọng 911 |
   | 1.000 | kỳ vọng 1.045; P(≥ 1.000) ≈ 1 | kỳ vọng 982; P(≥ 1.000) ≈ 0,04 |
   | 1.100 | kỳ vọng 1.140 | kỳ vọng 1.071; P(≥ 1.000) ≈ 1 |

   920 bài gần như chắc chắn **không đủ** 1.000 bài đủ điều kiện. 1.000 bài đủ với ước lượng điểm; trường hợp xấu được che bằng quy tắc bổ sung theo khối, nên không cần sinh dư từ đầu. Chênh lệch chi phí giữa 920 và 1.000 bài chỉ là 400 lượt sinh.
2. **Lấy mẫu ngẫu nhiên đơn giản, không phân tầng.** Capability chỉ có sau khi sinh (extractor chạy trên trajectory), nên không thể phân tầng theo capability trước khi sinh mà không dùng thông tin từ chính kết quả cần đo. Lấy mẫu ngẫu nhiên giữ pool đại diện cho phân bố GSM8K train [SUY RA].
3. **Xáo toàn bộ một lần rồi lấy tiền tố** (thay vì `sample(1000)`) để khối bổ sung là phần tiếp theo của cùng một thứ tự đã định trước. Quy tắc dừng chỉ phụ thuộc *số lượng* bài đủ điều kiện, không phụ thuộc bài nào khó hay dễ, nên không gây thiên lệch chọn bài [SUY RA].
4. **Lưu danh sách và hash** vì thuật toán `random` có thể đổi giữa các phiên bản Python; danh sách đã lưu mới là nguồn chuẩn, script chỉ dùng để tái tạo và kiểm tra [SUY RA; cùng cách làm với `splits/` ở Task 5].
5. Pool lớn hơn 5 × n_round đúng như ràng buộc #12 (pool lớn hơn khoảng 3–5 lần n_round để selection có nhiều lựa chọn) [CONFIG].

## 2. Seed sinh: đánh số tiếp từ index 100

**T6-2 [ĐÃ CHỐT 2026-10-21]:**
- Tạo một file input chuẩn `trajectory/pool/pool_v1_input.jsonl` gồm **100 bài batch_100 (giữ thứ tự cũ, index 0–99), tiếp theo là 1.000 bài mới theo thứ tự đã xáo (index 100–1.099)**, và các khối bổ sung nếu có (index 1.100 trở đi).
- Seed tính đúng công thức trong config: `20261009 + problem_index × 5 + k`. Bài mới dùng seed 20.261.509 – 20.266.508, không trùng seed nào của batch_100 (20.261.009 – 20.261.508).
- Script sinh nhận `--start-index` (hoặc đọc thẳng file input chuẩn) để chỉ sinh các dòng cần sinh mà vẫn giữ `problem_index` toàn cục.

**Lý do:**
1. **Không cần đổi config.** Config định nghĩa `problem_index` là thứ tự dòng trong file input. Coi `pool_v1_input.jsonl` là file input duy nhất của pool chính thức thì quy tắc giữ nguyên chữ, chỉ cần ghi rõ file nào là input [SUY RA].
2. **Mỗi trajectory có seed riêng, truy được ngược** từ `(problem_index, k)`, nên tái tạo hoặc kiểm tra một trajectory bất kỳ không cần đọc lại log chạy [SUY RA].
3. Nếu file mới bắt đầu lại từ index 0 thì bài mới dùng lại đúng các seed của batch_100. Không sai về thống kê, nhưng phá tính "một seed, một trajectory" và dễ nhầm khi đối chiếu [SUY RA].
4. Thứ tự batch_100 giữ nguyên để seed của các trajectory batch_100 đã có vẫn khớp công thức (402 trajectory của lần sinh đầu đã đúng quy tắc) [TÍNH].

## 3. Bài không có lời giải đúng sau K = 5 lần sinh: loại

**T6-3 [ĐÃ CHỐT 2026-10-21]:**
- **Không sinh thêm** cho bài nào. Mỗi bài đúng K = 5 lần sinh, một lần, một prompt.
- Bài không có trajectory valid nào: **giữ trong file raw và báo cáo, không đưa vào tập eligible** của pool. Ghi danh sách và số lượng trong `reports/task6/pool_report.md`.
- Trajectory invalid_format và invalid_answer cũng giữ trong raw, chỉ trajectory `valid` là eligible (đúng định nghĩa eligible đã có).
- Không dùng các trajectory sinh lại của batch_100 (mục 4).

**Lý do:**
1. **Giữ ngân sách sinh β_gen = K = 5 như nhau cho mọi bài** [CONFIG: β_gen]. Sinh thêm chỉ cho bài thất bại là cấp thêm ngân sách có điều kiện theo kết quả, làm bài khó có nhiều lượt thử hơn bài dễ và lệch phân bố của pool [SUY RA].
2. **Thống nhất với cách làm phổ biến khi lọc lời giải đúng.** Rejection sampling fine-tuning (RFT) sinh nhiều lời giải rồi chỉ giữ lời giải đúng làm dữ liệu huấn luyện; bài không có lời giải đúng không đóng góp dữ liệu [THAM KHẢO R2]. STaR cũng chỉ huấn luyện trên lời giải đúng; với bài trả lời sai, STaR dùng "rationalization" (sinh lại khi đã cho biết đáp án) [THAM KHẢO R3]. Dự án không dùng rationalization vì lời giải sinh khi đã biết đáp án là một phân phối khác với lời giải Teacher tự sinh, và vì nó chính là "sinh thêm có điều kiện" ở lý do 1.
3. **Không ảnh hưởng tới selection.** Với `n_cap = 1`, bài không có trajectory valid vốn không thể được chọn; loại bài chỉ làm giảm số bài eligible, và đã được bù bằng mục 1 [SUY RA].
4. **Đã lường trước số lượng:** khoảng 5% bài, tức khoảng 50–55 trên 1.100 bài [TÍNH, mục 0].

**Giới hạn cần ghi trong báo cáo:** loại các bài Teacher không giải được làm pool thiếu nhóm bài khó nhất. Đây là giới hạn chung của mọi phương pháp chưng cất có lọc theo đáp án, và áp dụng như nhau cho mọi phương pháp B0–B6 nên không làm lệch so sánh B5 với B4 [SUY RA].

## 4. Tái sử dụng batch_100

**T6-4 [ĐÃ CHỐT 2026-10-21]:** **sinh lại cả 100 bài batch_100 (500 trajectory) trong pipeline mới** (index 0–99, đúng seed cũ theo công thức), cùng backend, prompt và tham số với 1.000 bài mới. Pool sơ bộ cũ giữ nguyên, không ghi đè, chỉ dùng làm dữ liệu lịch sử của Task 4 và smoke test.

Phương án thay thế (không dùng, vì đã chọn vLLM ở mục 5): dùng lại **chỉ lần sinh đầu** `batch_100_teacher_raw.jsonl` (500 trajectory, prompt v1, seed đúng quy tắc), chấm lại bằng `answer_utils.py`; **không** dùng 98 trajectory sinh lại.

**Lý do:**
1. 78 trajectory trong pool sơ bộ được sinh bằng prompt khác prompt v1 và sau khi đã sinh lại có chọn lọc (mục 0). Đưa chúng vào pool chính thức vi phạm cả quy tắc prompt v1 lẫn quyết định 3 [TÍNH; SUY RA].
2. Sinh lại 100 bài chỉ tốn thêm 500 lượt sinh (khoảng 10% tổng), đổi lại pool chính thức đến từ **đúng một quy trình**: một backend, một prompt, một quy tắc seed, cùng tham số lấy mẫu [SUY RA].
3. Nếu dùng vLLM (mục 5), 100 bài này còn là phép **kiểm tra tương đương** giữa vLLM và HF: so tỉ lệ valid, tỉ lệ sai định dạng và độ dài trung bình với lần sinh đầu bằng HF (406/500 valid, 59 invalid_format, valid dài trung bình 238 token) [SUY RA].
4. `Task.md` 1.1 trước đây ghi "tái sử dụng pool sơ bộ, không sinh lại". Kế hoạch đó được thay bằng T6-4 vì phát hiện ở mục 0 (đã xác nhận 2026-10-21). Đã cân nhắc và **không chọn** phương án chỉ sinh lại 98 trajectory lỗi: đó là sinh thêm có điều kiện cho trajectory thất bại (mâu thuẫn T6-3) và trộn HF với vLLM trong cùng một bài.

## 5. Backend sinh: vLLM, với tham số lấy mẫu khớp HF

**T6-5 [ĐÃ CHỐT 2026-10-21]:**
- Dùng **vLLM** (ghim phiên bản, ghi vào manifest), chạy offline (`LLM.generate`) trên GPU có bf16 (L4 hoặc A100), `dtype = bfloat16`, ghim `revision` của Teacher.
- `SamplingParams` khai báo **tường minh**: `temperature = 0.7`, `top_p = 0.8`, `top_k = 20`, `repetition_penalty = 1.05`, `max_tokens = 512`, `seed = generation_seed` riêng cho từng request, dừng tại token kết thúc lượt của chat template.
- Prompt dựng bằng cùng `build_prompt` (chat template + `PROMPT_TEMPLATE` v1) với HF; kiểm tra bằng `check_prompt_template()`.
- Đặt `VLLM_ENABLE_V1_MULTIPROCESSING=0` để lịch xử lý tất định [THAM KHẢO R6].
- **Tiêu chí chấp nhận** (đặt trước): trên 100 bài batch_100, tỉ lệ trajectory valid của vLLM không khác lần sinh đầu bằng HF (81,2%) quá 5 điểm % *và* độ dài trung bình của trajectory valid không lệch quá 10%. Không đạt thì dừng, kiểm tra tham số, hoặc chuyển sang phương án HF.
- Ghi bổ sung vào config v2 (cùng đợt cập nhật analysis plan): `top_p`, `top_k`, `repetition_penalty`, backend và phiên bản.

**Lý do:**
1. **Tốc độ.** Script hiện tại sinh từng lời giải một bằng HF `generate`. Ước tính từ đo đạc: đánh giá Teacher 500 câu greedy, batch 16 mất 65 phút trên T4 [TÍNH: `eval_T3B_dev.summary.json`], nên 5.500 lượt sinh kể cả khi chạy theo batch cũng khoảng 12 giờ, chạy tuần tự còn lâu hơn nhiều. vLLM dùng PagedAttention và continuous batching; bài báo gốc báo cáo throughput cao hơn 2–4 lần so với các hệ thống phục vụ tốt nhất lúc đó (FasterTransformer, Orca) ở cùng độ trễ [THAM KHẢO R4], và HF `generate` không tối ưu cho throughput bằng các hệ thống này. Ước tính cần đo lại: dưới 1 giờ cho 5.500 lượt trên L4.
2. **Tái lập được theo từng trajectory.** `SamplingParams` có `seed` riêng cho từng request [THAM KHẢO R6], nên vẫn giữ quy tắc "một trajectory, một seed" của config. Batch trong HF thì khó gán seed riêng cho từng mẫu (`set_seed` áp dụng cho cả batch).
3. **Bắt buộc khai báo tham số tường minh.** Mặc định của vLLM là `top_p = 1.0`, `top_k = 0` (tắt), `repetition_penalty = 1.0` [THAM KHẢO R6], khác với mặc định mà HF đã áp dụng ngầm cho batch_100 (mục 0, phát hiện 5). Không khai báo thì phân phối lấy mẫu sẽ khác, dù cùng `temperature`.
4. **Không chạy vLLM trên T4.** T4 không có bf16 gốc, vLLM sẽ chạy fp16; repo đã ghi nhận nên tránh fp16 với Qwen2.5 (notebook smoke test) [SUY RA từ ghi chú trong repo].

**Giới hạn cần ghi:**
- vLLM chỉ đảm bảo tái lập trên cùng phần cứng và cùng phiên bản vLLM [THAM KHẢO R6]. Cùng seed, vLLM và HF **không** cho ra cùng một lời giải; điều được giữ là phân phối lấy mẫu (cùng model, prompt, tham số).
- Nếu chọn phương án HF (ví dụ không có GPU bf16): sửa script để sinh theo batch, ghi nối tiếp, chạy tiếp được khi ngắt; khai báo tường minh `top_p`, `top_k`, `repetition_penalty` (giá trị như trên) để không phụ thuộc mặc định ngầm; dùng phương án thay thế ở mục 4.

## 6. Việc kỹ thuật kèm theo (không cần quyết định, cần làm)

Script sinh hiện tại (`generate_teacher_trajectories_batch.py`) phải sửa trước khi chạy, bất kể backend:

| Vấn đề | Hậu quả | Sửa |
|---|---|---|
| Mở output bằng `"w"` | Chạy lại sau khi Colab ngắt sẽ **xoá kết quả đã sinh** | Ghi nối tiếp, bỏ qua `trajectory_id` đã có |
| Chấm bằng `verify_answer` cũ | Lệch với `answer_utils.py` (I1) | Dùng `answer_utils.evaluate_output` |
| Không có `--revision` | Không tái lập được | Đọc model và revision từ config |
| Không có `--start-index` | Không sinh tiếp được theo index toàn cục | Thêm tham số, kiểm tra seed khớp công thức |
| Tham số lấy mẫu ngầm | Phụ thuộc `generation_config` của model | Khai báo tường minh |

Sau khi sinh: validate theo `teacher_trajectory_schema.json`, kiểm tra không có bài thuộc D_dev/D_test, chạy capability extractor (rules v2), thống kê token theo tokenizer Student (chỉ báo cáo; `L̄ = 227,13` và `beta_round` giữ nguyên theo I3), lưu `trajectory/pool/pool_v1_*.jsonl` kèm manifest SHA-256 và `reports/task6/pool_report.md`. Không ghi đè file nào của pool sơ bộ.

### Ghi chú triển khai (2026-10-21)

- **Nguồn câu hỏi:** `pool_v1_input.jsonl` lấy câu hỏi và đáp án từ `data/raw/gsm8k_train.jsonl` (bản đã chuẩn hoá khoảng trắng, cũng là nguồn của D_dev), cho cả 100 bài batch_100. Lần sinh đầu bằng HF đã dùng `data/batch_100/batch_100.jsonl`, trong đó 23/100 câu khác `gsm8k_train.jsonl` **chỉ ở khoảng trắng** (đáp án giống nhau) [TÍNH]. Phép kiểm tra tương đương (T6-5) vì vậy so trên prompt gần giống, không hoàn toàn giống từng ký tự; ghi nhận trong `reports/task6/parity_vllm_hf.json`.
- **Token dừng:** `stop_token_ids = [151643, 151645]` (`<|endoftext|>`, `<|im_end|>`), đúng tập `eos_token_id` trong `generation_config` của model mà HF đã dùng.
- **Đã tạo** (`make_pool_input.py`, 2026-10-21): `trajectory/pool/pool_v1_candidate_order.txt` (6.868 ID), `pool_v1_input.jsonl` (1.100 dòng, SHA-256 `60f7c38e…`), `pool_v1_input_manifest.json`. Kiểm tra: không bài nào thuộc D_dev/D_test, 1.100 ID khác nhau, seed của index 0 và 98 khớp lần sinh đầu (20261009, 20261499).
- Script và các bước chạy: `scripts/generate_teacher_vllm.py`, `scripts/compare_vllm_hf.py`, `scripts/setup_pod.sh`, `Instruction_task6.md` (thư mục gốc repo).

### Kết quả chạy (2026-10-21)

- **Bước A (T6-5):** 100 bài batch_100, 500 lượt, 68,5 giây trên L4. Kiểm tra tương đương **PASS**: valid 402/500 (vLLM) so với 406/500 (HF), lệch −0,8 điểm %; độ dài trung bình lời giải valid 237,2 so với 236,8 token (+0,2%). `reports/task6/parity_vllm_hf.json`, log `reports/task6/gen_0_100.log`.
- **Bước B:** 1.000 bài mới (index 100–1.099), 5.000 lượt, 499,3 giây. Cùng vLLM 0.32.0, torch 2.13.0+cu130, L4, config SHA `7c5aa72d…`, input SHA `60f7c38e…` (`pool_v1_teacher_raw.jsonl.run_100_1100.json`, log `reports/task6/gen_100_1100.log`).
- **Môi trường:** Bước B chạy trên pod khác pod Bước A (pod cũ mất GPU). Image mới thiếu gói `sniffio` cho venv (`--system-site-packages`), đã cài bổ sung; vLLM và torch nằm trong venv trên network volume nên giữ nguyên phiên bản. `setup_pod.sh` đã thêm bước import `vllm.LLM` để phát hiện lỗi này sớm.
- **Tổng hợp `pool_v1_teacher_raw.jsonl`** [TÍNH]: 5.500 trajectory, không trùng ID, 1.100 bài đều đủ K = 5, 0 lỗi seed/ID so với công thức; valid 4.355 (79,2%), invalid_format 730 (13,3%), invalid_answer 415 (7,5%); finish_reason `length` 168 (3,1%).
- **T6-1:** 1.032 bài có ít nhất 1 lời giải đúng (batch_100 94/100, bài mới 938/1.000) ≥ 1.000 → **không cần khối bổ sung**. **T6-3:** 68 bài bị loại (6,2%), nằm trong khoảng tin cậy dự kiến [1,6%; 11,3%].
- **Kiểm tra rò rỉ** (`scripts/check_pool_leak.py`, `reports/task6/leak_check.json`): **PASS**. File split khớp hash trong `split_manifest.json`; cả 1.100 bài thuộc D_pool, không bài nào thuộc D_dev, D_test hay danh sách near-duplicate; câu hỏi và đáp án khớp `gsm8k_train.jsonl`; 0 câu trùng nguyên văn và 0 câu chung 13-gram với D_dev/D_test. Đối chứng: cùng hàm phát hiện được 5/5 near-duplicate đã loại khi chia split.

### T6-6. Nguồn văn bản để trích C(τ): toàn bộ output [ĐÃ CHỐT 2026-10-21]

- **Phát hiện** [TÍNH]: khi chạy extractor rules v2 trên `reasoning_trace + answer` như Task 4, có 302/4.355 trajectory valid (6,9%) mà Teacher giải xong **trước** dòng `REASONING:`, sau dòng này chỉ còn đoạn tóm tắt bằng lời (hoặc nguyên mẫu `<step-by-step reasoning>`). Ở những trajectory này C(τ) thiếu phép tính: 191 trajectory có C(τ) khác, 29 trajectory rỗng hẳn, vi phạm `minItems: 1` của schema. Batch_100 cũng có hiện tượng này (26/402 trajectory valid lần sinh HF).
- **Quyết định:** trích C(τ) từ **toàn bộ output** (`raw_generation`). Đây cũng là văn bản Student được huấn luyện (`student_common.response_text`). Extractor thêm tham số `--source raw`; mặc định `--source reasoning` vẫn giữ nguyên hành vi Task 4.
- **Kiểm chứng trên batch_100** (480 trajectory, gold v2; `reports/task6/extractor_source_batch100.csv`): mặc định tái lập **giống từng byte** predictions chính thức `reports/task4_reruns/rulesv2_goldv2/`. Với `--source raw`, 13/480 trajectory đổi C(τ); F1 addition 0,867 → 0,878, subtraction 0,922 → 0,927, multiplication 0,912 → 0,920, division 0,876 → 0,876, percentage giữ 0,964, fraction 0,941 → 0,936 (+2 FP, −1 FN). Kết luận: không làm giảm chất lượng extractor đã báo cáo ở Task 4.
- **Kết quả trên pool** (`trajectory/pool/pool_v1_capability_predictions.jsonl`, 4.355 trajectory valid): addition 64,3%, subtraction 50,6%, multiplication 80,0%, division 40,8%, percentage 12,1%, fraction 19,0%, ratio 0,8%. Còn **2 trajectory rỗng C(τ)** (`gsm8k_train_05690_traj_001`: lời giải đại số `5n + 10(n + 4)`; `gsm8k_train_04410_traj_004`: phép cộng diễn đạt bằng lời), do giới hạn của rules, không phải do thiếu phép tính. Hai trajectory này không qua schema nên không vào `pool_v1_verified.jsonl`; hai bài vẫn còn 4 trajectory valid khác.

### Schema v2 và pool đã xác minh [ĐÃ CHỐT 2026-10-21]

- **Phát hiện:** `schemas/teacher_trajectory_schema.json` (v1) đặt `additionalProperties: false` với 8 trường, nên cấm `question`, `ground_truth`, `raw_generation`, trong khi huấn luyện Student cần `question` và `raw_generation` (`student_common.encode_example`). Pool sơ bộ cũng chưa từng qua schema này.
- **Quyết định:** giữ nguyên v1, tạo `schemas/teacher_trajectory_schema_v2.json`: bắt buộc thêm `question`, `ground_truth`, `raw_generation`; siết `verification_status = "valid"`, `generation_seed` bắt buộc, định dạng `problem_id`/`trajectory_id`, `capabilities` không rỗng và không trùng.
- **Tạo pool** (`scripts/build_pool_verified.py`): một trajectory vào pool khi được `answer_utils` chấm lại là valid (khớp trạng thái đã lưu: 5.500/5.500), có C(τ) và qua schema v2. Kết quả [TÍNH]: **`pool_v1_verified.jsonl` 4.353 trajectory, 1.032 bài eligible**; loại 730 invalid_format, 415 invalid_answer, 2 lỗi schema (C(τ) rỗng, xem T6-6), liệt kê từng dòng ở `pool_v1_excluded.jsonl`. Số trajectory valid mỗi bài: 5 → 623 bài, 4 → 179, 3 → 115, 2 → 62, 1 → 53. Manifest SHA-256: `pool_v1_manifest.json`.
- **Kiểm tra lại độc lập:** 0 lỗi schema v2; phần 8 trường của v1 cũng qua schema v1 (0 lỗi); ID không trùng; 0 bài thuộc D_dev/D_test.

### Thống kê pool (2026-10-21) [TÍNH]

Script: `scripts/pool_stats.py` → `reports/task6/pool_stats.json`; `scripts/measure_pool_tokens.py` (tokenizer Student @989aa79) → `reports/task6/pool_token_stats.json`.

- **Trạng thái:** batch_100 402 valid / 59 invalid_format / 39 invalid_answer; bài mới 3.953 / 671 / 376. Số trajectory valid mỗi bài (trước schema): 0 → 68 bài, 1 → 53, 2 → 62, 3 → 115, 4 → 177, 5 → 625.
- **68 bài bị loại (T6-3):** 6 batch_100, 62 bài mới. 14 bài sai đáp án cả 5 lần; 54 bài có ít nhất 1 trajectory invalid_format; **32 bài có ít nhất 1 trajectory đúng số cuối** nếu chấm nới (chỉ chẩn đoán). Lời giải ở các bài này dài hơn hẳn: trung bình 371 token Teacher so với 268 của toàn pool.
- **Capability (4.353 trajectory verified):** multiplication 80,0%, addition 64,3%, subtraction 50,6%, division 40,8%, fraction 19,0%, percentage 12,1%, ratio 0,8%. Theo bài (1.032 bài, capability xuất hiện ở ít nhất 1 trajectory): multiplication 82,9%, addition 69,8%, subtraction 56,1%, division 47,7%, fraction 21,7%, percentage 12,4%, ratio 1,8% (19 bài). Số capability mỗi trajectory: 1 → 342, 2 → 1.741, 3 → 1.463, 4 → 610, 5 → 184, 6 → 13. 311 bài có các trajectory với C(τ) khác nhau.
- **Độ dài (tokenizer Student, chỉ phần response):** trung bình 245,8 token, trung vị 232, IQR 187–288, tối đa 512; kèm prompt trung bình 376,1. Lời giải ngắn nhất mỗi bài (B3): trung bình 215,6. Cao hơn `L̄ = 227,13` của pool sơ bộ 8,2%; theo I3, `L̄` và `beta_round = 45.426` giữ nguyên, nên mỗi vòng sẽ chứa khoảng 185 thay vì 200 trajectory trung bình (ghi nhận, không đổi config).
- **invalid_format 730 (13,3%), xem kỹ:**
  - Nguyên nhân: thiếu dòng `REASONING:` nhưng có `ANSWER:` 403; bị cắt ở 512 token 157; `ANSWER:` đứng trước `REASONING:` 76; chỉ có `\boxed{}` 59; không có dòng đáp án 18; nhãn đáp án có định dạng (`**ANSWER**:`) 17.
  - **Không do vLLM:** trên cùng 500 lượt batch_100, HF và vLLM đều có đúng 59 invalid_format.
  - **Không khác giữa batch_100 và bài mới:** 11,8% so với 13,4%, kiểm định hai tỉ lệ p = 0,31.
  - **Phần lớn là lệch định dạng, không phải sai toán:** 496/730 (68%) có số cuối (hoặc `\boxed{}` cuối) đúng đáp án; riêng nhóm thiếu `REASONING:` là 352/403. Nhóm bị cắt ở 512 token gần như đều sai (25/157 đúng) và chiếm 157/168 trajectory chạm giới hạn.
  - 318 bài có ít nhất 1 trajectory invalid_format, phần lớn chỉ 1–2 trajectory.
  - **Hệ quả:** chấm nghiêm theo I1 giữ nguyên cho pool (Student chỉ học output đúng định dạng prompt v1). Hạn chế cần ghi trong báo cáo: pool hơi lệch về bài ngắn và bài Teacher giữ đúng định dạng; khoảng 32/68 bài bị loại là do định dạng hoặc độ dài chứ không phải Teacher không giải được. Độ chính xác nới (đã có trong kế hoạch cập nhật analysis plan) nên báo cáo kèm cho Teacher và Student.

---

## Tóm tắt quyết định

| # | Quyết định | Đề xuất | Trạng thái |
|---|---|---|---|
| T6-1 | Số bài mới, cách chọn | 1.000 bài, xáo tất định seed 20261021, lấy tiền tố; thiếu thì thêm khối 100 bài | **Đã chốt 2026-10-21** |
| T6-2 | Seed | File input chuẩn: batch_100 (index 0–99) + bài mới (index 100+); giữ nguyên công thức config | **Đã chốt 2026-10-21** |
| T6-3 | Bài không có lời giải đúng | Loại khỏi eligible, giữ trong raw, báo cáo; không sinh thêm | **Đã chốt 2026-10-21** |
| T6-4 | batch_100 | Sinh lại trong pipeline mới; không dùng 98 trajectory sinh lại bằng prompt khác | **Đã chốt 2026-10-21** |
| T6-5 | Backend | vLLM, bf16, tham số lấy mẫu tường minh khớp HF, kiểm tra tương đương trên batch_100 | **Đã chốt 2026-10-21** |
| T6-6 | Nguồn trích C(τ) | Toàn bộ output (`--source raw`), kiểm chứng trên gold v2 batch_100 | **Đã chốt 2026-10-21** (thêm sau khi sinh) |

Ước tính chi phí: khoảng 5.500 lượt sinh (1.100 bài × 5), cộng tối đa vài khối bổ sung.

## 7. Tài liệu tham khảo

- **R1.** Cobbe, K. et al. (2021). *Training Verifiers to Solve Math Word Problems.* arXiv:2110.14168. (Bộ dữ liệu GSM8K.)
- **R2.** Yuan, Z. et al. (2023). *Scaling Relationship on Learning Mathematical Reasoning with Large Language Models.* arXiv:2308.01825. (Rejection sampling fine-tuning: sinh nhiều lời giải, chỉ giữ lời giải đúng.)
- **R3.** Zelikman, E., Wu, Y., Mu, J., Goodman, N. D. (2022). *STaR: Bootstrapping Reasoning With Reasoning.* NeurIPS 2022, arXiv:2203.14465. (Chỉ huấn luyện trên rationale cho đáp án đúng; rationalization cho bài sai.)
- **R4.** Kwon, W. et al. (2023). *Efficient Memory Management for Large Language Model Serving with PagedAttention.* SOSP 2023, arXiv:2309.06180. (vLLM; throughput cao hơn 2–4 lần so với FasterTransformer và Orca.)
- **R5.** Clopper, C. J., Pearson, E. S. (1934). *The use of confidence or fiducial limits illustrated in the case of the binomial.* Biometrika 26(4), 404–413. (Khoảng tin cậy chính xác cho tỉ lệ nhị thức.)
- **R6.** vLLM documentation: *Reproducibility* (https://docs.vllm.ai/en/latest/usage/reproducibility.html) và *SamplingParams* (https://docs.vllm.ai/en/latest/api/vllm/sampling_params.html), truy cập 2026-10-21.
- **R7.** `generation_config.json` của `Qwen/Qwen2.5-3B-Instruct` tại revision aa8e72537993ba99e69dfaafa59ed015b17504d1 (https://huggingface.co/Qwen/Qwen2.5-3B-Instruct), truy cập 2026-10-21.

Lệnh tính lại các số [TÍNH] ở mục 0 và 1 (chạy tại `experiments/week2September/manual`, trong `.venv`):
```bash
python - <<'EOF'
import json, sys, collections
sys.path.insert(0, "scripts"); from answer_utils import evaluate_output
v = [json.loads(l) for l in open("trajectory/pool/batch_100_teacher_raw.jsonl")]
st = collections.Counter(evaluate_output(r["raw_generation"], r["ground_truth"]) for r in v)
ok = {r["problem_id"] for r in v if evaluate_output(r["raw_generation"], r["ground_truth"]) == "valid"}
print(dict(st), "bài không có lời giải đúng:", 100 - len(ok))
from scipy.stats import beta, binom
print("Clopper-Pearson 95%:", beta.ppf(0.025, 5, 96), beta.ppf(0.975, 6, 95))
for n in (920, 1000, 1100):
    for p in (0.05, 0.113):
        print(n, p, "P(>=1000 eligible) =", 1 - binom.cdf(1000 - 95 - 1, n, 1 - p))
EOF
```
