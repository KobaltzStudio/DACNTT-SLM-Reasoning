# Đề xuất chốt quy tắc phân tích trước thí nghiệm chính

Ngày: 01/11/2026. Trạng thái: **đã chốt theo đề xuất** (B4 và B3 theo khối liên tiếp, tâm tính trên lời giải chưa học, dùng ngưỡng Δ ≥ 0,05). Đã áp dụng vào `analysis_plan.md` v2 và config v2; xem `experiments/week2September/manual/task7_decisions.md`.

Số liệu minh hoạ lấy từ smoke test (pool sơ bộ, 158 lời giải chưa học ở cả hai seed). Đây là số thăm dò để thiết kế quy tắc, không phải kết quả. Hai seed của smoke test học trên hai tập khác nhau, nên nhiễu đo được có thể lớn hơn nhiễu thật.

## 0. Điểm chặn: B4 chưa được định nghĩa ở vòng 2 và 3

Kế hoạch chỉ ghi B4 "chọn 1 lần tại S_0", protocol ghi "schedule fixed for all rounds", nhưng không nói vòng 2 và 3 lấy gì. Có hai cách hiểu:
- (a) Lặp lại cùng một tập ở cả 3 vòng (giống `b3_rule`: "computed once, reused for all rounds").
- (b) Xếp hạng một lần tại S_0 rồi lấy các khối liên tiếp: vòng 1 gần trung vị nhất, vòng 2 khối kế tiếp, vòng 3 khối tiếp theo.

Theo (a), B4 chỉ học khoảng 185 lời giải ba lần, còn B5 gần như luôn nhận lời giải mới, vì lời giải đã học có ℓ giảm khoảng 1,3σ nên rời khỏi vùng gần trung vị. So sánh chính khi đó chủ yếu đo "dữ liệu mới so với dữ liệu lặp", trái với câu "chỉ khác ở việc tính lại learnability" trong kế hoạch.

Đề xuất: chọn (b) và ghi rõ vào `analysis_plan.md` cùng config v2. B3 có cùng vấn đề và cần nhóm xem lại: tập B3 hiện được dùng lại ở mọi vòng.

## Thiết kế đo chung

- Lấy B4 làm phép đo lặp: B4 chọn dữ liệu từ S_0 và phá hoà theo `trajectory_id`, nên ba seed học trên cùng tập dữ liệu, chỉ khác seed huấn luyện. Cần kiểm tra selection log của ba seed trùng nhau trước khi dùng.
- Tập phân tích U: các lời giải chưa được huấn luyện ở bất kỳ seed nào đang so sánh, tính đến checkpoint sau của cặp checkpoint.
- Phân tích thêm một bản bỏ cả các bài có lời giải khác đã được học (độ nhạy), vì lời giải cùng bài có thể cũng được lợi.

## 1. Công thức ε

Đề xuất chính:

```
d_i^(a,b) = | L_proxy(τ_i | S_1^a) − L_proxy(τ_i | S_1^b) |,   i ∈ U,  (a,b) ∈ {(13,42), (13,2026), (42,2026)}
ε = phân vị 95% của toàn bộ d_i^(a,b)
```

Một thay đổi |L(τ | S_{t+1}) − L(τ | S_t)| được tính là thật khi lớn hơn ε.

Báo cáo kèm để đối chiếu: s_w² = trung bình theo τ của phương sai giữa các seed; ε_chuẩn = 1,96 × √2 × s_w ≈ 2,77 s_w.

