# Đề xuất cập nhật kế hoạch sau kiểm chứng P1 P2

Đề xuất bổ sung cho các tài liệu kế hoạch gốc. Các file DOCX được giữ nguyên.

- `C:\Users\PC - NGHI\Desktop\Pipeline\KeHoachTichHop_P1_P2_RunPod_BoSungSauValidation.docx` — SHA-256 `5f41889dc35847622e554dd8375691d28c25a34bf0a5ea442a559752f57ddb8c`
- `C:\Users\PC - NGHI\Desktop\Pipeline\P1_P2_RunPod_Merge_Plan_With_PostValidation.docx` — SHA-256 `625397689b90653c0c92b9611b13306aa90e4516b016a025d57d7b67b5e04d3e`
- `C:\Users\PC - NGHI\Desktop\Pipeline\KeHoachPhanCong_DieuChinh_Proposal1_14-20_11_2026.docx` — SHA-256 `89d081f450bbb4d09a3cf8264200c4a52fad3d04a2e13bb580946b03a42a61a8`

| Mục của kế hoạch | Hiện trạng và bằng chứng | Điều kiện cập nhật tiếp |
|---|---|---|
| Kế hoạch tích hợp, Bước 11 / RunPod integration | Hook và resume đã kiểm tra local, RunPod chưa chạy | GPU/image Linux, resolver path, dry-run và smoke/resume trên RunPod |
| Kế hoạch phân công, P1-F | Run A S1 83,2%; Run B S1 81.2%; Gold hook 85 ID và bảy capability đã xác minh | Run A S2 eval và S3, Run B S2/S3, phê duyệt riêng |
| Learning dynamics và final freeze | G6 37 nhóm logic; G7 partial; G8 7 figure dữ liệu quan sát | Phải có đủ sidecar/prediction và kiểm tra canonical |
| Phần 14.1 sau Final Validation | Các nghiên cứu bổ sung giữ trạng thái chờ | Hoàn tất validation, khóa checkpoint D_dev_select, đăng ký method/config/manifest riêng |
| Kết quả held-out và graph | D_test chưa chạy. Chưa suy ra cạnh prerequisite từ capability co-occurrence | Cần chọn checkpoint đã khóa và phê duyệt D_test; graph cần bằng chứng transfer độc lập |

## Checklist cập nhật

- [ ] Nối lại Run A S2 bằng prefix hợp lệ, kiểm tra adapter S1→S2 rồi chạy S3 nếu được duyệt.
- [ ] Duyệt Run B S2–S3, kiểm tra NLL theo checkpoint, lineage và sidecar từng lượt.
- [ ] Sinh lại bảng strict 415 ID, bảng động học và đúng bảy PNG/CSV ở namespace version mới.
- [ ] Ghi hash, GPU/CUDA, thời gian, run log, coverage và kết quả resume Linux. Chỉ khóa Final Validation sau đủ gate.

Bằng chứng chi tiết trong [audit S1](run_b_seed13_s1_validation.json), [dừng Run A](run_a_stopped_verification.json), [readiness figure](figure_readiness_seed13.json) và [handoff RunPod](runpod_handoff.md).
