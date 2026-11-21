# Đề xuất đường dẫn ổn định cho tích hợp P1 P2

Ưu tiên tạo một entry point từ `P2/experiments/p1p2_unified` truyền `--manual-root` về thư mục cũ. Lớp tương thích này giữ toàn bộ artifact và hash ở vị trí hiện tại. Một lần di chuyển thật cần phê duyệt riêng.

| Hiện tại | Đề xuất | Điều kiện |
|---|---|---|
| `P2/experiments/week2September/manual` | `P2/experiments/p1p2_unified` | Giai đoạn đầu chỉ thêm wrapper, chưa chuyển dữ liệu |
| `.../manual/{scripts,config,data,trajectory,splits}` | `.../p1p2_unified/{scripts,config,data,trajectory,splits}` | Nếu di chuyển thật, giữ relative layout và xác minh resolver path |
| `.../manual/{runs,models,reports}/p1p2_integration` | Layout tương ứng dưới root mới | Kiểm tra adapter, checkpoint log prefix, waypoint resume, manifest |
| `P1/experiments/week2September/manual` | Giữ nguyên | Repo P1 độc lập và đầy đủ nguồn lịch sử |
| `.../manual/runs/main`, `.../manual/models/task7`, sidecar lịch sử | Giữ vị trí gốc hoặc bản staging chỉ đọc | Không đổi bytes hay làm mất locator cũ |

Canonical wrapper có thể gọi `python <legacy-root>/scripts/run_p1_p2.py --manual-root <legacy-root> ...` bằng PowerShell hoặc Bash. Khi di chuyển file thật, rà `rg -n 'week2September[/\\]manual'` trong scripts, config và guide. Kiểm tra các import sibling, `__file__.resolve()`, config/pool cache, Windows/RunPod path, audit scripts và refs trong guide. Dùng nhánh thử nghiệm được phê duyệt và `git mv` riêng cho source tracked. Với artifact nghiên cứu, sao chép vào staging và đối chiếu SHA-256 trước khi thay đổi vận hành.

Chạy unit, fixture resume/no-overwrite, hook và dry-run từng method trước/sau. Rà stdout, plan paths, hashes, artifact count và case sensitivity Linux. Việc đánh giá không được gọi D_test. Đối với artifact cũ, giao lại đường dẫn gốc qua mapping chỉ đọc và kiểm tra hash với original bytes. Không rewrite manifest để hợp thức hóa migration.

Rollback bằng việc đưa entry point về legacy root và giữ bản checkout/copy cũ. Nếu có chênh lệch output, sắp xếp lại staging theo mapping ban đầu và mở audit riêng, không xóa dữ liệu để làm sạch kết quả. Không di chuyển hay đổi tên ở lượt này.
