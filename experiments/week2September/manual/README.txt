    TASK HANDOVER (DACNTT/KLTN): Reasoning Knowledge Distillation
    File đích dự kiến: experiments/week2September/manual/task.txt
    Ngày cập nhật: 2026-10-12

    MỤC ĐÍCH
    Tài liệu này bàn giao trạng thái dự án, các file/artifact đã tạo, tác dụng, các phần chưa hoàn thành và cách tiếp tục với expected results. Người nhận cần xác minh trạng thái thực tế của repo trước khi sửa dữ liệu hoặc chạy thí nghiệm. Các trạng thái bên dưới phản ánh tiến độ đã báo cáo trong cuộc trao đổi, không thay thế việc kiểm tra file trực tiếp.

    ======================================================================
    0. TÓM TẮT DỰ ÁN VÀ TRẠNG THÁI
    ======================================================================

    Chủ đề: Reasoning Knowledge Distillation (RKD). Teacher tạo reasoning traces/Chain-of-Thought để Student nhỏ hơn học reasoning nhiều bước. Trọng tâm là chọn và tổ chức dữ liệu huấn luyện thích ứng theo trạng thái/khả năng học của Student.

    Teacher dự kiến: Qwen2.5-3B-Instruct.
    Student dự kiến: Qwen2.5-1.5B-Instruct.
    Dataset đang triển khai: GSM8K.
    Đề xuất 1: Student-Specific Prerequisite-Transfer Graph Distillation.
    Đề xuất 2: Dynamic Learnability-Aware CoT Distillation.

    Tình trạng tổng quát:
    - Task 4 (Extractor): DONE trừ A2 (cập nhật 2026-10-12). 34/34 case reviewed; D1-D3 chốt trong config/guideline_v3.md; gold v2 (bỏ division ở 5 bài) + rules v2 (phần A+B); chạy lại 4 cấu hình, kết quả chính thức division F1 0.8756 (baseline 0.7831).
      BLOCKED: xác minh A2 annotate độc lập (A1/A2 trùng 30/30). Quyết định và lý do: task4_decisions.md. Việc còn lại: task4_todo.txt.
    - Task 5 (Freeze): DONE (cập nhật 2026-10-14). splits/ đã tạo và validate (D_pool 6968, D_dev 500, D_test 1319 = GSM8K test; 5 near-duplicate bị loại); selection_log_schema.json đã validate; experiment_config.json hết TBD (--frozen PASS); analysis_plan.md đầy đủ; manifest reports/task5/SHA256SUMS_task5.txt.
      B4/B5, L_proxy: config/proposal2_full_protocol.md (nguyên văn từ readme.md trước commit 3f7dce4), nhóm đã xác nhận. Đề xuất task5_decisions.md mục I: I1, I2, I6, I7, I8 đã chốt; I3, I4, I5 là giá trị tạm, chờ smoke test.
      Cập nhật 2026-10-20: smoke test XONG (Colab T4; S_0 0.712 -> S_1 0.830 / 0.818 với seed 13 / 42 trên D_dev), quyết định keep, không config v2.
        I3, I5 đã chốt; I4 (b = 7) giữ tạm, chốt khi đo L_emp (Task.md 2.2). Báo cáo: reports/task5/smoke_test_report.md; quyết định: task5_decisions.md mục J.
        Đã sửa status trong config/experiment_config.json (--frozen PASS) và tạo lại reports/task5/SHA256SUMS_task5.txt (33/33 OK).
      Cập nhật 2026-10-20: đo Teacher 3B trên D_dev = 0.886 (S_1 0.830 / 0.818), hơn S_1 6.2 điểm % -> GIỮ cặp Qwen2.5-3B -> Qwen2.5-1.5B.
        Dữ liệu: reports/task5/teacher_dev/; quyết định: task5_decisions.md mục K. Task 6: quyết định T6-1..T6-5 đã chốt 2026-10-21 (task6_decisions.md).
      Còn lại của Task 5:
        1. [XONG 2026-10-20] Smoke test trên D_dev (không dùng D_test) để chốt I3 (n_round 200, beta_round 45.426 token/vòng), I4 (b = 7 step), I5 (LoRA, lr 2e-4 cố định, batch 8):
           eval S_0 trên D_dev (đồng thời đo thời gian eval); train 1 vòng khoảng 200 trajectory chọn ngẫu nhiên từ pool sơ bộ; eval lại trên D_dev.
           Accuracy thay đổi rõ và loss giảm ổn định -> giữ giá trị; gần như không đổi -> tăng n_round hoặc epoch; loss dao động/tăng -> giảm lr.
           Đổi giá trị nào thì tạo config v2 kèm lý do, chạy lại validate_experiment_config.py --frozen, tạo lại reports/task5/SHA256SUMS_task5.txt. Phải xong trước thí nghiệm chính.
        2. Ràng buộc chuyển sang Task 6: pool chính thức >= 1000 bài D_pool (khoảng 900 bài x K=5 = 4.500 lượt sinh thêm), chấm bằng scripts/answer_utils.py.
           Nếu không đủ tài nguyên: giảm n_round tương ứng (vd. pool 500 bài -> n_round 100, khoảng 22.700 token/vòng), sửa I3 bằng config v2.
        3. requirements.txt: chuyển sang UTF-8 và thêm jsonschema (các script validate cần); cài torch cần --extra-index-url https://download.pytorch.org/whl/cu126. Thuộc Task 8.
    - Task 6 (Trajectory pool): đã sinh/recover pool sơ bộ 500 trajectory cho 100 problem; báo cáo trước ghi 480 valid và 20 invalid_answer. Chưa phải pool D_pool chính thức.
      Cập nhật 2026-10-21: đã sinh pool chính thức bằng vLLM 0.32.0 trên RunPod L4 (bf16), theo Instruction_task6.md.
        Kiểm tra tương đương vLLM/HF trên batch_100: PASS (valid 402/500 so với 406/500; độ dài +0.2%), reports/task6/parity_vllm_hf.json.
        trajectory/pool/pool_v1_teacher_raw.jsonl: 1.100 bài x K=5 = 5.500 trajectory; valid 4.355, invalid_format 730, invalid_answer 415.
        1.032 bài có >= 1 lời giải đúng (đạt >= 1.000), 68 bài bị loại (T6-3). Cập nhật 2026-10-22: Task 6 XONG. pool_v1_verified.jsonl 4.353 trajectory / 1.032 bài (schema v2, C(tau) rules v2 trên toàn bộ output),
          kiểm tra rò rỉ PASS; báo cáo reports/task6/pool_report.md; student_common.py trỏ sang pool v1.
    - Task 7 cập nhật 2026-11-01: đã chốt quy tắc trước khi chạy (task7_decisions.md, config v2, analysis_plan.md v2; v1 lưu ở *_v1). Chưa cài đặt pipeline.
    - Task 7 (S0 -> S1): chưa có bằng chứng về một vòng selection-training-evaluation hoàn chỉnh trên D_dev với số liệu thực.
      Cập nhật 2026-10-20: smoke test đã chạy 1 vòng train-evaluate S_0 -> S_1 trên D_dev, nhưng chọn dữ liệu ngẫu nhiên từ pool sơ bộ, chưa có selection theo L_proxy.
    - Task 8 (Docs/environment): chưa xác nhận protocol/README đồng bộ, dependency đủ và clean environment đã test.
    - Task 9 (Cloud): chưa có job cloud thành công nào được xác nhận trong trạng thái bàn giao này.

    Cảnh báo:
    1. “480 trajectory hợp lệ” chỉ là kết quả theo tiêu chí hiện có; không tự động chứng minh mọi đáp án đúng, schema chính thức đạt, hay dữ liệu được phép dùng cho training.
    2. Không ghi đè raw trajectory hoặc baseline reports.
    3. Không sửa gold/rule trước khi backup và ghi hash.
    4. Không training chính thức trước khi freeze split và experiment protocol.
    5. Không suy đoán file tồn tại chỉ vì file được nhắc trong tài liệu này; kiểm tra bằng Test-Path/Get-ChildItem.

    ======================================================================
    1. REPO, THƯ MỤC VÀ FILE ĐÃ ĐƯỢC XÁC NHẬN
    ======================================================================

    Repo:
    C:\KLTN-SLM-Reasoning

    Thư mục manual:
    C:\KLTN-SLM-Reasoning\experiments\week2September\manual

    Các file đã được xác nhận tồn tại bằng Test-Path:

    1. data\batch_100\batch_100_annotations.jsonl
       Nhãn capability thủ công hiện tại (gold cấp problem) cho batch 100. Không sửa trước adjudication/backup.

    2. config\capability_rules_v1.json
       Các rule/pattern dùng bởi extractor rule-based. Không sửa trước khi review và backup.

    3. reports\capability_extractor_batch100_report.csv
       Baseline metrics theo capability. Giữ nguyên để so sánh.

    4. reports\capability_extractor_batch100_report.json
       Baseline report dạng JSON. Giữ nguyên để so sánh.

    5. reports\error_analysis\division_false_positives.csv
       Các trajectory extractor dự đoán division nhưng gold hiện tại không có division. Đây là “FP so với gold hiện tại”, chưa phải kết luận đã adjudicate.

    6. reports\error_analysis\ratio_false_positives.csv
       Tương tự cho capability ratio.

    7. reports\error_analysis\capability_error_cases.csv
       Các case lỗi extractor dùng để phân tích FP/FN.

    8. trajectory\pool\batch_100_teacher_raw_recovered_v2.jsonl
       Raw Teacher pool đã recover; báo cáo có 500 trajectory cho 100 problem. Đây là artifact tốn thời gian sinh/recovery, phải giữ nguyên và không ghi đè.
       Các trường đã xác nhận trong record đầu tiên:
       problem_id, teacher_model, trajectory_id, checkpoint, question, reasoning_trace,
       answer, ground_truth, metadata, raw_generation.
       Không giả định có trường status; trường này không có trong record đã kiểm tra.

    9. reports\error_analysis\manual_adjudication.csv
       File adjudication, header:
       problem_id,capability,trajectory_ids_reviewed,gold_capabilities_before,trigger_type,
       trace_evidence,adjudication,decision,rationale,review_status
       [Cập nhật 2026-10-12] Đã điền đủ 34 dòng, 34 reviewed (xem task4_decisions.md).

    Các file/đường dẫn khác được nhắc trong kế hoạch nhưng phải xác minh trước khi dùng:
    - guideline_v2.md
    - issues\ambiguous_cases.jsonl
    - scripts\validate_annotation.py
    - scripts\validate_trajectory.py
    - teacher_trajectory_schema.json (vị trí thực tế chưa được xác nhận)
    - README.md hoặc readme.md
    - proposal2_trajectory_protocol.md
    - requirements.txt
    - scripts\test_capability_extractor.py
    - scripts\run_task4_extractor_batch100.py
    - scripts\analyze_capability_errors.py
    - scripts\extract_capabilities_rule_based.py
    - reports\error_analysis\adjudication_review_cases.csv
    - reports\error_analysis\reasoning_trace_review.txt
    - reports\error_analysis\baseline_backup\

    ======================================================================
    2. ARTIFACT VÀ KẾT QUẢ ĐÃ SINH
    ======================================================================

    2.1. Pool Teacher sơ bộ
    - Đã tạo/recover 500 trajectory ứng với 100 problem, theo tiến độ K=5 trajectory/problem.
    - File: trajectory\pool\batch_100_teacher_raw_recovered_v2.jsonl
    - Theo báo cáo: 480 trajectory valid, 20 trajectory invalid_answer.
    - Không sinh lại toàn bộ hoặc ghi đè file này. Sau khi split được freeze, lọc và tái sử dụng các trajectory đạt yêu cầu; chỉ sinh bổ sung nếu thiếu.
    - Pool chưa phải D_pool chính thức vì chưa đối chiếu split frozen, schema và verification.

    2.2. Extractor baseline
    - Đã có extractor rule-based ở mức trajectory.
    - Unit test trước đây báo `PASS: 28 unit cases` khi chạy:
      python experiments\week2September\manual\scripts\test_capability_extractor.py
      Xác minh đường dẫn/script hiện tại trước khi chạy lại.
    - Đã đánh giá 480 trajectory hợp lệ so với gold cấp problem. Giới hạn: nhiều trajectory cùng problem được so với cùng nhãn problem-level; đó không phải human gold độc lập ở cấp trajectory.

    Metrics baseline đã được báo cáo:

    Capability       Precision   Recall    F1       TP    FP    FN
    addition         0.8085      0.9344    0.8669   228   54    16
    subtraction      0.8848      0.9636    0.9225   238   31     9
    multiplication   0.8949      0.9292    0.9117   315   37    24
    division         0.6534      0.9771    0.7831   213  113     5
    percentage       1.0000      0.9298    0.9636    53    0     4
    fraction         0.8969      0.9886    0.9405    87   10     1
    ratio            N/A         N/A       N/A        0    2     0

    Ratio không có positive gold trong batch được đánh giá, nên P/R/F1 là N/A, không phải 0.
    Có discrepancy cần kiểm tra: baseline report ghi division FP=113, trong khi bảng nhóm false-positive được in trước đó có vẻ không khớp. Phải đối chiếu CSV và report JSON trước khi dùng số liệu chính thức.

    2.3. Error analysis và adjudication review
    Các file đã có:
    - reports\error_analysis\division_false_positives.csv
    - reports\error_analysis\ratio_false_positives.csv
    - reports\error_analysis\capability_error_cases.csv
    - reports\error_analysis\manual_adjudication.csv (header đã tạo, chưa hoàn tất)

    Các cột của division/ratio CSV đã xác nhận:
    error_type, capability, problem_id, trajectory_id, gold_has_capability,
    predicted_has_capability, gold_capabilities, predicted_capabilities, rules_fired,
    evidence, question, answer, ground_truth, verification_status, reasoning_trace.

    Đã báo cáo tạo:
    - reports\error_analysis\adjudication_review_cases.csv
      Có 34 problem-capability cases duy nhất: 32 division + 2 ratio. Xác minh lại số dòng trước khi review.
    - Có thể tạo reports\error_analysis\reasoning_trace_review.txt để gom trace đầy đủ; nếu file đã tồn tại, không ghi đè nội dung review của người khác.

    Case mẫu đã xem:
    problem_id: gsm8k_train_00087
    capability: ratio
    trajectory_id: gsm8k_train_00087_traj_002
    gold: ["division", "multiplication", "percentage"]
    rules_fired: ["rule_1"]
    evidence chứa “calculate the proportion of oysters with pearls”.
    Trace tính 25%=1/4; 16/4=4 pearls/dive; 56/4=14 dives.
    Vấn đề chưa chốt: rule ratio kích hoạt do “proportion”, nhưng phải đối chiếu guideline để xác định đây có phải capability ratio hay chỉ là percentage/division.
    Dòng mẫu tạm thời có thể là:
    adjudication=DEFINITION_AMBIGUITY
    decision=NEEDS_DISCUSSION
    review_status=needs_discussion
    Chỉ giữ kết luận này nếu sau khi đọc guideline vẫn chưa đủ rõ. Đây không phải kết luận cuối đã được adjudicate.

    ======================================================================
    3. TASK 4: MANUAL ADJUDICATION - HƯỚNG DẪN TIẾP TỤC
    ======================================================================

    Bước 4.1: Khởi tạo biến và xác minh file

    Chạy tại PowerShell:
    $Repo = "C:\KLTN-SLM-Reasoning"
    $Manual = "$Repo\experiments\week2September\manual"
    $OutDir = "$Manual\reports\error_analysis"
    $FinalRaw = "$Manual\trajectory\pool\batch_100_teacher_raw_recovered_v2.jsonl"
    $ReviewPath = "$OutDir\adjudication_review_cases.csv"
    $AdjudicationFile = "$OutDir\manual_adjudication.csv"
    $BackupDir = "$OutDir\baseline_backup"

    @($FinalRaw, $ReviewPath, $AdjudicationFile,
      "$Manual\data\batch_100\batch_100_annotations.jsonl",
      "$Manual\config\capability_rules_v1.json",
      "$Manual\reports\capability_extractor_batch100_report.json",
      "$OutDir\division_false_positives.csv",
      "$OutDir\ratio_false_positives.csv",
      "$OutDir\capability_error_cases.csv") |
    ForEach-Object { [PSCustomObject]@{ Exists = Test-Path $_; Path = $_ } } |
    Format-Table -AutoSize

    Expected: tất cả file nguồn cần dùng có Exists=True. Nếu thiếu file, dừng và tìm đúng đường dẫn; không tạo file nguồn giả để thay thế.

    Xác minh raw record:
    $FirstRaw = Get-Content $FinalRaw -TotalCount 1 | ConvertFrom-Json
    $FirstRaw.PSObject.Properties.Name

    Expected fields đã xác nhận: problem_id, teacher_model, trajectory_id, checkpoint, question, reasoning_trace, answer, ground_truth, metadata, raw_generation. Không dùng status làm trường bắt buộc.

    Bước 4.2: Xác minh 34 case

    $ReviewCases = Import-Csv $ReviewPath
    "Review rows: $($ReviewCases.Count)"
    $ReviewCases | Group-Object capability | Select-Object Name, Count

    Expected theo báo cáo trước: 34 case; 32 division và 2 ratio. Nếu khác, dừng và đối chiếu file/baseline trước khi review.

    Bước 4.3: Đọc trace đầy đủ
    - Dùng problem_id + trajectory_id để lấy đúng record từ raw JSONL.
    - Đọc question, reasoning_trace, answer và ground_truth.
    - Không chỉ dựa trên evidence bị cắt ngắn trong CSV.
    - Nếu không tìm thấy đúng một record cho trajectory_id, dừng case đó và điều tra ID; không kết luận từ trace thiếu.
    Ví dụ:
    $RawRecords = @(Get-Content $FinalRaw | ForEach-Object { $_ | ConvertFrom-Json })
    $TargetId = "gsm8k_train_00087_traj_002"
    $Target = @($RawRecords | Where-Object {
        $_.trajectory_id -eq $TargetId -and $_.problem_id -eq "gsm8k_train_00087"
    })
    if ($Target.Count -ne 1) { throw "Expected exactly one record; found $($Target.Count)" }
    $Target[0] | Select-Object problem_id, trajectory_id, question,
        reasoning_trace, answer, ground_truth | Format-List

    Bước 4.4: Chốt định nghĩa capability trước khi quyết định
    Đọc guideline_v2.md. Xác định nhất quán:
    - Gold mô tả kỹ năng cần để giải bài hay mọi phép toán xuất hiện trong một trace?
    - Khi nào division được gán riêng, đặc biệt nếu phép chia là bước trung gian cho fraction/percentage?
    - Từ “per” có đủ để gán division không? Không mặc định có.
    - Từ “ratio”/“proportion” có đủ để gán ratio không? Không mặc định có.
    - Percentage, fraction và ratio được phân biệt thế nào trong guideline?
    Nếu guideline chưa rõ, ghi definition ambiguity và thống nhất quy tắc trước khi đổi gold/rule. Không đổi quy ước giữa chừng.

    Bước 4.5: Điền manual_adjudication.csv

    Header 10 cột:
    problem_id,capability,trajectory_ids_reviewed,gold_capabilities_before,trigger_type,trace_evidence,adjudication,decision,rationale,review_status

    Ý nghĩa:
    - problem_id: ID bài.
    - capability: division hoặc ratio.
    - trajectory_ids_reviewed: tất cả trajectory đã đọc, ngăn cách bằng dấu `;`.
    - gold_capabilities_before: giữ nguyên gold trước chỉnh sửa.
    - trigger_type: lexical_keyword / numeric_operator / semantic_reasoning / mixed, dựa trên nguyên nhân thật.
    - trace_evidence: trích dẫn ngắn và phép tính/ngữ cảnh liên quan.
    - rationale: giải thích dựa trên đề bài, trace, gold và guideline.

    Giá trị adjudication:
    - FALSE_LEXICAL_TRIGGER: rule kích hoạt nhưng capability không được thể hiện theo định nghĩa đã chốt.
    - TRUE_CAPABILITY_OMITTED_FROM_GOLD: capability đúng theo định nghĩa nhưng gold hiện tại thiếu.
    - DEFINITION_AMBIGUITY: guideline chưa đủ rõ để kết luận.

    Giá trị decision:
    - KEEP_GOLD: giữ gold.
    - PROPOSE_GOLD_UPDATE: đề xuất sửa gold, cần xác minh/phê duyệt.
    - PROPOSE_RULE_CHANGE: đề xuất sửa rule, chưa tự sửa rule.
    - NEEDS_DISCUSSION: cần thống nhất định nghĩa/guideline.

    Giá trị review_status:
    - reviewed: đã đọc đủ trace và có kết luận theo guideline.
    - needs_discussion: đã xem nhưng còn ambiguity.
    - pending: chưa review xong.

    Ví dụ tạm thời cho gsm8k_train_00087 / ratio:
    problem_id = gsm8k_train_00087
    capability = ratio
    trajectory_ids_reviewed = gsm8k_train_00087_traj_002
    gold_capabilities_before = ["division", "multiplication", "percentage"]
    trigger_type = lexical_keyword
    trace_evidence = The trace says "calculate the proportion of oysters with pearls"; it then computes 16/4=4 and 56/4=14.
    adjudication = DEFINITION_AMBIGUITY
    decision = NEEDS_DISCUSSION
    rationale = Rule 1 fires on the word proportion. The trace uses 25% = 1/4 and division to calculate pearls per dive and the number of dives. The current evidence does not establish whether this use qualifies as ratio under the annotation guideline; keep gold and rule unchanged until the definition is resolved.
    review_status = needs_discussion

    Đây là mẫu minh họa, không phải kết luận chuyên môn cuối cùng. Sau khi đọc guideline, có thể cập nhật nếu có bằng chứng.

    Bước 4.6: Kiểm tra file CSV sau khi điền

    $Adjudication = Import-Csv $AdjudicationFile
    "Rows: $($Adjudication.Count)"
    "Reviewed: $(@($Adjudication | Where-Object { $_.review_status -eq 'reviewed' }).Count)"
    "Needs discussion: $(@($Adjudication | Where-Object { $_.review_status -eq 'needs_discussion' }).Count)"
    "Pending: $(@($Adjudication | Where-Object { $_.review_status -eq 'pending' }).Count)"

    "=== Missing fields ==="
    $Adjudication | Where-Object {
        [string]::IsNullOrWhiteSpace($_.problem_id) -or
        [string]::IsNullOrWhiteSpace($_.capability) -or
        [string]::IsNullOrWhiteSpace($_.adjudication) -or
        [string]::IsNullOrWhiteSpace($_.decision) -or
        [string]::IsNullOrWhiteSpace($_.rationale) -or
        [string]::IsNullOrWhiteSpace($_.review_status)
    } | Format-Table problem_id, capability, adjudication, decision, review_status

    "=== Duplicate problem-capability pairs ==="
    $Adjudication | Group-Object problem_id, capability |
        Where-Object { $_.Count -gt 1 } | Select-Object Name, Count

    Expected khi review đủ:
    - Rows=34.
    - Reviewed + Needs discussion + Pending = 34.
    - Pending=0 trước khi đóng giai đoạn review.
    - Missing fields: không có dòng nào.
    - Duplicate pairs: không có dòng nào.
    - Needs discussion có thể >0 nếu đã ghi rõ lý do; không ép mọi case thành reviewed.

    Kiểm tra giá trị:
    $ValidAdjudications = @("FALSE_LEXICAL_TRIGGER","TRUE_CAPABILITY_OMITTED_FROM_GOLD","DEFINITION_AMBIGUITY")
    $ValidDecisions = @("KEEP_GOLD","PROPOSE_GOLD_UPDATE","PROPOSE_RULE_CHANGE","NEEDS_DISCUSSION")
    $ValidStatuses = @("reviewed","needs_discussion","pending")
    $Adjudication | Where-Object {
        $_.adjudication -notin $ValidAdjudications -or
        $_.decision -notin $ValidDecisions -or
        $_.review_status -notin $ValidStatuses
    } | Format-Table problem_id, capability, adjudication, decision, review_status

    Expected: không có dòng nào.

    Bước 4.7: Sao lưu trước mọi thay đổi gold/rule/report
    Kiểm tra thư mục trước:
    if (Test-Path $BackupDir) {
        Write-Host "Backup folder exists. Inspect it; do not overwrite."
    } else {
        Write-Host "Backup folder absent; create it only after verifying source files."
    }
    Nếu backup đã tồn tại, không xóa/ghi đè; kiểm tra nội dung và chọn version mới nếu cần.
    Nếu chưa tồn tại, sao lưu:
    - data\batch_100\batch_100_annotations.jsonl -> baseline_backup\batch_100_annotations_before.jsonl
    - config\capability_rules_v1.json -> baseline_backup\capability_rules_v1_before.json
    - reports\capability_extractor_batch100_report.csv -> baseline_backup\capability_extractor_batch100_report_before.csv
    - reports\capability_extractor_batch100_report.json -> baseline_backup\capability_extractor_batch100_report_before.json
    Tạo SHA256 manifest cho raw JSONL, annotations, rules config và hai baseline reports. Không chỉnh sửa raw pool.

    Bước 4.8: Đối chiếu division FP discrepancy
    $DivisionFP = Import-Csv "$OutDir\division_false_positives.csv"
    $RatioFP = Import-Csv "$OutDir\ratio_false_positives.csv"
    "Division FP CSV rows: $($DivisionFP.Count)"
    "Distinct division FP trajectories: $(($DivisionFP | Select-Object -ExpandProperty trajectory_id -Unique).Count)"
    "Ratio FP CSV rows: $($RatioFP.Count)"
    Đối chiếu số này với report JSON/CSV. Baseline từng ghi division FP=113. Nếu CSV được sinh từ run khác hoặc discrepancy chưa giải thích được, dừng và tái tạo error analysis từ đúng baseline input.

    Bước 4.9: Sau khi adjudicate
    - TRUE_CAPABILITY_OMITTED_FROM_GOLD: đề xuất cập nhật gold theo guideline, có audit trail.
    - FALSE_LEXICAL_TRIGGER: đề xuất sửa rule dựa trên ngữ cảnh, không chỉ xóa từ khóa tùy tiện.
    - DEFINITION_AMBIGUITY: chốt guideline trước; giữ gold/rule nguyên trạng tới khi có quyết định.
    - Không coi việc chỉ sửa gold là cải thiện extractor.
    - Lưu baseline, report sau adjudicated gold, và report sau rule change riêng.
    - Sau khi được duyệt, chạy lại extractor trên cùng input và cùng tập trajectory hợp lệ. Kiểm tra runner dùng đúng config.
    - Không ghi đè baseline reports.

    Điều kiện hoàn thành phần adjudication:
    - Đã review 34 case hoặc đánh dấu needs_discussion với lý do cụ thể.
    - Không còn pending.
    - Không thiếu trường bắt buộc/duplicate pair/invalid enum.
    - Mọi sửa đổi gold/rule có backup, hash và rationale.
    - Report phân biệt ảnh hưởng của thay đổi gold với thay đổi extractor.

    ======================================================================
    4. TASK 4: CÁC ANNOTATION CÒN TỒN ĐỌNG CẦN GIẢI QUYẾT
    ======================================================================

    4.1. Pilot 30, annotator A2, Cohen's kappa
    Tình trạng: chưa có kappa được xác nhận; trước đó mới có A1.
    Việc:
    - Tìm guideline_v2.md và nguồn 30 problem gsm8k_train_00000-gsm8k_train_00029.
    - A2 annotate độc lập, không xem nhãn A1.
    - Tạo data\pilot\pilot_30_annotations_A2.jsonl.
    - Tính Cohen's kappa riêng cho 7 capability (binary label per problem/capability nếu phù hợp với format annotation).
    - Tạo agreement report ghi kappa, agreement/disagreement và nguyên nhân bất đồng.
    Expected:
    - Có kết quả cho đủ 7 capability.
    - Với kappa < 0.6: ghi lý do và sửa guideline có version.
    - Giữ A1 và A2 riêng; không ghi đè/gộp tự động.

    4.2. Supplement ratio/percentage/fraction
    Tình trạng được báo cáo trên batch 100: ratio=0, percentage=12, fraction=18.
    Việc:
    - Chọn problem GSM8K train ngoài batch_100.
    - Tránh ID trùng với batch_100, pilot/supplement đã có và split đã freeze sau này.
    - Annotate theo guideline đã chốt.
    - Validate bằng đúng validate_annotation.py sau khi xác minh đường dẫn/CLI.
    - Tạo data\supplement\supplement_annotations.jsonl.
    Expected:
    - ratio > 0.
    - Percentage positive > 12 và fraction positive > 18, nếu thống kê cùng định nghĩa/tập so sánh.
    - Báo cáo số problem thêm và số positive mỗi capability, không chỉ số dòng JSONL.

    4.3. Ambiguous cases
    5 case được báo cáo open: 00023, 00029, 00056, 00073, 00082.
    Việc:
    - Xác minh issues\ambiguous_cases.jsonl và nguồn GSM8K.
    - 00029, 00056, 00082: xác minh ground truth với nguồn gốc, ghi nguồn/cách kiểm tra.
    - 00023 và 00073: ghi cách diễn giải wording cuối cùng.
    - Case 00056 được báo cáo có câu “200 dozen cookies” nhưng ground truth cũ là 50. Xác minh nguồn trước khi sửa; không đổi chỉ vì Teacher trả lời khác.
    - Cập nhật từng record với status, decision, rationale và evidence.
    Expected: cả 5 case đóng hoặc còn open kèm lý do cụ thể và điều kiện để đóng. Không sửa âm thầm.

    ======================================================================
    5. TASK 5: FREEZE SETUP TRƯỚC TRAINING
    ======================================================================

    Cần có:
    1. splits/: problem IDs cho D_pool, D_dev, D_test; hash và quy tắc chia split.
    2. experiment_config.json: seed, Teacher/Student checkpoint, K, temperature, checkpoint schedule, training budget, selection parameters, evaluation protocol.
    3. selection_log_schema.json: schema ghi checkpoint nguồn, problem/trajectory IDs, L_proxy, tiêu chí/lý do chọn và outcome.
    4. analysis_plan.md: giả thuyết, metric chính, protocol, seed/budget và so sánh chính B5 vs B4.

    Việc:
    - Tìm tài liệu định nghĩa B4/B5; không tự suy diễn tên baseline.
    - Split ở mức problem ID, không ở mức trajectory; mọi trajectory của một problem theo cùng split để tránh leakage.
    - Kiểm tra ID không trùng giữa D_pool/D_dev/D_test.
    - Ghi hash từng split và hash dữ liệu/config/code quan trọng.
    - Validate config/schema.
    - Commit artifacts trước training vòng đầu và ghi commit hash.

    Expected:
    - Đủ các artifacts; split disjoint; số lượng mỗi split được ghi rõ; hash tái tính được.
    - B4/B5 được định nghĩa chính xác trong analysis_plan.
    - Không dùng D_dev/D_test làm training data.

    ======================================================================
    6. TASK 6: POOL CHÍNH THỨC TRÊN D_POOL
    ======================================================================

    Pool sơ bộ: 500 trajectory/100 problem, theo báo cáo 480 valid và 20 invalid_answer. Giữ raw file gốc.

    Sau khi Task 5 freeze đã hoàn thành:
    1. Lọc theo problem IDs trong D_pool.
    2. Kiểm tra mỗi problem có K=5 trajectory theo protocol.
    3. Xác minh answer so với ground_truth và ghi trạng thái theo schema; không gộp invalid_answer/incorrect/null nếu schema phân biệt.
    4. Validate bằng validate_trajectory.py theo teacher_trajectory_schema.json; xác minh đúng path/CLI.
    5. Thống kê số problem, expected/actual trajectories, schema-valid/invalid, correct/incorrect/null/invalid_answer và problem thiếu K.
    6. Chỉ tái sử dụng trajectory thuộc D_pool và đạt tiêu chí. Sinh bổ sung phần thiếu thay vì sinh lại tất cả nếu protocol/pipeline cho phép.
    7. Lưu pool chính thức ở đường dẫn/version riêng, kèm manifest/hash. Không ghi đè raw recovered v2.

    Expected:
    - Mọi record dùng trong pool chính thức đạt schema.
    - Không có problem thuộc D_dev/D_test trong training pool.
    - K=5/problem hoặc mọi ngoại lệ được ghi và xử lý trước training.
    - Có report verification và manifest/hash.

    ======================================================================
    7. TASK 7: THỰC NGHIỆM S0 -> S1
    ======================================================================

   Chỉ bắt đầu sau khi Task 5 freeze và Task 6 pool đã validate.

    7.1. S0
    - Chốt checkpoint Student Qwen2.5-1.5B-Instruct và version/hash.
    - Evaluate S0 trên D_dev theo metric đã freeze.
    - Lưu raw predictions, metrics, config và log.

    7.2. L_proxy và selection
    - Dùng đúng định nghĩa L_proxy trong proposal/protocol.
    - Tính L_proxy cho trajectory đã verify.
    - Áp dụng selection policy đã freeze.
    - Lưu selected trajectory manifest và selection log theo schema.

    7.3. Train S1
    - Train từ S0 với seed/budget/hyperparameters đã freeze.
    - Lưu checkpoint, training log, config, environment info và checkpoint record.
    - Không train với trajectory ngoài D_pool hoặc chưa validate.

    7.4. Evaluation/plots
    - Evaluate S0 và S1 trên cùng D_dev, cùng protocol.
    - Chạy render_graph.py và render_learning_curve.py trên dữ liệu thật, không dùng số synthetic để giả làm kết quả.
    Expected:
    - student_ckpt_000 và student_ckpt_001 (hoặc naming đã thống nhất).
    - Metrics S0/S1, raw evaluation logs, checkpoint record, selection manifest/log.
    - Graph/learning curve sinh từ số liệu thật.
    - Truy nguyên được checkpoint -> config -> selected IDs -> pool/split.

    ======================================================================
    8. TASK 8: TÀI LIỆU VÀ MÔI TRƯỜNG
    ======================================================================
    Công việc:
    1. Đối chiếu proposal2_trajectory_protocol.md với README.md/readme.md.
    2. Đồng bộ schema, K=5, temperature=0.7, verification, split, selection, training/evaluation.
    3. Kiểm tra requirements.txt; thêm jsonschema nếu validator thực sự dùng.
    4. Tạo môi trường sạch và cài dependencies từ đầu.
    5. Chạy unit tests, annotation validator, trajectory validator và các scripts cần thiết.
    6. Ghi lệnh chạy chuẩn, inputs/outputs, expected results và cách xử lý lỗi.
    Expected:
    - Protocol và README không mâu thuẫn.
    - Clean environment cài thành công.
    - Tests/validators chạy thành công với input hợp lệ và báo lỗi rõ với input sai.
    - Hạn chế hard-code đường dẫn tuyệt đối chỉ hoạt động trên một máy.

    ======================================================================
    9. TASK 9: CLOUD/AUTOMATION
    ======================================================================
    Cần chuẩn bị trước khi thuê:
    - Split/config/analysis plan đã freeze.
    - Pool D_pool đã validate.
    - Có ít nhất một vòng S0 -> S1 chạy ở môi trường thử nghiệm.
    - Clean environment và scripts đã test.
    - Ước lượng VRAM/disk/checkpoint/time dựa trên config thực tế.
    - Có log, checkpoint/resume, backup và cách tắt server tránh chi phí ngoài dự kiến.

    Trình tự:
    1. Cài môi trường, ghi versions.
    2. Chạy validation/smoke test nhỏ.
    3. Sinh batch trajectory nhỏ hoặc train smoke test.
    4. Kiểm tra output/log/checkpoint được lưu bền vững.
    5. Chỉ sau đó chạy job dài.

    Expected:
    - Ghi chú cấu hình server.
    - Environment log (OS, Python, CUDA/driver, package versions).
    - Ít nhất một job generation hoặc training hoàn thành.
    - Có log/output và hướng dẫn tái chạy/dừng job.

    ======================================================================
    10. BACKUP, GIT
    ======================================================================

    Trước khi sửa:
    - Kiểm tra git status --short và branch hiện tại.
    - Không xóa/ghi đè file đang được người khác sửa.
    - Backup baseline và ghi SHA256.
    - Commit thay đổi có ý nghĩa với message rõ ràng.
    - Kiểm tra .gitignore/policy trước khi commit raw data/checkpoint lớn.

    Sau mỗi giai đoạn, cần cập nhật task.txt:
    - Status: DONE / IN PROGRESS / BLOCKED.
    - Ngày hoàn thành.
    - Files/output paths.
    - Lệnh đã chạy.
    - Expected vs actual.
    - Git commit hash.
    - Vấn đề còn lại.

    ======================================================================
    11. CHECKLIST THEO THỨ TỰ
    ======================================================================

    [x] 1. Xác minh repo, branch, git status và file nguồn.
    [x] 2. Xác minh raw pool có 500 record/100 problem; giữ nguyên file.
    [x] 3. Xác minh review cases có 34; giải quyết discrepancy division FP=113.
    [x] 4. Đọc guideline và chốt định nghĩa capability. (D1-D3 chốt trong config/guideline_v3.md)
    [x] 5. Đọc trace 34 case; điền manual_adjudication.csv.
    [x] 6. Kiểm tra Rows/Reviewed/Needs discussion/Pending/missing/duplicates/invalid values.
    [x] 7. Sao lưu annotation, rules, baseline reports và tạo SHA256 manifest.
    [~] 8. Annotate pilot A2, tính kappa cho 7 capability. (BLOCKED: cần xác minh A2 độc lập, A1/A2 trùng 30/30)
    [x] 9. Bổ sung ratio/percentage/fraction annotations.
    [x] 10. Đóng 5 ambiguous cases.
    [x] 11. Chạy extractor có kiểm soát; lưu report mới, không ghi đè baseline. (reports/task4_reruns/)
    [x] 12. Tạo/freeze split, config, selection schema, analysis plan; commit. (--frozen PASS; smoke test 2026-10-20: I3, I5 đã chốt, I4 tạm, xem mục 0)
    [ ] 13. Validate pool chính thức trên D_pool.
    [ ] 14. Evaluate S0, tính L_proxy, selection, train S1, evaluate.
    [ ] 15. Render graph/learning curve từ số liệu thật.
    [ ] 16. Đồng bộ protocol/README, requirements, test clean environment.
    [ ] 17. Cloud smoke test; chỉ chạy dài sau khi pipeline ổn.
    [ ] 18. Cập nhật task.txt với kết quả thực tế và commit hash.

    ======================================================================
    12. TIÊU CHÍ HOÀN THÀNH TASK (DONE)
    ======================================================================

    Không đánh dấu DONE chỉ vì script chạy một lần. Chỉ đánh dấu DONE khi:
    - Input/output đúng và có thể kiểm tra.
    - Actual result khớp expected result hoặc sai lệch được giải thích.
    - Raw data/baseline không bị ghi đè.
    - Có log/report/manifest phù hợp.
    - Lệnh chạy có thể tái lập.
    - Quyết định thủ công có rationale/audit trail.
    - Thay đổi code/config/data được commit theo quy trình nhóm.

    KẾT LUẬN BÀN GIAO
    Tài sản quan trọng nhất hiện tại là raw pool 500 trajectory và baseline extractor/reports. Ưu tiên là hoàn thiện adjudication và 
    chất lượng nhãn, giữ nguyên raw pool/baseline, rồi freeze split/config, chốt pool D_pool chính thức, chạy S0 -> S1 và chuẩn bị cloud.
