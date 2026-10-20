# Tổng kết tuần 9 (19/10 – 25/10/2026)

Đề tài: Dynamic Learnability-aware CoT Knowledge Distillation

## I. Tổng quan

Tuần này nhóm khép lại giai đoạn chuẩn bị bằng cách cố định thiết lập thực nghiệm. Sau đó nhóm chạy smoke test đầu tiên: huấn luyện Student một vòng từ S_0 lên S_1 trên Google Colab. Đây là lần đầu tiên dự án có số liệu huấn luyện thật. Kết quả cho thấy Student học được từ lời giải của Teacher, nên nhóm giữ nguyên các tham số huấn luyện đang để tạm. Bên cạnh đó, nhóm sửa môi trường cài đặt, viết bảng tra thuật ngữ, đọc bài báo LARK và lập lại danh sách công việc cho các tuần tới.

## II. Công việc đã làm

### 1. Cố định thiết lập thực nghiệm (Task 5)

Nhóm chia dữ liệu thành ba tập với seed cố định: pool 6.968 câu, dev 500 câu, test là toàn bộ 1.319 câu test của GSM8K. Năm câu trong pool trùng đoạn văn từ 13 từ trở lên với dev hoặc test đã bị loại. Nhóm cũng đo độ dài lời giải của Teacher theo tokenizer của Student (trung bình khoảng 227 token) để ước lượng ngân sách token cho mỗi vòng. Sau đó nhóm cố định cấu hình thí nghiệm bản v1 (mô hình, số mẫu mỗi vòng, LoRA, learning rate, batch size), kế hoạch phân tích thống kê và định dạng nhật ký chọn dữ liệu, rồi lưu mã băm để không ai sửa được sau khi đã thấy kết quả. Hàm chấm đáp án cũng được viết lại và có bộ kiểm thử riêng.

### 2. Chuẩn bị smoke test

Smoke test nhằm trả lời ba câu hỏi: Student có học được gì từ Teacher không, các tham số tạm có hợp lý không, và chi phí chạy thực tế là bao nhiêu. Nhóm chốt cách làm trước khi chạy:
- Huấn luyện trên 200 trajectory chọn ngẫu nhiên từ 480 trajectory hợp lệ của pool sơ bộ.
- Coi là "thay đổi rõ" khi accuracy đổi từ 2 điểm % trở lên hoặc McNemar p < 0,1.
- Chạy với hai seed là 13 và 42, chỉ đánh giá trên dev, không dùng test.

Nhóm viết các script đánh giá, huấn luyện LoRA (loss chỉ tính trên phần lời giải), tính NLL cho pool và phân tích tự động, cùng một notebook Colab chạy toàn bộ quy trình và tự chạy tiếp khi bị ngắt. Trước khi lên Colab, nhóm chạy thử toàn bộ quy trình trên máy cá nhân bằng mô hình nhỏ Qwen2.5-0.5B. Lần chạy thử này phát hiện vấn đề về định dạng output, từ đó nhóm thêm chỉ số "accuracy lỏng" để chẩn đoán.

### 3. Kết quả smoke test

| | Seed 13 | Seed 42 |
|---|---|---|
| Accuracy trên dev (S_0 → S_1) | 71,2% → 83,0% | 71,2% → 81,8% |
| Số câu sai→đúng / đúng→sai | 89 / 30 (p ≈ 6e-8) | 84 / 31 (p ≈ 8e-7) |
| Accuracy lỏng, bỏ qua định dạng | 76,2% → 83,0% | 76,2% → 83,0% |
| Tỉ lệ đúng định dạng | 91,6% → 99,6% | 91,6% → 96,6% |
| Loss huấn luyện (đầu → cuối) | 0,225 → 0,189 | 0,235 → 0,208 |

Ở cả hai seed, accuracy tăng hơn 10 điểm %, vượt xa ngưỡng đã chốt, và kết quả giữa hai seed gần nhau. Theo tiêu chí đặt trước, nhóm **giữ nguyên các tham số tạm** (200 mẫu mỗi vòng, lr = 2e-4, batch 8) và không cần tạo cấu hình mới.

Tuy vậy, một phần mức tăng là do Student học được định dạng trả lời. Nếu bỏ qua định dạng, accuracy chỉ tăng khoảng 6,8 điểm. Phần học thêm về suy luận vì vậy vào khoảng 7 điểm, vẫn là một mức tăng rõ.

Về NLL trên pool, các trajectory đã dùng để huấn luyện giảm NLL nhiều gấp khoảng 2,5 lần các trajectory chưa dùng. Thứ hạng NLL gần như giữ nguyên sau một vòng, còn thứ hạng theo độ đo learnability (L_proxy) thay đổi đáng kể: chỉ khoảng một nửa trong top-200 trùng nhau. Đây mới là số liệu thăm dò, chưa diễn giải được khi chưa đo mức nhiễu.

