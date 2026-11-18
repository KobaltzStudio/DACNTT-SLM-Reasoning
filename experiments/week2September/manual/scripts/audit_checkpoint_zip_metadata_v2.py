import csv
import hashlib
import json
import zipfile
from pathlib import Path

MANUAL = Path(__file__).resolve().parents[1]
P2_ROOT = MANUAL.parents[2]

ZIP_ROOT = (
    P2_ROOT
    / "integration_staging"
    / "P1"
    / "models"
    / "task7"
    / "B4"
    / "seed_13"
)

WORKING_CONFIG = MANUAL / "config" / "experiment_config.json"
STAGING_CONFIG = MANUAL / "integration_staging" / "P1" / "config" / "experiment_config.json"
WORKING_SPLIT = MANUAL / "splits" / "split_manifest.json"

OUT_DIR = (
    MANUAL
    / "reports"
    / "p1p2_integration"
    / "checkpoint_zip_metadata_audit"
)

EXPECTED_CONFIG_SHA = "17cf4b837dc42ac5145aea762847ca5dfba4bae58d253560b3b0dd6a254b73c5"
EXPECTED_POOL_SHA = "95f34cff848bfbd16305e5f0ecc2656525dc1e319ca2b1a404f9b75c8029cd04"
EXPECTED_SPLIT_SHA = "85f4559246542d197c427318afb3eefb8b8492573b69ac23e691fc19ce93bbda"
EXPECTED_OLD_SPLIT_SHA = "8bac2c8d43eae6df53b63f97f353ed6006551f44d5562b74941455301fec09a3"
EXPECTED_CREATOR_SHA = "052635fa4891476e9ed284f33d372ccaf477fcb708ce5b2d2bf2abd6ac93f539"

CHECKPOINTS = {
    "student_ckpt_001.zip": {
        "zip_sha": "851742c95cdc1dba0333112f35f2f32d7e8cfe2e4235ae2c5ddc535bc2955615",
        "parent": "student_ckpt_000",
        "train_set_sha": "614816f15b980f9958dd1747a3c0773171d8112ad167e116b7a7651d9623a006",
    },
    "student_ckpt_002.zip": {
        "zip_sha": "8ae764306b33f9456ffd18b09b4824784a87b1e827d15178e8b26bdcbe307f6f",
        "parent": "student_ckpt_001",
        "train_set_sha": "cb82cb58ed58a92a8fd0dd33b09322e99191ecd048daf63a36b5ea4182898e1a",
    },
    "student_ckpt_003.zip": {
        "zip_sha": "cb55d9d34244f24964882f71a5654744d3d7cac8ca2ed6d7ebe77deb36c968df",
        "parent": "student_ckpt_002",
        "train_set_sha": "f16cb78cbdaf4ce5280d79c552adab5ec57f56ca26a3796b02995f0de2441e0e",
    },
}

def sha256_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def read_zip_json(zf, name):
    try:
        return json.loads(zf.read(name).decode("utf-8"))
    except KeyError:
        return None

