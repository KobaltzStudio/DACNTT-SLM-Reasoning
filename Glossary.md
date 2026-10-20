# SmallNote: Thuật ngữ và ký hiệu trong dự án

Tra cứu nhanh các keyword dùng trong protocol, config và báo cáo. Giá trị cụ thể lấy từ `experiments/week2September/manual/config/experiment_config.json` (config v1, 2026-10-14). Giá trị đánh dấu *(tạm)* đang chờ smoke test.

---

## 1. Mô hình và checkpoint

| Keyword | Ý nghĩa |
|---|---|
| **Teacher (T)** | Mô hình lớn sinh lời giải mẫu: `Qwen/Qwen2.5-3B-Instruct` |
| **Student (S)** | Mô hình nhỏ học lại từ lời giải của Teacher: `Qwen/Qwen2.5-1.5B-Instruct` |
| **S_t** | Student tại checkpoint thứ t (sau t vòng huấn luyện) |
| **S_0** | Student gốc, chưa fine-tune |
| **S_1, S_2, S_3** | Student sau vòng 1, 2, 3 |
| **S_{t+1} = Train(S_t, B_t)** | Vòng huấn luyện: lấy S_t, huấn luyện trên tập đã chọn B_t, được S_{t+1} |
| **`student_ckpt_{t:03d}`** | Tên lưu checkpoint, ví dụ `student_ckpt_000` = S_0 |
| **M** | Số vòng huấn luyện. M = 3 (S_0 → S_3) |
| **revision** | Mã commit của model trên HuggingFace, ghim cố định để chạy lại được |

## 2. Dữ liệu và tập chia

| Keyword | Ý nghĩa |
|---|---|
| **GSM8K** | Bộ bài toán đố tiểu học nhiều bước (7.473 câu train, 1.319 câu test) |
| **D_pool** | 6.968 câu từ GSM8K train, dùng để Teacher sinh lời giải và chọn dữ liệu huấn luyện |
| **D_dev** | 500 câu từ GSM8K train (85 câu bổ sung + 415 ngẫu nhiên), không trùng D_pool. Dùng để đo đạc và ra quyết định, **không bao giờ dùng để huấn luyện** |
| **D_test** | 1.319 câu GSM8K test chính thức, **chỉ dùng để báo cáo** kết quả cuối |
| **split_seed** | Seed chia tập: 363636 |
| **near-duplicate** | Câu trong D_pool có đoạn trùng ≥ 13 từ liên tiếp (13-gram) với D_dev/D_test thì bị loại. Đã loại 5 câu |
| **batch 100** | 100 câu đầu tiên được gán nhãn thủ công và sinh pool sơ bộ; nằm trong D_pool |
| **pilot 30** | 30 câu (thuộc batch 100) dùng để đo độ đồng thuận giữa 2 người gán nhãn |
| **supplement (85 câu)** | Câu bổ sung để đủ mẫu ratio/percentage/fraction; nằm trong D_dev |
| **problem_id** | Mã câu hỏi, ví dụ `gsm8k_train_00000`. Chia tập theo problem_id |

## 3. Trajectory và pool

| Keyword | Ý nghĩa |
|---|---|
| **trajectory (τ, tau)** | Một lời giải từng bước (chain-of-thought) Teacher sinh cho một câu hỏi |
| **CoT** | Chain-of-Thought: lời giải trình bày từng bước suy luận |
| **reasoning trace** | Phần suy luận trong trajectory (sau `REASONING:`) |
| **raw_generation** | Toàn bộ output gốc của Teacher (`REASONING: ... ANSWER: ...`). Dùng làm target khi huấn luyện |
| **trajectory_id** | Mã lời giải, ví dụ `gsm8k_train_00000_traj_001` |
| **K** | Số lời giải sinh cho mỗi câu: K = 5 |
| **temperature** | Độ ngẫu nhiên khi Teacher sinh: 0.7 |
| **generation_seed** | Seed sinh lời giải = 20261009 + problem_index × K + k |
| **P (pool)** | Tập ứng viên gồm các trajectory đã qua kiểm tra. Pool không bao giờ bị cắt bớt |
| **pool sơ bộ** | 500 trajectory cho batch 100: 480 hợp lệ trên 98 câu |
| **pool chính thức** | Pool cần có cho thí nghiệm chính: ≥ 1.000 câu thuộc D_pool |
| **verification_status** | `valid` (đúng), `invalid_answer` (sai đáp án), `invalid_format` (sai định dạng) |
| **eligible** | Trajectory đủ điều kiện để chọn: đã qua kiểm tra đáp án, định dạng và capability |
| **prompt v1 / PROMPT_TEMPLATE** | Mẫu prompt chung cho Teacher và Student, yêu cầu trả về `REASONING:` và `ANSWER:` |
| **answer_utils** | `scripts/answer_utils.py`: trích số cuối trong phần ANSWER và so với ground truth |
| **ground_truth** | Đáp án đúng của GSM8K |

