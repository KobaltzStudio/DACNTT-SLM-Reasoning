# Kiểm tra khả năng chuyển RunPod

RunPod chưa chạy. Windows manual root `C:\Users\PC - NGHI\Desktop\Pipeline\P2\experiments\week2September\manual` ánh xạ theo từng đường dẫn tương đối đến `/workspace/Pipeline/P2/experiments/week2September/manual`. Cả hai repo và đường dẫn staging gốc được giữ.

| Thành phần | Xử lý khi chuyển |
|---|---|
| Controller, training, eval và hook | `pathlib` dựng path mới từ manual root. Giữ đúng cấu trúc thư mục và tên adapter. |
| Round 1 train set | `state_file`, `nll_file` và `pool` có thể lưu Windows tuyệt đối. Linux không tự resolve UNC/drive path. Training có fallback kiểm tra pool, selector/controller cần mapping cho state/NLL. |
| S2 train log Run A | `checkpoint_parent` là đường dẫn Windows đến S1 và có SHA-256. Việc đối chiếu parent hiện dựa vào `Path.resolve`, nên chuyển adapter đơn thuần có thể chặn resume. |
| Checkpoint log và sidecar | So sánh checkpoint row có đường dẫn tuyệt đối trong khi sidecar buộc hash byte prefix của chính log. Sửa path trong log cũ sẽ làm mất provenance. |
| Prediction intent và adapter | Intent lưu adapter/content hash. Cần giữ byte của adapter config/weights/tokenizer và mọi file trong thư mục dùng để tính hash. |
| Các script audit lịch sử | Ví dụ `audit_g6_inputs.py`, `audit_g6_token_table.py`, `build_b4_seed13_capability_predictions.py` có path Windows hardcode. Dùng builder tích hợp có tùy chọn manual root cho phân tích hiện tại. |

**Blocker Linux:** triển khai hoặc xác minh một resolver chỉ đọc, nhận ánh xạ từ legacy prefix sang staging root. Cho phép thay path khi hậu tố relative nằm trong namespace cho phép và hash recorded khớp byte của bản staging. Giữ original train set, checkpoint log và sidecar bất biến. Đối chiếu **semantic path identity** cho trường locator và tiếp tục xác minh **original bytes** cho checkpoint prefix, train set, adapter và prediction. Dùng fixture Windows→Linux cho S0 inputs, S1 reuse, S2 partial eval và S3 parent lineage. Chạy dry-run ở Linux trước khi bật bất kỳ cơ hội thực thi nào. Các lệnh trong handoff là lệnh ứng viên đã khớp CLI, chưa là bằng chứng qua G9.