### 4. Môi trường và tài liệu

- **Môi trường cài đặt:** chuyển file danh sách thư viện sang UTF-8, thêm nguồn cài PyTorch cho CUDA 12.6 và bổ sung các thư viện còn thiếu. Môi trường nay cài được trên cả Windows và Linux với Python 3.11 đến 3.14.
- **Bảng tra thuật ngữ:** viết bảng tra các thuật ngữ và ký hiệu dùng trong protocol, cấu hình và báo cáo, để cả nhóm dùng chung một cách gọi.
- **Bài báo LARK (2026):** đọc và tóm tắt. Bài này chọn trajectory theo learnability đo tại checkpoint gốc của Student. Điểm khác so với đề tài của nhóm là LARK chỉ đo một lần và không cập nhật lại theo các vòng huấn luyện. Bài báo cũng cho thấy chọn ngẫu nhiên là baseline khó vượt, và LARK đủ rẻ để cài làm baseline.
- **Danh sách công việc:** lập lại danh sách theo mức ưu tiên. Ước tính dự án hoàn thành khoảng 30–35%.

## III. Khó khăn

**Thiếu dữ liệu để giữ đúng cấu hình.** Pool sơ bộ chỉ có 98 câu nên không chọn được 200 trajectory mà vẫn giữ quy tắc mỗi câu tối đa một trajectory mỗi vòng. Nhóm phải tạm bỏ quy tắc này trong smoke test, nên Student thấy ít câu khác nhau hơn so với thí nghiệm chính.

**Khó tách việc học định dạng khỏi việc học suy luận.** Quy tắc chấm chặt tính sai cả khi Student giải đúng nhưng trình bày sai định dạng. Vì vậy accuracy chặt tăng mạnh chưa chắc phản ánh khả năng suy luận. Nhóm phải thêm accuracy lỏng làm chỉ số chẩn đoán nhưng vẫn giữ quy tắc chấm đã chốt.

**Thiếu GPU.** Máy cá nhân chỉ có GPU 4GB nên nhóm phải chạy trên Colab. Việc này đòi hỏi đóng gói dữ liệu, kiểm tra checksum và viết notebook có khả năng chạy tiếp khi bị ngắt. GPU của Colab không phải lúc nào cũng hỗ trợ bf16, nên kết quả có thể lệch nhẹ so với lúc chạy trên cloud.

**Phải chọn ngưỡng trước khi chạy.** Tài liệu gốc chỉ ghi "thay đổi rõ" mà không có con số cụ thể. Nhóm phải tự chọn ngưỡng 2 điểm % và McNemar p < 0,1 dựa trên sai số chuẩn của 500 câu.

## IV. Tồn đọng

- **Kết quả chưa đưa về repo.** Kết quả chi tiết của Colab (từng câu, log loss từng bước, thời gian chạy, VRAM) chưa được chép về repo và chưa chạy lại phân tích ở máy local. Chưa có số liệu chi phí nên chưa ước tính được chi phí thuê cloud. Chưa viết báo cáo smoke test và chưa cập nhật trạng thái các tham số trong cấu hình.
- **Student còn ít chỗ để cải thiện.** Student đã đạt khoảng 83% sau một vòng, trong khi Teacher 3B chỉ hơn Student gốc khoảng 16 điểm. Thí nghiệm chính có thể chạm trần sớm, làm các phương pháp chọn dữ liệu khó tách nhau. Ngoài ra có 30 câu chuyển từ đúng sang sai, cho thấy kết quả từng câu dao động khá nhiều. Nhóm cần cân nhắc đổi cặp mô hình trước khi sinh pool chính thức.
- **Các việc còn lại từ tuần trước:** xác minh người annotate thứ hai có làm độc lập không, giảm nhận nhầm division trong bộ trích xuất capability, sinh pool chính thức 1.000 câu, và thuê máy chủ cloud.

## V. Kế hoạch tuần sau

- Đưa kết quả Colab về repo và chạy lại phân tích để xác nhận số liệu smoke test.
- Xem log loss từng bước, thời gian chạy và VRAM để kết luận về độ ổn định và ước tính chi phí cloud.
- Tính McNemar trên accuracy lỏng để biết mức tăng thật về suy luận có ý nghĩa thống kê không.
- Viết báo cáo smoke test và ghi quyết định giữ tham số vào cấu hình và nhật ký quyết định.
- Họp nhóm quyết định giữ hay đổi cặp Teacher–Student để tránh chạm trần ở thí nghiệm chính.
- Chọn nhà cung cấp cloud và chạy một job thử để chuẩn bị sinh pool chính thức.
- Sinh pool trajectory chính thức cho ít nhất 1.000 câu để có đủ dữ liệu cho các vòng chọn.
