# Rà soát và tự phản biện các công thức trong dự án

Ngày: 30/10/2026
Phạm vi: mọi công thức đang dùng hoặc đã chốt trong `config/experiment_config.json`, `config/proposal2_full_protocol.md`, `config/proposal1_graph_protocol.md`, `analysis_plan.md`, các script trong `scripts/`, các quyết định Task 4 đến Task 6, và bản giải thích công thức cho bài báo (`notes/methodology_formulas.md`).

Mỗi công thức được hỏi sáu câu: là gì, từ đâu ra, vì sao có, dùng để làm gì, còn cách nào khác, có nguồn khoa học không. Sau đó là phần phản biện. Mức độ:
- [Nặng]: có thể làm sai kết luận chính hoặc bị hội đồng bác, cần xử lý trước khi chạy thí nghiệm chính.
- [Vừa]: nên sửa hoặc ghi rõ trong bài, không chặn thí nghiệm.
- [Nhẹ]: chi tiết, ghi chú là đủ.

Về nguồn: những bài kinh điển (McNemar, Wilcoxon, Spearman...) tôi ghi tên tác giả và năm. Với các bài gần đây, chỗ nào chỉ dựa vào ghi chép trong repo tôi ghi rõ "theo ghi chép trong repo", vì chưa đối chiếu lại toàn văn.

---

## A. Learnability (Đề xuất 2, phần lõi của đề tài)

### A1. NLL chuẩn hoá theo độ dài

```
ℓ(τ | S_t) = −(1/|τ|) · Σ_i log p_{S_t}(τ_i | x, τ_<i)
```

- Là gì: mất mát trung bình trên mỗi token khi Student S_t "đọc" lời giải τ của Teacher (một lượt forward, không cập nhật trọng số). ℓ thấp: Student đã thấy lời giải này rất quen. ℓ cao: lời giải lạ với Student.
- Từ đâu ra: chính là hàm mất mát SFT chia cho số token, cũng là log của perplexity.
- Vì sao có: là tín hiệu rẻ nhất để đo "Student thấy lời giải này khó hay dễ" mà không cần huấn luyện thử.
- Dùng để làm gì: đầu vào của L_proxy (A2).
- Cách khác:
  - IFD (Instruction-Following Difficulty, Li và cs., 2024, "From Quantity to Quality"): tỉ lệ giữa loss có đề bài và loss không có đề bài, tách được phần khó do chính câu trả lời.
  - RHO-LOSS (Mindermann và cs., ICML 2022): loss hiện tại trừ loss của một mô hình tham chiếu, ưu tiên điểm "học được, đáng học, chưa học".
  - Tổng NLL (không chia độ dài), hoặc NLL chỉ trên các token số và phép tính.
- Nguồn: khái niệm chuẩn trong mô hình ngôn ngữ; dùng NLL hay perplexity để chọn dữ liệu là hướng phổ biến (IFD, RHO-LOSS, RHO-1 của Lin và cs., 2024). Theo ghi chép trong repo, LARK cũng dựa trên likelihood của Student tại checkpoint gốc.
- Phản biện:
  - [Vừa] ℓ tính trên toàn bộ output, gồm cả các token định dạng như "REASONING:", "ANSWER:". Những token này gần như luôn dễ, kéo ℓ xuống và làm lời giải ngắn bị thiệt hoặc lợi một cách hệ thống. Nên báo cáo thêm ℓ chỉ trên phần lời giải, ít nhất là thăm dò.
  - [Vừa] Chia cho |τ| làm mất thông tin độ dài, nhưng tương quan giữa ℓ và độ dài vẫn còn (lời giải dài có nhiều token "dễ" giữa câu). Cần kiểm tra tương quan ℓ với độ dài trên pool; nếu cao, chọn theo L_proxy thực chất là chọn theo độ dài, và B4/B5 sẽ gần B3.
  - [Nhẹ] Tên gọi: bài báo dùng Λ, protocol dùng L_proxy. Nên thống nhất một ký hiệu.

### A2. L_proxy: dải Gauss quanh trung vị

```
L_proxy(τ | S_t) = exp( −(ℓ(τ | S_t) − ℓ*_t)² / (2σ_t²) ),   ℓ*_t = median(ℓ),  σ_t = IQR(ℓ) / 1,349
```

