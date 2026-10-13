# Giải thích công thức: Phần 3. Methodology

Nguồn: `Adaptive_Reasoning_Knowledge_Distillation-2.docx`
Số dòng = số thứ tự đoạn văn (paragraph) khi trích xuất `word/document.xml` (phần 3 nằm ở **dòng 36-127**).

Ký hiệu chung: `q` = đề bài, `a` = đáp án đúng, `τ` = một trajectory (chuỗi suy luận CoT) của Teacher,
`θ` = tham số Student, `C` = tập capability (kỹ năng suy luận), `P` = trajectory pool, `B` = tập con được chọn để train.

---

## 3.1 Problem Formulation (dòng 37-58)

### (1) Tập dữ liệu (dòng 39)

**Công thức**

```
D = {(q_i, a_i)}_{i=1}^{N}
```

**Giải thích**
- Bộ dữ liệu suy luận gồm `N` cặp (đề bài, đáp án cuối đúng). Ở đây là GSM8K.
- `a_i` là ground-truth dùng để verify tự động, không phải lời giải mẫu.

**Code**
- `scripts/inspect_gsm8k.py/line1-120`: nạp và kiểm tra GSM8K
- `experiments/week2September/processed/trajectory_questions_50.jsonl`: `D` thực dùng (50 câu), sinh bởi `scripts/select_trajectory_subset.py/line18-63`

---

### (2) Tập trajectory ứng viên của một đề bài (dòng 42)

**Công thức**

```
P_i = { τ_i^1 , τ_i^2 , … , τ_i^K }
```

**Giải thích**
- Với mỗi `q_i`, sample Teacher `K` lần bằng stochastic decoding (temperature > 0) để thu `K` lời giải khác nhau.
- Phải dùng sampling chứ không greedy: greedy chỉ cho 1 đường suy luận ⇒ không có gì để "chọn lọc".
- Trong thí nghiệm: `K = 5`, `temperature = 0.7`, `max_tokens = 512`.

**Code**
- `scripts/generate_teacher_trajectories.py/line19-22`: `NUM_TRAJECTORIES=5`, `TEMPERATURE=0.7`, `MAX_TOKENS=512`
- `scripts/generate_teacher_trajectories.py/line193-241`: vòng lặp sample `K` lần / câu
- `scripts/generate_teacher_trajectories.py/line114-140`: checkpoint & resume theo khoá `(question_id, trajectory_id)`

---

### (3) Trajectory pool (dòng 44)

**Công thức**

```
P = ⋃_i P_i
```

**Giải thích**
- Hợp tất cả trajectory của mọi đề bài ⇒ "kho" `P` (50 câu × 5 = 250 trajectory).
- Điểm mấu chốt của paper: **`P` không bao giờ bị xoá bớt**; mọi phương pháp chỉ khác nhau ở cách chọn tập con `B ⊆ P`.

**Code**
- `experiments/week2September/raw/teacher_trajectories_50x5.jsonl` (output của `scripts/generate_teacher_trajectories.py`)

---

### (4) Định nghĩa trajectory đúng (dòng 46)

**Công thức**

```
â(τ_i^k) = a_i
```

**Giải thích**
- Trajectory được coi là *correct* khi đáp án trích ra từ nó trùng ground-truth.
- Correct là thuộc tính phía Teacher, **không** đồng nghĩa với "hữu ích cho Student" (đó là việc của learnability ở 3.6).
- Việc trích đáp án được tách thành stage riêng, có thể chạy lại offline: bug ở extractor từng làm nhiều trajectory đúng bị đánh dấu sai (dòng 63 trong docx).

**Code**
- `scripts/re_evaluate_teacher_trajectories.py/line35-65`: `extract_answer` (regex `####`, "final answer")
- `scripts/re_evaluate_teacher_trajectories.py/line15-32`: `normalize_number` (bỏ `,` và `$`, ép float nguyên về int)
- `scripts/re_evaluate_teacher_trajectories.py/line68-69`: `answers_equal` chính là `â = a`
- `scripts/re_evaluate_teacher_trajectories.py/line114-144`: chấm lại toàn pool mà không gọi lại Teacher

