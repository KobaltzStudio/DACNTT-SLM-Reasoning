import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

VNEXT = (
    BASE / "reports" / "capability" / "d3_regression"
    / "extractor_vnext_metrics.json"
)

VFINAL = (
    BASE / "reports" / "capability" / "d3_final_regression"
    / "extractor_vfinal_metrics.json"
)

VNEXT_PRED = (
    BASE / "reports" / "capability" / "d3_regression"
    / "extractor_predictions.jsonl"
)

VFINAL_PRED = (
    BASE / "reports" / "capability" / "d3_final_regression"
    / "extractor_predictions.jsonl"
)

def read_json(path):
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))

def read_jsonl(path):
    if not path.exists():
        raise FileNotFoundError(path)

    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows

def main():
    vnext = read_json(VNEXT)
    vfinal = read_json(VFINAL)

    vnext_predictions = read_jsonl(VNEXT_PRED)
    vfinal_predictions = read_jsonl(VFINAL_PRED)

    checks = {
        "gold_count_equal":
            vnext["gold_records"] == vfinal["gold_records"],

        "prediction_count_equal":
            vnext["prediction_records"] == vfinal["prediction_records"],

        "exact_matches_equal":
            vnext["exact_matches"] == vfinal["exact_matches"],

        "micro_metrics_equal":
            vnext["micro"] == vfinal["micro"],

        "macro_f1_equal":
            vnext["macro_f1"] == vfinal["macro_f1"],

        "capability_metrics_equal":
            vnext["capabilities"] == vfinal["capabilities"],

        "predictions_equal":
            vnext_predictions == vfinal_predictions,
    }

    print("GOLD vNEXT vs vFINAL CONSISTENCY CHECK")
    for name, passed in checks.items():
        print(f"[{'PASS' if passed else 'FAIL'}] {name}")

    print(f"vNext Gold records: {vnext['gold_records']}")
    print(f"vFinal Gold records: {vfinal['gold_records']}")

    if not all(checks.values()):
        raise SystemExit(
            "Consistency check failed. Do not proceed until investigated."
        )

    print("[PASS] vNext and vFinal regression results are identical.")

if __name__ == "__main__":
    main()
