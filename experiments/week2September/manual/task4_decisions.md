# Task 4 — Các quyết định đã đưa ra và lý do

Ngày: 2026-10-12. Người quyết định: Claude (theo yêu cầu "hoàn tất luôn Task 4" của chủ dự án).
Phạm vi: các việc còn mở trong `task4_todo.txt`. File này ghi **quyết định gì, vì sao, đổi file nào**.
Mọi quyết định đều có thể đảo ngược: bản cũ (gold v1, rules v1, guideline v2, baseline report) được giữ nguyên.

Nhãn nguồn: [TRÍCH] lấy nguyên từ file · [TÍNH] tính lại trong phiên này · [SUY RA] kết luận từ việc đọc đề/trace/guideline.

## Tóm tắt

| # | Vấn đề | Quyết định | Ảnh hưởng |
|---|---|---|---|
| D1 | "half / one-third of N" có gán `division` không | **Không.** Lấy phân số của một đại lượng chỉ là `fraction`, bất kể viết `N / k` hay `1/k × N` | Gold: bỏ `division` ở 5 bài batch_100 (00000, 00004, 00059, 00066, 00074) và 1 bài supplement (02893). 4 case D1 → `KEEP_GOLD` |
| D2 | 00089 có tính là `ratio` không | **Không.** Bài chỉ cần `60 / 4 = 15` nắm | Gold giữ nguyên; FP của traj 002 tính là FP do lộ trình trace |
| D3 | Trace dùng phép chia mà bài không cần (00071, 00097) | **Gold giữ ở cấp bài**; báo cáo riêng loại FP này | Gold giữ nguyên |
| R | Duyệt đề xuất rule v2 | **Duyệt phần A + B** → `config/capability_rules_v2.json` | Division F1 chính thức 0.7831 → 0.8756 |
| A2 | A2 có annotate độc lập không | **Chưa giải quyết được (BLOCKED)**: cần hỏi người annotate A2 | Kappa = 1.0 được ghi là chưa đáng tin |

## D1 — Phân số của một đại lượng

**Quyết định:** "half of N", "one-third of N", "1/4 the height of N" chỉ gán `fraction`. Chỉ gán `division` khi bài cần một phép chia riêng: chia đều, tìm số nhóm, tìm đơn giá/tỉ suất từ tổng, phép ngược (tìm tổng từ một phần, giải `11x = 286`), hoặc so sánh phần/tổng.

**Lý do:**
1. Gold hiện tại tự mâu thuẫn [TÍNH]. Trong 12 bài dạng "phân số của N" ở batch_100:
   - 7 bài không gán division: 00006, 00041, 00049, 00072, 00022, 00030, 00063;
   - 5 bài có gán: 00000, 00004, 00059, 00066, 00074.
   
   Quyết định theo phía đa số nên phải sửa ít gold hơn.
2. Guideline v2 tự mâu thuẫn [TRÍCH]. Calibration case 00004 ("half", `50 / 2`) cho gán cả fraction và division; case 00006 ("half" của 50) thì không. Hai bài cùng dạng "half of 50". Rule 3 lại viết: *"do not add `division` merely because a fraction could theoretically be represented using division"*. Quyết định này giữ Rule 3 và bỏ ngoại lệ 00004.
3. Lựa chọn khác là lấy cách viết trong lời giải gốc GSM8K làm chuẩn, tức thấy `N / k` thì gán division. Đây là gợi ý trước đó của tôi, nhưng tôi đã bỏ sau khi rà toàn bộ [TÍNH]. Lời giải gốc dùng ký hiệu tùy tiện: bài 00022 viết `572 x 1/4` và `286/2` cho cùng một loại bước. Nếu theo cách viết, phải sửa 9 gold, trong đó đảo ngược 3 case đã reviewed (00022, 00030, 00063), và nhãn phụ thuộc vào thói quen viết của người soạn GSM8K chứ không phụ thuộc capability.
4. Rule 1 của guideline gán theo capability mà bài **cần**. "Half of 50" cần hiểu phân số. Việc tính bằng `÷ 2` hay `× 0.5` là cách tính, không phải một capability riêng.

**Kiểm tra từng bài gold có division mà đề có từ chỉ phân số hoặc % [SUY RA]:**

