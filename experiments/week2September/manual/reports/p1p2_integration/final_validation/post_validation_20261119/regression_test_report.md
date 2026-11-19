# Nghiệm thu regression Windows CPU

Interpreter `C:\KLTN-SLM-Reasoning\.venv\Scripts\python.exe`, Python 3.11.9. Đặt `CUDA_VISIBLE_DEVICES=-1`, `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `MPLBACKEND=Agg` khi chạy suite. Fixtures chạy ở Temp; model subprocess được dựng stub trong fixture, hook/capability evaluator chỉ xử lý dữ liệu fixture sẵn có.

| Lệnh hoặc thao tác thực tế | Exit | Evidence |
|---|---:|---|
| `& $Python -B -m unittest discover -s tests -v` | 0 | 98 test, 30,501 s, `unittest_sealed.log` |
| Python `compile(p.read_bytes(), str(p), "exec")` cho 200 file scripts/tests | 0 | `integrity_sealed.log`; không tạo bytecode |
| Git Bash `bash -n` cho ba khối bash trong handoff | 0/0/0 | `integrity_sealed.log`; kiểm cú pháp, chưa chạy lệnh trên Linux |
| `& $Python -B scripts/run_p1_p2.py --help` và `& $Python -B scripts/run_p1p2_post_eval.py --help` | 0/0 | `controller_help.log`, `hook_help.log` |
| `Controller(..., resume=True, dry_run=True, runner=reject_subprocess)` và bốn tập method/seed/range | 0 | `final_integrity.json` và `readonly_plans_sealed.log` |
| `& $Python -B scripts/build_capability_learning_dynamics.py --manual . --legacy-windows-root (Get-Location).Path --output "$Evidence/g6_mapped_verified"` | 4 | 39/39 sidecar hợp lệ; thiếu bốn checkpoint, xem `g6_mapped_verified.log` |
| `& $Python -B scripts/select_checkpoint_on_dev.py --manual-root . --partial --output "$Evidence/g7_verified"` | 0 | Báo cáo partial `g7_verified/` |
| `& $Python -B scripts/build_p1p2_analysis_figures.py --manual-root . --allow-partial --output "$Evidence/g8"` | 4 | 7 PNG + 7 CSV, coverage partial |
| `& $Python -B scripts/build_p1p2_analysis_figures.py --manual-root . --allow-partial --preflight` | 0 | `g8_preflight.log` |
| `git diff --check`, `git status --short --branch` | 0/0 | `git_diff_check_final.log`, `git_status_final.log` |

Baseline phiên trước là 91 test PASS. Các lượt giữa phiên gồm 95 PASS và 97 PASS. Sau đó lượt 98 test trả exit 1 khi expected path của fixture còn dạng DOS 8.3 (`PC-NGH~1`) trong khi resolver trả path dài (`PC - NGHI`). Normalization `Path(temp).resolve()` trong fixture làm hai path tương đương và toàn bộ suite cuối PASS. Traceback giữ ở `unittest_verified.log`. Git Bash cần chạy kiểm cú pháp ngoài sandbox Windows do lỗi NT IPC ban đầu, giữ `static_validation.log`.

Test CPU bao phủ bộ tham số hook, round mapping, strict IDs, scientific selection, lineage, 75/500 partial resume không huấn luyện lại, atomic/no-overwrite, failure injection, khóa còn tồn tại và prefix thiếu newline. Chưa kiểm chứng thực thi Linux hoặc GPU tại phiên này.
