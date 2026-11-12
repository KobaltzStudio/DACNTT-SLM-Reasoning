# BÁO CÁO TIẾN ĐỘ — 14/11/2026
## Dynamic Learnability-aware CoT Knowledge Distillation
### Person A — Proposal 1: Capability Annotation, Gold Audit và Extractor Review

## I. Tổng quan

Trong ngày 14/11, nhóm đã hoàn thành vòng kiểm tra Gold supplement và review priority extractor-error queue. Người phụ trách đã xác nhận chấp thuận kết quả review 170 extractor-error records và phê duyệt kết quả review 85 Gold supplement records. Các kết quả được lưu thành artifact riêng; dữ liệu nguồn và các kết quả thực nghiệm lịch sử không bị ghi đè.

## II. Công việc đã hoàn thành

### 1. Gold vFinal inventory và integrity audit

- Đã kiểm tra Gold vFinal supplement gồm 85 records, 85 problem_id duy nhất.
- Đã đối chiếu các record với raw GSM8K, annotation metadata và snapshot Gold vNext.
- Đã hoàn thành AI-assisted review cho toàn bộ 85 records.
- 84 records giữ nguyên nhãn theo kết quả review.
- `gsm8k_train_00830` được làm rõ bằng prompt và reasoning trace do người phụ trách cung cấp. Người phụ trách xác nhận không thay thế record bằng ví dụ Janet grocery budget. Gold labels hiện tại được giữ nguyên: `addition`, `multiplication`, `percentage`.
- Người phụ trách đã phê duyệt kết quả review 85 supplement records.

### 2. Review 170 priority extractor-error records

- Đã review 170/170 records, với 170 problem_id duy nhất và không có duplicate.
- Đã điền các trường review: `review_status`, `error_classification`, `gold_label_correct`, `extractor_rule_issue`, `proposed_action`, `review_notes`, `reviewer`.
- Phân loại: 153 `MISSING_RULE`, 16 `MIXED_MISSING_AND_OVERLY_BROAD_RULES`, 1 `SOURCE_VARIANT_MISMATCH`.
- Tổng số lần xuất hiện FN theo capability: addition 68, subtraction 65, multiplication 117, division 81, percentage 0, fraction 0, ratio 6.
- Tổng số lần xuất hiện FP theo capability: addition 3, subtraction 1, multiplication 3, division 8, percentage 0, fraction 2, ratio 0.
- Đây là số lần xuất hiện capability trong FN/FP, không phải số problem duy nhất.
- Người phụ trách đã xác nhận đồng ý với kết quả review 170 records.

### 3. Áp dụng Guideline v3

Review áp dụng nguyên tắc:
- Gold là problem-level, không phải tập hợp mọi operation xuất hiện trong một trajectory.
- Fraction-of-quantity không tự động kéo theo division.
- Division chỉ áp dụng trong các trường hợp sharing, grouping, unit value/rate, inverse hoặc part-to-whole comparison.
- Ratio chỉ được gán khi proportional reasoning là đối tượng trung tâm.

### 4. Approval và lưu trữ kết quả

Đã tạo approval record riêng cho 85 Gold supplement review và 170 extractor-error review. Approval chỉ áp dụng cho kết quả review; không đồng nghĩa với việc cho phép thay đổi Gold source, raw GSM8K hoặc extractor rules.

## III. Kết quả và nhận xét

Priority error review cho thấy missing rules là nhóm lỗi chủ đạo. Multiplication có 117 FN occurrences, tiếp theo là division 81, subtraction 65 và addition 68. Điều này gợi ý extractor hiện tại cần cải thiện khả năng nhận diện phép toán trong ngữ cảnh, đặc biệt là số lượng × đơn giá, tổng hợp đại lượng, phép trừ phần còn lại và các tình huống division đúng theo định nghĩa v3.

Không nên xử lý bằng cách bổ sung keyword đơn lẻ. Mỗi thay đổi rule cần có positive/negative examples và regression tests để tránh tăng false positives.

## IV. Giới hạn và công việc chưa hoàn thành

- Raw GSM8K source package chỉ cung cấp question và final answer; không có worked solution cho toàn bộ 170 priority records. Vì vậy, phân tích cơ chế extractor dựa trên question, Gold, prediction, evidence, rules fired và annotation notes; không tuyên bố đã xác minh độc lập reasoning trace cho toàn bộ Gold.
- Review và approval đã hoàn tất, nhưng chưa triển khai thay đổi extractor rules.
- Chưa chạy regression test mới sau khi chỉnh rule.
- Chưa có cơ sở để tuyên bố Proposal 1 cải thiện Student mastery hoặc transfer; các kết luận này cần thực nghiệm riêng.
- Báo cáo này không xác nhận bất kỳ thay đổi nào đối với training, evaluation hoặc RunPod artifacts.

## V. Kế hoạch tiếp theo

1. Thiết kế thay đổi extractor rules theo nhóm lỗi ưu tiên, bắt đầu với multiplication, division, subtraction và addition.
2. Xây dựng positive/negative regression cases từ 170-row review; tách lỗi extractor khỏi các trường hợp trajectory-route false positive.
3. Tạo phiên bản rule mới, không ghi đè rule hoặc D3 historical outputs.
4. Chạy unit tests và regression evaluation; báo cáo precision, recall, F1, exact match và phân tích theo capability.
5. Tiếp tục phần Student mastery/transfer evaluation bằng protocol đã xác định; không suy diễn từ extractor metrics sang Student learning outcomes.

## VI. Kết luận

Trong phạm vi Proposal 1 của ngày 14/11/2026, Gold supplement review (85 records) và priority extractor-error review (170 records) đã được hoàn thành và được người phụ trách phê duyệt. Các artifact review và approval được lưu riêng, không làm thay đổi dữ liệu nguồn hoặc kết quả thực nghiệm lịch sử. Công việc tiếp theo là chuyển các phát hiện lỗi thành thay đổi extractor có versioning và regression validation.