---

### (5) Hàm mất mát SFT (dòng 49)

**Công thức**

```
L(θ) = − Σ_{(q,τ) ∈ B}  Σ_{t=1}^{|τ|}  log p_θ( τ_t | q , τ_{<t} )
```

**Giải thích**
- Đây là cross-entropy token-level tiêu chuẩn: Student học sinh lại từng token của trajectory Teacher, điều kiện trên đề bài và các token đã sinh trước đó.
- Tổng ngoài chạy trên tập **được chọn** `B`: nên toàn bộ paper xoay quanh câu hỏi *chọn `B` thế nào*, không phải đổi hàm loss.
- Lưu ý: loss này **không chuẩn hoá theo độ dài**; phiên bản chuẩn hoá `1/|τ|` được dùng làm tín hiệu learnability ở công thức (19).

**Code**
- *Chưa có*: repo hiện dừng ở giai đoạn sinh/phân tích dữ liệu, chưa có script fine-tune Student.

---

### (6) Selection policy tĩnh + ngân sách (dòng 52)

**Công thức**

```
B = π(P ; θ) ,   subject to  |B| ≤ β
```

**Giải thích**
- `π` là chính sách chọn dữ liệu, `β` là ngân sách (số example hoặc số token).
- Phần lớn phương pháp hiện tại tính `π` **một lần duy nhất trước khi train**, dựa trên chất lượng trajectory / độ khó đề bài / một lần đo Student ban đầu.

**Code**
- `scripts/select_traces_automatically.py/line59-124`: một `π` cụ thể: chấm điểm rồi lấy Top-K (`TOP_K=2` ở line 17) ⇒ chính là ràng buộc `|B| ≤ β`
- `scripts/compare_selection_strategies.py/line40-60`: hai `π` baseline: random và difficulty-only, cùng ngân sách `TOP_K`

---

### (7) Selection policy động theo checkpoint (dòng 54)

**Công thức**

```
B_m = π(P ; θ_m) ,   m = 0, 1, …, M
```

**Giải thích**
- Đóng góp cốt lõi: `π` được **đánh giá lại tại từng checkpoint** `θ_m`, nên tập train của stage `m` phụ thuộc năng lực Student *ngay lúc đó*.
- Hai hệ quả: (a) trajectory bị loại ở stage `m` vẫn nằm trong `P` và có thể được chọn ở stage sau, không có gì bị vứt vĩnh viễn; (b) bắt buộc phải có một mô hình tường minh về "trạng thái Student" (mục 3.4-3.6).

**Code**
- *Chưa có*: cần vòng lặp train nhiều stage.

---

### (8) Mục tiêu tối ưu (dòng 57)

**Công thức**

```
max_π  Acc( S_{θ_M} ; D_test )   subject to  Σ_m |B_m| ≤ β
```

**Giải thích**
- Tối đa accuracy của Student **cuối cùng** trên tập held-out, với tổng ngân sách cộng dồn qua mọi stage bị chặn bởi `β`.
- Cố định `β` là bắt buộc về mặt thiết kế thí nghiệm: bất kỳ chiến lược chọn nào cũng "thắng" nếu được train nhiều dữ liệu hơn. Mọi baseline ở Section 4 dùng cùng `β`.

**Code**
- `scripts/teacher_student_comparison.py/line1-214`: đo accuracy Teacher vs Student (phần `Acc(·)`)
- `scripts/analyze_comparison.py/line1-117`: tổng hợp kết quả so sánh

---

## 3.3 Difficulty Analysis (dòng 64-69)

### (9) Điểm độ khó của đề bài (dòng 66-67)

**Công thức**

