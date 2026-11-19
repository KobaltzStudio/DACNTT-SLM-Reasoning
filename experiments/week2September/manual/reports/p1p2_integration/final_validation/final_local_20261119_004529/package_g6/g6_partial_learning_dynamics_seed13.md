# Capability learning dynamics — seed 13

**G6 status: PARTIAL.** Analysis is single-seed; no mean ± SD across seeds.

- Discovered sidecars across approved roots: 39 (expected None)
- Valid sidecars across approved roots: 39
- Metric rows in seed-13 scope (including shared S0): 63
- Correctness: `status == valid`
- Gold evaluation: 85 approved records; D_dev coverage: 500 IDs
- Shared S0 baseline is included once.
- B4/B5 S1 prediction alias is annotated; prediction equality is not proof of physical weight equality.

## Required method/checkpoint matrix

| Method | Checkpoint | Status |
|---|---|---|
| B4 | S1 | PRESENT |
| B4 | S2 | PRESENT |
| B4 | S3 | PRESENT |
| B5 | S1 | PRESENT |
| B5 | S2 | PRESENT |
| B5 | S3 | PRESENT |
| P1-DEFICIT | S1 | PRESENT |
| P1-DEFICIT | S2 | MISSING |
| P1-DEFICIT | S3 | MISSING |
| P1P2 | S1 | PRESENT |
| P1P2 | S2 | MISSING |
| P1P2 | S3 | MISSING |
| SHARED | S0 | PRESENT |

## Capability metrics

| Method | Checkpoint | Capability | Correct / Support | Mastery | Wilson 95% CI |
|---|---|---|---:|---:|---:|
| B4 | S1 | addition | 18/30 | 0.6000 | [0.4232, 0.7541] |
| B4 | S1 | subtraction | 40/51 | 0.7843 | [0.6537, 0.8751] |
| B4 | S1 | multiplication | 59/73 | 0.8082 | [0.7034, 0.8822] |
| B4 | S1 | division | 38/47 | 0.8085 | [0.6746, 0.8958] |
| B4 | S1 | percentage | 21/29 | 0.7241 | [0.5428, 0.8530] |
| B4 | S1 | fraction | 23/31 | 0.7419 | [0.5675, 0.8630] |
| B4 | S1 | ratio | 26/30 | 0.8667 | [0.7032, 0.9469] |
| B4 | S2 | addition | 23/30 | 0.7667 | [0.5907, 0.8821] |
| B4 | S2 | subtraction | 36/51 | 0.7059 | [0.5700, 0.8129] |
| B4 | S2 | multiplication | 56/73 | 0.7671 | [0.6583, 0.8492] |
| B4 | S2 | division | 39/47 | 0.8298 | [0.6986, 0.9111] |
| B4 | S2 | percentage | 20/29 | 0.6897 | [0.5077, 0.8272] |
| B4 | S2 | fraction | 25/31 | 0.8065 | [0.6372, 0.9081] |
| B4 | S2 | ratio | 26/30 | 0.8667 | [0.7032, 0.9469] |
| B4 | S3 | addition | 21/30 | 0.7000 | [0.5212, 0.8334] |
| B4 | S3 | subtraction | 41/51 | 0.8039 | [0.6754, 0.8898] |
| B4 | S3 | multiplication | 61/73 | 0.8356 | [0.7343, 0.9034] |
| B4 | S3 | division | 38/47 | 0.8085 | [0.6746, 0.8958] |
| B4 | S3 | percentage | 21/29 | 0.7241 | [0.5428, 0.8530] |
| B4 | S3 | fraction | 27/31 | 0.8710 | [0.7115, 0.9487] |
| B4 | S3 | ratio | 26/30 | 0.8667 | [0.7032, 0.9469] |
| B5 | S1 | addition | 22/30 | 0.7333 | [0.5555, 0.8582] |
| B5 | S1 | subtraction | 41/51 | 0.8039 | [0.6754, 0.8898] |
| B5 | S1 | multiplication | 60/73 | 0.8219 | [0.7188, 0.8929] |
| B5 | S1 | division | 38/47 | 0.8085 | [0.6746, 0.8958] |
| B5 | S1 | percentage | 23/29 | 0.7931 | [0.6161, 0.9015] |
| B5 | S1 | fraction | 24/31 | 0.7742 | [0.6019, 0.8860] |
| B5 | S1 | ratio | 25/30 | 0.8333 | [0.6644, 0.9266] |
| B5 | S2 | addition | 22/30 | 0.7333 | [0.5555, 0.8582] |
| B5 | S2 | subtraction | 35/51 | 0.6863 | [0.5497, 0.7967] |
| B5 | S2 | multiplication | 56/73 | 0.7671 | [0.6583, 0.8492] |
| B5 | S2 | division | 33/47 | 0.7021 | [0.5602, 0.8135] |
| B5 | S2 | percentage | 18/29 | 0.6207 | [0.4400, 0.7731] |
| B5 | S2 | fraction | 26/31 | 0.8387 | [0.6737, 0.9291] |
| B5 | S2 | ratio | 24/30 | 0.8000 | [0.6269, 0.9049] |
| B5 | S3 | addition | 21/30 | 0.7000 | [0.5212, 0.8334] |
| B5 | S3 | subtraction | 39/51 | 0.7647 | [0.6324, 0.8600] |
| B5 | S3 | multiplication | 64/73 | 0.8767 | [0.7820, 0.9338] |
| B5 | S3 | division | 40/47 | 0.8511 | [0.7231, 0.9259] |
| B5 | S3 | percentage | 23/29 | 0.7931 | [0.6161, 0.9015] |
| B5 | S3 | fraction | 23/31 | 0.7419 | [0.5675, 0.8630] |
| B5 | S3 | ratio | 28/30 | 0.9333 | [0.7868, 0.9815] |
| P1-DEFICIT | S1 | addition | 22/30 | 0.7333 | [0.5555, 0.8582] |
| P1-DEFICIT | S1 | subtraction | 39/51 | 0.7647 | [0.6324, 0.8600] |
| P1-DEFICIT | S1 | multiplication | 60/73 | 0.8219 | [0.7188, 0.8929] |
| P1-DEFICIT | S1 | division | 37/47 | 0.7872 | [0.6510, 0.8801] |
| P1-DEFICIT | S1 | percentage | 24/29 | 0.8276 | [0.6545, 0.9240] |
| P1-DEFICIT | S1 | fraction | 23/31 | 0.7419 | [0.5675, 0.8630] |
| P1-DEFICIT | S1 | ratio | 25/30 | 0.8333 | [0.6644, 0.9266] |
| P1P2 | S1 | addition | 20/30 | 0.6667 | [0.4878, 0.8077] |
| P1P2 | S1 | subtraction | 37/51 | 0.7255 | [0.5905, 0.8289] |
| P1P2 | S1 | multiplication | 57/73 | 0.7808 | [0.6732, 0.8603] |
| P1P2 | S1 | division | 37/47 | 0.7872 | [0.6510, 0.8801] |
| P1P2 | S1 | percentage | 20/29 | 0.6897 | [0.5077, 0.8272] |
| P1P2 | S1 | fraction | 25/31 | 0.8065 | [0.6372, 0.9081] |
| P1P2 | S1 | ratio | 24/30 | 0.8000 | [0.6269, 0.9049] |
| SHARED | S0 | addition | 19/30 | 0.6333 | [0.4551, 0.7813] |
| SHARED | S0 | subtraction | 37/51 | 0.7255 | [0.5905, 0.8289] |
| SHARED | S0 | multiplication | 53/73 | 0.7260 | [0.6144, 0.8151] |
| SHARED | S0 | division | 35/47 | 0.7447 | [0.6049, 0.8475] |
| SHARED | S0 | percentage | 19/29 | 0.6552 | [0.4735, 0.8006] |
| SHARED | S0 | fraction | 24/31 | 0.7742 | [0.6019, 0.8860] |
| SHARED | S0 | ratio | 22/30 | 0.7333 | [0.5555, 0.8582] |