def parent_name(value):
    if not value:
        return None
    return str(value).replace("\\", "/").rstrip("/").split("/")[-1]

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("MANUAL:", MANUAL)
    print("P2_ROOT:", P2_ROOT)
    print("ZIP_ROOT:", ZIP_ROOT)
    print("WORKING_CONFIG:", WORKING_CONFIG)
    print("STAGING_CONFIG:", STAGING_CONFIG)
    print("WORKING_SPLIT:", WORKING_SPLIT)

    for p in (WORKING_CONFIG, STAGING_CONFIG, WORKING_SPLIT):
        if not p.is_file():
            raise SystemExit(f"REQUIRED_FILE_MISSING: {p}")

    working_config_sha = sha256_file(WORKING_CONFIG)
    staging_config_sha = sha256_file(STAGING_CONFIG)
    split_sha = sha256_file(WORKING_SPLIT)

    working_config = read_json(WORKING_CONFIG)
    staging_config = read_json(STAGING_CONFIG)

    working_declared_split = (
        working_config.get("splits", {}).get("manifest_sha256")
    )
    staging_declared_split = (
        staging_config.get("splits", {}).get("manifest_sha256")
    )

    config_checks = {
        "working_config_hash_recorded": working_config_sha == "e27fcf0ae16ec9b391a85757e0cc8ffa5630e29129f805d9dca495e2fdd2c461",
        "staging_config_hash_expected": staging_config_sha == EXPECTED_CONFIG_SHA,
        "actual_split_hash_expected": split_sha == EXPECTED_SPLIT_SHA,
        "working_declared_split_mismatch_confirmed": working_declared_split == EXPECTED_OLD_SPLIT_SHA,
        "staging_declared_split_matches_actual": staging_declared_split == split_sha,
    }

    results = []

    for filename, expected in CHECKPOINTS.items():
        checkpoint_dir = filename.removesuffix(".zip")
        zip_path = ZIP_ROOT / checkpoint_dir / filename

        print("\n========================================")
        print("CHECKPOINT:", filename)
        print("PATH:", zip_path)

        record = {
            "filename": filename,
            "path": str(zip_path),
            "exists": zip_path.is_file(),
        }

        if not zip_path.is_file():
            record["status"] = "MISSING"
            record["checks"] = {"file_exists": False}
            results.append(record)
            print("STATUS: MISSING")
            continue

        actual_zip_sha = sha256_file(zip_path)

        with zipfile.ZipFile(zip_path, "r") as zf:
            bad_entry = zf.testzip()
            names = zf.namelist()
            train_log = read_zip_json(zf, "train_log.json")
            adapter = read_zip_json(zf, "adapter_config.json")

        if train_log is None or adapter is None:
            record["status"] = "MISSING_METADATA"
            record["checks"] = {
                "train_log_present": train_log is not None,
                "adapter_config_present": adapter is not None,
            }
            results.append(record)
            print("STATUS: MISSING_METADATA")
            continue

        actual_parent = parent_name(train_log.get("checkpoint_parent"))

        checks = {
            "zip_sha256_match": actual_zip_sha == expected["zip_sha"],
            "zip_integrity_ok": bad_entry is None,
            "train_log_present": "train_log.json" in names,
            "adapter_config_present": "adapter_config.json" in names,
            "adapter_weights_present": "adapter_model.safetensors" in names,
            "seed_is_13": train_log.get("seed") == 13,
            "data_order_seed_is_13": train_log.get("data_order_seed") == 13,
            "config_sha256_match": train_log.get("config_sha256") == EXPECTED_CONFIG_SHA,
            "pool_sha256_match": train_log.get("pool_sha256") == EXPECTED_POOL_SHA,
            "train_set_sha256_match": train_log.get("train_set_sha256") == expected["train_set_sha"],
            "parent_checkpoint_match": actual_parent == expected["parent"],
            "model_match": train_log.get("model") == "Qwen/Qwen2.5-1.5B-Instruct",
            "model_revision_match": train_log.get("revision") == "989aa7980e4cf806f80c7fef2b1adb7bc71aa306",
            "epochs_match": train_log.get("epochs") == 1,
            "steps_match": train_log.get("steps") == 24,
            "effective_batch_match": train_log.get("effective_batch") == 8,
            "learning_rate_match": train_log.get("learning_rate") == 0.0002,
            "lora_rank_match": adapter.get("r") == 16,
            "lora_alpha_match": adapter.get("lora_alpha") == 32,
            "lora_dropout_match": adapter.get("lora_dropout") == 0.1,
            "lora_target_modules_present": set(adapter.get("target_modules", [])) == {
                "q_proj", "k_proj", "v_proj", "o_proj",
                "gate_proj", "up_proj", "down_proj"
            },
        }

        record.update({
            "sha256": actual_zip_sha,
            "zip_integrity": "OK" if bad_entry is None else f"BAD:{bad_entry}",
            "train_log": train_log,
            "adapter_config": adapter,
            "checks": checks,
            "all_checks_pass": all(checks.values()),
            "status": "PASS" if all(checks.values()) else "CHECK_FAILED",
        })

        print("ZIP_SHA256:", actual_zip_sha)
        print("PARENT:", actual_parent)
        print("CONFIG_SHA256:", train_log.get("config_sha256"))
        print("TRAIN_SET_SHA256:", train_log.get("train_set_sha256"))
        print("CHECKS:", json.dumps(checks, indent=2))
        print("STATUS:", record["status"])

        results.append(record)

    all_checkpoints_pass = (
        len(results) == 3
        and all(r.get("status") == "PASS" for r in results)
    )

    summary = {
        "audit_version": "v2.1",
        "scope": "B4 seed 13, S1-S3 only",
        "zip_root": str(ZIP_ROOT),
        "config_provenance": {
            "working_config_path": str(WORKING_CONFIG),
            "working_config_sha256": working_config_sha,
            "working_declared_split_sha256": working_declared_split,
            "staging_config_path": str(STAGING_CONFIG),
            "staging_config_sha256": staging_config_sha,
            "staging_declared_split_sha256": staging_declared_split,
            "actual_split_path": str(WORKING_SPLIT),
            "actual_split_sha256": split_sha,
            "checks": config_checks,
        },
        "checkpoint_count": 3,
        "found_count": sum(bool(r.get("exists")) for r in results),
        "pass_count": sum(r.get("status") == "PASS" for r in results),
        "all_checkpoints_pass": all_checkpoints_pass,
        "checkpoints": results,
    }

    json_path = OUT_DIR / "checkpoint_zip_metadata_audit_v2.json"
    csv_path = OUT_DIR / "checkpoint_zip_metadata_audit_v2.csv"

    json_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        fields = [
            "filename", "status", "sha256", "zip_integrity",
            "seed", "checkpoint_parent", "config_sha256",
            "train_set_sha256", "pool_sha256", "n_examples",
            "adapter_weights_present", "all_checks_pass",
        ]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()

        for r in results:
            tl = r.get("train_log", {})
            writer.writerow({
                "filename": r["filename"],
                "status": r.get("status"),
                "sha256": r.get("sha256"),
                "zip_integrity": r.get("zip_integrity"),
                "seed": tl.get("seed"),
                "checkpoint_parent": parent_name(tl.get("checkpoint_parent")),
                "config_sha256": tl.get("config_sha256"),
                "train_set_sha256": tl.get("train_set_sha256"),
                "pool_sha256": tl.get("pool_sha256"),
                "n_examples": tl.get("n_examples"),
                "adapter_weights_present": r.get("checks", {}).get("adapter_weights_present"),
                "all_checks_pass": r.get("all_checks_pass"),
            })

    print("\n========== FINAL SUMMARY ==========")
    print("FOUND:", summary["found_count"], "/", summary["checkpoint_count"])
    print("PASS:", summary["pass_count"])
    print("ALL_CHECKPOINTS_PASS:", summary["all_checkpoints_pass"])
    print("CONFIG_CHECKS:", json.dumps(config_checks, indent=2))
    print("JSON:", json_path)
    print("CSV:", csv_path)

    if not all_checkpoints_pass:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
