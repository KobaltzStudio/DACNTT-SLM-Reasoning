# Audit post-evaluation hook

**PASS trên CPU và artifact S1 đã công bố.** `hook_help.log` ghi CLI xác minh. Các tham số controller dựng động từ method, seed và round.

```text
--method --seed --round --prediction --checkpoint --output-dir --manual-root
--train-set --selection-log --train-log --checkpoint-log --gold-manifest
--gold-labels --approval-csv --dev-ids --config
```

Approval CSV là `data/gold_releases/vFinal_2026-11-16/gold_supplement_85_approved_review.csv`. `checkpoint_log.jsonl` nằm ở method/seed root. Controller kiểm tra D_dev đủ 500 ID duy nhất và đúng tag trước khi công bố checkpoint record mới rồi gọi hook. Hook đối chiếu tag và danh tính train set, adapter, log row và SHA của các đầu vào. Sidecar giữ hash bytes của prefix checkpoint log đến checkpoint tương ứng. Sau hook, capability state xác minh nguồn và công bố cho selection round kế tiếp.

Evaluator xác minh đúng Gold 85 IDs, bảy capabilities và strict `status == "valid"`. Test subprocess với D_dev 1/500 trả lỗi coverage và không công bố sidecar. Các fixture runtime xác minh chính sách publish/no-overwrite, tiếp tục evaluation prefix, checkpoint tag, lineage, subprocess failure và resume. Việc kiểm tra S1 thật chỉ dùng artifact đã lưu. Không gọi evaluator mô hình.