```
d(q) = f_len(q) + f_num(q) + f_op(q) + f_frac(q)          ∈ [0, 8]

f_len  : +2 nếu > 80 từ,          +1 nếu > 45 từ
f_num  : +2 nếu ≥ 8 con số,       +1 nếu ≥ 5 con số
f_op   : +2 nếu ≥ 5 operation cue, +1 nếu ≥ 3 cue
f_frac : +2 nếu có phân số / phần trăm

easy: d ≤ 2 | medium: 3 ≤ d ≤ 4 | hard: d ≥ 5
```

**Giải thích**
- Ước lượng độ khó **giải thích được**, tính hoàn toàn từ bề mặt câu hỏi (không cần chạy model).
- Hạn chế được thừa nhận: chỉ đo độ phức tạp *từ vựng*, không đo độ sâu suy luận; và trong thực nghiệm nó phân biệt rất yếu giữa các mức accuracy ⇒ chỉ dùng làm **feature mô tả / baseline**, không phải tiêu chí chọn chính.

**Code**
- `scripts/difficulty_analysis.py/line32-82`: `calculate_difficulty`: đúng 4 thành phần và các ngưỡng 80/45, 8/5, 5/3, cùng ngưỡng phân loại 2/4
- `scripts/difficulty_analysis.py/line10-14`: `extract_numbers` (→ `f_num`)
- `scripts/difficulty_analysis.py/line17-29`: `count_operations` (→ `f_op`, lexicon toán tử)
- `scripts/difficulty_analysis.py/line39-46`: regex phân số/phần trăm (→ `f_frac`)
- `scripts/analyze_difficulty_performance.py/line25-56`: accuracy theo từng nhóm độ khó (kiểm chứng hạn chế nói trên)

---

### (9b) Metadata cấu trúc của trajectory (dòng 68 (mô tả, không đánh số))

**Công thức (mô tả bằng lời trong paper)**

```
trajectory_length  = số từ của τ
number_of_steps    = số bước suy luận tường minh trong τ
numeric density    = số biểu thức số trong τ
```

**Giải thích**
- `d(q)` mô tả **bài toán yêu cầu gì**; nhóm đặc trưng này mô tả **lời giải được trình bày ra sao**.
- Giữ cả hai vì hai trajectory cùng `d(q)` vẫn có thể khác nhau rõ rệt về độ phức tạp trình bày.

**Code**
- `scripts/analyze_trace_quality.py/line89-104`: `process_record` tính cả 3 đại lượng
- `scripts/analyze_trace_quality.py/line69-86`: `count_numbers`
- `scripts/analyze_trace_quality.py/line60-66`: `count_steps` (ưu tiên "Step N", fallback danh sách đánh số)

---

## 3.4 Student Capability (dòng 70-88)

### (10) Tập capability (dòng 72, 74)

**Công thức**

```
C = { c_1 , … , c_n }        C(q) ⊆ C
```

**Giải thích**
- Với bài toán số học: `C` = {addition, subtraction, multiplication, division, percentage, fraction, ratio}.
- `C(q)` là tập kỹ năng mà đề bài `q` huy động: **multi-label**, một câu thường dùng nhiều kỹ năng.

**Code**
- `scripts/analyze_student_gaps.py/line16-76`: `SKILL_KEYWORDS`, đúng 7 capability
- `scripts/analyze_trajectory_skills.py/line15-76`: bản lexicon dùng cho trajectory

---

### (11) Mật độ cue của capability (dòng 77)

**Công thức**

```
h_c(x) = | { w ∈ L_c : w xuất hiện trong x } |
```

**Giải thích**
- `L_c` là lexicon (danh sách từ khoá bề mặt) của capability `c`; `h_c(x)` đếm số **cue khác nhau** của `c` có trong văn bản `x`.
- Đếm *distinct term*, không phải số lần xuất hiện.

