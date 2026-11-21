# P1/P2 Unified — workspace bàn giao

Workspace này giữ bản nhập liệu sealed cho RunPod, code tích hợp, deployment wrappers, hồ sơ khoa học và recovery. Read [operator handoff](docs/HANDOFF_FOR_RUNPOD_OPERATOR.md) and [final report](docs/FINAL_HANDOFF_REPORT.md) before working on a new checkpoint.

| Path | Scope |
|---|---|
| `runtime/P2/experiments/week2September/manual/` | Bản sao byte-for-byte gồm source, config, Gold/split, run/adapter, NLL và kết quả đã nghiệm thu |
| `runtime/manifests/` | Hai SHA neo và các index từ gói sealed |
| `deployment/` | Công cụ xác minh và chạy từng checkpoint có phê duyệt |
| `analysis/` | G6/G7/G8 quan sát hiện có; lưu trữ nội bộ |
| `github/` | Cây ứng viên độc lập, cần duyệt quyền công bố |
| `docs/`, `future_research/`, `recovery/`, `manifests/` | Protocol, evidence, đề xuất nghiên cứu, khôi phục và danh sách chuyển |

Workspace root là vùng nội bộ. Chỉ `github/` là ứng viên để khởi tạo Git repository sau khi được duyệt. Gói runtime, cache, datasets, weights, reports và recovery có đường dẫn tuyệt đối thuộc luồng chuyển riêng. Không chạy thật tại cây sealed. Dùng cây làm việc mới và theo thứ tự trong [README RunPod](deployment/README_RUNPOD.md).