| Bài | Đề cần gì | Division |
|---|---|---|
| 00000 | "one-third of the shells" | **bỏ** |
| 00004 | "half the full hike distance" | **bỏ** |
| 00059 | "half the height", "1/4 the height" | **bỏ** |
| 00066 | "sold half of the remaining" | **bỏ** |
| 00074 | "a third of her 9 cupcakes" | **bỏ** |
| 00043 | "splits it evenly with his roommate" | giữ (chia đều) |
| 00017 | 300 / 25: số coin cần bán | giữ (số nhóm) |
| 00054 | 18 / 1.5: số ly | giữ (số nhóm) |
| 00005, 00014, 00076 | "equal number", "split evenly", "divided evenly" | giữ (chia đều) |
| 00011 | 104 / 0.65: tìm tổng | giữ (phép ngược) |
| 00025 | 40 / 80: "what percentage of her life" | giữ (phần/tổng) |
| 00056, 00078, 00087 | số nhóm | giữ |

Kiểm tra thêm: 00068 (`6/3` = giá mỗi cuốn) và 00023 (`11x = 286`) là đơn giá và phép ngược nên giữ division. 00090 (`6/2` = "every other day") là đếm, không cần chia; gold không có division nên giữ nguyên.

**File thay đổi:**
- `config/guideline_v3.md` (mới; v2 giữ nguyên): mục "Changes from v2", Rule 2 Division (5 trường hợp cần chia), Rule 3 Fraction + Division (00043 là ví dụ đúng, 00004 là phản ví dụ), sửa calibration case 00004.
- `data/batch_100/batch_100_annotations_v2.jsonl` (mới; v1 giữ nguyên): bỏ `division` ở 5 bài, ghi lý do vào `notes`. `validate_annotation.py` → VALID 100.
- `data/supplement/supplement_annotations_v2.jsonl` (mới; bản cũ giữ nguyên): bỏ `division` ở 02893 ("1/3 of the schools", "half of the schools"). `validate_annotation.py` → VALID 85. Đây là bài duy nhất trong 85 bài supplement bị ảnh hưởng; 10 bài supplement khác có cả fraction và division đều cần chia thật (tìm tổng từ một phần, chia nhóm, chia theo tỉ lệ).
- `reports/error_analysis/gold_change_log.csv`: 6 dòng audit (trước, sau, lý do, căn cứ, ngày).
- `reports/supplement_coverage_report.json`: thêm khối `positive_counts_gold_v2`. Division: batch_100 47 → 42, supplement 48 → 47; ratio/percentage/fraction không đổi.
- `manual_adjudication.csv`: 00006, 00041, 00049, 00072 → `FALSE_LEXICAL_TRIGGER` / `KEEP_GOLD` / `reviewed`. Rule bắt toán tử `N / k`, nhưng theo định nghĩa v3 đây không phải capability division.

**Không sửa:** `data/pilot/pilot_30_annotations*.jsonl`, vì đó là bản ghi gốc của từng annotator. Trong pilot, A1 và A2 đều gán division cho 00000 và 00004; gold v2 khác pilot ở 2 bài này và đã ghi trong gold_change_log.

## D2 — 00089 không gán ratio

**Quyết định:** giữ gold `[division, multiplication]`, đổi dòng 00089/ratio sang `KEEP_GOLD` / `reviewed`.

**Lý do [SUY RA]:** đề "cứ mỗi nắm 5 quả thì ăn 1" giải được bằng `5 - 1 = 4` quả mỗi nắm, rồi `60 / 4 = 15` nắm, `15 × 5 = 75`. Đây là phép tính thông thường; Rule 6 ghi rõ *"can be solved using ordinary arithmetic without ratio reasoning"* thì không gán ratio. Lời giải gốc GSM8K và 4/5 trajectory giải đúng cách này. Riêng traj 002 chọn cách tỉ lệ (`60 × 5 / 4`), nên extractor đọc đúng trace đó; FP này là do lộ trình của trace, không phải lỗi gold.

Nhãn adjudication giữ `DEFINITION_AMBIGUITY`: bản chất case là câu hỏi gold thuộc cấp nào, nay đã chốt. README chỉ cho 3 giá trị nên không thêm enum mới.

## D3 — Gold giữ ở cấp bài

**Quyết định:** gold ghi capability bài **cần**, không ghi mọi phép tính một trace dùng. Khi trace dùng thêm phép tính không cần thiết, giữ gold và báo cáo riêng loại FP này. Đã thêm vào guideline_v3 mục 15.

**Lý do:**
- 00097: `60 hoa/ngày × 6 ngày = 360` là đủ; "5 giờ/ngày" là thông tin gây nhiễu. Trace (và cả lời giải gốc) tính `60 / 5 = 12 hoa/giờ` là đi đường vòng.
- 00071: "lớn nhanh gấp đôi" → `(36 − 24) × 2 = 24`. Riêng traj 003 đặt tốc độ `12 / t` rồi triệt tiêu.
- Phương án gán nhãn cấp trajectory phải gán tay khoảng 480 trace, quá tốn so với lợi ích ở bước này. Nên làm sau nếu Đề xuất 2 thực sự cần capability theo từng trajectory.

