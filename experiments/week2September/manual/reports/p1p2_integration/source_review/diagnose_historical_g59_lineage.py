import argparse
import hashlib
import json
import zipfile
from pathlib import Path

EXPECTED_ZIP_SHA256 = (
    "A4C657E7D643D4BE6839EAF6614485AB"
    "3DD0AB26C825765D993C783E9371BE9F"
)

def sha256(data):
    return hashlib.sha256(data).hexdigest()

def json_bytes(obj, *, sort_keys=False, compact=False):
    if compact:
        text = json.dumps(
            obj, ensure_ascii=False, sort_keys=sort_keys,
            separators=(",", ":")
        )
    else:
        text = json.dumps(
            obj, ensure_ascii=False, sort_keys=sort_keys
        )
    return text.encode("utf-8")

def read_member(zf, names, suffix):
    suffix = suffix.replace("\\", "/")
    matches = [
        n for n in names
        if n.replace("\\", "/").endswith(suffix)
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected exactly one member ending in {suffix!r}; "
            f"found {len(matches)}: {matches[:10]}"
        )
    name = matches[0]
    return name, zf.read(name)

def parse_json_member(zf, names, suffix):
    name, raw = read_member(zf, names, suffix)
    return name, raw, json.loads(raw.decode("utf-8-sig"))

def parse_jsonl_bytes(raw, label):
    records = []
    errors = []
    text = raw.decode("utf-8-sig")
    for line_no, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except Exception as exc:
            errors.append({
                "line": line_no,
                "error": str(exc),
                "sample": line[:500],
            })
    print(f"{label}_JSONL_RECORDS =", len(records))
    print(f"{label}_JSONL_ERRORS =", len(errors))
    for item in errors[:5]:
        print("JSONL_ERROR =", json.dumps(item, ensure_ascii=False))
    return records

def show_hash(label, data, expected):
    actual = sha256(data)
    print(
        f"{label}: {actual} "
        f"MATCH_RECORDED={actual.lower() == str(expected).lower()}"
    )
    return actual

def inspect_train_set(method, seed, zf, names):
    base = f"{method}_seed{seed}/"

    set_name, set_raw, train_set = parse_json_member(
        zf, names, f"{base}round_000/train_set.json"
    )
    log_name, log_raw, train_log = parse_json_member(
        zf, names, f"{base}S1/adapter/train_log.json"
    )

    print("\n" + "-" * 90)
    print(f"TRAIN SET INSPECTION: {method}_seed{seed} S1")
    print("-" * 90)

    print("TRAIN_SET_MEMBER =", set_name)
    print("TRAIN_LOG_MEMBER =", log_name)
    print("TRAIN_SET_KEYS =", sorted(train_set.keys()))
    print("TRAIN_LOG_KEYS =", sorted(train_log.keys()))

    recorded = train_log.get("train_set_sha256")
    print("RECORDED_TRAIN_SET_SHA256 =", recorded)
    print("TRAIN_LOG_TRAIN_SET_FIELD =", train_log.get("train_set"))
    print("TRAIN_LOG_N_EXAMPLES =", train_log.get("n_examples"))

    show_hash("RAW_FILE_SHA256", set_raw, recorded)

    candidates = {
        "json_default": json_bytes(train_set),
        "json_sorted": json_bytes(train_set, sort_keys=True),
        "json_compact": json_bytes(train_set, compact=True),
        "json_sorted_compact": json_bytes(
            train_set, sort_keys=True, compact=True
        ),
    }

    for key, value in candidates.items():
        show_hash(key.upper(), value, recorded)

    trajectory_ids = train_set.get("trajectory_ids", [])
    print("TRAJECTORY_ID_COUNT =", len(trajectory_ids))
    print("TRAJECTORY_ID_SAMPLE =", trajectory_ids[:10])

    trajectory_candidates = {
        "ids_json_default": json_bytes(trajectory_ids),
        "ids_json_compact": json_bytes(trajectory_ids, compact=True),
        "ids_newline": ("\n".join(trajectory_ids)).encode("utf-8"),
        "ids_newline_final": (
            "\n".join(trajectory_ids) + "\n"
        ).encode("utf-8"),
    }

    for key, value in trajectory_candidates.items():
        show_hash(key.upper(), value, recorded)

    print("TRAIN_SET_METHOD =", train_set.get("method"))
    print("TRAIN_SET_ROUND =", train_set.get("round"))
    print("TRAIN_SET_SEED =", train_set.get("training_seed"))
    print("TRAIN_SET_N_SELECTED =", train_set.get("n_selected"))
    print("TRAIN_SET_TOKENS_USED =", train_set.get("tokens_used"))
    print("TRAIN_SET_POOL_SHA256 =", train_set.get("pool_sha256"))
    print("TRAIN_SET_CONFIG_SHA256 =", train_set.get("config_sha256"))

    return {
        "raw_sha": sha256(set_raw),
        "recorded_sha": recorded,
        "train_set": train_set,
        "train_log": train_log,
        "train_set_raw": set_raw,
        "train_log_raw": log_raw,
    }