**Code**
- `scripts/analyze_student_gaps.py/line93-106`: `infer_skills`: `if keyword in text: scores[skill] += 1`, mỗi keyword cộng tối đa 1 ⇒ đúng nghĩa "distinct cue"

---

### (12) Gán capability cho đề bài (dòng 79)

**Công thức**

```
C(q) = { c ∈ C : h_c(q) > 0 }
```

**Giải thích**
- Chỉ cần **một** cue xuất hiện là gán capability đó cho câu hỏi.
- Hai phạm vi annotation được giữ **tách biệt**:
  - *Phạm vi đề bài* (dùng cho gap `g_c`): chỉ tính trên `q`, để ước lượng phản ánh yêu cầu bài toán chứ không bị ảnh hưởng bởi cách hành văn của Teacher.
  - *Phạm vi trajectory* (dùng cho scoring 3.6.3): tính trên `q + τ` ghép lại.

**Code**
- `scripts/analyze_student_gaps.py/line126-132`: annotate **chỉ từ** `item["question"]` (phạm vi đề bài)
- `scripts/analyze_trajectory_skills.py/line122-134`: annotate từ `question + "\n" + trajectory` (phạm vi trajectory)

---

### (13) Mastery của capability (dòng 83)

**Công thức**

```
              | { q : c ∈ C(q) ,  S_θ giải đúng q } |
m_c(θ)  =  ───────────────────────────────────────────
                     | { q : c ∈ C(q) } |
```

**Giải thích**
- Accuracy của Student **giới hạn trên các câu có dùng capability `c`** ⇒ profile năng lực mịn hơn accuracy tổng.
- `m_c` là hàm của `θ` ⇒ phải đo lại ở **mỗi checkpoint**.
- Rủi ro: nếu mẫu số nhỏ, ước lượng rất nhiễu ⇒ dùng ngưỡng support `n_min` (xem (15b)).

**Code**
- *Chưa có bản theo capability.* Bản gần nhất là accuracy theo nhóm độ khó: `scripts/analyze_difficulty_performance.py/line25-56` (cùng dạng "lọc tập con rồi lấy tỉ lệ đúng", chỉ cần đổi điều kiện lọc từ `difficulty` sang `c ∈ C(q)`).

---

### (14) Capability gap (dòng 85)

**Công thức**

```
g_c(θ) = (1 / |E(θ)|) · Σ_{q ∈ E(θ)}  h_c(q)

E(θ) = { q : Teacher đúng  ∧  Student sai }
```

**Giải thích**
- `E(θ)` = tập câu **có lời giải đúng để dạy nhưng Student chưa làm được**: đúng phần có thể chuyển giao bằng distillation. Định nghĩa gap tương đối so với Teacher, vì kỹ năng mà cả hai đều không có thì không thể distill.
- `g_c` là **mật độ cue trung bình** của capability `c` trên tập thất bại đó: thước đo "mức độ nổi bật", không phải tỉ lệ:
  - không âm, chặn trên bởi `|L_c|` chứ không phải bởi 1;
  - một câu đóng góp nhiều hơn nếu gọi tới capability qua nhiều cue khác nhau.
- Hai lưu ý khi dùng: (a) chỉ so sánh **theo thứ hạng** giữa các capability, vì lexicon to hơn thì điểm tự nhiên cao hơn; (b) **không** đọc `g_c` như "tỉ lệ câu sai có chứa capability này".
- Đây là tín hiệu Student-side chính cho mục 3.5, và được tính lại ở mọi checkpoint.

**Code**
- `scripts/analyze_student_gaps.py/line113-118`: dựng `E(θ)`: `teacher_correct and not student_correct`
- `scripts/analyze_student_gaps.py/line124-137`: cộng dồn `Σ h_c(q)` và `total = |E(θ)|`
- `scripts/analyze_student_gaps.py/line144-152`: `normalized_gap = count / total` **chính là `g_c(θ)`**
- `scripts/select_teacher_correct_student_wrong.py/line40-44`: cùng bộ lọc `E(θ)`, xuất ra file trajectory
- Output: `experiments/week2September/processed/student_skill_gap.json`