- Là gì: điểm từ 0 đến 1, cao nhất khi ℓ bằng trung vị của pool, giảm dần khi ℓ lệch về hai phía.
- Từ đâu ra: quyết định thiết kế của nhóm (QĐ #18 trong `analysis_plan.md`), dạng mềm của "dải cứng" ℓ_low ≤ ℓ ≤ ℓ_high trong bản phương pháp của bài báo.
- Vì sao có: giả định "vùng vừa sức": lời giải quá dễ thì Student không học thêm được gì, quá khó thì chưa học nổi. Ý tưởng gần với "vùng phát triển gần" (Vygotsky) và curriculum learning (Bengio và cs., 2009).
- Dùng để làm gì: điểm chọn dữ liệu của B4 (tính một lần tại S_0) và B5 (tính lại mỗi vòng).
- Cách khác:
  - Dải cứng (chỉ nhận ℓ trong [ℓ_low, ℓ_high]).
  - Chọn theo ℓ cao (dữ liệu khó, giàu thông tin; tinh thần của RHO-LOSS và active learning).
  - Chọn theo ℓ thấp (dữ liệu dễ, ổn định).
  - Với bài toán có đáp án: chọn bài có xác suất giải đúng gần 0,5, tức cực đại p(1 − p). Hướng này có trong các nghiên cứu curriculum cho RL gần đây (ví dụ "Learning to Reason at the Frontier of Learnability", Foster và Foerster, 2025; cần đối chiếu toàn văn trước khi trích).
- Nguồn: không có bài nào cho đúng công thức này. Hai thành phần có nguồn (median và IQR/1,349 là thống kê bền vững, xem A3), còn việc "chọn vùng giữa theo hình chuông, tâm là trung vị" là giả thuyết của nhóm.
- Phản biện:
  - [Nặng] Chưa có bằng chứng "vùng giữa" tốt hơn hai đầu. Nếu bị hỏi "tại sao không chọn lời giải khó nhất", hiện chưa có câu trả lời. `Task.md` mục 2.4 đã đề xuất thêm biến thể chọn ℓ cao và ℓ thấp; nên chạy ít nhất một seed, ghi là thăm dò.
  - [Nặng] Tâm ℓ* là trung vị của chính pool tại mỗi checkpoint, nên điểm chỉ mang nghĩa tương đối. Khi Student giỏi lên, toàn bộ ℓ giảm, nhưng tâm cũng giảm theo, và luôn có khoảng một nửa pool có điểm trên 0,61. Một phần "learnability thay đổi theo checkpoint" vì vậy có thể chỉ là do đặt lại tâm, không phải Student đổi cách nhìn từng lời giải. Phân tích giả thuyết H nên xét cả thứ hạng ℓ (không phụ thuộc tâm) bên cạnh L_proxy.
  - [Vừa] Đính chính 01/11/2026: σ không ảnh hưởng thứ tự chọn của B4 và B5, vì L_proxy chỉ giảm đơn điệu theo |ℓ − ℓ*|; đổi σ thì điểm đổi nhưng thứ hạng giữ nguyên. Tập chọn thực chất là các lời giải gần trung vị nhất (top khoảng 4% pool). σ chỉ có tác dụng với điểm của B6 và với thang đo khi tính ε. Bản trước ghi sai rằng đổi σ sẽ đổi tập chọn.
  - [Vừa] Trung vị tính trên "pool eligible", gồm cả các lời giải đã được huấn luyện ở vòng trước. Các lời giải này có ℓ giảm mạnh (smoke test: giảm gấp khoảng 2,5 lần lời giải chưa học), kéo trung vị xuống. Cần ghi rõ có loại chúng khỏi phép tính trung vị hay không.
  - [Nhẹ] Ở vòng đầu, B4 và B5 dùng cùng L_proxy tại S_0 nên chọn giống hệt nhau. Chênh lệch chỉ có thể xuất hiện từ vòng 2, tức chỉ 2 trong 3 vòng có tác dụng. Điều này làm khác biệt B5 với B4 càng khó thấy.

### A3. σ = IQR / 1,349

- Là gì: ước lượng độ lệch chuẩn từ khoảng tứ phân vị.
- Từ đâu ra: với phân phối chuẩn, Q3 − Q1 = 2 × 0,6745σ = 1,349σ.
- Vì sao có: phân bố ℓ lệch và có đuôi (lời giải bị cắt, lời giải lạ), độ lệch chuẩn thường bị ngoại lai kéo lệch; IQR chỉ phụ thuộc nửa giữa của dữ liệu.
- Dùng để làm gì: độ rộng của dải trong A2.
- Cách khác: MAD/0,6745 (trung vị độ lệch tuyệt đối), độ lệch chuẩn thường, hoặc chọn σ bằng tinh chỉnh trên D_dev.
- Nguồn: thống kê bền vững chuẩn, có trong các giáo trình (ví dụ Huber, "Robust Statistics"; Rousseeuw và Croux, 1993 về các ước lượng độ phân tán bền vững).
- Phản biện:
  - [Nhẹ] Hệ số 1,349 chỉ đúng khi dữ liệu gần chuẩn. Phân bố ℓ lệch phải, nên σ ước lượng chỉ là "độ rộng tương đối", không phải độ lệch chuẩn thật. Không sai, nhưng không nên gọi là độ lệch chuẩn trong bài.
  - [Nhẹ] Cách tính tứ phân vị chưa ghi trong config: script dùng `statistics.quantiles` (mặc định "exclusive"), trong khi numpy mặc định nội suy tuyến tính. Hai cách cho σ khác nhau một chút. Nên ghi phương pháp vào config hoặc dùng chung một hàm.

### A4. Learnability thực nghiệm L_emp

```
L_emp(G | S_t) = ( Acc_dev(S_t + train(G)) − Acc_dev(S_t) ) / b
```

- Là gì: mức tăng accuracy trên dev khi huấn luyện thử Student trên một nhóm G lời giải, chia cho số bước huấn luyện b.
- Từ đâu ra: dạng cụ thể của định nghĩa chung "learnability = learning_gain / training_cost" trong protocol.
- Vì sao có: L_proxy chỉ là đại lượng gián tiếp; L_emp là "đáp án thật" để kiểm tra L_proxy có ý nghĩa không (proxy validity).
- Dùng để làm gì: tính Spearman giữa L_proxy trung bình theo nhóm và L_emp.
- Cách khác: đo bằng loss trên dev thay vì accuracy (liên tục, ít nhiễu hơn); đo theo capability; dùng ảnh hưởng (influence function) hoặc xấp xỉ gradient như LESS (Xia và cs., 2024) để ước lượng tác động của từng mẫu.
- Nguồn: ý tưởng đo giá trị dữ liệu bằng huấn luyện thử là phổ biến (data valuation, ví dụ Data Shapley của Ghorbani và Zou, 2019); công thức cụ thể là của nhóm.
- Phản biện:
  - [Nặng] Có khả năng tín hiệu nhỏ hơn nhiễu. Sai số chuẩn của accuracy trên 500 câu khoảng 1,9 điểm %, và giữa hai seed của smoke test đã lệch 1,2 điểm, trong khi G chỉ có 50 lời giải và 7 bước huấn luyện. `analysis_plan.md` đã thừa nhận rủi ro này. Nên dùng loss trên dev (hoặc accuracy chấm nới) làm thước đo phụ để có cơ hội thấy tín hiệu.
  - [Vừa] Chia cho b không đổi thứ hạng vì b như nhau cho mọi nhóm; công thức thực chất là mức tăng thô. Không sai, nhưng gọi là "gain/cost" dễ gây hiểu nhầm.
  - [Vừa] 5 nhóm chia theo độ dài, nên L_emp đo "nhóm ngắn hay dài học tốt hơn" chứ không đo learnability theo nghĩa L_proxy. Với chỉ 5 điểm, Spearman chỉ nhận các giá trị rời rạc và rất khó có ý nghĩa thống kê: với n = 5, kiểm định một phía cần ρ ≥ 0,9 (p ≈ 0,042), kiểm định hai phía cần ρ = 1 (p ≈ 0,017).

### A5. Phần dư Brier (lưu kèm, thăm dò)

```
brier_sum = Σ_t ‖π_t − onehot(τ_t)‖² = Σ_t ( Σ_v p_v² − 2·p_{τ_t} + 1 )
```

- Là gì: tổng sai số bình phương giữa phân phối dự đoán và token thật, tính cùng lượt forward với ℓ.
- Từ đâu ra: Brier score (Brier, 1950). Theo ghi chú trong `compute_nll.py`, dùng để tính điểm LARK (Eq. 7) sau này mà không cần chạy lại.
- Dùng để làm gì: hiện chưa dùng; chuẩn bị cho baseline LARK.
- Phản biện: [Nhẹ] Công thức trong code đúng về đại số. Nếu không cài LARK làm baseline thì nên ghi rõ đây là dữ liệu dư, không xuất hiện trong bài.

### A6. Điểm của B6: learnability nhân với mục tiêu capability

```
score(τ | S_t) = L_proxy(τ | S_t) · [ α · 1{c*_t ∈ C(τ)} + (1 − α) · cov(τ) ]
```

- Là gì: kết hợp Đề xuất 2 (learnability) với Đề xuất 1 (capability đang là nút thắt c*_t và độ phủ cov(τ)).
- Từ đâu ra: thiết kế của nhóm.
- Vì sao có: để nối hai đề xuất.
- Cách khác: cộng có trọng số thay vì nhân; chọn theo tầng (lọc theo capability rồi xếp theo L_proxy).
- Nguồn: không có.
- Phản biện:
  - [Vừa] α chưa được tinh chỉnh và c*_t phụ thuộc công thức bottleneck (E4) vốn chưa đo được. B6 đã bị đưa ra khỏi phạm vi bắt buộc; nếu không chạy thì nên bỏ khỏi phần phương pháp chính của bài, chỉ để ở hướng phát triển.

### A7. Hạn ngạch giữ lại r = 50% (chỉ cho B6)

- Là gì: mỗi vòng giữ lại một nửa ngân sách cho dữ liệu đã chọn trước đó.
- Nguồn: theo ghi chép trong `analysis_plan.md`, lấy từ TiC-LM (α_t = 1/2, đã đối chiếu toàn văn), nhưng bối cảnh đó là continual pretraining theo thời gian.
- Phản biện: [Nhẹ] Nhóm đã tự ghi hạn chế này. Vì chỉ dùng cho B6 nên ảnh hưởng thấp.

---

## B. Ngân sách và huấn luyện

### B1. Ngân sách mỗi vòng

```
beta_round = n_round × L̄ = 200 × 227,13 = 45.426 token;   beta_total = M × beta_round = 136.278 token
```

- Là gì: số token lời giải tối đa được huấn luyện mỗi vòng, giống nhau cho mọi phương pháp.
- Từ đâu ra: QĐ #12 và I3 (Task 5). L̄ là độ dài trung bình theo tokenizer Student của pool sơ bộ.
- Vì sao có: so sánh công bằng. Nếu tính theo số mẫu, phương pháp chọn lời giải dài sẽ được học nhiều token hơn.
- Cách khác: ngân sách theo số mẫu; theo FLOPs; theo số bước tối ưu.
- Nguồn: so sánh các phương pháp chọn dữ liệu ở cùng ngân sách là chuẩn trong lĩnh vực (LESS, các benchmark chọn dữ liệu). Con số 200 là quyết định của nhóm, đã kiểm tra qua smoke test.
- Phản biện:
  - [Vừa] L̄ lấy từ pool sơ bộ, trong khi pool chính thức dài hơn 8,2%. Mỗi vòng thực tế chỉ chứa khoảng 185 lời giải. Không sai về công bằng (vẫn cùng token), nhưng cần ghi rõ, và kiểm tra B3 (chọn lời giải ngắn nhất) sẽ được nhiều lời giải hơn hẳn các phương pháp khác trong cùng ngân sách.
  - [Nhẹ] Chỉ tính token lời giải, không tính token đề bài, trong khi chi phí tính toán gồm cả hai. Đã ghi trong analysis plan.

### B2. Hàm mất mát SFT chỉ trên lời giải

```
L(θ) = − Σ_{(x,τ)∈B} Σ_t log p_θ(τ_t | x, τ_<t)    (token đề bài bị che)
```

- Nguồn: chuẩn của fine-tuning có giám sát; "completion-only loss" là mặc định phổ biến (ví dụ trong thư viện TRL). Theo `analysis_plan.md`, các siêu tham số LoRA lấy theo QLoRA (Dettmers và cs., 2023).
- Phản biện:
  - [Vừa] Code lấy trung bình trên token của cả batch hiệu dụng, không phải tổng như công thức trong bài. Hai cách chỉ khác hệ số, nhưng ảnh hưởng tới learning rate thực tế; công thức trong bài nên viết đúng như code.
  - [Nhẹ] Siêu tham số chưa tinh chỉnh; đã ghi trong hạn chế.

### B3. Yêu cầu kích thước pool

```
pool ≥ 3 đến 5 × n_round  →  ≥ 1.000 bài
```

- Vì sao có: với n_cap = 1, mỗi vòng chọn tối đa một lời giải mỗi bài, nên số bài phải lớn hơn nhiều so với số lời giải chọn mỗi vòng, nếu không mọi phương pháp sẽ chọn gần như cùng một tập.
- Nguồn: quyết định của nhóm (QĐ #12).
- Phản biện: [Nhẹ] Hệ số 3 đến 5 không có lý do định lượng. Có thể bổ sung bằng một con số kiểm tra được: tỉ lệ trùng giữa tập chọn của B2 và B4 ở vòng 1. Nếu trùng quá nhiều thì pool vẫn nhỏ.

### B4. Quy tắc seed sinh lời giải

```
generation_seed = 20261009 + problem_index × 5 + k
```

- Là gì: mỗi lời giải có một seed riêng, không trùng nhau.
- Nguồn: kỹ thuật lập trình để tái lập, không cần nguồn khoa học.
- Phản biện: không có vấn đề. Đã kiểm tra 0 lỗi trên 5.500 lời giải.

---

## C. Chấm đáp án và lọc dữ liệu

### C1. Đúng hay sai (I1)

```
đúng ⇔ final_number(ANSWER) = final_number(ground_truth)   (số cuối cùng, bỏ "," "$" "%", chuẩn hoá Decimal)
```

- Nguồn: lấy số cuối cùng làm đáp án là cách làm phổ biến khi đánh giá GSM8K (Cobbe và cs., 2021 dùng đáp án sau "####"; nhiều bộ đánh giá lấy số cuối).
- Phản biện:
  - [Vừa] Lời giải sai định dạng bị tính là sai dù đáp án đúng. Smoke test cho thấy khoảng 40% mức tăng là do học định dạng. Đã có accuracy chấm nới làm chỉ số chẩn đoán; nên đưa nó vào kế hoạch phân tích trước khi chạy.
  - [Nhẹ] Bỏ dấu "%" có thể gây đúng nhầm khi đáp án là phần trăm và Teacher ghi tỉ lệ (0,25 so với 25). Hiếm, nhưng nên kiểm tra vài ví dụ.

### C2. Accuracy chấm nới (thăm dò)

- Là gì: so số cuối của toàn bộ output (hoặc `\boxed{}` cuối) với đáp án, bỏ qua định dạng.
- Phản biện: [Vừa] Có thể đúng nhầm khi số cuối trùng ngẫu nhiên với đáp án (ví dụ một bước trung gian). Chỉ nên dùng để chẩn đoán, không làm chỉ số chính. Nên kiểm tra thủ công một mẫu nhỏ để ước lượng tỉ lệ đúng nhầm.

### C3. Lọc câu gần trùng bằng 13-gram

- Là gì: loại khỏi pool câu nào có chung ít nhất một chuỗi 13 từ liên tiếp với dev hoặc test.
- Nguồn: phân tích nhiễm dữ liệu của GPT-3 (Brown và cs., 2020) dùng đúng ngưỡng 13-gram. Đây là cơ sở tài liệu cho con số 13; `missing_progress.md` đang ghi là "chưa có cơ sở", nên cập nhật.
- Phản biện: [Nhẹ] 13-gram chỉ bắt được trùng gần nguyên văn, không bắt được bài viết lại với số khác (cùng cấu trúc). Với GSM8K, đây là giới hạn chấp nhận được, ghi trong hạn chế.

### C4. Khoảng tin cậy Clopper–Pearson cho tỉ lệ bài không có lời giải đúng

- Nguồn: Clopper và Pearson (1934), khoảng tin cậy chính xác cho tỉ lệ nhị thức.
- Phản biện: không có vấn đề. Đã dùng đúng để dự đoán số bài bị loại (thực tế 6,2%, nằm trong [1,6%; 11,3%]).

### C5. Kiểm định hai tỉ lệ cho invalid_format (batch_100 so với bài mới)

- Nguồn: z-test hai tỉ lệ, chuẩn.
- Phản biện: [Vừa] Phép thử coi 5.500 lời giải là độc lập, nhưng 5 lời giải của cùng một bài có tương quan. p = 0,31 vì vậy hơi lạc quan về độ chính xác. Kết luận "không khác nhau" vẫn đứng, nhưng nếu đưa vào bài thì nên tính theo cụm bài (ví dụ bootstrap theo bài).

---

## D. Phân tích thống kê (kế hoạch đã chốt)

### D1. McNemar trong từng seed

- Nguồn: McNemar (1947), kiểm định cho dữ liệu cặp nhị phân; Dietterich (1998) khuyến nghị cho so sánh hai bộ phân loại trên cùng tập test.
- Phản biện: không có vấn đề về phương pháp. [Nhẹ] Nên ghi rõ dùng bản chính xác (nhị thức) hay bản xấp xỉ chi bình phương; code smoke test dùng bản chính xác.

### D2. Trung bình chênh lệch qua seed kèm CI 95%

- Phản biện: [Nặng] Chỉ có 3 seed. CI dựa trên phân phối t với 2 bậc tự do có hệ số 4,30, rất rộng. Gần như chắc chắn CI sẽ chứa 0 trừ khi khác biệt lớn. Cần nói trước điều này trong bài, và dựa nhiều hơn vào McNemar trong từng seed cùng tính nhất quán chiều của khác biệt qua cả 3 seed. Thêm 2 seed tuỳ chọn (7, 77) nếu GPU cho phép sẽ giúp nhiều.

### D3. Bootstrap cặp trên tập test

- Nguồn: Efron (1979); áp dụng cho so sánh hệ thống NLP trong Koehn (2004), Berg-Kirkpatrick và cs. (2012).
- Phản biện: không có vấn đề.

### D4. Ngưỡng dung sai ε và trần nhiễu ρ_noise

```
ε = nửa độ rộng 95% của nhiễu đo;  thay đổi thật ⇔ |L(τ|S_{t+1}) − L(τ|S_t)| > ε
```

- Là gì: mức thay đổi tối thiểu để coi learnability của một lời giải "thật sự thay đổi".
- Từ đâu ra: thiết kế của nhóm, theo tinh thần độ tin cậy test-retest trong đo lường.
- Phản biện:
  - [Nặng] Định nghĩa chưa đủ cụ thể để tính: "nhiễu đo" là phân phối của cái gì? Hiệu L giữa hai seed của từng lời giải? Độ lệch chuẩn đó chia √2 hay không? Lấy 1,96 × SD hay phân vị 97,5% thực nghiệm? Mỗi cách cho ε khác nhau. Cần viết công thức chính xác và chốt trước khi đo.
  - [Vừa] Đo nhiễu bằng hai seed huấn luyện khác nhau đo cả biến thiên do huấn luyện, không chỉ sai số đo. Đây là lựa chọn hợp lý (đúng loại nhiễu cần loại trừ), nhưng nên gọi đúng tên.

### D5. So ρ(L_t, L_{t+1}) với ρ_noise

- Phản biện: [Nặng] Kế hoạch ghi "ρ thấp hơn có ý nghĩa so với ρ_noise" nhưng chưa nói dùng kiểm định nào. Hai hệ số tương quan này tính trên cùng tập lời giải nên phụ thuộc nhau; cần kiểm định cho tương quan phụ thuộc (ví dụ Steiger, 1980) hoặc bootstrap theo lời giải. Phải chốt trước khi chạy.

### D6. Wilcoxon cho thay đổi theo lời giải

- Nguồn: Wilcoxon (1945).
- Phản biện: [Nặng] Với khoảng 4.000 lời giải, gần như mọi chênh lệch nhỏ đều có ý nghĩa thống kê, và sau huấn luyện ℓ giảm gần như cho mọi lời giải. Wilcoxon trên ℓ sẽ luôn có ý nghĩa mà không nói gì về giả thuyết H. Trên L_proxy, do đã đặt lại tâm (A2), kết quả cũng khó diễn giải. Cần báo cáo effect size và tách lời giải đã học với chưa học (mục 2.4 của `Task.md`).

### D7. Jaccard(B_t, B_{t+1}) và phân loại profile

- Nguồn: Jaccard (1901); profile tăng, giảm, ổn định, không đơn điệu là định nghĩa của nhóm dựa trên ε.
- Phản biện: [Vừa] Với B4, lịch chọn cố định từ S_0 nên Jaccard qua các vòng phụ thuộc quy tắc chọn lại, không phản ánh learnability. Chỉ nên so Jaccard của B5 với một mốc tham chiếu (ví dụ Jaccard của B2 ngẫu nhiên, hoặc của hai seed cùng checkpoint).

### D8. Proxy validity: Spearman(L_proxy, L_emp) kèm bootstrap

- Nguồn: Spearman (1904); bootstrap như D3.
- Phản biện: [Nặng] Chỉ có 5 nhóm (xem A4), Spearman trên 5 điểm gần như không thể có ý nghĩa thống kê và CI bootstrap rất rộng. Nên tăng số nhóm (ví dụ 10 nhóm × 25 lời giải) hoặc chấp nhận trước rằng kết quả chỉ mang tính mô tả.

### D9. Holm–Bonferroni

- Nguồn: Holm (1979).
- Phản biện: không có vấn đề.

### D10. Các ngưỡng quyết định đặt trước

| Ngưỡng | Dùng ở | Cơ sở | Phản biện |
|---|---|---|---|
| Δaccuracy ≥ 2 điểm % hoặc McNemar p < 0,1 | Smoke test | Sai số chuẩn accuracy trên 500 câu khoảng 1,9 điểm % | Hợp lý cho mục đích kiểm tra; p < 0,1 lỏng hơn mức 0,05 thông thường, nên ghi lý do |
| Teacher hơn Student ≥ 5 điểm % | Giữ cặp mô hình | Quyết định nhóm | [Vừa] Không có cơ sở định lượng; con số liên quan trực tiếp hơn là số câu Teacher đúng mà Student sai (khoảng 55/500) |
| Lệch tỉ lệ hợp lệ ≤ 5 điểm %, lệch độ dài ≤ 10% | Parity vLLM/HF | Quyết định nhóm | [Nhẹ] 5 điểm % rộng so với sai số chuẩn khoảng 1,8 điểm % trên 500 lời giải; kết quả thực tế lệch 0,8 nên không ảnh hưởng |
| "Khoảng 40% mức tăng là do định dạng" | Diễn giải smoke test | 1 − Δ(chấm nới) / Δ(chấm chặt) = 1 − 6,8/11,2 ≈ 39% | [Nhẹ] Là tỉ lệ của các giá trị trung bình, không có CI; nên viết "khoảng" như đã làm |

---

## E. Capability và Đề xuất 1

### E1. Mastery và deficit

```
M(c | S_t) = accuracy của Student trên tập con dev cần capability c;    D(c | S_t) = 1 − M(c | S_t)
```

- Nguồn: đo năng lực theo kỹ năng là ý tưởng của knowledge tracing (Corbett và Anderson, 1994) và đánh giá theo kỹ năng; công thức cụ thể là của nhóm.
- Phản biện:
  - [Vừa] Một câu thường cần nhiều capability (94/100 câu batch 100), nên sai một câu bị tính là yếu ở mọi capability của câu đó. M(c) vì vậy bị trộn lẫn giữa các capability. Có thể dùng hồi quy logistic trên các capability (mô hình kiểu Q-matrix trong cognitive diagnosis) để tách.
  - [Vừa] Capability của câu dev lấy từ đâu: nhãn thủ công (chỉ có cho 100 + 85 câu) hay extractor (F1 0,86 đến 0,96, chưa kiểm tra trên lời giải Student)? Cần chốt.

### E2. Bản phương pháp của bài báo dùng "gap" theo từ khoá

```
h_c(x) = số từ khoá của c xuất hiện trong x;   g_c(θ) = (1/|E(θ)|) · Σ_{q∈E(θ)} h_c(q),  E(θ) = {Teacher đúng ∧ Student sai}
```

- Phản biện: [Nặng] Không khớp với dự án hiện tại. Dự án đã bỏ cách gán capability bằng từ khoá, chuyển sang extractor theo luật (Task 4), và protocol dùng deficit D = 1 − M. `notes/methodology_formulas.md` còn dẫn các script LM Studio cũ không còn dùng. Nếu bài báo giữ công thức g_c, hội đồng sẽ thấy mâu thuẫn với phần thực nghiệm. Cần viết lại phần này của bài báo theo protocol hiện tại.

### E3. Transfer và bottleneck

```
Protocol:   T(A → B | S_t) = mức tăng M(B) khi huấn luyện riêng A;   bottleneck(i) = D_i · Σ_j T(i → j)
Bài báo:    w_tr(c → c′) = m_{c′}(θ + Δ_c) − m_{c′}(θ);   B(c) = g_c · Σ w_tr · R(c),   R(c) = Π m_{c″} trên các tiền đề c″
```

- Nguồn: ý tưởng transfer giữa các tác vụ có trong Taskonomy (Zamir và cs., 2018) và các nghiên cứu về chọn tác vụ phụ trợ; cấu trúc tiền đề gần với knowledge space theory. Công thức cụ thể là của nhóm. Protocol tự ghi đây "không phải công thức cuối cùng".
- Phản biện:
  - [Nặng] Hai phiên bản không thống nhất: protocol dùng D, bài báo dùng g và thêm thừa số R. Cần chọn một.
  - [Nặng] T cần huấn luyện can thiệp riêng cho từng capability (7 capability × nhiều seed), dự án đã quyết định không làm. Nếu không đo T, mọi công thức bottleneck và readiness không có số để tính. Bài báo chỉ nên trình bày chúng như hướng phát triển, hoặc bỏ.
  - [Vừa] R là tích các mastery, nên một tiền đề có mastery thấp kéo R về gần 0. Hiệu ứng "cổng" này là chủ ý, nhưng rất nhạy với nhiễu của M (đặc biệt với capability hiếm như ratio, chỉ 19 câu trong pool).

### E4. Trọng số cạnh tiền đề (bài báo)

```
w_pre(c′ → c) = P(Student sai câu cần c | sai câu cần c′) − P(Student sai câu cần c)
```

- Phản biện: [Vừa] Đây là tương quan có điều kiện, không phải quan hệ tiền đề. Hai capability hay đi cùng nhau trong một câu (cộng và nhân cùng xuất hiện ở 2.155/4.353 lời giải của pool) sẽ có w_pre cao mà không cần có quan hệ phụ thuộc. Nếu giữ, phải gọi là "đồng thất bại" (co-failure) và không suy ra nhân quả.

### E5. Precision, Recall, F1 của extractor; Cohen's kappa giữa người gán nhãn

- Nguồn: F1 (van Rijsbergen, 1979); Cohen's kappa (Cohen, 1960).
- Phản biện:
  - [Vừa] Kappa = 1,0 chưa dùng được vì chưa xác minh A2 gán nhãn độc lập. Đã ghi trong hạn chế.
  - [Nhẹ] F1 tính trên 480 lời giải của 100 câu, nên các lời giải cùng câu không độc lập; F1 theo câu và theo lời giải nên báo cáo cả hai.

### E6. Điểm độ khó d(q) ∈ [0, 8] (bài báo, giai đoạn đầu)

```
d(q) = f_len(q) + f_num(q) + f_op(q) + f_frac(q)
```

- Nguồn: heuristic của nhóm ở giai đoạn baseline, không có nguồn.
- Phản biện: [Vừa] Không còn dùng trong thí nghiệm hiện tại. Nếu bài báo vẫn trình bày thì cần nói rõ chỉ dùng để mô tả dữ liệu ban đầu, hoặc bỏ để tránh câu hỏi "tại sao trọng số các thành phần bằng nhau".

---

## F. Tóm tắt: những gì cần làm trước khi chạy thí nghiệm chính

Các vấn đề [Nặng], xếp theo mức ưu tiên:

1. Viết công thức chính xác cho ε và chọn kiểm định so ρ(L_t, L_{t+1}) với ρ_noise (D4, D5). Phải chốt trước khi đo, nếu không phần kiểm định giả thuyết H không có quy tắc.
2. Bổ sung phân tích không phụ thuộc việc đặt lại tâm: thứ hạng ℓ, và tách lời giải đã học với chưa học (A2, D6).
3. Thêm ít nhất một biến thể chọn theo ℓ cao và ℓ thấp (một seed, ghi là thăm dò) để trả lời "tại sao chọn vùng giữa" (A2).
4. Tăng số nhóm của L_emp hoặc chấp nhận trước rằng proxy validity chỉ mang tính mô tả; dùng loss trên dev làm thước đo phụ (A4, D8).
5. Nói trước trong bài rằng CI qua 3 seed rất rộng; dựa vào McNemar từng seed và tính nhất quán chiều; chạy thêm seed nếu có GPU (D2).
6. Viết lại phần Đề xuất 1 trong bài báo theo protocol hiện tại (deficit thay cho gap theo từ khoá), và chuyển transfer/bottleneck/readiness sang hướng phát triển nếu không đo T (E2, E3).

Các vấn đề [Vừa] nên làm khi có thời gian:
- Kiểm tra tương quan giữa ℓ và độ dài lời giải (A1).
- Ghi rõ trung vị có loại lời giải đã học hay không (A2).
- Đưa accuracy chấm nới vào kế hoạch phân tích (C1).
- Viết công thức loss đúng như code (trung bình theo token) (B2).
- Kiểm định theo cụm bài khi so tỉ lệ giữa các nhóm lời giải (C5).
- Chốt nguồn nhãn capability cho tập dev khi tính mastery (E1).

Công thức có nguồn chuẩn và không có vấn đề: σ = IQR/1,349, 13-gram (GPT-3), Clopper–Pearson, McNemar, bootstrap cặp, Holm–Bonferroni, Brier, F1, quy tắc seed.
