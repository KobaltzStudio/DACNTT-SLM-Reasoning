# Git change inventory

Git root `C:\Users\PC - NGHI\Desktop\Pipeline\P2`, branch `codex/controller-dryrun-fix`. Root Pipeline có `GPTGUIDE.txt` nằm ngoài Git root P2. Trạng thái đầy đủ tại `git_status_final.log`; `git diff --check` exit 0 (cảnh báo line endings). Diff tracked hiện có 11 file, +680/−209, gồm thay đổi từ các phiên trước. Không cập nhật index, commit hoặc push.

| Nguồn sửa trong phiên | Mục đích |
|---|---|
| `scripts/p1p2_paths.py` (mới) | Resolver legacy Windows chỉ đọc với root tường minh và kiểm soát containment |
| `scripts/p1p2_controller.py` | Kiểm lineage theo locator + SHA, D_dev status/summary/prefix, NLL adapter path, checkpoint log và lập kế hoạch stage đúng |
| `scripts/p1p2_artifact_manager.py`, `scripts/capability_eval.py` | Dùng chung directory SHA compatible với artifacts Windows, từ chối case collision |
| `scripts/train_round.py` | Đối chiếu pool stage với locator/SHA mà vẫn giữ nguyên train-set bytes |
| `scripts/run_p1p2_post_eval.py` | Approval CSV vFinal, kiểm đầy đủ integrated lineage trước publish/reuse |
| `scripts/build_capability_learning_dynamics.py` | Kiểm byte của checkpoint và prediction trong chế độ mapped, với nhánh G4 riêng |
| `scripts/select_checkpoint_on_dev.py` | Kiểm SHA của adapter P1 tại canonical path trước khi chấp nhận prediction |
| `tests/test_p1p2_runtime.py`, `tests/test_p1p2_artifact_manager.py`, `tests/test_p1p2_analysis.py` | Regression staging, 75-row resume, hook negative, log newline, hash ordering và G4 mapping |

Danh sách source/tests untracked gồm `scripts/build_p1p2_analysis_figures.py`, `scripts/p1p2_paths.py`, `scripts/select_checkpoint_on_dev.py`, `tests/test_p1p2_analysis.py`, `tests/test_p1p2_runtime.py`. Giữ nguyên các thư mục runs/models/reports đã untracked từ trước. `git_modified_tracked.log` và `git_untracked_source.log` ghi path đầy đủ trong Git. `runpod_transfer_verification_sealed.json` có SHA trước/sau phân biệt source thay đổi tại phiên này.

File được tạo ở thư mục bằng chứng mới và 5 file metadata recovery cùng GUIDE được cập nhật. 52 SHA bảo vệ khớp trước/sau và 572 file transfer cũ khớp byte; không có checkpoint, Gold, split, historical evaluation hoặc frozen config bị ghi đè.
