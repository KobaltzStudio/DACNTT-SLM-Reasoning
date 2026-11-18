from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


CAPABILITIES = [
    "addition",
    "subtraction",
    "multiplication",
    "division",
    "percentage",
    "fraction",
    "ratio",
]

Z_95 = 1.959963984540054

REPO = Path(__file__).resolve().parents[4]
MANUAL = REPO / "experiments" / "week2September" / "manual"

GOLD_DIR = MANUAL / "data" / "gold_vnext_frozen_2026-11-16_r1"
GOLD_BATCH = GOLD_DIR / "batch_100_annotations_vnext.jsonl"
GOLD_SUPPLEMENT = GOLD_DIR / "supplement_annotations_vnext.jsonl"
GOLD_MANIFEST = GOLD_DIR / "gold_vnext_manifest.json"

ADJUDICATION_CSV = (
    MANUAL / "reports" / "capability" / "d3_audit"
    / "adjudication_human_confirmed.csv"
)

DEV_IDS_FILE = MANUAL / "splits" / "d_dev_ids.txt"

DEFAULT_PREDICTIONS = (
    MANUAL / "reports" / "task7" / "B4" / "seed_13"
    / "eval_student_ckpt_001_dev.jsonl"
)

DEFAULT_CHECKPOINT = (
    MANUAL / "models" / "task7" / "B4" / "seed_13"
    / "student_ckpt_001"
)

DEFAULT_OUT = (
    MANUAL / "reports" / "capability" / "student_eval_2026-11-17"
)

EXPECTED_HASHES = {
    "gold_batch": "5b655ab6705fa8d6178871d35f30712b90058354a29952b9e51e88e0108c8a9f",
    "gold_supplement": "8c41bc4e5c237a289dfcda92fcc691bf84b0ff5552ea8c8249c3947d3725ae26",
    "adjudication_csv": "f9a8d55f5079ec94ad31cb0c933a6a0d00409cce0815e47fbefd80c1354224ab",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(path)

    rows = []
    with path.open("r", encoding="utf-8-sig") as f:
        for line_no, line in enumerate(f, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSONL: {path}, line {line_no}: {exc}"
                ) from exc
            if not isinstance(row, dict):
                raise ValueError(
                    f"Expected JSON object: {path}, line {line_no}"
                )
            rows.append(row)
    return rows


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def read_ids(path: Path) -> set[str]:
    if not path.exists():
        raise FileNotFoundError(path)
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    }


def assert_unique_ids(rows: list[dict], source: str) -> None:
    ids = [
        str(row.get("problem_id", "")).strip()
        for row in rows
    ]
    missing = [i for i, value in enumerate(ids) if not value]
    duplicates = sorted(
        key for key, count in Counter(ids).items()
        if key and count > 1
    )

    if missing:
        raise ValueError(
            f"{source}: {len(missing)} records have missing problem_id"
        )
    if duplicates:
        raise ValueError(
            f"{source}: duplicate problem_id: {duplicates[:20]}"
        )


def parse_capabilities(value: str | list | None) -> list[str]:
    if value is None:
        return []

    if isinstance(value, list):
        labels = [str(x).strip() for x in value if str(x).strip()]
    else:
        labels = [
            item.strip()
            for item in str(value).split(";")
            if item.strip()
        ]

    unknown = sorted(set(labels) - set(CAPABILITIES))
    if unknown:
        raise ValueError(f"Unknown capability labels: {unknown}")

    if len(labels) != len(set(labels)):
        raise ValueError(f"Duplicate capability labels: {labels}")

    return sorted(labels)