> Khớp với hạn chế nêu ở docx dòng 88: trong lần chạy sơ bộ, `fraction` và `ratio` nhận khối lượng bằng 0 vì cue không xuất hiện trong lexicon, thấy được ngay trong file output trên.

---

## 3.5 Student-Specific Prerequisite-Transfer Graph (dòng 89-106)

### (15b) Trạng thái node capability (dòng 91 (không đánh số công thức))

**Công thức**

```
state(c, θ_m) = ( m_c(θ_m) , g_c(θ_m) , n_c , coverage_c , #examples_c )
node bị loại khỏi ranking nếu  n_c < n_min
```

**Giải thích**
- `n_c` (support) = số câu eval có dùng `c`; `coverage_c` = mức phủ của `c` trong pool.
- Ghi tường minh hai đại lượng này vì chúng **chặn độ tin cậy** của các đại lượng còn lại: support thấp ⇒ `m_c` nhiễu; coverage thấp ⇒ dù phát hiện là bottleneck cũng không có dữ liệu để train.

**Code**
- *Chưa có.* Thành phần `n_c` có thể lấy từ `scripts/analyze_student_gaps.py/line130-132` (`question_skills`); `coverage_c` từ `scripts/analyze_trajectory_skills.py/line128-134` (`skill_set` trên pool).

---

### (15) Trọng số cạnh prerequisite (dòng 94)

**Công thức**

```
w_pre(c′ → c) = P( Student sai ở câu-c | Student sai ở c′ ) − P( Student sai ở câu-c )
```

**Giải thích**
- Đo **tỉ lệ thất bại có điều kiện, bất đối xứng**, trên tập `Q(c, c′)` = các câu dùng đồng thời cả hai capability.
- Dương ⇔ việc sai ở `c′` làm tăng xác suất sai ở `c` **vượt mức nền** ⇒ `c′` có dấu hiệu là tiên quyết của `c`.
- Trừ đi base rate `P(sai ở c)` để loại bỏ các capability vốn dĩ khó với Student nói chung (nếu không, mọi capability khó đều trông như prerequisite).
- Hậu xử lý: giữ cạnh khi `w_pre` vượt ngưỡng **và** đủ số câu hỗ trợ; rồi ép về DAG bằng cách bỏ cạnh yếu hơn trong mỗi 2-cycle và làm transitive reduction ⇒ chỉ còn phụ thuộc trực tiếp.
- Đây là quan hệ **tương quan, không phải nhân quả** ⇒ các cạnh chỉ là giả thuyết ràng buộc thứ tự train, được kiểm chứng gián tiếp qua ablation (Section 4.1.3).

**Code**
- *Chưa có.*

---

### (16) Trọng số cạnh transfer (dòng 98)

**Công thức**

```
w_tr(c → c′) = m_{c′}( θ_m + Δ_c ) − m_{c′}( θ_m )
```

**Giải thích**
- Khác với prerequisite (quan sát), transfer được đo **can thiệp**: tại checkpoint, train một LoRA adapter vài bước **chỉ trên trajectory thuộc `c`**, thu được update `Δ_c`, rồi đo lại mastery của **mọi** capability.
- `w_tr(c → c)` (đường chéo) = cải thiện trực tiếp; các phần tử ngoài đường chéo = cải thiện gián tiếp (lan toả).
- Adapter probe bị **huỷ sau khi đo**, không merge vào Student ⇒ phép đo không làm nhiễm quỹ đạo huấn luyện đang nghiên cứu.
- Chi phí: `|C|` lần probe + `|C|` lần re-eval mỗi checkpoint ⇒ giới hạn bằng step budget ngắn, chỉ probe capability qua ngưỡng support/coverage, và chỉ chạy ở checkpoint refresh graph.
- Ma trận `W_tr` nói chung **bất đối xứng**: cải thiện kỹ năng nền có thể kéo theo kỹ năng phụ thuộc mà chiều ngược lại không đúng.