## Sidecar validation

- B4 S2: VALID — C:\Users\PC - NGHI\Desktop\Pipeline\p1p2_unified\runpod_package_20261119_004529\P2\experiments\week2September\manual\reports\capability\g5_9_historical_20261117\B4_seed13_S2
- B4 S3: VALID — C:\Users\PC - NGHI\Desktop\Pipeline\p1p2_unified\runpod_package_20261119_004529\P2\experiments\week2September\manual\reports\capability\g5_9_historical_20261117\B4_seed13_S3
- B5 S1: VALID — C:\Users\PC - NGHI\Desktop\Pipeline\p1p2_unified\runpod_package_20261119_004529\P2\experiments\week2September\manual\reports\capability\g5_9_historical_20261117\B5_seed13_S1
- B5 S2: VALID — C:\Users\PC - NGHI\Desktop\Pipeline\p1p2_unified\runpod_package_20261119_004529\P2\experiments\week2September\manual\reports\capability\g5_9_historical_20261117\B5_seed13_S2
- B5 S3: VALID — C:\Users\PC - NGHI\Desktop\Pipeline\p1p2_unified\runpod_package_20261119_004529\P2\experiments\week2September\manual\reports\capability\g5_9_historical_20261117\B5_seed13_S3
- SHARED S0: VALID — C:\Users\PC - NGHI\Desktop\Pipeline\p1p2_unified\runpod_package_20261119_004529\P2\experiments\week2September\manual\reports\capability\g5_9_real_data_s0\SHARED_seed0_S0
- B4 S1: VALID — C:\Users\PC - NGHI\Desktop\Pipeline\p1p2_unified\runpod_package_20261119_004529\P2\experiments\week2September\manual\reports\capability_g4_validation\B4_seed13_S1
- B4 S2: VALID — C:\Users\PC - NGHI\Desktop\Pipeline\p1p2_unified\runpod_package_20261119_004529\P2\experiments\week2September\manual\reports\capability_g4_validation\B4_seed13_S2
- B4 S3: VALID — C:\Users\PC - NGHI\Desktop\Pipeline\p1p2_unified\runpod_package_20261119_004529\P2\experiments\week2September\manual\reports\capability_g4_validation\B4_seed13_S3
- P1-DEFICIT S1: VALID — C:\Users\PC - NGHI\Desktop\Pipeline\p1p2_unified\runpod_package_20261119_004529\P2\experiments\week2September\manual\reports\p1p2_integration\capability_sidecars\P1-DEFICIT_seed13_S1
- P1P2 S1: VALID — C:\Users\PC - NGHI\Desktop\Pipeline\p1p2_unified\runpod_package_20261119_004529\P2\experiments\week2September\manual\reports\p1p2_integration\capability_sidecars\P1P2_seed13_S1
