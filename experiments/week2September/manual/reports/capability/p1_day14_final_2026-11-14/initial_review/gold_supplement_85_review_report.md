# Báo cáo AI review Gold supplement – 85 records

## 1. Phạm vi và kết quả

- Đã đọc và đối chiếu 85 record supplement Gold vFinal với câu hỏi và final answer trong GSM8K.
- Record duy nhất: 85/85.
- Kết quả đề xuất: 84 record giữ nguyên nhãn; 1 record cần manual adjudication do bất nhất nguồn.
- Đây là AI review proposal, chưa phải human confirmation/approval.

## 2. Giới hạn bằng chứng

- `gsm8k_train.jsonl` chỉ có `question` và `ground_truth` (final answer). Không có worked solution/reference reasoning trace.
- Vì thiếu solution trace, không thể xác nhận độc lập toàn bộ chuỗi suy luận hoặc tính đúng của final answer. Review tập trung vào việc nhãn capability có được câu hỏi hỗ trợ hay không, kết hợp annotation notes hiện có.
- `gold_vfinal` và `gold_vnext` có cùng nội dung cho cả 85 record supplement; điều này chỉ chứng minh hai snapshot giống nhau, không chứng minh nhãn đúng.
- A1/A2 có 25 cặp annotation; đây không phải evidence rằng toàn bộ 85 supplement đã được double-annotate.

## 3. Record cần người phụ trách quyết định

### gsm8k_train_00830

- Câu hỏi không cung cấp giá mango lassi, nhưng ghi chú annotation mô tả phép tính giả định lassi giá $2; ground truth chỉ là `25`.
- Đề xuất: giữ nguyên nhãn hiện tại tạm thời; không tự sửa. Cần xác nhận đúng phiên bản câu hỏi/đáp án/solution source trước khi chốt.

## 4. Các giả định cần lưu ý

- `gsm8k_train_00769`: phép tính xác suất dựa trên giả định hai vụ kiện độc lập; câu hỏi không nêu rõ độc lập.
- `gsm8k_train_00239`: cách hiểu phần giao 5% phụ thuộc mẫu số là tổng số germs; annotation notes đã ghi nhận cách hiểu này.
- `gsm8k_train_00713`: bài toán xác suất nhiều tầng; không có solution trace để kiểm tra giả định diễn giải độc lập.
- Với ratio, division chỉ được giữ khi cần chia tổng thành các phần hoặc tìm giá trị một phần; với fraction/percentage, không gán division/multiplication chỉ vì đó là cách thực thi phép tính.

## 5. Việc chưa thể hoàn tất

- Chưa thể hoàn thành review 170 extractor-error records vì ZIP không chứa `priority_error_review_annotated.csv` hoặc `priority_error_review.csv`.
- Chưa thể đối chiếu chính thức với guideline v3 vì ZIP không chứa `guideline_v3.md`. Phần diễn giải hiện tại dựa trên các quy tắc guideline v3 đã được xác định trong ngữ cảnh dự án; cần file gốc để kiểm tra câu chữ/phiên bản trước khi đóng hồ sơ.
- Chưa được phép ghi bất kỳ dòng nào thành human `CONFIRMED`; cột human approval vẫn là `PENDING_USER_REVIEW`.

## 6. Hành động tiếp theo

1. Người dùng xem `gold_supplement_85_ai_review.csv`, đặc biệt record `gsm8k_train_00830`.
2. Cung cấp thêm `priority_error_review_annotated.csv`, `priority_error_review.csv` (nếu có), và `guideline_v3.md` để hoàn thành review 170 extractor errors và xác thực quy tắc.
3. Sau khi người dùng phản hồi chấp thuận hoặc yêu cầu sửa, tạo bản approval/changelog riêng. Không sửa ngược lịch sử annotator hoặc giả lập human confirmation.

## 7. Ý nghĩa trạng thái

- `AI_REVIEW_NO_CHANGE`: AI đã xem câu hỏi/nhãn/ghi chú và hiện chưa đề xuất đổi nhãn; không đồng nghĩa human-confirmed.
- `NEEDS_MANUAL_ADJUDICATION`: cần quyết định từ người phụ trách do thiếu/không nhất quán bằng chứng.
- `PENDING_USER_REVIEW`: chờ người dùng duyệt kết quả AI.