## R — Duyệt rule v2 (phần A + B)

**Quyết định:** duyệt cả phần A và B, đưa vào `config/capability_rules_v2.json`. Bản này giống hệt đề xuất `partAB` trừ `schema_version` và `notes`; `scripts/test_capability_rules_v2.py` kiểm tra điều này qua 44 unit case.

**Lý do:**
- Phần A (bỏ `per`, thêm rule cho dạng `210 points / 5 games`, ratio bỏ qua `proportion of`): đúng với 18 case đã adjudicate và không mất TP.
- Phần B (bỏ `a / b` khi là hệ số nhân, như `2 / 5 times 400`): trước đây tôi đề xuất hoãn vì làm mất TP ở 00000 và 00074. Với quyết định D1, hai bài này không còn division trong gold, nên các "TP bị mất" thực ra là dự đoán đúng. Phần B nay khớp với guideline_v3.

**Kết quả chạy lại** trên đúng 480 trajectory (`--raw trajectory/pool/batch_100_teacher_raw_recovered_v2.jsonl`) [TÍNH], xem `reports/task4_reruns/metrics_summary.csv`:

| Lần chạy | Mục đích | Division P / R / F1 | TP/FP/FN | Micro F1 (7 cap) |
|---|---|---|---|---|
| rules v1 + gold v1 | tái lập baseline | 0.6534 / 0.9771 / 0.7831 | 213/113/5 | 0.8811 |
| rules v1 + gold v2 | chỉ đổi gold | 0.5828 / 0.9744 / 0.7294 | 190/136/5 | 0.8710 |
| rules v2 + gold v1 | chỉ đổi rule | 0.8661 / 0.9495 / 0.9059 | 207/32/11 | 0.9075 |
| **rules v2 + gold v2** | **kết quả chính thức** | **0.7950 / 0.9744 / 0.8756** | **190/49/5** | **0.9022** |

- Ratio: FP 2 → 1 (chỉ còn 00089 traj 002). 5 capability còn lại không đổi.
- Lần chạy rules v1 + gold v1 cho JSON report, predictions và input giống baseline từng byte. CSV khác hash chỉ vì ký tự xuống dòng; nội dung giống hệt. Runner sửa đúng.
- **Đổi gold làm F1 đo được giảm** (0.7831 → 0.7294 khi giữ rules v1). Đây là hệ quả đúng của việc làm gold nhất quán, không phải lỗi. Theo README 4.9, cải thiện của extractor phải đọc ở cột "chỉ đổi rule" hoặc so trên cùng gold: với gold v2, F1 tăng từ 0.7294 lên 0.8756 và FN vẫn là 5.

**49 FP division còn lại** (rules v2 + gold v2) [TÍNH]:

| Loại | Số FP | Bài |
|---|---|---|
| Phân số của N viết thành `N / k` | 38 | 00000, 00004, 00006, 00022, 00030, 00041, 00049, 00059, 00063, 00066, 00072 |
| Phép tính phân số/% viết bằng `/` (`6 / 4 = 3 / 2`, `20 / 2` cho 50%) | 8 | 00007, 00016, 00067 |
| Trace đi đường vòng (D3) | 3 | 00071, 00097 |

Nhóm 38 FP không sửa được bằng regex trên trace, vì `50 / 2` trong "half of that is 50 / 2" và trong "split between 2" giống hệt nhau. Muốn xử lý cần đọc thêm ngữ cảnh đề bài, nên tôi để thành hướng cải tiến, không sửa vội trong Task 4.

## A2 — Chưa giải quyết được (BLOCKED)

`pilot_30_annotations_A2.jsonl` trùng A1 30/30 cả danh sách capability (kể cả thứ tự) và difficulty; chỉ khác phần `notes` [TÍNH]. Không thể xác minh A2 có annotate độc lập không nếu không hỏi người làm. Tôi không tự tạo nhãn A2 vì như vậy là giả mạo nhãn người.

Cần làm:
1. Hỏi người annotate A2.
2. Nếu A2 không độc lập: một người khác annotate lại 30 bài mà không xem A1, nên thêm các bài dạng "half of N" (00006, 00041, 00049, 00072, 00004, 00059) và dùng guideline_v3.
3. Chạy `scripts/calculate_annotation_agreement.py --a1 ... --a2 ...`.

Ngoài ra, supplement (85 bài) chỉ có A1 annotate; đây là giới hạn.

## Các sửa nhỏ khác

