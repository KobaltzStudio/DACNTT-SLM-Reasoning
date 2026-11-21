# Phương án cleanup và migration

**PASS kiểm kê. NOT RUN thao tác thật.** Bảng `cleanup_inventory_updated.csv` kiểm 4.790 file, 65 ZIP và 213 bytecode candidates (~2,36 MB). Có 1.753 kết quả tóm tắt locator ở 1.132 file. 596 file có tham chiếu `week2September/manual` hoặc biến thể dấu gạch. Scan đọc source, shell, docs, YAML/JSON và checkpoint metadata dạng văn bản UTF-8 tới 2 MiB; file nhị phân, ZIP content, file lớn hơn, symlink/junction và cache dir môi trường không thuộc scan text. Các số CRC member lấy từ lần audit trước khi SHA ZIP còn khớp. Đồ thị phụ thuộc tĩnh không thay thế kiểm thử sau bàn giao.

| Nguồn hiện tại | Đích đề xuất | Xử lý sau phê duyệt |
|---|---|---|
| `P2/experiments/week2September/manual/` | Giữ đường dẫn hiện hành | KEEP runtime, input và mọi artifact, tránh phá provenance và reference lịch sử |
| Chưa có `P2/experiments/p1p2_unified/` | Đường dẫn tên mới | Thêm lớp hướng dẫn/entry point mỏng trỏ canonical manual, chuyển đúng cwd khi chạy. Áp dụng khi user duyệt. |
| Các file transfer có SHA | Linux `/workspace/Pipeline/P2/experiments/week2September/manual/` và `/workspace/Pipeline/P2/` | Stage byte-for-byte theo hai manifest. Không copy toàn bộ tree và không chỉnh đường dẫn trong artifact. |
| `P1/experiments/week2September/manual/config/config_p1.zip` | `<verified-backup>/Pipeline_archive_20261119/P1/experiments/week2September/manual/config/config_p1.zip` | Chỉ đề xuất lưu bản archive byte-for-byte, giữ bản tại chỗ đến khi có quyết định riêng. SHA `274e375b23f47e29a40e5631500d51fc6570d203d2582e542908878bab537ef7`, CRC 14/14. |
| `P1/experiments/week2September/manual/scripts/scripts_p1_original.zip` | `<verified-backup>/Pipeline_archive_20261119/P1/experiments/week2September/manual/scripts/scripts_p1_original.zip` | Giữ nguồn proposal. SHA `873677512fff8d2d644a16ef0aa65fb608418a16bf6ef30e07add70185d5503f`, CRC 186/186. |
| `P1/experiments/week2September/manual/manual.zip` | Giữ đường dẫn hiện hành | UNKNOWN, 720/735 members khớp. Không xóa. Hai `ZIP/P1/manual.zip` và `ZIP/P2/manual.zip` là archive khác, cũng giữ. |
| 213 `__pycache__/*.pyc` trong CSV | Không có đích | DELETE CANDIDATE, chỉ cân nhắc sau xác minh lại Git và source tương ứng, trình danh sách trước khi thực thi. |

`p1p2_unified` mô tả đúng scope tích hợp. Đổi tên cả manual trộn source hiện hành với input, lịch sử P2, report và checkpoint. Các script dùng `Path(__file__).resolve().parents`, lệnh shell cd và những checkpoint ghi path tuyệt đối khiến đổi tên nguyên cây có rủi ro cao. Giữ P1/P2 Git roots độc lập, tránh di chuyển untracked scripts/tests.

### Nghiệm thu và rollback

1. Sau khi được phê duyệt, chốt đúng file/destination, yêu cầu file list no-overwrite, ghi Git status, process/lock, SHA source, free disk và backup URL/path thực tế. Xác minh backup trước khi chuyển bất kỳ file nào.
2. Thử trên staging có root canonical. Xác minh hai manifest, CPU tests, 0 bước ở A/B S1, đúng 4 bước chờ ở A S2, B S2/S3 lấy đúng parent, namespace và scope dev. Kiểm tra lại các cấu hình, symlink, shell cwd và locator bắt buộc.
3. So sánh G6 partial, G7 partial, G8 CSV, số ID và SHA artifacts tại staging. Hai archive proposal cần ~645 KB. Bộ chuyển RunPod ~572 MB chưa gồm cache Student và output, trong khi copy toàn manual ~1,74 GB. ZIP chiếm ~534 MB. Snapshot ổ hiện tại còn ~93,4 GB; dung lượng volume đích cần đo riêng.
4. Rollback khi SHA lệch, test fail hoặc resolve sai. Ngừng dùng lớp entry point mới và trỏ lại manual gốc, cách ly staging và lưu log. Nếu có bước được duyệt chuyển dữ liệu, copy ngược từ backup đã xác minh vào đúng path, kiểm SHA rồi mới xin duyệt dọn staging. Không dùng git clean/reset, không restore đè hồ sơ mới.
