# Audit unified controller

**PASS trên Windows CPU.** Source dispatch và các tình huống resume được kiểm chứng bằng fixture và kế hoạch đọc artifact thật. Log huấn luyện S1 của hai phương pháp là bằng chứng từ phiên trước.

| Hợp đồng | Bằng chứng |
|---|---|
| CLI | `controller_help.log` và tests của runner bao phủ `--method/--methods`, `--seed/--seeds`, `--round/--rounds`, khoảng checkpoint, `--resume` và `--dry-run`. Khoảng S1→S3 chọn S2 và S3. |
| Scientific protocol | P1-DEFICIT dùng mean capability deficit. P1P2 dùng 0,5 × deficit + 0,5 × percentile rank của L_proxy, average rank cho ties. Round 1 dùng shared S0 và NLL S0 cho P1P2. Round 2/3 lấy NLL từ S1/S2 và đối chiếu adapter SHA. |
| Baseline P2 | B2/B3 theo selector P2, B4 cố định NLL S0, B5 lấy NLL theo checkpoint. Controller chuyển round sang index bằng offset −1 khi gọi selector P2. Kiểm thử parser ma trận đủ sáu methods và ba seeds. Runtime toàn bộ ma trận chưa chạy. |
| Chaining | S1 khởi tạo từ Student base, S2/S3 dùng adapter trước, kiểm tra đúng path đã resolve và SHA. |
| Namespace, lock, atomic publish | Seed 13/42/2026 dùng `p1p2_integration`. Fixture seed riêng dùng `p1p2_integration_custom`. Lock đã có, adapter dở dang, fingerprint không khớp, dự đoán không hợp lệ đều chặn tiến trình và bảo toàn bytes. Sidecar dùng staging + rename no-overwrite. Checkpoint log append và fsync, giữ nguyên prefix đã ký. |
| Failure recovery | Fixture tiêm lỗi NLL, selection, train, eval, hook, state, công bố checkpoint và atomic artifact. Resume kiểm tra adapter, intent, prefix D_dev, checkpoint log, sidecar và state. Dòng cuối thiếu newline chặn append. |
| Split | Command evaluation của controller dùng `--split dev`. D_test ID được dùng để kiểm tra phân tách và leakage. |

`readonly_plans.json` ghi các kế hoạch từ artifact thật. A S1 và B S1 có 0 bước. A S2 có 4 bước gồm D_dev, checkpoint log, hook và capability state, không train/NLL và không sang S3. Khoảng B S2–S3 lập kế hoạch 16 bước, có NLL S1/S2 và đúng adapter cha. Runner trong lần kiểm tra sẽ báo lỗi nếu có subprocess được gọi.

Source hardening áp dụng cho kiểm tra lineage, portability, prediction và no-overwrite. Giữ các lựa chọn frozen, model, pool, token table, LoRA và split theo protocol hiện hành.