**Code**
- *Chưa có.*

---

### (17) Điểm bottleneck (dòng 102)

**Công thức**

```
B(c, θ_m) = g_c(θ_m) · ( Σ_{c′ ≠ c}  w_tr(c → c′) ) · R(c, θ_m)
```

**Giải thích**
- Tích của **ba** thừa số, thiếu bất kỳ cái nào cũng kéo điểm về 0:
  1. `g_c`: Student đang hụt nhiều ở kỹ năng này (ưu tiên nơi chiếm phần lớn thất bại có thể chuyển giao);
  2. `Σ w_tr`: cải thiện nó **lan toả** sang các kỹ năng khác (chỉ cộng phần ngoài đường chéo);
  3. `R`: kỹ năng đã **sẵn sàng** để học (xem (18)).
- Capability bị đánh dấu unreliable ở 3.5.1 (support thấp) nhận điểm 0.
- Mỗi stage: chọn capability có `B` cao nhất làm mục tiêu, dồn ngân sách stage vào trajectory luyện nó, rồi ước lượng lại graph ở checkpoint sau ⇒ **thứ tự học sinh ra dần theo trạng thái Student**, không định trước. Đây chính là nghĩa "Student-specific": hai Student cùng accuracy tổng nhưng khác capability profile sẽ nhận thứ tự train khác nhau.

**Code**
- *Chưa có.* Bản sơ khai theo tinh thần "chọn theo gap": `scripts/select_traces_automatically.py/line63-73` (`skill_score = Σ_{c ∈ skill_set} g_c`), mới chỉ có thừa số thứ nhất, thiếu `Σ w_tr` và `R`.

---

### (18) Thừa số readiness (dòng 104)

**Công thức**

```
R(c, θ_m) = ∏_{ c″ : (c″ → c) ∈ E_pre }  m_{c″}(θ_m)
```

**Giải thích**
- **Tích** mastery của tất cả prerequisite của `c`.
- Dùng tích (chứ không phải tổng/trung bình) để tạo hiệu ứng cổng: chỉ cần **một** prerequisite chưa nắm (`m ≈ 0`) là `R ≈ 0` ⇒ triệt tiêu điểm bottleneck.
- Ý nghĩa: train một kỹ năng khi tiền đề của nó chưa đủ thì được kỳ vọng là **không hiệu quả**, nên hoãn lại.
- Capability không có prerequisite: tích rỗng = 1 ⇒ luôn sẵn sàng.

**Code**
- *Chưa có.*

---

## 3.6 Dynamic Learnability-Aware CoT Distillation (dòng 107-127)

### (19) Ước lượng learnability: NLL chuẩn hoá độ dài (dòng 110)

**Công thức**

```
ℓ(τ | q, θ) = − (1 / |τ|) · Σ_{t=1}^{|τ|}  log p_θ( τ_t | q , τ_{<t} )
```

**Giải thích**
- Giống loss (5) nhưng **chia cho `|τ|`** để trajectory dài không tự động bị chấm "khó"; và chỉ cần **một forward pass, không backward** ⇒ rẻ.
- Diễn giải là **độ bất ngờ (surprise)** của Student đối với lời giải Teacher:
  - `ℓ` rất thấp ⇒ trajectory đã gần phân phối đầu ra của Student ⇒ gradient bé, tốn ngân sách mà không thay đổi gì;
  - `ℓ` rất cao ⇒ nằm quá xa phân phối hiện tại ⇒ update lớn nhưng thiếu nền tảng, dễ mất ổn định và học vẹt (memorisation) không tổng quát hoá.
- Vùng hữu ích nằm **ở giữa**, tương ứng khái niệm *zone of proximal development*.

