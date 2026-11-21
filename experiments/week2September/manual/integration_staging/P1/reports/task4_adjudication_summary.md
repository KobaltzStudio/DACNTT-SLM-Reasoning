# Task 4: Adjudication, độ tin cậy nhãn, kết luận gold/rules

> **Cập nhật 2026-10-12 (lần 2):** D1-D3 đã chốt, rules v2 (A+B) đã duyệt, gold v2 đã tạo và extractor đã chạy lại. Các mục 2, 3, 5 bên dưới là trạng thái *trước* khi chốt. Trạng thái hiện tại và lý do: `../task4_decisions.md`; số liệu: `task4_reruns/metrics_summary.csv`.

Ngày: 2026-10-12. Làm theo README.txt mục 3 (Bước 4.1-4.9) và mục 4 (4.1-4.3).
Phạm vi: 480 trajectory hợp lệ của batch_100, gold cấp problem.

Nhãn nguồn: [TRÍCH] lấy nguyên từ file · [TÍNH] tính lại từ dữ liệu trong repo · [SUY RA] kết luận từ việc đọc trace/guideline.

## 1. README mục 3: Manual adjudication

| Bước | Kết quả | Nguồn |
|---|---|---|
| 4.1 Xác minh file | Đủ file nguồn; raw có 10 trường như README mô tả | [TÍNH] |
| 4.2 Số case | 34 = 32 division + 2 ratio | [TÍNH] `error_analysis/adjudication_review_cases.csv` |
| 4.3 Đọc trace | Đọc đủ 5 trajectory hợp lệ của mỗi bài | [TÍNH] `trajectory/pool/batch_100_teacher_verified.jsonl` |
| 4.4 Định nghĩa | Gold = capability bài cần (guideline Rule 1, Procedure Step 2); `per` và `proportion` không đủ để gán; phân số làm hệ số nhân là fraction (Rule 3); quy đổi % là percentage (Rule 5) | [TRÍCH] `config/guideline_v2.md` |
| 4.5-4.6 Điền + kiểm tra | 34 dòng; 27 reviewed, 7 needs_discussion, 0 pending; không thiếu trường, không trùng, enum hợp lệ | [TÍNH] `scripts/validate_manual_adjudication.py` → PASS |
| 4.7 Backup + hash | 5 file baseline + `SHA256SUMS.txt`; 7/7 OK, baseline không bị ghi đè | `error_analysis/baseline_backup/` |
| 4.8 Số FP division | CSV 113 dòng = 113 trajectory = FP 113 trong report; không có sai lệch | [TÍNH] |
| 4.9 Sau adjudicate | Không sửa gold, không áp dụng rule. Đề xuất sửa rule lưu riêng, chờ duyệt | Mục 3 bên dưới |

Input của baseline [TÍNH]: `recovered_v2` → `prepare_task4_trajectory_input.py` → `verified` (480 trajectory), tái lập được giống từng byte. Lưu ý cho lần chạy lại theo Bước 4.9: runner mặc định đọc `batch_100_teacher_raw.jsonl`, file này chỉ cho 402 trajectory, nên phải truyền `--raw trajectory/pool/batch_100_teacher_raw_recovered_v2.jsonl`. Runner hiện cũng chưa có tham số nhận file rules và luôn ghi vào đường dẫn baseline report.

### Kết quả adjudication

| Adjudication | Decision | Số case | Problem |
|---|---|---|---|
| FALSE_LEXICAL_TRIGGER: `per` (đơn vị tỉ suất) | PROPOSE_RULE_CHANGE | 17 | 00015, 00021, 00042, 00048, 00057, 00058, 00061, 00064, 00065, 00079, 00080, 00084, 00085, 00088, 00090, 00096, 00099 |
| FALSE_LEXICAL_TRIGGER: phân số/% làm hệ số nhân | PROPOSE_RULE_CHANGE | 9 | 00007, 00016, 00022, 00027, 00030, 00032, 00035, 00063, 00067 |
| FALSE_LEXICAL_TRIGGER: ratio do `proportion of` | PROPOSE_RULE_CHANGE | 1 | 00087 |
| DEFINITION_AMBIGUITY: D1 (`half of N` viết thành `N / 2`) | NEEDS_DISCUSSION | 4 | 00006, 00041, 00049, 00072 |
| DEFINITION_AMBIGUITY: D2 (ratio 5:4) | NEEDS_DISCUSSION | 1 | 00089 |
| DEFINITION_AMBIGUITY: D3 (trace dùng phép chia mà bài không cần) | NEEDS_DISCUSSION | 2 | 00071, 00097 |
| TRUE_CAPABILITY_OMITTED_FROM_GOLD | - | 0 | - |

Case 00087 khác case mẫu trong README (README gợi ý DEFINITION_AMBIGUITY). Lý do: guideline Rule 6 (dòng 307) đã loại trừ rõ trường hợp "division as ordinary arithmetic". README cho phép cập nhật khi có bằng chứng.

## 2. Metrics chính thức

Giữ nguyên baseline, vì gold không đổi và rule chưa được duyệt [TRÍCH] `reports/capability_extractor_batch100_report.json`: division P/R/F1 = 0.6534 / 0.9771 / 0.7831 (TP 213, FP 113, FN 5); ratio N/A (FP 2).

## 3. Đề xuất sửa rule (CHƯA duyệt, CHƯA áp dụng)

