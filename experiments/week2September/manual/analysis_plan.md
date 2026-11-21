# Analysis Plan (Proposal 2: Dynamic Learnability-Aware CoT Distillation)

Trạng thái: **FROZEN v2** (2026-11-01), đi cùng `config/experiment_config.json` v2, chốt trước mọi lần chạy chính. Thay đổi so với v1 và lý do: `task7_decisions.md` [T7-x]; bản v1 lưu ở `analysis_plan_v1.md`. I4 (b = 7) vẫn tạm. Thay đổi sau freeze phải tạo version mới kèm lý do.
Ngày: 2026-11-01 (v1: 2026-10-14).

Nguồn:
- [README CŨ §x]: `readme.md` gốc trước commit 3f7dce4 (`git show 3f7dce4^:readme.md`), trích nguyên văn ở `config/proposal2_full_protocol.md`. Nhóm đã xác nhận các định nghĩa này còn hiệu lực (2026-10-14).
- [QĐ #x]: `task5_decisions.md` mục A–G (nhóm chốt).
- [ĐX #Ix]: `task5_decisions.md` mục I (đề xuất có lập luận).
- [T7-x]: `task7_decisions.md`.
- Tham số cụ thể: `config/experiment_config.json`.

## 1. Giả thuyết

**H (chính)** [README CŨ §19]: learnability L(τ | S_t) của một trajectory thay đổi khi trạng thái Student thay đổi.
Nếu L(τ | S_0) ≈ L(τ | S_1) ≈ L(τ | S_2) trong phạm vi tolerance ε (mục 6), H không được ủng hộ trong setting đó.

**H_sel (hệ quả cho selection)**: nếu H đúng, chọn dữ liệu theo learnability tính lại ở mỗi checkpoint (B5) cho accuracy cao hơn chọn một lần ở S_0 (B4) với cùng tín hiệu và cùng budget [README CŨ §16.2].

Kết quả null và âm được giữ và báo cáo chi tiết như kết quả dương [README CŨ §19, §19.1].

## 2. Dữ liệu và split

| Split | Nguồn | Dùng cho | Không bao giờ dùng cho |
|---|---|---|---|
| D_pool | GSM8K train | sinh trajectory, pool, train Student | đánh giá |
| D_dev | GSM8K train, không giao D_pool | L_emp, mastery theo capability, tune, early stopping | train Student |
| D_test | GSM8K test chính thức | báo cáo | selection, tune, early stopping, mọi quyết định thiết kế |

[README CŨ §13.1]. Chi tiết chia: [QĐ #4–9]; file `splits/` + `splits/split_manifest.json`.
Kết quả: D_pool 6968 bài (gồm toàn bộ batch_100), D_dev 500 (85 supplement + 415 ngẫu nhiên), D_test 1319; 5 bài D_pool bị loại do trùng 13-gram với D_dev/D_test (task5_decisions.md mục H).
Kết quả nào tính trên D_test trước freeze phải ghi là exploratory.

## 3. Quy trình

S_{t+1} = Train(S_t, B_t), t = 0 … M−1, M = 3 [README CŨ §5.1, QĐ #11].
Tại mỗi checkpoint S_t:
1. Lưu `student_ckpt_{t:03d}`.
2. Đánh giá trên D_dev; đánh giá D_test tại S_0 … S_3 [QĐ #28], kết quả D_test không dùng cho quyết định nào.
3. Tính lại L_proxy cho toàn bộ pool eligible (B5, B6).
4. Đo L_emp chỉ tại S_0 [QĐ #13].

Ghi log theo `schemas/selection_log_schema.json`.

## 4. Learnability

**L_proxy** [README CŨ §9.1(a)]:
- ℓ(τ | S_t) = −(1/|τ|) Σ log p_{S_t}(τ_i | x, τ_<i)
- L_proxy(τ | S_t) = exp(−(ℓ − ℓ*_t)² / (2σ_t²))
- ℓ*_t = median, σ_t = IQR / 1.349 của ℓ trên tập tham chiếu tại S_t [QĐ #18, T7-3]: các trajectory eligible chưa được train trong lần chạy đó (tại S_0 là toàn bộ eligible). L_proxy vẫn tính cho mọi trajectory eligible. Quy tắc cố định; chỉ giá trị tính lại mỗi checkpoint.
- Chỉ chấm trajectory đã verify.

**L_emp** [README CŨ §9.1(b)]:
- L_emp(G | S_t) = (Acc_dev(S_t + train(G)) − Acc_dev(S_t)) / b
- G: 5 nhóm × 50 trajectory theo ngũ phân vị độ dài token tại S_0 (seed 363636); b = 7 step = 1 epoch ở batch 8, cùng chế độ với một vòng train [ĐX #I4].
- Đo trên D_dev, trung bình qua các training seed.

## 5. Phương pháp so sánh

Mọi phương pháp dùng chung pool, lịch checkpoint, budget và seed [README CŨ §16.2].

| ID | Phương pháp | Khi nào chọn | Tín hiệu | Trạng thái [QĐ #29] |
|---|---|---|---|---|
| B0 | Không train | - | S_0 | bắt buộc |
| B1 | Toàn pool | - | mọi trajectory verify (tham chiếu, tốn hơn) | nếu đủ tài nguyên |
| B2 | Random | mỗi vòng | ngẫu nhiên, cùng budget | bắt buộc |
| B3 | Heuristic | 1 lần, đi tiếp theo thứ tự qua các vòng [T7-2] | trajectory đúng ngắn nhất mỗi bài [QĐ #24] | bắt buộc |
| B4 | Static learnability | xếp hạng 1 lần tại S_0, đi tiếp theo thứ hạng qua các vòng [T7-1] | L_proxy(τ \| S_0) | bắt buộc |
| B5 | Dynamic learnability | mỗi checkpoint | L_proxy(τ \| S_t) | bắt buộc |
| B6 | Dynamic + bottleneck | mỗi checkpoint | L_proxy · [α·1{c*_t ∈ C(τ)} + (1−α)·cov(τ)] | nếu đủ tài nguyên |
| - | Ablation: dynamic với điểm bị xáo trộn | mỗi checkpoint | L_proxy xáo trộn | nên có |

Ràng buộc chọn [README CŨ §16.1, QĐ #20–23]: n_cap = 1; được chọn lại qua các vòng (B2, B5, ablation); hòa điểm theo trajectory_id; lấp đầy tới beta_round token. B3 và B4 không lặp trajectory: mỗi vòng đi tiếp từ chỗ vòng trước dừng; trajectory bị n_cap bỏ qua trong một vòng vẫn còn cho vòng sau [T7-1, T7-2].
Retention quota r = 50% [QĐ #21; TiC-LM α_t = 1/2], **chỉ áp dụng cho B6** [ĐX #I7], để B4, B5 và ablation chỉ khác nhau ở tín hiệu learnability.
Budget: beta_round = 45.426 token response/vòng (n_round = 200 × L̄ = 227.13), tổng 136.278; token prompt bị mask khỏi loss và không tính vào budget [ĐX #I2, #I3]. B1 là ngoại lệ (toàn pool, không cùng budget).
Train: LoRA r16/α32 trên mọi lớp linear, dropout 0.1, AdamW, lr 2e-4 cố định, batch 8, 1 epoch/vòng, completion-only loss, tiếp tục cùng adapter qua các vòng [QĐ #14, ĐX #I5].

**So sánh chính: B5 vs B4.** Cùng tín hiệu, cùng budget, chỉ khác có tính lại learnability hay không.
So sánh phụ: B4 vs B3 (nhìn vào Student có lợi hơn heuristic không), B4/B5 vs B2 (hơn ngẫu nhiên không), B5 vs ablation (lợi ích đến từ tín hiệu hay từ việc đổi dữ liệu mỗi vòng).

## 6. Metric

[README CŨ §10.1]
- **Chính:** exact-match accuracy trên D_test.
- **Phụ:** accuracy chấm nới [T7-5]; accuracy theo capability trên D_dev; tỉ lệ trích được đáp án; độ dài output trung bình của Student.
- **Accuracy chấm nới:** số cuối cùng ở bất kỳ đâu trong output khớp đáp án, bỏ qua định dạng (`answer_utils.answers_match`, như `eval_student.py`). Luôn báo cáo cùng accuracy chặt và tỉ lệ đúng định dạng. McNemar và CI qua seed cho B5 vs B4 trên chỉ số này là phân tích phụ, không thay kết luận chính; nếu hai chỉ số ngược nhau thì báo cáo cả hai. Đọc thủ công nhóm `invalid_format` có `lenient_correct = True` trên D_test tại S_0 và S_3 (tối đa 100 trường hợp mỗi checkpoint) để ước lượng tỉ lệ đúng nhầm.
- **Dynamic learnability:** Spearman ρ giữa L(·|S_t) và L(·|S_{t+1}); Jaccard(B_t, B_{t+1}); tỉ lệ trajectory vào/ra dải learnability; phân loại profile (tăng/giảm/ổn định/không đơn điệu) theo ε.
- **Hiệu quả:** accuracy D_test theo cumulative training tokens và diện tích dưới đường cong; beta_est (số forward pass để tính lại L_proxy).

Quy trình eval cố định [QĐ #25, #26]: greedy, max_new_tokens = 512, prompt v1 (`PROMPT_TEMPLATE` của `scripts/generate_teacher_trajectories_batch.py`).
Answer extractor/verifier: `scripts/answer_utils.py` (tách REASONING/ANSWER, số cuối, chuẩn hóa Decimal); tái tạo đúng trạng thái verify của pool sơ bộ (480/20). Output không trích được đáp án (`invalid_format`) tính là sai; tỉ lệ format compliance báo cáo riêng [ĐX #I1].

## 7. Kiểm định thống kê

Pre-registration [README CŨ §19.1]: chốt trước khi chạy metric chính (accuracy D_test), so sánh chính (B5 vs B4), mức ý nghĩa α = 0.05 và quy tắc tolerance. Mọi phân tích khác ghi là exploratory.

- **Trong một seed:** McNemar trên đúng/sai theo từng bài (paired) [QĐ #30].
- **Qua các seed:** trung bình chênh lệch paired, kèm 95% CI; training seeds [13, 42, 2026] dùng chung cho mọi phương pháp [QĐ #16]. Kết luận phải nhất quán qua các seed, không chỉ ở trung bình.
- **Phép đo lặp** [T7-6]: các lần chạy B4 của ba training seed (cùng dữ liệu, khác seed; phải kiểm tra selection log trùng nhau). U = các trajectory chưa được train trong B4 tính đến checkpoint sau của cặp đang xét.
- **Tolerance ε cho "xấp xỉ bằng"** [README CŨ §19.1, T7-6]: ε = phân vị 95% của |L(τ|S_1^a) − L(τ|S_1^b)| trên U, gộp mọi cặp seed. Báo cáo kèm 2,77·s_w (Bland & Altman) và CI bootstrap theo bài. Một thay đổi |L(τ|S_{t+1}) − L(τ|S_t)| chỉ tính là vượt nhiễu nếu > ε; báo cáo tỉ lệ vượt ε so với mốc 5%. Phân loại profile theo từng trajectory chỉ mang tính mô tả.
- **Kiểm định H** [T7-4, T7-7]: cho S_0→S_1 và S_1→S_2, trên B4. ρ_change^a = Spearman(L|S_t^a, L|S_{t+1}^a); ρ_noise^a = trung bình Spearman(L|S_{t+1}^a, L|S_{t+1}^b), b ≠ a; Δ^a = ρ_noise^a − ρ_change^a, tính trên U. Suy luận bằng bootstrap theo cụm `problem_id`, 10.000 lần, seed 363636, cùng mẫu cho mọi seed. H được ủng hộ ở một cặp khi **mọi** seed có cận dưới một phía 95% của Δ^a > 0 và Δ^a ≥ 0,05 (quy ước của nhóm, không có nguồn).
- **Thang đo quyết định** [T7-7]: L_proxy. Δ trên thứ hạng ℓ báo cáo kèm CI. Nếu L_proxy đạt mà ℓ không đạt thì chỉ kết luận "thứ hạng theo khoảng cách tới trung vị thay đổi", không kết luận learnability của trajectory thay đổi.
- **Mô tả và độ nhạy:** Wilcoxon signed-rank kèm effect size chỉ để mô tả. Độ nhạy: mốc √ρ_noise ở S_0→S_1; kiểm định Steiger; U bỏ các bài có trajectory đã train; lặp lại trên B2. Bootstrap chỉ phản ánh lấy mẫu bài toán; về seed chỉ có 3 giá trị.
- **Độ nhạy của việc chọn với nhiễu:** Jaccard giữa tập chọn vòng 2 của B5 ở các seed, so với mức ngẫu nhiên khoảng 0,02 [T7-8].
- **Proxy validity:** Spearman giữa L_proxy trung bình theo nhóm và L_emp, kèm bootstrap CI.
- **Nhiều so sánh:** Holm-Bonferroni qua các baseline và các phân tích theo capability.
- **Báo cáo:** effect size và CI đi kèm p-value.

## 8. Giới hạn đã biết

- Định nghĩa protocol lấy từ README cũ đã bị xóa khỏi readme.md; bản chép nguyên văn ở `config/proposal2_full_protocol.md`.
- Nhãn capability: A2 chưa xác minh annotate độc lập (Task 4, kappa = 1.0 chưa đáng tin); supplement chỉ có A1.
- D_dev không stratify theo capability ngoài 85 bài supplement [QĐ #7].
- Pool sơ bộ chỉ 98 bài có trajectory valid; config v1 yêu cầu pool chính thức ≥ 1000 bài D_pool (Task 6) [ĐX #I3].
- Budget 600 trajectory sau 3 vòng có thể làm accuracy thay đổi ít; nếu smoke test cho thấy vậy, đổi bằng config v2 **trước** khi chạy thí nghiệm chính.
- L_emp với b = 7 step có thể nhỏ hơn nhiễu; khi đó proxy validity không kết luận được và được báo cáo như vậy.
- Hyperparameters training chưa tune, lấy theo QLoRA (Dettmers et al., 2023) [ĐX #I5]; alpha chưa tune [QĐ #19].
- r = 50% theo TiC-LM (α_t = 1/2, đã đối chiếu toàn văn), nhưng bối cảnh là continual pretraining theo thời gian, khác bài toán này.

## 9. Trạng thái freeze

- Không còn TBD trong `config/experiment_config.json` (`scripts/validate_experiment_config.py --frozen`: PASS).
- Manifest: `reports/task5/SHA256SUMS_task5.txt`.
- Còn cần: smoke test để chốt [ĐX #I3, I4, I5] (README.txt mục 0, Task 5 "Còn lại").
