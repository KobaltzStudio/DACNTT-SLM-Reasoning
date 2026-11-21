import csv
import hashlib
import json
import re
import zipfile
from pathlib import Path

MANUAL = Path(__file__).resolve().parents[1]
P2_ROOT = MANUAL.parents[2]

OUT_DIR = (
    MANUAL
    / "reports"
    / "p1p2_integration"
    / "checkpoint_inventory_audit"
)

EXCLUDED_DIRS = {
    ".venv", "__pycache__", ".git", "node_modules",
    ".pytest_cache", ".mypy_cache"
}

METHODS = {"B2", "B3", "B4", "B5"}
SEEDS = {13, 42, 2026}
ROUNDS = {"S1", "S2", "S3"}

def sha256_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def read_json_bytes(data):
    try:
        return json.loads(data.decode("utf-8-sig"))
    except Exception:
        return None

def parse_context(path_text, train_log=None):
    text = path_text.replace("\\", "/")
    parts = text.split("/")

    method = None
    seed = None
    round_name = None

    for p in parts:
        if p in METHODS:
            method = p

        m = re.fullmatch(r"seed[_-]?(\d+)", p, re.I)
        if m:
            seed = int(m.group(1))

        m = re.fullmatch(r"S([123])", p, re.I)
        if m:
            round_name = "S" + m.group(1)

    if train_log:
        seed = train_log.get("seed", seed)

    ckpt_match = re.search(r"student_ckpt_(00[123])", text)
    if ckpt_match and round_name is None:
        round_name = {
            "001": "S1",
            "002": "S2",
            "003": "S3",
        }[ckpt_match.group(1)]

    return method, seed, round_name

def scan_zip(path):
    row = {
        "artifact_type": "zip",
        "path": str(path),
        "exists": True,
        "artifact_sha256": None,
        "zip_integrity": None,
        "weights_present": False,
        "train_log_present": False,
        "adapter_config_present": False,
        "metadata_error": None,
    }

    try:
        row["artifact_sha256"] = sha256_file(path)

        with zipfile.ZipFile(path, "r") as zf:
            bad = zf.testzip()
            names = zf.namelist()

            row["zip_integrity"] = "OK" if bad is None else f"BAD:{bad}"
            row["weights_present"] = any(
                n.endswith("adapter_model.safetensors")
                or n.endswith("adapter_model.bin")
                for n in names
            )

            train_entries = [
                n for n in names if n.endswith("train_log.json")
            ]
            adapter_entries = [
                n for n in names if n.endswith("adapter_config.json")
            ]

            row["train_log_present"] = bool(train_entries)
            row["adapter_config_present"] = bool(adapter_entries)

            train_log = None
            adapter = None

            if train_entries:
                train_log = read_json_bytes(zf.read(train_entries[0]))

            if adapter_entries:
                adapter = read_json_bytes(zf.read(adapter_entries[0]))

            row["train_log"] = train_log
            row["adapter_config"] = adapter

    except Exception as e:
        row["metadata_error"] = repr(e)
        row["zip_integrity"] = "ERROR"

    method, seed, round_name = parse_context(
        str(path), row.get("train_log")
    )

    row["method"] = method
    row["seed"] = seed
    row["round"] = round_name
    return row