## 4. Capability (Đề xuất 1)

| Keyword | Ý nghĩa |
|---|---|
| **capability (c)** | Kỹ năng cần để giải bài. Taxonomy cố định gồm 7 loại: addition, subtraction, multiplication, division, percentage, fraction, ratio |
| **C(τ)** | Tập capability xuất hiện trong trajectory τ |
| **taxonomy** | Danh sách capability, đã chốt cho giai đoạn thủ công |
| **gold** | Nhãn capability thủ công (cấp câu hỏi), dùng làm chuẩn để chấm extractor |
| **capability extractor** | Bộ trích capability tự động dựa trên luật (`capability_rules_v2.json`) |
| **guideline v3** | Quy tắc gán nhãn hiện hành (ví dụ: "half of N" chỉ là fraction, không tính division) |
| **D1, D2, D3** | Ba quyết định định nghĩa capability đã chốt trong Task 4 |
| **A1, A2** | Người gán nhãn thứ nhất và thứ hai |
| **Cohen's kappa (κ)** | Độ đồng thuận giữa hai người gán nhãn (1.0 = trùng hoàn toàn) |
| **adjudication** | Xem xét thủ công từng trường hợp extractor và gold không khớp |
| **M(c \| S_t)** | Mastery: accuracy của Student trên các câu thuộc capability c tại S_t |
| **D(c \| S_t)** | Deficit: 1 − M(c \| S_t), mức Student còn yếu ở capability c |
| **ΔM(c, t)** | Thay đổi mastery giữa hai checkpoint liên tiếp |
| **T(A → B \| S_t)** | Transfer: huấn luyện capability A làm mastery của B thay đổi bao nhiêu |
| **prerequisite edge** | Cạnh phụ thuộc A → B (A là tiền đề của B) |
| **bottleneck (c\*_t)** | Capability nút thắt tại S_t: yếu và cải thiện nó có thể kéo theo nhiều capability khác |
| **B_i** | Điểm bottleneck đề xuất: D_i × Σ_j T(i → j) |
| **G_t** | Đồ thị capability tại S_t |
| **plateau / sudden gain / sudden drop** | Trạng thái đường cong học: đi ngang / tăng đột biến / giảm đột biến |
| **θ_plateau, θ_anomaly** | Ngưỡng phân loại các trạng thái trên (ví dụ θ_anomaly = 0.20) |

## 5. Learnability (Đề xuất 2)

| Keyword | Ý nghĩa |
|---|---|
| **learnability L(τ \| S_t)** | Mức "dễ học" của trajectory τ đối với Student ở trạng thái S_t |
| **ℓ(τ \| S_t)** | NLL chuẩn hoá theo độ dài: mức Student "bất ngờ" khi đọc τ (1 forward pass, không backward) |
| **NLL** | Negative log-likelihood. Thấp = Student thấy quen, cao = thấy lạ |
| **L_proxy** | Độ dễ học ước lượng, dùng để chọn dữ liệu: exp(−(ℓ − ℓ\*_t)² / (2σ_t²)). Cao nhất khi ℓ ở vùng giữa |
| **ℓ\*_t** | Tâm của dải: median của ℓ trên pool tại S_t |
| **σ_t** | Độ rộng dải: IQR của ℓ / 1.349 |
| **band** | Vùng ℓ gần ℓ\*_t, nơi trajectory được coi là dễ học nhất |
| **L_emp** | Độ dễ học đo thật: (Acc_dev sau khi huấn luyện nhóm G − Acc_dev trước) / b. Dùng để kiểm chứng L_proxy |
| **G (group)** | Nhóm trajectory dùng để đo L_emp: 50 trajectory/nhóm, chia 5 nhóm theo độ dài token |
| **probe** | Lần huấn luyện thử ngắn trên một nhóm G để đo L_emp |
| **learnability profile** | Chuỗi giá trị L(τ \| S_0), L(τ \| S_1), ... của một trajectory |
| **increasing / decreasing / stable / non-monotonic** | Các dạng profile: tăng / giảm / ổn định / lên xuống |
| **H** | Giả thuyết chính: L(τ \| S_t) thay đổi khi Student thay đổi |
| **H_sel** | Hệ quả: nếu H đúng thì chọn lại dữ liệu mỗi vòng (B5) tốt hơn chọn một lần (B4) |