def inspect_jsonl_member(zf, names, suffix, label):
    name, raw = read_member(zf, names, suffix)
    print(f"\n[{label}]")
    print("MEMBER =", name)
    print("RAW_SHA256 =", sha256(raw))
    print("RAW_BYTES =", len(raw))

    records = parse_jsonl_bytes(raw, label)
    for i, record in enumerate(records[:8]):
        print(
            f"{label}_RECORD_{i} =",
            json.dumps(record, ensure_ascii=False)[:5000]
        )

    return name, raw, records

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    args = ap.parse_args()

    root = Path(args.root).resolve()
    archive_path = root / "runs" / "main" / "main.zip"

    if not archive_path.is_file():
        raise FileNotFoundError(archive_path)

    archive_sha = sha256(archive_path.read_bytes())

    print("ARCHIVE =", archive_path)
    print("ARCHIVE_SHA256 =", archive_sha)
    print("ARCHIVE_SHA_EXPECTED =", EXPECTED_ZIP_SHA256)
    print(
        "ARCHIVE_SHA_MATCH =",
        archive_sha.upper() == EXPECTED_ZIP_SHA256
    )

    if archive_sha.upper() != EXPECTED_ZIP_SHA256:
        raise RuntimeError("main.zip SHA-256 differs from audited archive.")

    with zipfile.ZipFile(archive_path, "r") as zf:
        bad = zf.testzip()
        print("ZIP_INTEGRITY =", "PASS" if bad is None else f"FAIL: {bad}")
        if bad is not None:
            raise RuntimeError(f"Corrupt ZIP member: {bad}")

        names = zf.namelist()
        comparisons = {}

        for seed in (13, 42, 2026):
            print("\n" + "=" * 100)
            print(f"B4/B5 S1 ALIAS DIAGNOSTIC — SEED {seed}")
            print("=" * 100)

            for method in ("B4", "B5"):
                key = f"{method}_seed{seed}"
                result = inspect_train_set(method, seed, zf, names)

                prefix = f"{method}_seed{seed}/"

                selection_name, selection_raw, selection_records = (
                    inspect_jsonl_member(
                        zf, names,
                        f"{prefix}round_000/selection_log.jsonl",
                        f"{key}_SELECTION"
                    )
                )

                checkpoint_name, checkpoint_raw, checkpoint_records = (
                    inspect_jsonl_member(
                        zf, names,
                        f"{prefix}checkpoint_log.jsonl",
                        f"{key}_CHECKPOINT"
                    )
                )

                result["selection_sha"] = sha256(selection_raw)
                result["selection_records"] = selection_records
                result["checkpoint_sha"] = sha256(checkpoint_raw)
                result["checkpoint_records"] = checkpoint_records

                comparisons[key] = result

                print("\nCHECKPOINT_RECORD_TYPES:")
                for i, record in enumerate(checkpoint_records):
                    print(
                        f"CHECKPOINT_{i}_KEYS =",
                        sorted(record.keys())
                    )
                    print(
                        f"CHECKPOINT_{i}_RECORD =",
                        json.dumps(record, ensure_ascii=False)[:8000]
                    )

                print("SELECTION_MEMBER =", selection_name)
                print("CHECKPOINT_MEMBER =", checkpoint_name)

            b4 = comparisons[f"B4_seed{seed}"]
            b5 = comparisons[f"B5_seed{seed}"]

            print("\n" + "-" * 90)
            print(f"ALIAS COMPARISON SUMMARY — SEED {seed}")
            print("-" * 90)

            for label, left, right in (
                ("TRAIN_SET_RAW_SHA", b4["raw_sha"], b5["raw_sha"]),
                ("TRAIN_LOG_RECORDED_SHA", b4["recorded_sha"], b5["recorded_sha"]),
                ("SELECTION_LOG_SHA", b4["selection_sha"], b5["selection_sha"]),
                ("CHECKPOINT_LOG_SHA", b4["checkpoint_sha"], b5["checkpoint_sha"]),
            ):
                print(
                    label,
                    "B4 =", left,
                    "B5 =", right,
                    "MATCH =", left == right,
                )

            b4_ids = b4["train_set"].get("trajectory_ids", [])
            b5_ids = b5["train_set"].get("trajectory_ids", [])
            print("TRAJECTORY_IDS_EQUAL =", b4_ids == b5_ids)
            print("TRAJECTORY_IDS_COUNTS =", len(b4_ids), len(b5_ids))

            print(
                "B4_TRAIN_SET_HASH_MATCHES_RECORDED =",
                str(b4["raw_sha"]).lower()
                == str(b4["recorded_sha"]).lower()
            )
            print(
                "B5_TRAIN_SET_HASH_MATCHES_RECORDED =",
                str(b5["raw_sha"]).lower()
                == str(b5["recorded_sha"]).lower()
            )

    print("\nDIAGNOSTIC_COMPLETE=PASS")
    print("ARCHIVE_MODIFIED=false")
    print("HISTORICAL_ARTIFACTS_MODIFIED=false")
    print("POST_EVAL_HOOKS_EXECUTED=false")

if __name__ == "__main__":
    main()
