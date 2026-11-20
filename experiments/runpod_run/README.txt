Kết quả chạy P1/P2 Unified seed 13 trên RunPod (L4, network volume), ngày 2026-11-19.
Bản pull về từ pod, đã kiểm bằng ops.py verify-results và FINAL_ANALYSIS_SHA256SUMS.txt.

Bộ              SHA RESULTS_SHA256SUMS.txt / index                                  strict D_dev
a-s2            092f220b4ca0587a633f3bbaf4ed91437e88ab937f7ed22e4eb1ccc182b27e92  P1-DEFICIT S2 418/500 = 83.6%
a-s3            a8ae13757b647e60cd4d66557a2003bae312fe04b302a938df84667befbd14ce  P1-DEFICIT S3 413/500 = 82.6%
b-s2            4121e251c3136dc65792efe0218eabac590cd784d2fec53b3b5ba3dc34d0014d  P1P2 S2 417/500 = 83.4%
b-s3            5eaadfb6f50e5593567936c4cac37493c9fc5055cc49854470fb1867ff083aa7  P1P2 S3 411/500 = 82.2%
analysis-seed13 93af176953ce2dfa1bb7979c462f4938f2b5679685231dbab81926a9de48e285  G6/G7/G8, D_test audit-only
G7 checkpoint_selection_seed13.json 88b8af5a6be34c77e335f5774311d62da1d34efb46dadc615badf9163510b633 (FINAL)
G7 chọn: P1-DEFICIT S2, P1P2 S2, B5 S1, B4 S2 (415 câu D_dev_select, hòa thì lấy checkpoint sớm hơn).

Không có trong git: thư mục models/ (adapter LoRA, tokenizer); xem .gitignore.
Vì vậy verify-results chỉ pass trên bản đầy đủ (~/p1p2-incoming hoặc network volume).
Adapter A S2 (P1-DEFICIT student_ckpt_002) không có trong bộ nào; chỉ nằm trên network volume.
Ghi chú cần Nghi xác nhận: 2 file .sh đẩy lại ở dạng CRLF cho khớp seal; source lên pod bằng rsync github/;
S1 chạy trên Windows, S2/S3 chạy trên L4.
