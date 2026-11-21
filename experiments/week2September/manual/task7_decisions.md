# Task 7: Các quyết định trước thí nghiệm chính

Trạng thái: **ĐÃ CHỐT (2026-11-01)** T7-1 đến T7-8; **T7-9 (2026-11-10)** làm rõ khi cài đặt, xem mục riêng. T7-1 đến T7-8 theo đúng đề xuất trong `notes/analysis_rules_proposal.md` (giải thích, số minh hoạ và nguồn nằm ở file đó). Chốt trước khi có bất kỳ số liệu nào của thí nghiệm chính. Mọi thay đổi sau này phải ghi thêm mục mới kèm lý do.

Áp dụng trong: `config/experiment_config.json` v2, `analysis_plan.md` v2. Manifest: `reports/task7/SHA256SUMS_task7_setup.txt`.

Số minh hoạ chỉ từ smoke test trên pool sơ bộ, không phải kết quả.

| # | Quyết định | Lý do ngắn |
|---|---|---|
| T7-1 | B4: xếp hạng một lần tại S_0 theo L_proxy, mỗi vòng đi tiếp theo thứ hạng, không lặp trajectory. Trajectory bị n_cap bỏ qua trong một vòng vẫn còn cho vòng sau | Nếu lặp cùng một tập, B5 vs B4 lẫn với "dữ liệu mới so với lặp", trái với thiết kế "chỉ khác ở việc tính lại" |
| T7-2 | B3: xáo các bài một lần, mỗi vòng đi tiếp theo thứ tự, không lặp trajectory | Nhất quán với T7-1. Đủ dữ liệu: tổng lời giải ngắn nhất 222.521 token, lớn hơn tổng ngân sách 136.278 |
| T7-3 | ℓ*_t và σ_t tính trên các trajectory eligible chưa train trong lần chạy đó; L_proxy vẫn tính cho mọi trajectory eligible | Lời giải đã học có ℓ giảm cơ học (khoảng 0,091 so với 0,036). Lợi ích thật chưa chắc, vì nhiễu seed lớn hơn độ dịch tâm |
| T7-4 | Ngưỡng Δ ≥ 0,05 trong tiêu chí H | Quy ước của nhóm, không có nguồn, chỉ để chặn chênh lệch rất nhỏ do mẫu lớn |
| T7-5 | Accuracy chấm nới là chỉ số phụ đã đăng ký trước, luôn báo cáo cùng accuracy chặt và tỉ lệ đúng định dạng; đọc thủ công nhóm đúng nhờ chấm nới | Khoảng 40% mức tăng ở smoke test đến từ học định dạng |
| T7-6 | ε = phân vị 95% của \|L^a − L^b\| trên U, đo bằng các lần chạy B4 tại S_1; báo cáo kèm 2,77·s_w | Nhiễu L_proxy không đồng đều nên công thức dựa trên phân phối chuẩn không phù hợp |
| T7-7 | Kiểm định H: bootstrap theo cụm bài toán, tính trên B4, phải đạt ở mọi seed. Thang đo quyết định là L_proxy, báo cáo kèm ℓ và ràng buộc cách viết kết luận | Hai hệ số tương quan phụ thuộc nhau, các lời giải cùng bài không độc lập. Trên smoke test, Δ của L_proxy là 0,16–0,23, của ℓ chỉ 0,01–0,02 |
| T7-8 | Báo cáo Jaccard giữa tập chọn vòng 2 của B5 ở các seed, so với mức ngẫu nhiên khoảng 0,02 | Nhiễu seed của ℓ (khoảng 0,2σ) lớn hơn nửa độ rộng dải chọn (khoảng 0,05σ), nên tập chọn có thể phụ thuộc nhiều vào seed |

## T7-9: Làm rõ khi cài đặt (2026-11-10)

Chốt trước khi chạy chính, chưa có số liệu nào của thí nghiệm chính. Hai mục dưới đây không đổi giá trị nào trong config hay kế hoạch phân tích, chỉ làm rõ cách hiểu.

| # | Quyết định | Lý do ngắn |
|---|---|---|
| T7-9a | Đơn vị ngân sách là token phản hồi theo tokenizer Student, **không tính** `<|im_end|>`; giữ `beta_round = 45.426`. Token có tính loss khi train bằng số đó cộng 1 mỗi trajectory và được ghi riêng trong train log (`supervised_tokens`). Câu "supervised (loss-bearing) response tokens" trong `budget.unit` của config được hiểu theo nghĩa này | `L̄ = 227,13` (`reports/task5/pool_token_stats.json`) đếm không có `<|im_end|>`, nên 45.426 = 200 × L̄ cùng đơn vị. Chênh khoảng 1 token mỗi trajectory (khoảng 0,4–0,5% mỗi vòng), gần như đều giữa các phương pháp |
| T7-9b | `scripts/answer_utils.py` là extractor/verifier chính thức theo I1 (`task5_decisions.md`). Dòng "Status: PROPOSED, not frozen" trong docstring của file là chữ cũ từ trước khi chốt; giữ nguyên file | Sửa file sẽ làm lệch hash trong `reports/task5/SHA256SUMS_task5.txt`, mà smoke test và pool v1 đã chạy với đúng file này |

Còn chờ nhóm quyết định (chưa thuộc T7-9): dừng khi trajectory kế tiếp vượt ngân sách (đang cài: dừng, không lấy bù), giữ hay bỏ ablation và seed của nó (đang cài: `training_seed * 100 + round + 50`), biến thể chọn theo ℓ cao / ℓ thấp, phiên bản nhãn capability dùng khi đánh giá (đang dùng supplement v2).

## Ảnh hưởng tới các file khác

- Config và kế hoạch v1 được lưu nguyên vẹn ở `config/experiment_config_v1.json` (SHA-256 `7c5aa72d…`) và `analysis_plan_v1.md`. Smoke test và pool v1 đã chạy với config v1; `pool_v1_manifest.json` và các file `run_*.json` ghi đúng hash này. Chạy lại các script Task 6 bây giờ sẽ ghi hash của v2.
- `reports/task5/SHA256SUMS_task5.txt`: chỉ đổi đường dẫn hai dòng sang các file `_v1`, hash giữ nguyên; vẫn khớp 33/33.
- Không đổi: ngân sách, cấu hình huấn luyện, seed, quy trình đánh giá, so sánh chính B5 vs B4, chỉ số chính, pool v1. `config/proposal2_full_protocol.md` là bản chép nguyên văn nên giữ nguyên; khi khác nhau, `analysis_plan.md` v2 được ưu tiên.
- Chi phí thêm: NLL của B4 tại S_2 cho 3 seed (khoảng 1 giờ mỗi lượt trên T4, chưa đo trên L4). NLL của B4 tại S_1 trùng với B5 nên không tốn thêm.

## Việc còn để ngỏ

- I4 (probe b = 7) vẫn tạm, chốt khi đo L_emp.
- L_emp chỉ có 5 nhóm nên Spearman với L_proxy gần như chỉ mang tính mô tả. Chưa đổi quy tắc này trong đợt chốt.
- Chưa bổ sung biến thể chọn theo ℓ cao và ℓ thấp (`notes/formula_review.md`, mục A2).
- Scripts chưa cài đặt các quy tắc trên. Việc này thuộc `Task.md` mục 2.1.
