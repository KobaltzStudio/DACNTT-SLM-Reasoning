# Portability Windows → Linux

**PARTIAL.** Windows CPU xác minh resolver, provenance và plan; Linux resume và G9 chưa chạy. WSL chỉ liệt kê môi trường Docker Desktop. Docker Linux engine không có endpoint hoạt động tại thời điểm kiểm tra. Không bật Docker, không tải image và không kết nối RunPod.

## Lỗi và cách xử lý

- Train set ghi `pool`, `state_file`, `nll_file` theo path gốc. Controller hoặc train engine resolve bằng root staging và so đúng locator cùng SHA, tránh dùng nhầm pool hoặc NLL.
- `train_log.json` ghi `checkpoint_parent`. Controller resolve locator về adapter cha đã xác minh và so SHA.
- Checkpoint log ghi path Windows cho train set, adapter và train log. Khi so sánh, chỉ chuẩn hóa các locator trong bộ nhớ. Hook/sidecar tiếp tục dùng bytes của prefix gốc. Các dòng mới dùng đường dẫn của Linux staging. Giữ manual root Linux ổn định sau khi đã sinh artifact mới.
- Windows sắp thứ tự tên adapter theo chữ thường khi tính directory hash. Thuật toán dùng thứ tự này trên mọi host, giữ nguyên casing, relative name và bytes file trong digest. Test kiểm chứng `adapter_config.json` đứng trước `README.md`. Case collision bị chặn. Artifact có hash theo thứ tự Linux cũ, nếu phát hiện, phải audit riêng.
- G6 map thêm đúng nhánh ngoài manual `P2/integration_staging/G4_CHECKPOINT_AUDIT/extracted_checkpoints` cho checkpoint archive. Checkpoint thiếu hoặc hash sai bị từ chối ở chế độ mapped. Không mở rộng mapping sang cây thư mục tùy ý.
- Resolver yêu cầu Windows prefix tường minh, giữ relative suffix, từ chối traversal, đường dẫn ngoài root và escape qua symlink. Đường dẫn audit được giữ nguyên trong các artifact.

`runpod_path_reference_inventory_sealed.csv` kiểm kê 226 locator trong metadata của bộ transfer (220 có đích, 6 locator G4 train set/train log ngoài mapping runtime chỉ để diễn giải lineage). Cả 6 thuộc sidecar G4. Train log nằm trong bộ adapter G4, original train sets G4 không được controller tích hợp sử dụng. Scope inventory không gồm mọi bản sao lịch sử bên ngoài transfer.

`runpod_transfer_verification_sealed.json` xác minh 572/582 file của manifest cũ có SHA không đổi. 10 file thay đổi thuộc source/tests được ghi old/new SHA. Bộ cuối có 616 file ở manual root và 22 file phụ ở P2 root, gồm 21 file archive G4 và dependency lock. Dữ liệu được nhận diện theo path tương đối và SHA, không chỉnh JSON để di chuyển.

## Resume đã kiểm chứng

Fixture copy staging đầy đủ S1 và prefix S2 75/500, đổi root, tái dùng S1 với 0 bước và plan đúng 4 bước S2. Bytes của checkpoint log và prediction prefix khớp. Sai source root bị chặn. Fixture chaining kiểm tra S3 dùng adapter S2 và NLL mới theo checkpoint. Windows plan thật cho A S2 trùng phạm vi fixture. B S1 đã hoàn tất nhận 0 bước. Cần thực hiện CPU dry-run trên Linux với bộ transfer thật và đối chiếu từng stage trước khi xin phê duyệt GPU.