- `scripts/run_task4_extractor_batch100.py`: thêm `--rules` và `--tag`. Có `--tag` thì mọi output ghi vào `reports/task4_reruns/<tag>/`, không đụng baseline. Không truyền gì thì chạy như cũ.
- `reports/error_analysis/baseline_backup/SHA256SUMS_ambiguous_cases.txt`: trỏ sang `ambiguous_cases_before.jsonl`, nên `sha256sum -c` giờ ra OK thay vì luôn FAILED.
- `reports/task4_reruns/SHA256SUMS.txt`: manifest cho guideline v3, rules v2, gold v2, change log, adjudication, input và 4 lần chạy lại.
- Nguồn đối chiếu lời giải gốc: Hugging Face `openai/gsm8k`, config `main`, file `main/train-00000-of-00001.parquet`, SHA256 `ea82612e...419d`, tra theo `source_index`. Cả 7473 câu hỏi khớp với `data/raw/gsm8k_train.jsonl` sau khi chuẩn hóa khoảng trắng.

## Rà soát lần 2 (cùng ngày)

Đã rà lại toàn bộ sau khi áp dụng, kết quả:

| Kiểm tra | Kết quả |
|---|---|
| Cả 42 bài batch_100 có division trong gold v2, đối chiếu với 5 trường hợp cần chia của v3 | 42/42 đúng [SUY RA] |
| 00029 ("every 3rd floor", có division) và 00090 ("every other day", không có division) có mâu thuẫn không | Không. Division của 00029 đến từ `800 / 10` (tỉ suất); cả 5 trace của 00090 đều đếm ngày 2, 4, 6, không chia [TÍNH] |
| Supplement (85 bài, gán theo v2) có bị D1 ảnh hưởng không | 1 bài (02893) → đã sửa như trên [TÍNH] |
| Gold batch_100 v1 ở 30 bài đầu có trùng pilot A1 không | Trùng 30/30; gold v2 chỉ khác pilot ở 00000, 00004 [TÍNH] |
| Guideline v3 còn câu nào hiểu division theo cách viết không | 2 chỗ, đã sửa: cuối Rule 4 thêm định nghĩa "occurs in the reasoning" theo v3; mục 14 thêm ghi chú pilot division 15/30 → 13/30 theo gold v2 |
| Rationale trong `manual_adjudication.csv` còn ghi "pending approval" không | 26 dòng → đổi thành "approved 2026-10-12 in config/capability_rules_v2.json" |
| Default runner `--raw` cho 402 trajectory | Đúng, 98 bị loại [TÍNH]; đã ghi vào `trajectory/pool/README.md` |

## Cách kiểm tra lại

```bash
cd experiments/week2September/manual
python3 scripts/test_capability_extractor.py          # PASS 28 (rules v1)
python3 scripts/test_capability_rules_v2.py           # PASS 44 (rules v2)
python3 scripts/validate_manual_adjudication.py       # 34 reviewed, PASS
python3 scripts/validate_annotation.py data/batch_100/batch_100_annotations_v2.jsonl   # cần jsonschema
python3 scripts/validate_annotation.py data/supplement/supplement_annotations_v2.jsonl
sha256sum -c reports/error_analysis/baseline_backup/SHA256SUMS.txt
sha256sum -c reports/error_analysis/baseline_backup/SHA256SUMS_ambiguous_cases.txt
sha256sum -c reports/task4_reruns/SHA256SUMS.txt
python3 scripts/run_task4_extractor_batch100.py \
  --raw trajectory/pool/batch_100_teacher_raw_recovered_v2.jsonl \
  --rules config/capability_rules_v2.json \
  --manual data/batch_100/batch_100_annotations_v2.jsonl --tag rulesv2_goldv2
```

## Khi nào đảo ngược

- Nếu nhóm muốn "half of N" có division: khôi phục 6 bài trong `gold_change_log.csv` là chưa đủ. Để nhất quán phải **thêm** division cho mọi bài dạng "phân số của N" chưa có division: batch_100 gồm 00006, 00022, 00030, 00041, 00049, 00063, 00072; supplement cần rà lại 21 bài có fraction mà không có division (ví dụ 00155, 01280, 03734). Sửa 4 dòng D1 trong `manual_adjudication.csv` sang `TRUE_CAPABILITY_OMITTED_FROM_GOLD`, sửa guideline_v3 (Rule 2, Rule 3, case 00004), và dùng rules phần A thay vì A+B.
- Nếu Đề xuất 2 cần capability cấp trajectory: thay quyết định D3 bằng nhãn cấp trajectory; các FP do đường vòng và nhóm `N / k` sẽ được chấm lại.