Giải thích:
- Hai phép đo đều có nhiễu, nên hiệu của chúng có độ lệch chuẩn √2 × s_w, không phải s_w. Đây là hệ số lặp lại (repeatability coefficient) của Bland và Altman; Weir gọi là minimal difference.
- Công thức 2,77 s_w giả định sai số gần chuẩn và như nhau ở mọi mức. L_proxy không thoả điều này. Trên smoke test, phân vị 95% của |d| thay đổi theo mức điểm, từ 0,15 (vùng điểm cao) đến 0,30 (vùng 0,3–0,6), và ε_chuẩn = 0,215 thấp hơn phân vị thực nghiệm 0,251. Vì vậy nên dùng phân vị thực nghiệm làm số chính. Câu "nửa độ rộng 95%" trong kế hoạch hiện tại cũng khớp với cách này.
- Với mỗi lời giải, khoảng 5% sẽ vượt ε chỉ do nhiễu. Vì vậy chỉ số cần báo cáo là tỉ lệ vượt ε so với mốc 5%, không kết luận cho từng lời giải riêng lẻ.
- Ở cặp S_0 → S_1, S_0 không có nhiễu seed nên ε này hơi thận trọng. Giữ một ε chung cho đơn giản.

Cách khác đã cân nhắc: chỉ dùng 2,77 s_w (đơn giản, trích trực tiếp nhưng sai giả định); ε riêng theo từng mức điểm (chính xác hơn nhưng phức tạp, ít mẫu ở mỗi mức).

Nguồn: Bland và Altman (1996), BMJ 313:744; Weir (2005), J Strength Cond Res 19(1):231–240. Hai bài này nêu nguyên tắc; dùng phân vị thực nghiệm cho L_proxy là điều chỉnh của nhóm.

## 2. Kiểm định so ρ(L_t, L_{t+1}) với ρ_noise

Đề xuất chính: bootstrap theo cụm bài toán.

```
Với mỗi seed a:
  ρ_change^a = Spearman( L(·|S_t^a), L(·|S_{t+1}^a) ) trên U
  ρ_noise^a  = trung bình Spearman( L(·|S_{t+1}^a), L(·|S_{t+1}^b) ), b ≠ a, trên U (đo trên B4)
  Δ^a = ρ_noise^a − ρ_change^a
Lấy lại mẫu theo problem_id (mọi lời giải của bài đi cùng nhau), 10.000 lần, tính lại Δ^a trên cùng mẫu.
```

H được ủng hộ ở một cặp checkpoint khi cả ba seed đều có:
1. cận dưới một phía 95% của Δ^a lớn hơn 0;
2. Δ^a ≥ 0,05 (ngưỡng thực tiễn do nhóm tự đặt, cần duyệt).

Áp dụng cho S_0 → S_1 và S_1 → S_2, và cả ρ_change lẫn ρ_noise đều tính trên chính các lần chạy B4, để hai số dùng chung phép đo và cùng điều kiện huấn luyện. Cặp S_1 → S_2 cần thêm NLL của B4 tại S_2 cho ba seed.

Thang đo quyết định phải chốt trước. Đề xuất: tiêu chí trên áp dụng cho L_proxy (đại lượng thật sự dùng để chọn, đúng kế hoạch đã chốt). Δ trên thứ hạng ℓ được báo cáo kèm CI. Nếu chỉ L_proxy đạt mà ℓ không đạt thì không viết "learnability của lời giải thay đổi", mà viết "thứ hạng theo khoảng cách tới trung vị thay đổi". Trên smoke test, Δ của L_proxy là 0,16–0,23, còn Δ của ℓ chỉ 0,01–0,02, nên trường hợp này có thể xảy ra thật.

Hạn chế: bootstrap chỉ phản ánh việc lấy mẫu bài toán, không phản ánh biến thiên giữa các seed; về seed chỉ có 3 giá trị và yêu cầu nhất quán cả 3.

