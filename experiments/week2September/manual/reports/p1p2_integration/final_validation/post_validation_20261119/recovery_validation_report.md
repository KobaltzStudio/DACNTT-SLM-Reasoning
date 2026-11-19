# Recovery validation

**PASS cho snapshot phiên hiện tại.** Đọc cả năm file trong `reports/p1p2_integration/session_recovery/`. Xác minh live Git branch và worktree, process tree qua CIM, GPU qua nvidia-smi, controller lock và artifact SHA. `process_final.json` và `locks_final.json` là arrays rỗng. GPU hiển thị ứng dụng hệ thống ở thời điểm audit nhưng không có Python Run A/Run B. 52 SHA khớp, không phát hiện mismatch.

| Scope | Trạng thái sau xác minh |
|---|---|
| Run A S1 | PASS, strict D_dev 416/500, plan 0 |
| Run A S2 | PARTIAL, 26 optimizer steps, adapter/intent/prefix 75/500 đã bảo toàn; chưa có completed D_dev summary, Gold sidecar hoặc state |
| Run A S3 | NOT_STARTED |
| Run B S1 | PASS, 406/500, 184 trajectories, 45.221/45.426 tokens, 23 steps, effective batch 8, Gold 85 IDs / 7 capabilities, plan 0 |
| Run B S2/S3 | NOT_STARTED |
| GPU jobs trong lượt kiểm tra | NOT_RUN |
| Linux smoke / RunPod | NOT_RUN / DELEGATED |

`NEXT_SESSION_START_HERE` trong recovery guide là điểm vào hiện hành. Trường `post_validation_hardening` trong JSON lưu kết quả, SHA của evidence, command exits, phạm vi và phê duyệt. Snapshot là dữ liệu quan sát. Phiên sau kiểm tra lại PID/parent/command/start time, GPU, Git, locks, logs và SHA. Watcher từ lần Run B trước không phải cơ chế chạy tiếp khi hết usage. Không chạy watcher cũ để ghi đè metadata phiên mới.
