# Phạm vi dữ liệu G6–G8

| Gate | Status | Kết quả hiện tại |
|---|---|---|
| G6 | PARTIAL | 39/39 sidecar hợp lệ, 37 nhóm logic. Hai bản ghi B4 có provenance thay thế và không được đếm hai lần. Bảng seed 13 có 63 dòng (9 nhóm × 7 capabilities), chung một S0, Wilson CI 95%. |
| G7 | PARTIAL | 9 checkpoint quan sát, đúng 415 D_dev_select ID, A S1 đạt 347/415, B S1 đạt 340/415. Không có checkpoint nào được chốt thắng. |
| G8 | PARTIAL | 7 PNG và 7 CSV tái tạo từ artifact quan sát. Toàn bộ 14 file tái tạo có cùng SHA với bản trước và 38 file đầu vào được rehash. Coverage S0–S3 còn thiếu. |

G6 giữ số correct, incorrect, mastery và support theo taxonomy Gold. G6 mapped xác minh cả 3 artifact checkpoint G4 ngoài manual root bằng đúng SHA và giới hạn phạm vi mapping. Kết quả chính thức của phiên là `g6_mapped_verified/` với exit 4 do coverage chưa đủ. Lần kiểm tra mapped đầu tiên phát hiện 3 đường dẫn G4 ngoài manual và ghi bằng chứng riêng trong `g6_mapped.log`.

G7 dùng strict `status == "valid"` đúng subset từ manifest, tie-break checkpoint sớm nhất khi đủ candidates. Kiểm chứng byte prediction và adapter P1, giữ nguồn B4 S1 derived theo SHA đã xác minh. B4/B5 S1 chưa có bằng chứng SHA checkpoint trùng nhau nên giữ provenance riêng. D_dev_select IDs SHA-256 là `c08527e9c90181d2a35e037dc314fe17d8681aaf5ae57b7d6ee041ed014b6508`. Split manifest SHA-256 là `526b76686b5ee7dc55771ba12e245f02fd21f0ca647484e23c19a6f629925e2f`. Xem `g7_verified/`, exit 0 xác nhận bản partial được công bố.

G8 có selection Jaccard, selection composition, D_dev accuracy, capability mastery, capability makeup, L_proxy distribution và P1 capability learning curves. D_dev full 500 giữ nhãn riêng với G7. CSV giữ scope seed 13 và nguồn, điểm vắng mặt được ghi trong manifest. R2 của A có selection đã lưu nên có thể đóng góp selection, còn prediction 75/500 không đủ làm điểm accuracy/mastery. Learnability lấy từ scoring artifacts P2/P1P2, không dùng raw NLL thay L_proxy. Hình phục vụ phân tích mô tả. Không suy ra cạnh prerequisite từ các hình.

Artifact kiểm chứng ở `analysis_artifact_verification.json`, `g8/figure_manifest.json` và `g8_preflight.log`. Các report mới chỉ đọc dữ liệu đóng băng và công bố vào thư mục riêng. Cần P1-DEFICIT S2/S3 và P1P2 S2/S3 đã xác minh để đóng các gate.