## 6. Chọn dữ liệu (selection)

| Keyword | Ý nghĩa |
|---|---|
| **B_t** | Tập trajectory được chọn để huấn luyện ở vòng t |
| **π(P; S_t)** | Chính sách chọn: từ pool P và trạng thái S_t cho ra B_t |
| **score(τ \| S_t)** | Điểm chọn đầy đủ: L_proxy × [α·𝟙{c\*_t ∈ C(τ)} + (1 − α)·cov(τ)] |
| **α (alpha)** | Trọng số giữa ưu tiên bottleneck và độ phủ capability: 0.5 (chưa tune). Chỉ ảnh hưởng B6 |
| **cov(τ)** | Tỉ lệ capability chưa thành thạo mà τ bao phủ |
| **n_cap** | Số trajectory tối đa của cùng một câu trong một vòng: 1 |
| **retention quota (r)** | Phần ngân sách dành cho capability đã thành thạo để hạn chế quên: 50% (theo TiC-LM). Chỉ áp dụng B6 |
| **reselect** | Cho phép chọn lại trajectory ở các vòng sau: có |
| **tie-break** | Cách xử lý điểm bằng nhau: theo `trajectory_id` tăng dần |
| **selection log** | File ghi điểm, danh sách được chọn và ngân sách đã dùng mỗi vòng (`selection_log_schema.json`) |

## 7. Ngân sách (budget)

| Keyword | Ý nghĩa |
|---|---|
| **β_gen** | Ngân sách sinh của Teacher: K = 5 trajectory/câu |
| **β_round** | Ngân sách huấn luyện mỗi vòng, tính bằng token response: 45.426 token *(tạm)* |
| **n_round** | Số trajectory mỗi vòng: 200 *(tạm)*. β_round = n_round × độ dài trung bình |
| **L̄** | Độ dài response trung bình theo tokenizer Student: 227,13 token |
| **β_total** | Tổng ngân sách = M × β_round = 136.278 token, giống nhau cho mọi phương pháp |
| **b** | Probe budget: số optimizer step cho một lần đo L_emp: 7 step *(tạm)* |
| **β_est** | Chi phí ước lượng learnability: số forward pass của Student mỗi checkpoint (phải báo cáo) |

## 8. Huấn luyện

| Keyword | Ý nghĩa |
|---|---|
| **SFT** | Supervised fine-tuning: huấn luyện Student bắt chước lời giải của Teacher |
| **KD / RKD** | (Reasoning) Knowledge Distillation: chuyển khả năng suy luận từ Teacher sang Student |
| **LoRA** | Fine-tune bằng adapter hạng thấp: r = 16, alpha = 32, dropout 0.1, áp dụng mọi lớp linear *(tạm)* |
| **QLoRA** | LoRA trên model nén 4-bit; chỉ dùng cho smoke test trên GPU 4GB |
| **adapter** | Phần trọng số LoRA; được giữ và huấn luyện tiếp qua các vòng |
| **completion-only loss** | Loss chỉ tính trên phần lời giải, prompt bị mask |
| **lr** | Learning rate: 2e-4, constant *(tạm)* |
| **effective batch size** | Batch thực tế = per-device × gradient accumulation: 8 *(tạm)* |
| **epochs_per_round** | 1 epoch mỗi vòng |
| **training_seed** | Seed huấn luyện: 13, 42, 2026 (thêm 7, 77 nếu đủ tài nguyên) |
| **data_order_seed** | Seed xáo dữ liệu = training_seed |
| **smoke test** | Chạy thử 1 vòng S_0 → S_1 trên D_dev để chốt tham số tạm (Task.md mục 0.1) |

## 9. Phương pháp so sánh (baselines)

