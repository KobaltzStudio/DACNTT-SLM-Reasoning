from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path


EXPECTED_MAIN_ZIP_SHA256 = (
    "a4c657e7d643d4be6839eaf6614485ab"
    "3dd0ab26c825765d993c783e9371be9f"
)

METHODS = ("B2", "B3", "B4", "B5")
SEEDS = (13, 42, 2026)
ROUNDS = (1, 2, 3)

VALID_STATUSES = {
    "valid",
    "invalid_answer",
    "invalid_format",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_bytes(data: bytes, description: str) -> dict:
    try:
        value = json.loads(data.decode("utf-8-sig"))
    except Exception as exc:
        raise ValueError(
            f"Invalid JSON {description}: {exc}"
        ) from exc

    if not isinstance(value, dict):
        raise ValueError(
            f"Expected JSON object: {description}"
        )

    return value


def jsonl_bytes(data: bytes, description: str) -> list[dict]:
    rows = []

    for line_no, line in enumerate(
        data.decode("utf-8-sig").splitlines(), 1
    ):
        if not line.strip():
            continue

        try:
            row = json.loads(line)
        except Exception as exc:
            raise ValueError(
                f"Invalid JSONL {description}:{line_no}: {exc}"
            ) from exc

        if not isinstance(row, dict):
            raise ValueError(
                f"Expected JSON object in {description}:{line_no}"
            )

        rows.append(row)

    return rows


def read_member(archive, name: str) -> bytes:
    try:
        return archive.read(name)
    except KeyError as exc:
        raise FileNotFoundError(
            f"Missing main.zip member: {name}"
        ) from exc


def validate_prediction(
    data: bytes,
    dev_ids: set[str],
    label: str,
) -> list[dict]:
    rows = jsonl_bytes(data, label)

    ids = [
        str(row.get("problem_id", "")).strip()
        for row in rows
    ]

    if len(rows) != 500:
        raise ValueError(
            f"{label}: expected 500 rows, got {len(rows)}"
        )

    if any(not value for value in ids):
        raise ValueError(f"{label}: empty problem_id")

    if len(ids) != len(set(ids)):
        raise ValueError(f"{label}: duplicate problem_id")

    if set(ids) != dev_ids:
        raise ValueError(f"{label}: IDs do not equal D_dev")

    for row in rows:
        status = row.get("status")
        if status not in VALID_STATUSES:
            raise ValueError(
                f"{label}: invalid status {status!r} "
                f"for {row.get('problem_id')}"
            )

    return rows


def validate_context(
    archive,
    method: str,
    seed: int,
    round_no: int,
    dev_ids: set[str],
) -> dict:
    run_name = f"{method}_seed{seed}"
    checkpoint_name = f"student_ckpt_{round_no:03d}"
    round_dir = f"round_{round_no - 1:03d}"

    members = {
        "prediction": (
            f"{run_name}/S{round_no}/eval_dev.jsonl"
        ),
        "train_log": (
            f"{run_name}/S{round_no}/adapter/train_log.json"
        ),
        "adapter_config": (
            f"{run_name}/S{round_no}/adapter/adapter_config.json"
        ),
        "checkpoint_log": (
            f"{run_name}/checkpoint_log.jsonl"
        ),
        "train_set": (
            f"{run_name}/{round_dir}/train_set.json"
        ),
        "selection_log": (
            f"{run_name}/{round_dir}/selection_log.jsonl"
        ),
        "eval_marker": (
            f"{run_name}/.done/"
            f"eval_dev_{run_name}_S{round_no}.json"
        ),
    }

    raw = {
        key: read_member(archive, member)
        for key, member in members.items()
    }

    predictions = validate_prediction(
        raw["prediction"],
        dev_ids,
        members["prediction"],
    )

    train_log = json_bytes(
        raw["train_log"], members["train_log"]
    )
    adapter_config = json_bytes(
        raw["adapter_config"], members["adapter_config"]
    )
    train_set = json_bytes(
        raw["train_set"], members["train_set"]
    )
    marker = json_bytes(
        raw["eval_marker"], members["eval_marker"]
    )

    selection_rows = jsonl_bytes(
        raw["selection_log"], members["selection_log"]
    )
    checkpoint_records = jsonl_bytes(
        raw["checkpoint_log"], members["checkpoint_log"]
    )

    if train_log.get("seed") != seed:
        raise ValueError(
            f"{run_name} S{round_no}: train-log seed mismatch"
        )

    if train_log.get("model") != "Qwen/Qwen2.5-1.5B-Instruct":
        raise ValueError(
            f"{run_name} S{round_no}: unexpected Student model"
        )

    trajectory_ids = train_set.get("trajectory_ids")

    if not isinstance(trajectory_ids, list) or not trajectory_ids:
        raise ValueError(
            f"{run_name} S{round_no}: invalid trajectory_ids"
        )

    if any(not isinstance(x, str) or not x.strip() for x in trajectory_ids):
        raise ValueError(
            f"{run_name} S{round_no}: invalid trajectory ID value"
        )

    if len(trajectory_ids) != len(set(trajectory_ids)):
        raise ValueError(
            f"{run_name} S{round_no}: duplicate trajectory IDs"
        )

    if train_log.get("n_examples") != len(trajectory_ids):
        raise ValueError(
            f"{run_name} S{round_no}: n_examples mismatch"
        )

    # Preserve both hashes. A mismatch is recorded as provenance
    # information and is NOT a G5.9 blocking condition.
    archived_train_set_hash = sha256_bytes(raw["train_set"])
    logged_train_set_hash = train_log.get("train_set_sha256")

    if not isinstance(logged_train_set_hash, str):
        train_set_hash_status = "TRAIN_LOG_HASH_UNAVAILABLE"
    elif archived_train_set_hash == logged_train_set_hash:
        train_set_hash_status = "MATCH"
    else:
        train_set_hash_status = "DIFFERENT_ARCHIVED_AND_TRAIN_TIME_BYTES"

    checkpoint_name_expected = checkpoint_name

    matches = [
        row for row in checkpoint_records
        if row.get("record_type") == "checkpoint"
        and row.get("checkpoint") == checkpoint_name_expected
        and row.get("round") == round_no
        and row.get("method") == method
        and row.get("training_seed") == seed
    ]

    if len(matches) != 1:
        raise ValueError(
            f"{run_name} S{round_no}: expected one checkpoint record; "
            f"found {len(matches)}"
        )

    checkpoint_record = matches[0]

    if checkpoint_record.get("selected_trajectory_ids") != trajectory_ids:
        raise ValueError(
            f"{run_name} S{round_no}: checkpoint/train-set IDs mismatch"
        )

    marker_command = marker.get("command")
    reused_from = marker.get("reused_from")

    # B4 S1 is a declared alias of B5 S1 for the same seed.
    # Its marker records reuse provenance instead of an evaluation command.
    if method == "B4" and round_no == 1:
        if not isinstance(reused_from, str) or not reused_from.strip():
            raise ValueError(
                f"{run_name} S{round_no}: expected B5 S1 alias marker"
            )

        normalized_source = reused_from.strip().replace("\\", "/").rstrip("/")
        expected_suffix = f"B5_seed{seed}/S1"

        if not normalized_source.endswith(expected_suffix):
            raise ValueError(
                f"{run_name} S{round_no}: alias target is not "
                f"the matching B5 seed S1: {reused_from}"
            )

        if not isinstance(marker.get("reason"), str) or not marker["reason"].strip():
            raise ValueError(
                f"{run_name} S{round_no}: alias marker lacks reason"
            )

        if marker_command:
            raise ValueError(
                f"{run_name} S{round_no}: alias marker unexpectedly "
                "contains a command"
            )

    else:
        if reused_from:
            raise ValueError(
                f"{run_name} S{round_no}: unexpected evaluation alias"
            )

        if (
            not isinstance(marker_command, str)
            or (
                "--split dev" not in marker_command
                and "--split=dev" not in marker_command
            )
        ):
            raise ValueError(
                f"{run_name} S{round_no}: marker lacks dev evaluation command"
            )

    member_hashes = {
        key: sha256_bytes(value)
        for key, value in raw.items()
    }

    reference = {
        "schema": "p1p2.historical_checkpoint_reference.v2",
        "reference_type": "main_zip_checkpoint_metadata_reference",
        "method": method,
        "seed": seed,
        "round": round_no,
        "run_id": f"{method}_seed{seed}_S{round_no}",
        "checkpoint": checkpoint_name,
        "physical_weights_included": False,
        "source_archive": "runs/main/main.zip",
        "source_archive_sha256": EXPECTED_MAIN_ZIP_SHA256,
        "archive_members": members,
        "archive_member_sha256": member_hashes,
        "training_metadata": {
            "student_model": train_log.get("model"),
            "student_revision": train_log.get("revision"),
            "training_seed": train_log.get("seed"),
            "data_order_seed": train_log.get("data_order_seed"),
            "checkpoint_parent": checkpoint_record.get(
                "parent_checkpoint"
            ),
            "train_set_sha256_archived": archived_train_set_hash,
            "train_set_sha256_logged": logged_train_set_hash,
            "train_set_hash_comparison": train_set_hash_status,
            "training_config_sha256": train_log.get("config_sha256"),
            "training_pool_sha256": train_log.get("pool_sha256"),
            "n_examples": train_log.get("n_examples"),
            "steps": train_log.get("steps"),
            "selection_log_rows": len(selection_rows),
            "adapter_config_sha256": member_hashes["adapter_config"],
        },
        "evaluation_metadata": {
            "prediction_sha256": member_hashes["prediction"],
            "prediction_rows": len(predictions),
            "prediction_unique_ids": len({
                row["problem_id"] for row in predictions
            }),
            "strict_metric": "status == valid",
            "evaluation_command": marker_command,
        },
        "limitations": [
            "Metadata reference only; physical adapter weights are not included.",
            "Archived train-set bytes and train-time hash are both preserved.",
            "Historical training pool/config hashes are recorded, "
            "not independently reconstructed.",
        ],
    }

    return {
        "method": method,
        "seed": seed,
        "round": round_no,
        "run_id": reference["run_id"],
        "members": members,
        "raw": raw,
        "reference": reference,
        "prediction_hash": member_hashes["prediction"],
        "train_log_hash": member_hashes["train_log"],
        "train_set_hash_status": train_set_hash_status,
    }


def verify_aliases(archive, dev_ids: set[str]) -> list[dict]:
    aliases = []

    for seed in SEEDS:
        b4 = validate_context(archive, "B4", seed, 1, dev_ids)
        b5 = validate_context(archive, "B5", seed, 1, dev_ids)

        if b4["prediction_hash"] != b5["prediction_hash"]:
            raise ValueError(
                f"B4/B5 S1 prediction alias mismatch for seed {seed}"
            )

        if b4["train_log_hash"] != b5["train_log_hash"]:
            raise ValueError(
                f"B4/B5 S1 train-log alias mismatch for seed {seed}"
            )

        marker_name = b4["members"]["eval_marker"]
        marker = json_bytes(
            read_member(archive, marker_name),
            marker_name,
        )

        reused_from = marker.get("reused_from", "")

        if f"B5_seed{seed}/S1" not in reused_from:
            raise ValueError(
                f"B4/B5 S1 alias marker invalid for seed {seed}"
            )

        aliases.append({
            "alias_run_id": f"B4_seed{seed}_S1",
            "canonical_run_id": f"B5_seed{seed}_S1",
            "prediction_sha256": b4["prediction_hash"],
            "train_log_sha256": b4["train_log_hash"],
            "status": "EXACT_ALIAS_CONFIRMED",
        })

    return aliases


def write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(
            f"Refusing to overwrite input artifact: {path}"
        )
    path.write_bytes(data)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run historical G5.9 capability sidecars from main.zip "
            "without model inference or training."
        )
    )
    parser.add_argument("--root", required=True)
    args = parser.parse_args()

    root = Path(args.root).resolve()

    archive_path = root / "runs" / "main" / "main.zip"
    dev_path = root / "splits" / "d_dev_ids.txt"
    hook_path = root / "scripts" / "run_p1p2_post_eval.py"

    for path in (archive_path, dev_path, hook_path):
        if not path.is_file():
            raise FileNotFoundError(path)

    archive_hash = sha256_file(archive_path)
    if archive_hash != EXPECTED_MAIN_ZIP_SHA256:
        raise ValueError(
            "main.zip SHA256 mismatch. "
            f"expected={EXPECTED_MAIN_ZIP_SHA256}; actual={archive_hash}"
        )

    dev_ids = {
        line.strip()
        for line in dev_path.read_text(
            encoding="utf-8-sig"
        ).splitlines()
        if line.strip()
    }

    if len(dev_ids) != 500:
        raise ValueError(
            f"Expected 500 D_dev IDs, got {len(dev_ids)}"
        )

    help_result = subprocess.run(
        [sys.executable, str(hook_path), "--help"],
        cwd=root,
        capture_output=True,
        text=True,
    )

    if help_result.returncode != 0:
        raise RuntimeError(
            "Post-evaluation hook --help failed:\n"
            + help_result.stdout + "\n" + help_result.stderr
        )

    required_cli = (
        "--method", "--seed", "--round",
        "--prediction", "--checkpoint", "--out-dir",
        "--train-set", "--selection-log",
        "--train-log", "--checkpoint-log",
    )

    missing_cli = [
        flag for flag in required_cli
        if flag not in help_result.stdout
    ]

    if missing_cli:
        raise RuntimeError(
            f"Hook CLI missing required flags: {missing_cli}"
        )

    stamp = datetime.now(timezone.utc).strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    input_root = (
        root / "reports" / "p1p2_integration"
        / "historical_g59_inputs" / f"run_{stamp}"
    )

    prediction_root = input_root / "predictions"
    reference_root = input_root / "checkpoint_references"
    lineage_root = input_root / "lineage"

    prepared = []

    # Validate the entire archive and all 33 contexts before
    # publishing inputs or invoking the post-evaluation hook.
    with zipfile.ZipFile(archive_path, "r") as archive:
        bad_member = archive.testzip()
        if bad_member is not None:
            raise ValueError(f"Corrupt ZIP member: {bad_member}")

        aliases = verify_aliases(archive, dev_ids)

        for method in METHODS:
            for seed in SEEDS:
                for round_no in ROUNDS:
                    if method == "B4" and round_no == 1:
                        continue

                    item = validate_context(
                        archive, method, seed, round_no, dev_ids
                    )
                    prepared.append(item)

    if len(prepared) != 33:
        raise RuntimeError(
            f"Expected 33 unique contexts; got {len(prepared)}"
        )

    expected_ids = {item["run_id"] for item in prepared}
    if len(expected_ids) != 33:
        raise RuntimeError("Duplicate historical run IDs detected")

    # Verify that the hook's declared supported methods match
    # the historical method set before starting the batch.
    hook_source = hook_path.read_text(encoding="utf-8-sig")
    for method in METHODS:
        if f'"{method}"' not in hook_source:
            raise RuntimeError(
                f"Hook source does not declare method {method}"
            )

    input_root.mkdir(parents=True, exist_ok=False)
    prediction_root.mkdir()
    reference_root.mkdir()
    lineage_root.mkdir()

    # Extract every input required by the hook.
    for item in prepared:
        run_id = item["run_id"]

        item["prediction_path"] = (
            prediction_root / f"{run_id}.jsonl"
        )
        item["reference_path"] = (
            reference_root / f"{run_id}.json"
        )

        write_bytes(
            item["prediction_path"],
            item["raw"]["prediction"],
        )

        reference_data = (
            json.dumps(
                item["reference"],
                ensure_ascii=False,
                indent=2,
            ) + "\n"
        ).encode("utf-8")

        write_bytes(item["reference_path"], reference_data)

        item["lineage_paths"] = {}

        for key in (
            "train_set",
            "selection_log",
            "train_log",
            "checkpoint_log",
        ):
            suffix = (
                ".json"
                if key in ("train_set", "train_log")
                else ".jsonl"
            )
            path = lineage_root / run_id / f"{key}{suffix}"

            write_bytes(path, item["raw"][key])
            item["lineage_paths"][key] = path

    sidecar_root = (
        root / "reports" / "capability"
        / "g5_9_historical_20261117"
    )

    results = []

    for item in prepared:
        run_id = item["run_id"]
        out_dir = sidecar_root / run_id
        log_path = input_root / f"{run_id}_hook.log"
        lineage = item["lineage_paths"]

        command = [
            sys.executable,
            str(hook_path),
            "--method", item["method"],
            "--seed", str(item["seed"]),
            "--round", str(item["round"]),
            "--prediction", str(item["prediction_path"]),
            "--checkpoint", str(item["reference_path"]),
            "--out-dir", str(out_dir),
            "--train-set", str(lineage["train_set"]),
            "--selection-log", str(lineage["selection_log"]),
            "--train-log", str(lineage["train_log"]),
            "--checkpoint-log", str(lineage["checkpoint_log"]),
        ]

        result = subprocess.run(
            command,
            cwd=root,
            capture_output=True,
            text=True,
        )

        log_path.write_text(
            "COMMAND:\n"
            + subprocess.list2cmdline(command)
            + "\n\nSTDOUT:\n"
            + result.stdout
            + "\n\nSTDERR:\n"
            + result.stderr,
            encoding="utf-8",
        )

        manifest_path = (
            out_dir / "student_capability_evaluation_manifest.json"
        )

        status = "PASS"
        manifest = None

        if result.returncode != 0:
            status = "HOOK_FAILED"
        elif not manifest_path.is_file():
            status = "SIDECAR_MANIFEST_MISSING"
        else:
            try:
                manifest = json.loads(
                    manifest_path.read_text(encoding="utf-8-sig")
                )
            except Exception:
                status = "SIDECAR_MANIFEST_INVALID"

            if status == "PASS":
                expected = {
                    "run_id": run_id,
                    "method": item["method"],
                    "seed": item["seed"],
                    "round": item["round"],
                    "n_capability_rows": 7,
                }

                for key, value in expected.items():
                    if manifest.get(key) != value:
                        status = "SIDECAR_MANIFEST_MISMATCH"
                        break

        results.append({
            "run_id": run_id,
            "method": item["method"],
            "seed": item["seed"],
            "round": item["round"],
            "status": status,
            "returncode": result.returncode,
            "prediction_sha256": item["prediction_hash"],
            "checkpoint_reference_sha256": sha256_file(
                item["reference_path"]
            ),
            "train_set_hash_comparison": (
                item["train_set_hash_status"]
            ),
            "sidecar_path": str(out_dir),
            "hook_log": str(log_path),
        })

        print(
            f"HISTORICAL_HOOK={status} RUN_ID={run_id}"
        )

    passed = sum(
        row["status"] == "PASS" for row in results
    )

    batch_manifest = {
        "schema": "p1p2.historical_g59_batch.v2",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "main_zip_sha256": archive_hash,
        "d_dev_count": len(dev_ids),
        "expected_unique_contexts": 33,
        "prepared_contexts": len(prepared),
        "passed_contexts": passed,
        "failed_contexts": len(results) - passed,
        "alias_policy": "B4_S1_reuses_B5_S1_once_per_seed",
        "aliases": aliases,
        "results": results,
        "train_set_hash_policy": (
            "Record archived and train-time hashes; mismatch is "
            "provenance metadata, not a G5.9 blocking condition."
        ),
        "historical_pool_hash_status": (
            "RECORDED_NOT_RECONSTRUCTED"
        ),
        "historical_training_config_hash_status": (
            "RECORDED_NOT_RECONSTRUCTED"
        ),
        "physical_weights_status": (
            "PARTIAL_METADATA_REFERENCES_USED"
        ),
    }

    manifest_path = (
        input_root / "historical_g59_batch_manifest.json"
    )

    manifest_path.write_text(
        json.dumps(
            batch_manifest,
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    print(f"\nHISTORICAL_G59_PREPARED={len(prepared)}")
    print(f"HISTORICAL_G59_HOOK_PASSED={passed}/33")
    print(f"HISTORICAL_G59_MANIFEST={manifest_path}")

    if passed != 33:
        print("HISTORICAL_G59_BATCH=NOT_PASS")
        return 1

    print("HISTORICAL_G59_BATCH=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())