Giải thích:
- Vì cùng tính trên B4, ρ_change và ρ_noise dùng chung L(·|S_{t+1}^a) nên phụ thuộc nhau. So như hai tương quan độc lập là sai; Steiger (1980) nêu các kiểm định riêng cho trường hợp này.
- Steiger giả định các quan sát độc lập, trong khi 5 lời giải của cùng bài có liên quan. Vì vậy bootstrap phải lấy theo bài. Field và Welsh (2007) cho thấy cluster bootstrap ước lượng phương sai nhất quán trong các mô hình họ xét.
- Pool có khoảng 4.000 lời giải nên chênh rất nhỏ cũng có ý nghĩa thống kê. Do đó cần thêm ngưỡng Δ. Con số 0,05 không có nguồn và phân biệt kém: trên smoke test, L_proxy vượt rất xa (0,16–0,23). Lớp bảo vệ chính vẫn là yêu cầu nhất quán cả 3 seed và báo cáo ℓ.
- Dùng ρ_noise làm mốc là thận trọng ở cặp S_0 → S_1. Theo hiệu chỉnh suy giảm của Spearman (1904), nếu thứ hạng thật không đổi thì tương quan kỳ vọng khoảng √(r_0 × r_1) = √ρ_noise, cao hơn ρ_noise vì S_0 không có nhiễu seed. Báo cáo thêm mốc √ρ_noise như phân tích độ nhạy.
- Cùng phân tích trên thứ hạng ℓ, để tách ảnh hưởng của việc đặt lại tâm trong L_proxy. Trên smoke test, Spearman của ℓ giữa S_0 và S_1 là 0,94, trong khi của L_proxy là 0,62–0,69; giữa hai seed tại S_1 lần lượt là 0,95 và 0,85. Khoảng cách trên ℓ nhỏ hơn hẳn, nên có thể kết luận về "learnability thay đổi" phụ thuộc mạnh vào thang đo.

Cách khác đã cân nhắc: kiểm định Steiger (nhanh, nhưng giả định độc lập, nên giữ làm đối chiếu); bootstrap thường theo lời giải (bỏ qua cụm, CI quá hẹp).

Wilcoxon trong kế hoạch hiện tại: nên giữ để mô tả, kèm effect size, nhưng không dùng làm tiêu chí ủng hộ H. Với cỡ mẫu này, nó gần như luôn có ý nghĩa.

Nguồn: Steiger (1980), Psychological Bulletin 87(2):245–251; Field và Welsh (2007), JRSS-B 69(3):369–390; Spearman (1904), American Journal of Psychology 15(1):72–101.

## 3. Trung vị có loại lời giải đã học không

Đề xuất:

```
ℓ*_t, σ_t tính trên các lời giải eligible chưa được huấn luyện trong lần chạy đó
L_proxy vẫn được tính cho mọi lời giải eligible; lời giải đã học vẫn được chọn lại theo quy tắc hiện hành
```

Tại S_0 quy tắc này trùng với quy tắc cũ. B4 không bị ảnh hưởng vì chỉ tính tại S_0. Đây là thay đổi của `ell_star_rule` và `sigma_rule` nên cần config v2. Chưa có lần chạy chính nào nên đổi lúc này là hợp lệ.

Giải thích:
- Mục đích của tâm là phản ánh trạng thái của Student trên dữ liệu chưa học. Trên smoke test, ℓ của lời giải đã học giảm khoảng 0,091, lời giải chưa học giảm khoảng 0,036. Giữ lời giải đã học sẽ kéo tâm xuống vì một nguyên nhân cơ học.
- Nghe như ảnh hưởng nhỏ, nhưng không nhỏ. L_proxy chỉ phụ thuộc khoảng cách tới tâm, nên top khoảng 185 lời giải (4,2% pool) nằm trong dải rất hẹp, khoảng ±0,053σ nếu ℓ gần chuẩn. Thử trên smoke test với tỉ lệ đã học 4,3%, tâm dịch khoảng 0,03σ nếu lời giải đã học được chọn ngẫu nhiên, và khoảng 0,06σ nếu chúng là các lời giải gần trung vị (đúng với B4, B5). Theo xấp xỉ chuẩn, Jaccard của hai tập chọn còn khoảng 0,3–0,55. Đây chỉ là ước tính thô, tính từ 480 lời giải với 13 lời giải đại diện; nhiễu seed (mục 5) còn lớn hơn độ dịch này, nên lợi ích thật của đề xuất chưa chắc.
- RHO-LOSS (Mindermann và cs., 2022) cũng dùng tập holdout làm mốc để tách phần loss còn học được. Đề xuất ở đây chỉ cùng tinh thần "mốc tham chiếu không lẫn dữ liệu đã học"; bài báo không đề xuất quy tắc này.