| ID | Tên | Cách chọn dữ liệu |
|---|---|---|
| **B0** | No training | Không huấn luyện, chỉ S_0 |
| **B1** | Full pool | Huấn luyện trên toàn bộ pool (tham chiếu, tốn hơn, tuỳ chọn) |
| **B2** | Random | Chọn ngẫu nhiên mỗi vòng, cùng ngân sách |
| **B3** | Heuristic | Mỗi câu lấy lời giải ngắn nhất, chọn một lần |
| **B4** | Static learnability | Dùng L_proxy tính **một lần** tại S_0 cho mọi vòng |
| **B5** | Dynamic learnability | Tính lại L_proxy **mỗi vòng** tại S_t |
| **B6** | Dynamic + bottleneck | B5 + điểm bottleneck/coverage + retention (tuỳ chọn) |
| **shuffled scores** | Ablation | Chọn lại mỗi vòng nhưng xáo điểm, để tách hiệu ứng "chọn lại" khỏi tín hiệu learnability |
| **B5 vs B4** | So sánh chính | Chỉ khác nhau ở việc có tính lại learnability hay không |

## 10. Đánh giá và thống kê

| Keyword | Ý nghĩa |
|---|---|
| **Acc / exact-match accuracy** | Tỉ lệ câu có đáp án cuối khớp ground truth. Metric chính, đo trên D_test |
| **greedy decoding** | Sinh không ngẫu nhiên (temperature 0), max 512 token khi đánh giá |
| **format compliance** | Tỉ lệ output đúng định dạng `REASONING:` / `ANSWER:` |
| **Spearman ρ** | Tương quan thứ hạng; dùng đo độ ổn định xếp hạng L giữa hai checkpoint |
| **ρ_noise** | Tương quan khi đo lại cùng một checkpoint: mức nhiễu nền |
| **ε (epsilon)** | Ngưỡng "xấp xỉ bằng": thay đổi nhỏ hơn ε coi như không đổi |
| **Jaccard(B_t, B_{t+1})** | Độ trùng giữa tập được chọn ở hai vòng liên tiếp |
| **band transitions** | Tỉ lệ trajectory vào/ra dải learnability giữa hai checkpoint |
| **McNemar** | Kiểm định cặp đúng/sai từng câu giữa hai mô hình (trong một seed) |
| **Wilcoxon signed-rank** | Kiểm định thay đổi L theo từng trajectory giữa hai checkpoint |
| **paired bootstrap** | Lấy mẫu lại để ước lượng khoảng tin cậy cho chênh lệch accuracy |
| **95% CI** | Khoảng tin cậy 95% |
| **Holm-Bonferroni** | Hiệu chỉnh khi làm nhiều kiểm định cùng lúc |
| **α = 0.05** | Mức ý nghĩa thống kê (khác với α trọng số chọn dữ liệu ở mục 6) |
| **pre-registration / freeze** | Chốt thiết kế, tham số và phân tích **trước** khi xem kết quả |
| **exploratory** | Phân tích không nằm trong kế hoạch chốt trước; chỉ mang tính thăm dò |
| **null result** | Không tìm thấy khác biệt; vẫn phải báo cáo đầy đủ |

## 11. Quản lý thí nghiệm

| Keyword | Ý nghĩa |
|---|---|
| **Đề xuất 1** | Student-Specific Prerequisite-Transfer Graph Distillation (capability, transfer, learning dynamics) |
| **Đề xuất 2** | Dynamic Learnability-Aware CoT Distillation (trọng tâm chính) |
| **Task 1–9** | Các đầu việc của nhóm: 1–3 thủ công, 4 extractor, 5 freeze, 6 pool, 7 S_0 → S_1, 8 tài liệu/môi trường, 9 cloud |
| **config v1 / v2** | Phiên bản `experiment_config.json`. Mọi thay đổi sau freeze phải tạo version mới kèm lý do |
| **I1–I8** | Các đề xuất tham số trong `task5_decisions.md` mục I. I3 (budget), I4 (b), I5 (hyperparameters) còn tạm |
| **SHA256SUMS** | File mã băm để chứng minh dữ liệu/config không bị sửa sau khi chốt |
| **manifest** | File mô tả nguồn, quy tắc, số lượng và hash (ví dụ `split_manifest.json`) |
| **TiC-LM** | Bài báo (ACL 2025) làm nguồn cho retention r = 50% |
| **LM Studio** | Phần mềm chạy model local, dùng ở giai đoạn đầu để gọi Teacher qua API kiểu OpenAI |