**Code**
- *Chưa có*: cần truy cập logprob của Student (API LM Studio hiện dùng trong repo chỉ sinh text: `scripts/common_lmstudio.py/line1-130`).

---

### (20) Learnability dạng dải cứng (hard band) (dòng 112)

**Công thức**

```
Λ(τ | θ) = 1   nếu  ℓ_low ≤ ℓ(τ | q, θ) ≤ ℓ_high
Λ(τ | θ) = 0   ngược lại
```

**Giải thích**
- Learnability được định nghĩa là **một dải**, không phải sở thích đơn điệu "càng khó càng tốt" hay "càng dễ càng tốt".
- `ℓ_low`, `ℓ_high` đặt theo **quantile thực nghiệm** của phân phối `ℓ` trên pool tại checkpoint hiện tại, không phải ngưỡng tuyệt đối: nhờ đó tiêu chí vẫn có nghĩa khi mức likelihood tổng thể dịch chuyển trong lúc train.

**Code**
- *Chưa có.*

---

### (21) Learnability dạng mềm (soft, dùng trong thực tế) (dòng 114)

**Công thức**

```
                  ⎛     ( ℓ(τ | q, θ) − ℓ* )²  ⎞
Λ(τ | θ) = exp ⎜ − ────────────────────────  ⎟
                  ⎝            2 σ²            ⎠
```

**Giải thích**
- Gaussian quanh tâm dải `ℓ*`: điểm giảm **mượt** về hai phía thay vì cắt cứng ⇒ tránh hiệu ứng bậc thang ở biên và cho phép xếp hạng trajectory thay vì chỉ nhận/loại.
- `σ` điều khiển độ rộng dải; `Λ ∈ (0, 1]`, đạt 1 khi `ℓ = ℓ*`.

**Code**
- *Chưa có.*

---

### (22) Tập được nạp tại checkpoint (admitted set) (dòng 119)

**Công thức**

```
A_m = { τ ∈ P :  τ correct  ,  ℓ_low^(m) ≤ ℓ(τ | q, θ_m) ≤ ℓ_high^(m) }
```

**Giải thích**
- Tính trên **toàn bộ pool `P`**, không phải trên phần còn lại sau các lần chọn trước; pool không bao giờ bị prune.
- Hệ quả hai chiều:
  - trajectory bị loại ở stage `m` vì `ℓ` quá cao có thể **vào lại** `A_{m′}` với `m′ > m` khi Student khá lên và `ℓ` giảm;
  - trajectory đã được hấp thụ sẽ **rơi xuống dưới `ℓ_low`** và bị đẩy ra khỏi tập, giải phóng ngân sách.
- Điều kiện `τ correct` là bắt buộc: chỉ trajectory đúng mới đủ tư cách; learnability quyết định **cái nào trong số đó** và **khi nào**.

**Code**
- Phần lọc `τ correct`: `scripts/select_traces_automatically.py/line54-57` và `scripts/compare_selection_strategies.py/line40-44`
- Phần dải `ℓ` và tính lại theo checkpoint: *chưa có*.

---

### (23) Chi phí re-evaluation (dòng 121)

**Công thức**

```
O(|P|)  forward pass / checkpoint        O(M · |P|)  cho toàn bộ quá trình train
```

**Giải thích**
- Mỗi checkpoint chỉ cần **1 forward pass / trajectory**, không backward ⇒ có thể batch tối đa theo bộ nhớ.
- Nếu pool quá lớn: giới hạn trên một **random subsample cỡ cố định, rút lại ở mỗi checkpoint**.
- Chi phí này phải được đối chiếu với chi phí train (Section 4.2): một cơ chế chọn dữ liệu mà overhead xấp xỉ chi phí train thẳng cả pool thì không có lý do tồn tại.

**Code**
- *Chưa có.*

---

### (24) Điểm tổng hợp để lập lịch trajectory (dòng 124)

**Công thức**