Cách khác: giữ quy tắc cũ (không cần config v2, nhưng để lại độ lệch cơ học và phải ghi là hạn chế); loại cả các bài có lời giải đã học (sạch hơn, nhưng sau 3 vòng có thể mất tới khoảng 40–50% pool làm mốc).

Không có nguồn nào quy định đúng cách làm này; đây là quyết định thiết kế của nhóm.

## 4. Accuracy chấm nới

Đề xuất đưa vào `analysis_plan.md`, mục 6 và 7:

- Định nghĩa: `lenient_correct` = số cuối cùng ở bất kỳ đâu trong output khớp đáp án, bỏ qua định dạng (`answer_utils.answers_match(output, ground_truth)`, đúng như `eval_student.py`).
- Vai trò: chỉ số phụ đã đăng ký trước. Chỉ số chính vẫn là accuracy chấm chặt trên D_test.
- Báo cáo cùng lúc ba số cho mọi phương pháp và checkpoint: accuracy chặt, accuracy chấm nới, tỉ lệ đúng định dạng.
- Kiểm định: McNemar và CI qua seed như chỉ số chính, cho B5 với B4. Không thay kết luận của so sánh chính. Nếu hai chỉ số cho kết luận ngược nhau thì báo cáo cả hai và nêu rõ.
- Kiểm tra đúng nhầm: đọc thủ công toàn bộ, hoặc tối đa 100 trường hợp, thuộc nhóm invalid_format có `lenient_correct = True` trên D_test của S_0 và một checkpoint cuối, để ước lượng tỉ lệ đúng nhầm.

Giải thích:
- Trên smoke test, chấm chặt tăng 10,6–11,8 điểm, chấm nới chỉ tăng 6,8 điểm (McNemar p ≈ 0,001 ở cả hai seed). Nếu chỉ báo cáo số chặt, phần học định dạng sẽ bị hiểu là học suy luận.
- Trong dữ liệu smoke test, phần khác nhau giữa hai chỉ số nằm hoàn toàn ở nhóm invalid_format: không có câu nào hợp lệ mà chấm nới sai, hay invalid_answer mà chấm nới đúng. Nhóm cần đọc thủ công vì thế khá nhỏ (S_0 có 25 câu trên D_dev).
- Tách chỉ số chính và phụ từ trước là nguyên tắc của ICH E9. IFEval (Zhou và cs., 2023) cho thấy việc tuân thủ định dạng là thứ có thể đo riêng và tự động.
- Lấy số cuối làm đáp án là cách đơn giản, có thể đúng nhầm khi số cuối trùng hợp với đáp án, nên chỉ dùng làm chỉ số phụ.

Lưu ý: `pool_stats.py` dùng biến thể có thêm `\boxed{}` cho Teacher. Khi báo cáo cần ghi rõ định nghĩa, hoặc thống nhất về một định nghĩa.

Nguồn: ICH E9 (1998); Zhou và cs. (2023), arXiv:2311.07911. McNemar: Dietterich (1998), Neural Computation 10(7).

## 5. Phát hiện thêm khi tính các số trên

Việc chọn top theo L_proxy rất nhạy với nhiễu. Trên smoke test, nhiễu giữa hai seed của ℓ sau khi trừ tâm là s_w ≈ 0,2σ, lớn hơn khoảng 4 lần nửa độ rộng của dải chọn (khoảng 0,053σ). Vì vậy thành viên của tập chọn, nhất là ở B5, có thể phụ thuộc nhiều vào seed. Số này có thể phóng đại vì hai seed học trên hai tập khác nhau, nhưng cần đo lại trên B4.

