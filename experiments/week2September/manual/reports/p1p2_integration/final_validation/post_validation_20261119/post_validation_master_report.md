# P1/P2 post-validation hardening — 2026-11-19

**Windows CPU đã nghiệm thu.** 98 test PASS, 200 source/test files compile trong bộ nhớ, `git diff --check` sạch. Controller xác nhận A/B S1 đã hoàn tất và A S2 chỉ thiếu các bước đánh giá/công bố. Không phát sinh training, model evaluation, NLL, D_test, RunPod hay thay đổi frozen artifact.

| Task | Status | Evidence |
|---|---|---|
| P0 Recovery, quy trình/lock/GPU, Git và SHA | PASS | `recovery_validation_report.md`, 52 hash trước/sau khớp |
| A Unified controller và scientific protocol | PASS Windows CPU | `controller_contract_audit.md`, `readonly_plans.json` |
| B Hook contract | PASS Windows CPU | `hook_contract_audit.md` |
| C Regression | PASS | `regression_test_report.md`, 98/98, exit 0 |
| D G6 | PARTIAL | 39 sidecar, 37 nhóm, 2 bản ghi provenance thay thế, `g6_mapped_verified/` |
| E G7 | PARTIAL | 9 quan sát, 415 ID, chưa có winner, `g7_verified/` |
| F G8 | PARTIAL | 7/7 PNG và CSV khớp bản trước, `g8/` |
| G Portability và handoff | PARTIAL | 616 + 22 file xác minh SHA, Linux chưa dry-run, G9 NOT RUN / DELEGATED |
| H Recovery | PASS | 5 file persistent, `next_session_handoff.md` |
| I Cleanup/migration | PASS audit; NOT RUN thay đổi | `cleanup_inventory_updated.csv`, `cleanup_migration_proposal.md` |
| J Documentation | PASS | `Pipeline/GPTGUIDE.txt` phần F và `runpod_handoff_updated.md` |

**Run A** S1 PASS 83,2% strict D_dev. S2 training complete (26 LoRA steps), D_dev 75/500. S3 NOT RUN. **Run B** S1 PASS 81,2% strict D_dev, B S2/S3 NOT RUN. Phân tích hiện tại đang thiếu A S2/S3 và B S2/S3. Các hình phục vụ phân tích mô tả. Prerequisite graph vẫn thuộc phạm vi nghiên cứu sau.

Manifest staged giữ nguyên archive artifacts, giữ digest thân log và tạo bằng chứng mới. Chạy Linux CPU dry-run ở host được duyệt, xác minh runtime/paths trước khi xin quyền cho từng checkpoint còn thiếu. Cleanup là audit, chờ phê duyệt cụ thể. Xem `git_change_inventory.md` cho source thay đổi và worktree.