```
score(τ | θ_m) = Λ(τ | θ_m) · [ α · 1{ c*_m ∈ C(q_τ) }  +  (1 − α) · cov(τ) ]

c*_m   = capability có điểm bottleneck B(·, θ_m) lớn nhất
1{·}   = indicator: trajectory có luyện đúng capability mục tiêu không
cov(τ) = tỉ lệ capability **chưa thành thạo** mà τ có chạm tới
α ∈ [0,1)
```

**Giải thích**
- Hợp nhất hai cơ chế: **`Λ`** (thích ứng theo *thời gian*, mục 3.6) nhân với **ngoặc vuông** (thích ứng theo *cấu trúc*, mục 3.5).
- Vì là **phép nhân**, trajectory nằm ngoài dải learnability bị loại bất kể nó luyện đúng bottleneck hay không.
- `α` cân bằng giữa **tập trung** vào bottleneck (`α → 1`) và **phủ rộng** nhiều kỹ năng còn yếu (`α → 0`).
- Lấp ngân sách stage `β_m` bằng cách sample theo thứ tự điểm giảm dần, kèm hai ràng buộc: **cap theo từng đề bài** (tránh một câu chiếm cả stage bằng 5 trajectory của nó) và **giữ lại tối thiểu** các capability đã thành thạo (hạn chế quên).
- Hai cấu hình suy biến = hai ablation ở Section 4.1.3: đặt dải nạp = cả pool ⇒ chỉ còn chọn theo bottleneck; cố định capability mục tiêu mà vẫn giữ dải ⇒ chỉ còn chọn theo learnability.

**Code**
- Bản gần nhất hiện có: `scripts/select_traces_automatically.py/line61-124`
  - `line63-73`: `skill_score = Σ_{c ∈ C(q,τ)} g_c` ≈ thành phần "khớp kỹ năng đang hụt" (nhưng dùng tổng gap thay cho `α·1{·} + (1−α)·cov`)
  - `line76-100`: `final_score = skill_score + 0.1 · quality_score`, trong đó `quality_score` dựa trên số bước và độ dài ⇒ **thay thế tạm cho `Λ`** bằng heuristic bề mặt, không dùng likelihood Student
  - `line116-124`: sort giảm dần rồi cắt Top-K = lấp ngân sách
- Ràng buộc per-problem cap, retention chống quên, và `Λ` thật: *chưa có*.

---

## Tóm tắt trạng thái hiện thực hoá

| Mục | Công thức | Trạng thái code |
|---|---|---|
| 3.1 | (1)(2)(3)(4) pool & correctness | ✅ đầy đủ |
| 3.1 | (5) loss SFT, (7) policy động, (8) mục tiêu | ❌ chưa (chưa có training loop) |
| 3.1 | (6) policy tĩnh + budget | ✅ có bản baseline (Top-K) |
| 3.3 | (9) `d(q)` + metadata trajectory | ✅ đầy đủ |
| 3.4 | (11)(12)(14) `h_c`, `C(q)`, `g_c` | ✅ đầy đủ |
| 3.4 | (13) `m_c` mastery theo capability | ⚠️ mới có accuracy theo độ khó |
| 3.5 | (15)(16)(17)(18) graph, transfer, bottleneck | ❌ chưa |
| 3.6 | (19)(20)(21)(22)(23) learnability | ❌ chưa (cần logprob của Student) |
| 3.6 | (24) composite score | ⚠️ có bản heuristic thay thế |

**Hai thứ chặn phần còn lại:**
1. **Truy cập logprob của Student**: mọi công thức 3.6 đều dựa vào `ℓ(τ|q,θ)`; backend LM Studio hiện tại trong `scripts/common_lmstudio.py` chỉ trả text.
2. **Training loop nhiều stage có checkpoint**: điều kiện cần cho `θ_0…θ_M`, tức cho (7), (16), (22) và toàn bộ vòng lặp thích ứng.