def wilson_interval(correct: int, total: int) -> tuple[float | None, float | None]:
    if total == 0:
        return None, None

    p = correct / total
    z2 = Z_95 * Z_95
    denominator = 1.0 + z2 / total
    center = (p + z2 / (2.0 * total)) / denominator
    margin = (
        Z_95
        * math.sqrt(
            (p * (1.0 - p) / total)
            + (z2 / (4.0 * total * total))
        )
        / denominator
    )
    return max(0.0, center - margin), min(1.0, center + margin)


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write("\n")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"Refusing to write empty metrics CSV: {path}")

    fields = list(rows[0].keys())
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def load_confirmed_gold(dev_ids: set[str]) -> tuple[list[dict], dict]:
    batch = read_jsonl(GOLD_BATCH)
    supplement = read_jsonl(GOLD_SUPPLEMENT)
    assert_unique_ids(batch, "Gold batch")
    assert_unique_ids(supplement, "Gold supplement")

    batch_ids = {r["problem_id"] for r in batch}
    supplement_by_id = {r["problem_id"]: r for r in supplement}

    overlap = sorted(batch_ids & set(supplement_by_id))
    if overlap:
        raise ValueError(
            f"Gold batch/supplement ID overlap: {overlap[:20]}"
        )

    adjudications = read_csv(ADJUDICATION_CSV)
    adjudication_ids = [
        str(r.get("problem_id", "")).strip()
        for r in adjudications
    ]
    if any(not x for x in adjudication_ids):
        raise ValueError("Adjudication CSV contains empty problem_id")

    duplicate_adjudications = sorted(
        key for key, count in Counter(adjudication_ids).items()
        if count > 1
    )
    if duplicate_adjudications:
        raise ValueError(
            f"Duplicate adjudication IDs: {duplicate_adjudications}"
        )

    confirmed = []
    excluded_status_counts = Counter()
    missing_from_supplement = []
    outside_dev = []
    label_mismatches = []

    for row in adjudications:
        problem_id = str(row["problem_id"]).strip()
        status = str(row.get("human_review_status", "")).strip().upper()

        if status != "CONFIRMED":
            excluded_status_counts[status or "EMPTY"] += 1
            continue

        if problem_id not in dev_ids:
            outside_dev.append(problem_id)
            continue

        gold_row = supplement_by_id.get(problem_id)
        if gold_row is None:
            missing_from_supplement.append(problem_id)
            continue

        human_labels = parse_capabilities(
            row.get("human_confirmed_capabilities", "")
        )
        frozen_labels = parse_capabilities(
            gold_row.get("capabilities_manual", [])
        )

        if not human_labels:
            raise ValueError(
                f"{problem_id}: confirmed record has no human labels"
            )

        if human_labels != frozen_labels:
            label_mismatches.append({
                "problem_id": problem_id,
                "human_confirmed_capabilities": human_labels,
                "frozen_capabilities_manual": frozen_labels,
            })
            continue

        confirmed.append({
            "problem_id": problem_id,
            "capabilities": human_labels,
            "difficulty": str(
                row.get("human_confirmed_difficulty", "")
            ).strip(),
            "human_review_status": status,
            "human_reviewer": str(
                row.get("human_reviewer", "")
            ).strip(),
            "gold_source": "gold_vnext_frozen_2026-11-16_r1/supplement_annotations_vnext.jsonl",
            "annotation_version": "vNext-candidate-2026-11-16-r1",
        })

    if outside_dev:
        raise ValueError(
            "Human-confirmed adjudication IDs outside D_dev: "
            + repr(outside_dev)
        )
    if missing_from_supplement:
        raise ValueError(
            "Confirmed IDs missing from frozen supplement: "
            + repr(missing_from_supplement)
        )
    if label_mismatches:
        raise ValueError(
            "Human-confirmed labels differ from frozen Gold labels: "
            + json.dumps(label_mismatches, ensure_ascii=False)
        )
    if not confirmed:
        raise ValueError("No confirmed Gold records found in D_dev")

    return confirmed, {
        "gold_batch_records": len(batch),
        "gold_supplement_records": len(supplement),
        "adjudication_csv_records": len(adjudications),
        "human_confirmed_d_dev_records": len(confirmed),
        "excluded_adjudication_status_counts": dict(excluded_status_counts),
        "gold_batch_sha256": sha256_file(GOLD_BATCH),
        "gold_supplement_sha256": sha256_file(GOLD_SUPPLEMENT),
        "adjudication_csv_sha256": sha256_file(ADJUDICATION_CSV),
    }