Đề xuất: báo cáo thêm Jaccard giữa tập chọn của B5 ở các seed khác nhau, đặc biệt tập chọn vòng 2 từ S_1 của ba seed, vì S_1 là phép đo lặp. Mốc so sánh là Jaccard ngẫu nhiên khoảng 0,02 (185 trong 4.353). Nếu Jaccard gần mốc này thì B5 khác B4 phần lớn do nhiễu, không phải do tín hiệu. Có thể kiểm tra ngay sau vòng 1. Việc này không đổi quy tắc chọn đã chốt.

## 6. Việc cần làm nếu nhóm đồng ý

0. Chốt định nghĩa B4 ở vòng 2 và 3 (mục 0), xem lại B3.
1. Thêm các quy tắc trên vào `analysis_plan.md` (mục 3, 6, 7).
2. Tạo config v2 cho quy tắc tâm và σ (nếu chọn đề xuất ở mục 3), chạy `validate_experiment_config.py --frozen`, tạo lại manifest.
3. Ghi quyết định và lý do vào file quyết định Task 7.
4. Làm tất cả trước khi có NLL của B4 tại S_1.

## 7. Giới hạn của các con số trong đề xuất

- Mọi số minh hoạ đến từ 158 lời giải của pool sơ bộ, trên hai seed học hai tập khác nhau. Các mức 0,15–0,30 ở mục 1 tính từ các nhóm chỉ có 17 đến 76 lời giải, nên chỉ nói được rằng nhiễu có đổi theo mức điểm, chưa nói được đổi bao nhiêu.
- ε là một số duy nhất, nhưng nhiễu đổi theo mức điểm, và L_proxy có thể không đổi khi ℓ đi từ bên này sang bên kia trung vị. Vì vậy phân loại profile theo từng lời giải chỉ nên xem là mô tả. ε ước lượng từ 3 cặp seed, nên báo cáo kèm CI bootstrap theo bài.
- Loại lời giải đã học khỏi U cũng loại phần gần trung vị nhất tại S_0, nên có thể lệch tương quan. Thử trên smoke test, ảnh hưởng nhỏ (Spearman đổi dưới 0,03, không rõ chiều), nhưng mẫu nhỏ. Báo cáo thêm phân tích trên B2 (chọn ngẫu nhiên) làm đối chiếu.
- ICH E9 là hướng dẫn cho thử nghiệm lâm sàng, ở đây chỉ mượn nguyên tắc tách chỉ số chính và phụ.

## Tài liệu tham khảo

Đã kiểm tra thông tin thư mục hoặc tóm tắt qua tìm kiếm ngày 01/11/2026, chưa đọc toàn văn từng bài. Cần đối chiếu bản gốc trước khi trích trong bài báo:
- Bland, J. M., Altman, D. G. (1996). Measurement error. BMJ 313:744 (bản kiểm tra qua tìm kiếm chỉ có đoạn trích). Sai số tỉ lệ với mức đo: BMJ 313:106.
- Weir, J. P. (2005). Quantifying test-retest reliability using the intraclass correlation coefficient and the SEM. J Strength Cond Res 19(1):231–240.
- Steiger, J. H. (1980). Tests for comparing elements of a correlation matrix. Psychological Bulletin 87(2):245–251.
- Field, C. A., Welsh, A. H. (2007). Bootstrapping clustered data. JRSS-B 69(3):369–390.
- Mindermann, S. và cs. (2022). Prioritized Training on Points that are Learnable, Worth Learning, and Not Yet Learnt. ICML, PMLR 162:15630–15649.
- ICH E9 (1998). Statistical Principles for Clinical Trials.
- Zhou, J. và cs. (2023). Instruction-Following Evaluation for Large Language Models. arXiv:2311.07911.

Ghi theo trí nhớ, chưa kiểm tra lại trong đợt này:
- Spearman, C. (1904). The proof and measurement of association between two things. American Journal of Psychology 15(1):72–101.
- Dietterich, T. G. (1998). Approximate statistical tests for comparing supervised classification learning algorithms. Neural Computation 10(7):1895–1923.
