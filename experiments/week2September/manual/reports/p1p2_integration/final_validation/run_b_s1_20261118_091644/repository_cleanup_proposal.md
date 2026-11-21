# Đề xuất lưu trữ và dọn repository

Kiểm kê chỉ đọc 4713 file ở Pipeline, P1 và P2.
Bỏ qua metadata Git, venv, node_modules, junction và thư mục bằng chứng của chính lượt kiểm kê.

- ARCHIVE: 83
- DELETE CANDIDATE: 213
- KEEP: 4113
- UNKNOWN / NEEDS REVIEW: 304

Chỉ coi bytecode có source hiện hữu là ứng viên xóa. Không xóa file nào. Các archive có SHA-256, danh sách thành viên mẫu, phạm vi so với file giải nén và trường hợp chưa biết trong CSV.

| ZIP | Members | Verified subset | Proposed disposition |
|---|---:|---:|---|
| `P1/experiments/week2September/manual/config/config_p1.zip` | 14 | 14 | ARCHIVE, all inspected members match extracted copies |
| `P1/experiments/week2September/manual/manual.zip` | 735 | 720 | KEEP pending proof of a complete extracted equivalent |
| `P1/experiments/week2September/manual/reports/capability/p1_day14_final_2026-11-14/incoming/P1_adjudication_review_2026-11-14.zip` | 4 | 0 | KEEP pending proof of a complete extracted equivalent |
| `P1/experiments/week2September/manual/reports/capability/p1_day14_final_2026-11-14/incoming/P1_day14_final_2026-11-14.zip` | 8 | 0 | KEEP pending proof of a complete extracted equivalent |
| `P1/experiments/week2September/manual/reports/capability/p1_extractor_v3_2026-11-14/P1_extractor_v3_working_2026-11-14.zip` | 15 | 0 | KEEP pending proof of a complete extracted equivalent |
| `P1/experiments/week2September/manual/reports/task7/B4/seed_13/seed_13.zip` | 10 | 10 | ARCHIVE, all inspected members match extracted copies |
| `P1/experiments/week2September/manual/scripts/scripts_p1_original.zip` | 186 | 186 | ARCHIVE, all inspected members match extracted copies |
| `P2/experiments/week2September/manual/config/config_p2.zip` | 11 | 11 | ARCHIVE, all inspected members match extracted copies |
| `P2/experiments/week2September/manual/controller_current_source_20261118.zip` | 32 | 24 | KEEP pending proof of a complete extracted equivalent |
| `P2/experiments/week2September/manual/controller_missing_inputs_20261118.zip` | 5 | 3 | KEEP pending proof of a complete extracted equivalent |
| `P2/experiments/week2September/manual/integration_staging/P1/reports/capability/p1_day14_final_2026-11-14/incoming/P1_adjudication_review_2026-11-14.zip` | 4 | 0 | KEEP pending proof of a complete extracted equivalent |
| `P2/experiments/week2September/manual/integration_staging/P1/reports/capability/p1_day14_final_2026-11-14/incoming/P1_day14_final_2026-11-14.zip` | 8 | 0 | KEEP pending proof of a complete extracted equivalent |
| `P2/experiments/week2September/manual/integration_staging/P1/reports/capability/p1_extractor_v3_2026-11-14/P1_extractor_v3_working_2026-11-14.zip` | 15 | 0 | KEEP pending proof of a complete extracted equivalent |
| `P2/experiments/week2September/manual/integration_staging/P1/reports/task7/B4/seed_13/seed_13.zip` | 10 | 10 | ARCHIVE, all inspected members match extracted copies |
| `P2/experiments/week2September/manual/p1p2_artifact_manager_delivery_20261117.zip` | 2 | 2 | ARCHIVE, all inspected members match extracted copies |
| `P2/experiments/week2September/manual/p1p2_controller_fixed.zip` | 18 | 11 | KEEP pending proof of a complete extracted equivalent |
| `P2/experiments/week2September/manual/p1p2_controller_fixed_v2.zip` | 18 | 11 | KEEP pending proof of a complete extracted equivalent |
| `P2/experiments/week2September/manual/p1p2_controller_fixed_v3.zip` | 18 | 11 | KEEP pending proof of a complete extracted equivalent |
| `P2/experiments/week2September/manual/p1p2_method_registry_delivery_20261117.zip` | 3 | 0 | KEEP pending proof of a complete extracted equivalent |
| `P2/experiments/week2September/manual/p1p2_unified_config_delivery_20261117.zip` | 4 | 0 | KEEP pending proof of a complete extracted equivalent |
| `P2/experiments/week2September/manual/reports/p1p2_integration/checkpoint_inventory_audit/schema_alias_audit/run_20261117_110254/run_20261117_110254.zip` | 4 | 4 | ARCHIVE, all inspected members match extracted copies |
| `P2/experiments/week2September/manual/reports/p1p2_integration/g5_preflight_audit.zip` | 6 | 6 | ARCHIVE, all inspected members match extracted copies |
| `P2/experiments/week2September/manual/reports/p1p2_integration/historical_g59_evidence_20261117_155335_374.zip` | 70 | 63 | KEEP pending proof of a complete extracted equivalent |
| `P2/experiments/week2September/manual/reports/p1p2_integration/source_review/contract_chunks_20261117/contract_chunks_20261117.zip` | 10 | 10 | ARCHIVE, all inspected members match extracted copies |
| `P2/experiments/week2September/manual/reports/p1p2_integration/source_review/controller_source_bundle_20261118_094804.zip` | 42 | 41 | KEEP pending proof of a complete extracted equivalent |
| `P2/experiments/week2September/manual/reports/task7/main_results/figures/Figures_p2.zip` | 6 | 6 | ARCHIVE, all inspected members match extracted copies |
| `P2/experiments/week2September/manual/runs/check/check.zip` | 2 | 2 | ARCHIVE, all inspected members match extracted copies |
| `P2/experiments/week2September/manual/runs/main/B4_seed13/B4_seed13.zip` | 45 | 42 | KEEP pending proof of a complete extracted equivalent |
| `P2/experiments/week2September/manual/runs/main/main.zip` | 700 | 664 | KEEP pending proof of a complete extracted equivalent |
| `P2/experiments/week2September/manual/runs/pilot/pilot.zip` | 71 | 68 | KEEP pending proof of a complete extracted equivalent |
| `P2/experiments/week2September/manual/scripts/scripts.zip` | 203 | 197 | KEEP pending proof of a complete extracted equivalent |
| `P2/experiments/week2September/manual/selection_dependency_20261118.zip` | 1 | 1 | ARCHIVE, all inspected members match extracted copies |
| `P2/integration_staging/P1/models/task7/B4/seed_13/student_ckpt_001/student_ckpt_001.zip` | 7 | 5 | KEEP pending proof of a complete extracted equivalent |
| `P2/integration_staging/P1/models/task7/B4/seed_13/student_ckpt_002/student_ckpt_002.zip` | 7 | 5 | KEEP pending proof of a complete extracted equivalent |
| `P2/integration_staging/P1/models/task7/B4/seed_13/student_ckpt_003/student_ckpt_003.zip` | 7 | 5 | KEEP pending proof of a complete extracted equivalent |
| `script_configneeded/script_configneeded.zip` | 18 | 18 | ARCHIVE, all inspected members match extracted copies |
| `ZIP/P1/_b4b5_patch.zip` | 25 | 0 | KEEP pending proof of a complete extracted equivalent |
| `ZIP/P1/config.zip` | 14 | 0 | KEEP pending proof of a complete extracted equivalent |
| `ZIP/P1/data.zip` | 50 | 0 | KEEP pending proof of a complete extracted equivalent |
| `ZIP/P1/experiments.zip` | 1 | 0 | KEEP pending proof of a complete extracted equivalent |
| `ZIP/P1/graph.zip` | 4 | 0 | KEEP pending proof of a complete extracted equivalent |
| `ZIP/P1/learning_dynamics.zip` | 1 | 0 | KEEP pending proof of a complete extracted equivalent |
| `ZIP/P1/logs.zip` | 4 | 0 | KEEP pending proof of a complete extracted equivalent |
| `ZIP/P1/manual.zip` | 11 | 0 | KEEP pending proof of a complete extracted equivalent |
| `ZIP/P1/models.zip` | 18 | 0 | KEEP pending proof of a complete extracted equivalent |
| `ZIP/P1/processed.zip` | 11 | 0 | KEEP pending proof of a complete extracted equivalent |
| `ZIP/P1/raw.zip` | 5 | 0 | KEEP pending proof of a complete extracted equivalent |
| `ZIP/P1/reports.zip` | 414 | 0 | KEEP pending proof of a complete extracted equivalent |
| `ZIP/P1/results.zip` | 3 | 0 | KEEP pending proof of a complete extracted equivalent |
| `ZIP/P1/schemas.zip` | 9 | 0 | KEEP pending proof of a complete extracted equivalent |
| `ZIP/P1/scripts.zip` | 186 | 0 | KEEP pending proof of a complete extracted equivalent |
| `ZIP/P1/splits.zip` | 5 | 0 | KEEP pending proof of a complete extracted equivalent |
| `ZIP/P1/trajectory.zip` | 22 | 0 | KEEP pending proof of a complete extracted equivalent |
| `ZIP/P2/config.zip` | 11 | 0 | KEEP pending proof of a complete extracted equivalent |
| `ZIP/P2/data.zip` | 33 | 0 | KEEP pending proof of a complete extracted equivalent |
| `ZIP/P2/graph.zip` | 4 | 0 | KEEP pending proof of a complete extracted equivalent |
| `ZIP/P2/learning_dynamics.zip` | 1 | 0 | KEEP pending proof of a complete extracted equivalent |
| `ZIP/P2/manual.zip` | 11 | 0 | KEEP pending proof of a complete extracted equivalent |
| `ZIP/P2/notes.zip` | 6 | 0 | KEEP pending proof of a complete extracted equivalent |
| `ZIP/P2/reports.zip` | 171 | 0 | KEEP pending proof of a complete extracted equivalent |
| `ZIP/P2/runs.zip` | 773 | 0 | KEEP pending proof of a complete extracted equivalent |
| `ZIP/P2/schemas.zip` | 9 | 0 | KEEP pending proof of a complete extracted equivalent |
| `ZIP/P2/scripts.zip` | 123 | 0 | KEEP pending proof of a complete extracted equivalent |
| `ZIP/P2/splits.zip` | 5 | 0 | KEEP pending proof of a complete extracted equivalent |
| `ZIP/P2/trajectory.zip` | 24 | 0 | KEEP pending proof of a complete extracted equivalent |

ARCHIVE chỉ là đề xuất lưu giữ có thể khôi phục. Đối chiếu lại Git, source input và checksum trước khi duyệt di chuyển. Không đổi tên, không xóa, không extract ZIP.