def validate_expected_hashes(source_hashes: dict) -> None:
    actual = {
        "gold_batch": source_hashes["gold_batch_sha256"],
        "gold_supplement": source_hashes["gold_supplement_sha256"],
        "adjudication_csv": source_hashes["adjudication_csv_sha256"],
    }
    mismatches = {
        key: {
            "expected": EXPECTED_HASHES[key],
            "actual": actual[key],
        }
        for key in EXPECTED_HASHES
        if actual[key] != EXPECTED_HASHES[key]
    }
    if mismatches:
        raise ValueError(
            "Frozen input hash mismatch; fail closed: "
            + json.dumps(mismatches, ensure_ascii=False)
        )


def evaluate(
    predictions_path: Path,
    checkpoint_path: Path,
    output_dir: Path,
    checkpoint_name: str,
    method: str,
    seed: int,
    round_name: str,
) -> None:
    for path in (
        GOLD_BATCH,
        GOLD_SUPPLEMENT,
        ADJUDICATION_CSV,
        DEV_IDS_FILE,
        predictions_path,
    ):
        if not path.exists():
            raise FileNotFoundError(path)

    if not checkpoint_path.exists():
        raise FileNotFoundError(checkpoint_path)

    dev_ids = read_ids(DEV_IDS_FILE)
    if not dev_ids:
        raise ValueError("D_dev ID file is empty")

    gold_rows, gold_source_info = load_confirmed_gold(dev_ids)
    validate_expected_hashes(gold_source_info)

    prediction_rows = read_jsonl(predictions_path)
    assert_unique_ids(prediction_rows, "Student predictions")

    prediction_ids = {
        str(row["problem_id"]).strip()
        for row in prediction_rows
    }

    # The prediction file must be a D_dev prediction artifact.
    predictions_outside_dev = sorted(prediction_ids - dev_ids)
    if predictions_outside_dev:
        raise ValueError(
            "Prediction IDs outside D_dev: "
            + repr(predictions_outside_dev[:30])
        )

    # Do not combine different checkpoints in one prediction file.
    checkpoint_values = {
        str(row.get("checkpoint", "")).strip()
        for row in prediction_rows
    }
    if checkpoint_values != {checkpoint_name}:
        raise ValueError(
            f"Checkpoint mismatch. Expected {checkpoint_name}; "
            f"found {sorted(checkpoint_values)}"
        )

    # The official evaluator must have produced strict boolean correctness.
    invalid_correct = [
        row["problem_id"]
        for row in prediction_rows
        if not isinstance(row.get("correct"), bool)
    ]
    if invalid_correct:
        raise ValueError(
            "Missing/non-boolean strict 'correct' field for IDs: "
            + repr(invalid_correct[:30])
        )

    prediction_by_id = {
        str(row["problem_id"]).strip(): row
        for row in prediction_rows
    }

    gold_ids = {row["problem_id"] for row in gold_rows}
    matched_ids = sorted(gold_ids & prediction_ids)
    missing_prediction_ids = sorted(gold_ids - prediction_ids)
    predictions_without_confirmed_gold = sorted(prediction_ids - gold_ids)

    # Metrics use only the common, real prediction/confirmed-Gold subset.
    matched_gold = [
        row for row in gold_rows
        if row["problem_id"] in prediction_by_id
    ]

    metric_rows = []
    for capability in CAPABILITIES:
        support_rows = [
            row for row in matched_gold
            if capability in row["capabilities"]
        ]

        n_support = len(support_rows)
        n_correct = sum(
            1
            for row in support_rows
            if prediction_by_id[row["problem_id"]]["correct"] is True
        )

        accuracy = (
            n_correct / n_support
            if n_support
            else None
        )
        deficit = (
            1.0 - accuracy
            if accuracy is not None
            else None
        )
        ci_low, ci_high = wilson_interval(n_correct, n_support)

        metric_rows.append({
            "checkpoint": checkpoint_name,
            "method": method,
            "seed": seed,
            "round": round_name,
            "capability": capability,
            "n_support": n_support,
            "n_correct": n_correct,
            "n_incorrect": n_support - n_correct,
            "mastery_accuracy": accuracy,
            "deficit": deficit,
            "ci95_low": ci_low,
            "ci95_high": ci_high,
            "ci_method": "Wilson score interval",
            "delta_vs_baseline": None,
            "delta_note": (
                "Not computed: only one checkpoint has been evaluated."
            ),
        })

    coverage = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS_WITH_COVERAGE_REPORTED",
        "join_key": "problem_id",
        "gold_policy": (
            "human_review_status=CONFIRMED AND problem_id in D_dev; "
            "human_confirmed_capabilities must match frozen supplement labels"
        ),
        "correctness_field": "correct",
        "correctness_policy": (
            "Strict boolean correctness emitted by eval_student.py; "
            "lenient_correct is not used"
        ),
        "checkpoint": checkpoint_name,
        "method": method,
        "seed": seed,
        "round": round_name,
        "checkpoint_path": str(checkpoint_path),
        "prediction_file": str(predictions_path),
        "prediction_sha256": sha256_file(predictions_path),
        "checkpoint_adapter_sha256": (
            sha256_file(checkpoint_path / "adapter_model.safetensors")
            if (checkpoint_path / "adapter_model.safetensors").exists()
            else None
        ),
        "d_dev_unique_ids": len(dev_ids),
        "prediction_records": len(prediction_rows),
        "prediction_unique_ids": len(prediction_ids),
        "confirmed_gold_records": len(gold_rows),
        "confirmed_gold_ids": len(gold_ids),
        "matched_gold_prediction_ids": len(matched_ids),
        "missing_prediction_count": len(missing_prediction_ids),
        "missing_prediction_ids": missing_prediction_ids,
        "prediction_ids_without_confirmed_gold_count": len(
            predictions_without_confirmed_gold
        ),
        "prediction_ids_without_confirmed_gold": (
            predictions_without_confirmed_gold
        ),
        "prediction_ids_outside_d_dev": predictions_outside_dev,
        "coverage_rate": (
            len(matched_ids) / len(gold_ids)
            if gold_ids else None
        ),
        "gold_source": gold_source_info,
        "capability_support": {
            row["capability"]: row["n_support"]
            for row in metric_rows
        },
        "notes": [
            "Prediction IDs without confirmed Gold are not scored.",
            "Missing predictions are not imputed.",
            "A multi-capability problem contributes to each of its labels.",
            "Support is capability-specific and must not be summed as unique problems.",
            "Delta requires at least two comparable checkpoints on a common ID subset.",
        ],
    }

    # The confirmed inventory is an explicit reproducibility artifact.
    inventory_path = output_dir / "gold_confirmed_inventory.json"
    write_json(inventory_path, {
        "annotation_version": "vNext-candidate-2026-11-16-r1",
        "split": "D_dev",
        "records": gold_rows,
        "source": gold_source_info,
    })

    metrics_jsonl = output_dir / "capability_metrics.jsonl"
    metrics_csv = output_dir / "capability_metrics.csv"
    coverage_json = output_dir / "prediction_coverage_report.json"

    write_jsonl(metrics_jsonl, metric_rows)
    write_csv(metrics_csv, metric_rows)
    write_json(coverage_json, coverage)

    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "evaluator": str(Path(__file__).resolve()),
        "evaluator_sha256": sha256_file(Path(__file__).resolve()),
        "checkpoint": checkpoint_name,
        "method": method,
        "seed": seed,
        "round": round_name,
        "gold_inventory": str(inventory_path),
        "metrics_jsonl": str(metrics_jsonl),
        "metrics_csv": str(metrics_csv),
        "coverage_report": str(coverage_json),
        "prediction_sha256": sha256_file(predictions_path),
        "gold_source_hashes": gold_source_info,
        "metric_definition": {
            "mastery": "n_correct / n_support",
            "deficit": "1 - mastery",
            "confidence_interval": "95% Wilson score interval",
        },
        "delta_status": "NOT_COMPUTABLE_SINGLE_CHECKPOINT",
    }
    write_json(output_dir / "student_capability_evaluation_manifest.json", manifest)

    print("STUDENT_CAPABILITY_EVALUATION: PASS")
    print("CHECKPOINT:", checkpoint_name)
    print("METHOD / SEED / ROUND:", method, seed, round_name)
    print("D_DEV_IDS:", len(dev_ids))
    print("PREDICTION_RECORDS:", len(prediction_rows))
    print("CONFIRMED_GOLD_D_DEV:", len(gold_rows))
    print("MATCHED_IDS:", len(matched_ids))
    print("MISSING_PREDICTIONS:", len(missing_prediction_ids))
    print("COVERAGE_RATE:", coverage["coverage_rate"])
    print("\nCAPABILITY METRICS")
    for row in metric_rows:
        if row["n_support"] == 0:
            print(
                row["capability"],
                "support=0; mastery=NA; CI=NA"
            )
        else:
            print(
                f'{row["capability"]}: '
                f'n={row["n_support"]}, '
                f'correct={row["n_correct"]}, '
                f'mastery={row["mastery_accuracy"]:.4f}, '
                f'deficit={row["deficit"]:.4f}, '
                f'CI95=[{row["ci95_low"]:.4f}, {row["ci95_high"]:.4f}]'
            )

    print("\nOUTPUTS")
    print(metrics_jsonl)
    print(metrics_csv)
    print(coverage_json)
    print(inventory_path)
    print(output_dir / "student_capability_evaluation_manifest.json")