Thư mục: `reports/error_analysis/rule_change_proposal/`. `config/capability_rules_v1.json` không đổi.

| Phần | Thay đổi | Căn cứ |
|---|---|---|
| A (không phụ thuộc D1) | division rule_2: bỏ `per`; thêm rule_3 cho dạng "số + đơn vị / số" (`210 points / 5 games`); ratio: `proportion of` không còn kích hoạt | 17 case `per`, 00087 |
| B (liên quan D1) | division rule_1: bỏ qua `a / b` khi đứng trước/sau times/x/*/of (`2 / 5 times 400`, `10 / 100 times 40`); hỗ trợ `480,000 / 240` | 9 case phân số/%, guideline Rule 3 và Rule 5 |

Chạy thử (dry-run, chỉ để làm căn cứ duyệt; output không lưu vào repo) [TÍNH]:

| Division | P | R | F1 | TP/FP/FN |
|---|---|---|---|---|
| Baseline v1 | 0.6534 | 0.9771 | 0.7831 | 213 / 113 / 5 |
| Đề xuất A | 0.7889 | 0.9771 | 0.8730 | 213 / 57 / 5 |
| Đề xuất A+B | 0.8661 | 0.9495 | 0.9059 | 207 / 32 / 11 |

Ratio: FP 2 → 1 ở cả A và A+B. 5 capability còn lại không đổi.
- Phần A không làm mất TP nào.
- Phần B mất 7 TP và thêm 1 TP. 6 trong số TP bị mất là 00000 và 00074 (`1 / 3 times N`), hai bài mà gold gán division cho "one-third of N", tức chính là D1. TP mất còn lại (00060_traj_005) là trace không có phép chia nào. TP thêm là 00010_traj_001 (`10 pounds / 5`).
- Unit test: `test_rules_v2_proposed.py partA` → PASS 38; `partAB` → PASS 44; test v1 → PASS 28.

Sau khi được duyệt (README 4.9): đưa file đã duyệt vào `config/`, chạy lại trên cùng 480 trajectory với `--raw` đúng, và lưu report riêng, không ghi đè baseline.

## 4. README mục 4: Annotation tồn đọng

| Mục | Kết quả | Nguồn |
|---|---|---|
| 4.1 Pilot A2 + kappa | Tính lại độc lập: kappa = 1.0 cho 6 capability, ratio N/A (0 dương ở cả hai), khớp report. A1/A2 là hai file riêng, notes khác nhau. Không có bất đồng nên không cần sửa guideline (ngưỡng kappa < 0.6) | [TÍNH] `reports/agreement_report.json` |
| 4.2 Supplement | `validate_annotation.py`: VALID 85 record; 85 problem, không trùng batch_100/pilot; ratio 30, percentage 29, fraction 31 (đều đạt kỳ vọng > 0, > 12, > 18) | [TÍNH] `reports/supplement_coverage_report.json` |
| 4.3 Ambiguous | Đã đối chiếu cả 5 bài với GSM8K gốc (Hugging Face `openai/gsm8k`, theo source_index); mỗi record được bổ sung rationale, evidence, verification_source; 00073 được ghi rõ cách hiểu (×4 → 58); `check_ambiguous_cases.py` → PASS | [TÍNH] `data/issues/ambiguous_cases.jsonl` |

Chi tiết 4.3 [SUY RA]: ground truth 50 của 00056 là nhãn gốc của GSM8K. Lời giải tham chiếu của GSM8K tính cho "200 cookies" và bỏ qua chữ "dozen", nên nhãn này mâu thuẫn với đề bài (theo nghĩa đen phải là 600). Không sửa ground truth vì đó là nhãn nguồn; việc có loại bài này khỏi split hay không thuộc Task 5.

Giới hạn về độ tin cậy nhãn [SUY RA]: kappa = 1.0 không phát hiện được D1. Cả A1 và A2 đều gán 00004 có division và 00006 không có, cho cùng một dạng "half of N".

## 5. Cần quyết định (NEEDS_DISCUSSION, 7 case)

- **D1**: `half/one-third of N` có gán division không? Gold đang mâu thuẫn: 00000, 00004, 00043, 00059, 00066, 00074 có division; 00006, 00041, 00049, 00072 không có. Guideline mục 4 cũng tự mâu thuẫn ([TRÍCH] dòng 168-206). Nếu chọn gán division, đề xuất A+B đạt F1 = 0.9434 (dry-run với gold giả định).
- **D2**: 00089 ("ăn 1 trong mỗi 5 quả") có tính là ratio không?
- **D3**: khi trace dùng phép chia mà bài không cần (00071, 00097), nên tính trajectory đó như thế nào khi chấm với gold cấp problem?
- **Duyệt đề xuất sửa rule**: phần A, phần B, hay cả hai.

## 6. Cách tái lập

```bash
cd experiments/week2September/manual
python3 scripts/test_capability_extractor.py
python3 scripts/validate_manual_adjudication.py
python3 scripts/check_ambiguous_cases.py data/issues/ambiguous_cases.jsonl
sha256sum -c reports/error_analysis/baseline_backup/SHA256SUMS.txt
python3 reports/error_analysis/rule_change_proposal/test_rules_v2_proposed.py partA
python3 reports/error_analysis/rule_change_proposal/test_rules_v2_proposed.py partAB
```