def scan_checkpoint_dir(path):
    row = {
        "artifact_type": "directory",
        "path": str(path),
        "exists": path.is_dir(),
        "artifact_sha256": None,
        "zip_integrity": "N/A",
        "weights_present": False,
        "train_log_present": False,
        "adapter_config_present": False,
        "metadata_error": None,
    }

    weights = list(path.rglob("adapter_model.safetensors"))
    if not weights:
        weights = list(path.rglob("adapter_model.bin"))

    train_logs = list(path.rglob("train_log.json"))
    adapter_configs = list(path.rglob("adapter_config.json"))

    row["weights_present"] = bool(weights)
    row["train_log_present"] = bool(train_logs)
    row["adapter_config_present"] = bool(adapter_configs)

    train_log = None
    adapter = None

    if train_logs:
        try:
            train_log = json.loads(
                train_logs[0].read_text(encoding="utf-8-sig")
            )
        except Exception as e:
            row["metadata_error"] = f"train_log: {e!r}"

    if adapter_configs:
        try:
            adapter = json.loads(
                adapter_configs[0].read_text(encoding="utf-8-sig")
            )
        except Exception as e:
            row["metadata_error"] = (
                (row["metadata_error"] or "")
                + f" adapter_config: {e!r}"
            )

    row["train_log"] = train_log
    row["adapter_config"] = adapter

    method, seed, round_name = parse_context(
        str(path), train_log
    )

    row["method"] = method
    row["seed"] = seed
    row["round"] = round_name

    return row

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("P2_ROOT:", P2_ROOT)
    print("MANUAL:", MANUAL)

    zip_files = []
    checkpoint_dirs = []

    for p in P2_ROOT.rglob("*"):
        if any(part in EXCLUDED_DIRS for part in p.parts):
            continue

        if not p.is_file() and not p.is_dir():
            continue

        if p.is_file() and p.suffix.lower() == ".zip":
            if re.search(r"student_ckpt_00[123]\.zip$", p.name):
                zip_files.append(p)

        elif p.is_dir() and re.fullmatch(
            r"student_ckpt_00[123]", p.name
        ):
            checkpoint_dirs.append(p)

    zip_files = sorted(set(zip_files))
    checkpoint_dirs = sorted(set(checkpoint_dirs))

    print("ZIP_COUNT:", len(zip_files))
    print("CHECKPOINT_DIR_COUNT:", len(checkpoint_dirs))

    rows = []

    for p in zip_files:
        rows.append(scan_zip(p))

    for p in checkpoint_dirs:
        rows.append(scan_checkpoint_dir(p))

    # Add normalized training metadata for CSV/reporting.
    for row in rows:
        tl = row.get("train_log") or {}
        adapter = row.get("adapter_config") or {}

        row["checkpoint_parent"] = tl.get("checkpoint_parent")
        row["config_sha256"] = tl.get("config_sha256")
        row["train_set_sha256"] = tl.get("train_set_sha256")
        row["pool_sha256"] = tl.get("pool_sha256")
        row["model"] = tl.get("model")
        row["model_revision"] = tl.get("revision")
        row["lora_rank"] = adapter.get("r")
        row["lora_alpha"] = adapter.get("lora_alpha")
        row["lora_dropout"] = adapter.get("lora_dropout")

        if row["method"] not in METHODS:
            row["context_status"] = "METHOD_UNRESOLVED"
        elif row["seed"] not in SEEDS:
            row["context_status"] = "SEED_OUTSIDE_REGISTERED_MATRIX"
        elif row["round"] not in ROUNDS:
            row["context_status"] = "ROUND_UNRESOLVED"
        else:
            row["context_status"] = "REGISTERED_CONTEXT_CANDIDATE"

        if row["artifact_type"] == "zip":
            if row["zip_integrity"] != "OK":
                row["artifact_status"] = "ZIP_INVALID"
            elif not row["weights_present"]:
                row["artifact_status"] = "WEIGHTS_MISSING"
            elif not row["train_log_present"]:
                row["artifact_status"] = "TRAIN_LOG_MISSING"
            elif not row["adapter_config_present"]:
                row["artifact_status"] = "ADAPTER_CONFIG_MISSING"
            else:
                row["artifact_status"] = "COMPLETE_ZIP_CANDIDATE"
        else:
            if not row["weights_present"]:
                row["artifact_status"] = "WEIGHTS_MISSING"
            elif not row["train_log_present"]:
                row["artifact_status"] = "TRAIN_LOG_MISSING"
            elif not row["adapter_config_present"]:
                row["artifact_status"] = "ADAPTER_CONFIG_MISSING"
            else:
                row["artifact_status"] = "COMPLETE_DIRECTORY_CANDIDATE"

    # Expected matrix: 36 trained contexts.
    expected = [
        {
            "method": method,
            "seed": seed,
            "round": round_name,
        }
        for method in sorted(METHODS)
        for seed in sorted(SEEDS)
        for round_name in sorted(ROUNDS)
    ]

    found_contexts = set()
    for row in rows:
        if (
            row["method"] in METHODS
            and row["seed"] in SEEDS
            and row["round"] in ROUNDS
            and row["weights_present"]
            and row["train_log_present"]
        ):
            found_contexts.add((
                row["method"], row["seed"], row["round"]
            ))

    matrix = []
    for item in expected:
        key = (item["method"], item["seed"], item["round"])
        matching = [
            r for r in rows
            if (
                r["method"], r["seed"], r["round"]
            ) == key
        ]

        matrix.append({
            **item,
            "artifact_count": len(matching),
            "has_weights_and_train_log": key in found_contexts,
            "artifact_paths": [r["path"] for r in matching],
        })

    summary = {
        "audit_version": "1.0",
        "scope": "Read-only checkpoint inventory; no training or extraction",
        "p2_root": str(P2_ROOT),
        "zip_count": len(zip_files),
        "checkpoint_directory_count": len(checkpoint_dirs),
        "artifact_count": len(rows),
        "registered_method_seed_round_contexts": 36,
        "contexts_with_weights_and_train_log": len(found_contexts),
        "missing_context_count": 36 - len(found_contexts),
        "expected_matrix": matrix,
        "artifacts": rows,
        "important_note": (
            "This scan inventories artifacts. It does not prove that "
            "different method/seed paths contain distinct model states. "
            "Shared checkpoint aliases must be resolved from execution "
            "markers and training logs."
        ),
    }

    json_path = OUT_DIR / "checkpoint_inventory_audit.json"
    csv_path = OUT_DIR / "checkpoint_inventory_artifacts.csv"
    matrix_path = OUT_DIR / "checkpoint_inventory_matrix.csv"

    # Remove bulky raw metadata from artifact CSV.
    csv_fields = [
        "artifact_type", "path", "artifact_sha256",
        "method", "seed", "round", "context_status",
        "artifact_status", "zip_integrity",
        "weights_present", "train_log_present",
        "adapter_config_present", "checkpoint_parent",
        "config_sha256", "train_set_sha256", "pool_sha256",
        "model", "model_revision", "lora_rank",
        "lora_alpha", "lora_dropout", "metadata_error",
    ]

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k) for k in csv_fields})

    with matrix_path.open("w", newline="", encoding="utf-8-sig") as f:
        fields = [
            "method", "seed", "round", "artifact_count",
            "has_weights_and_train_log", "artifact_paths",
        ]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for item in matrix:
            out = dict(item)
            out["artifact_paths"] = " || ".join(item["artifact_paths"])
            writer.writerow({k: out.get(k) for k in fields})

    # Store full JSON, including original train logs and adapter configs.
    json_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    print("\n========== INVENTORY SUMMARY ==========")
    print("ZIP_COUNT:", len(zip_files))
    print("CHECKPOINT_DIR_COUNT:", len(checkpoint_dirs))
    print("ARTIFACT_COUNT:", len(rows))
    print("REGISTERED_CONTEXTS:", 36)
    print("CONTEXTS_WITH_WEIGHTS_AND_TRAIN_LOG:", len(found_contexts))
    print("MISSING_CONTEXTS:", 36 - len(found_contexts))
    print("JSON:", json_path)
    print("CSV:", csv_path)
    print("MATRIX:", matrix_path)

if __name__ == "__main__":
    main()