def self_test() -> None:
    # Wilson interval boundary and central checks.
    low, high = wilson_interval(0, 10)
    assert low is not None and high is not None and 0 <= low <= high <= 1

    low, high = wilson_interval(10, 10)
    assert low is not None and high is not None and 0 <= low <= high <= 1

    assert wilson_interval(0, 0) == (None, None)

    # Multi-label support must count one problem in both capabilities.
    sample = [
        {"problem_id": "p1", "capabilities": ["addition", "fraction"]},
        {"problem_id": "p2", "capabilities": ["addition"]},
    ]
    addition_support = sum("addition" in x["capabilities"] for x in sample)
    fraction_support = sum("fraction" in x["capabilities"] for x in sample)
    assert addition_support == 2
    assert fraction_support == 1

    # Duplicate ID detection.
    try:
        assert_unique_ids(
            [{"problem_id": "p1"}, {"problem_id": "p1"}],
            "self-test",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Duplicate-ID test did not fail")

    # Missing ID detection.
    try:
        assert_unique_ids([{"problem_id": ""}], "self-test")
    except ValueError:
        pass
    else:
        raise AssertionError("Missing-ID test did not fail")

    # Unknown labels must fail closed.
    try:
        parse_capabilities("addition;unknown_capability")
    except ValueError:
        pass
    else:
        raise AssertionError("Unknown-capability test did not fail")

    print("SELF_TEST_STATUS: PASS")
    print("TESTS: Wilson CI, empty support, multi-label, duplicate ID, missing ID, unknown label")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", type=Path, default=DEFAULT_PREDICTIONS)
    parser.add_argument("--checkpoint-path", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--checkpoint-name",
        default="B4_seed13_student_ckpt_001",
    )
    parser.add_argument("--method", default="B4")
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument("--round", dest="round_name", default="round_001")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return

    evaluate(
        predictions_path=args.predictions.resolve(),
        checkpoint_path=args.checkpoint_path.resolve(),
        output_dir=args.output_dir.resolve(),
        checkpoint_name=args.checkpoint_name,
        method=args.method,
        seed=args.seed,
        round_name=args.round_name,
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"STUDENT_CAPABILITY_EVALUATION: FAIL: {exc}", file=sys.stderr)
        raise
