# NEXT_SESSION_START_HERE

- Workspace `C:\Users\PC - NGHI\Desktop\Pipeline`, Git root `C:\Users\PC - NGHI\Desktop\Pipeline\P2`.
- Working directory `C:\Users\PC - NGHI\Desktop\Pipeline\P2\experiments\week2September\manual`.
- Branch `codex/controller-dryrun-fix`.
- Mốc hoàn thành là 98 tests CPU, G6–G8 partial đã tái tạo, 638 file transfer được xác minh, update GPTGUIDE và recovery. Run A/B đều có S1 PASS. A S2 còn 75/500, đã lưu adapter. Chưa có S3 hoặc B S2.
- Không có PID pipeline và controller lock tại lúc ghi. Đọc `process_final.json`, `locks_final.json`, `gpu_final.log`, `protected_hashes_after.json` và `readonly_plans.json`.
- Tiếp theo khi được phân công là Linux CPU staging/dry-run theo `runpod_handoff_updated.md`, đối chiếu hai manifest SHA và xác minh scope trước khi xin quyền GPU. Cleanup mới ở mức đề xuất và cần phê duyệt riêng.
- Lệnh local an toàn gồm `git --no-optional-locks status --short --branch`, `Get-CimInstance Win32_Process` lọc Python, `nvidia-smi`, `Get-FileHash -Algorithm SHA256`, đọc logs và `& $Python -B -m unittest discover -s tests -v` với CUDA ẩn/offline.
- Tránh lệnh controller live, resume local, training/evaluation/NLL mới, D_test, RunPod, xóa/rename/move artifacts, git clean/reset/commit/push. Quyết định cần duyệt gồm môi trường Linux/RunPod staging, các job A S2/S3 hoặc B S2/S3, và file list/destination cleanup.

> Đọc AGENTS.md, GPTGUIDE.txt và `reports/p1p2_integration/session_recovery/RECOVERY_GUIDE.md` từ workspace. Dùng `NEXT_SESSION_START_HERE` để tìm evidence mới. Xác minh live branch, PID tree, GPU, locks, logs và SHA trước khi hành động. Giữ A/B S1 và 75 dòng A S2, không chạy lại. Mục tiếp theo là xác minh CPU staging Windows→Linux theo handoff khi được phân công. Không launch GPU job, D_test hay RunPod và không đổi/xóa artifact nếu chưa có phê duyệt.
