# Smoke test: kết quả phân tích tự động

Ngưỡng: |ΔAcc| ≥ 2% hoặc McNemar p < 0.1.

| Seed | Acc S_0 | Acc S_1 | Δ | sai→đúng | đúng→sai | p | Format S_0→S_1 | Loss đầu→cuối | Quyết định |
|---|---|---|---|---|---|---|---|---|---|
| 13 | 0.712 | 0.830 | +0.118 | 89 | 30 | 5.69e-08 | 0.916→0.996 | 0.225→0.189 | Accuracy tăng rõ, loss giảm: giữ I3/I4/I5 (CẢNH BÁO: tỉ lệ đúng định dạng đổi ≥ 5 điểm %, so với accuracy lỏng trước khi kết luận) |
| 42 | 0.712 | 0.818 | +0.106 | 84 | 31 | 8.03e-07 | 0.916→0.966 | 0.235→0.208 | Accuracy tăng rõ, loss giảm: giữ I3/I4/I5 |

Accuracy lỏng (exploratory, số cuối trong output, bỏ qua định dạng):
- seed 13: 0.762 → 0.830
- seed 42: 0.762 → 0.830

**Quyết định chung:** `keep`
Chênh lệch Δ giữa các seed: 0.012

## NLL (exploratory), seed 13

| Nhóm | n | Spearman ℓ(S_0), ℓ(S_1) | Δℓ trung bình |
|---|---|---|---|
| all | 480 | 0.857 | -0.0586 |
| trained | 200 | 0.902 | -0.0906 |
| untrained | 280 | 0.944 | -0.0358 |

L_proxy: Spearman S_0/S_1 = 0.575, Jaccard top-200 = 0.439

## NLL (exploratory), seed 42

| Nhóm | n | Spearman ℓ(S_0), ℓ(S_1) | Δℓ trung bình |
|---|---|---|---|
| all | 480 | 0.869 | -0.0568 |
| trained | 200 | 0.888 | -0.0865 |
| untrained | 280 | 0.950 | -0.0356 |

L_proxy: Spearman S_0/S_1 = 0.646, Jaccard top-200 = 0.509
