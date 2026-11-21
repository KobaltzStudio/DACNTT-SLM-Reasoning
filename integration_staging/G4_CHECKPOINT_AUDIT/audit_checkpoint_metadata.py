from pathlib import Path
import hashlib
import json
import os
import sys

P2 = Path(r"C:\Users\PC - NGHI\Desktop\Pipeline\P2")
AUDIT_DIR = P2 / "integration_staging" / "G4_CHECKPOINT_AUDIT"
EXTRACTED = AUDIT_DIR / "extracted_checkpoints" / "B4_seed13"

EXPECTED_CONFIG_SHA256 = (
    "17cf4b837dc42ac5145aea762847ca5dfba4bae58d253560b3b0dd6a254b73c5"
)

CHECKPOINTS = {
    "S1": EXTRACTED / "S1",
    "S2": EXTRACTED / "S2",
    "S3": EXTRACTED / "S3",
}

SKIP_DIRS = {
    ".venv", "venv", "__pycache__", "node_modules", ".git"
}

CONFIG_EXTENSIONS = {
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg"
}

def sha256_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def read_json(path):
    try:
        with path.open("r", encoding="utf-8-sig") as f:
            return json.load(f), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"

def walk_files(root):
    for current, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for filename in sorted(files):
            yield Path(current) / filename

def inspect_checkpoint(stage, checkpoint_dir):
    result = {
        "stage": stage,
        "checkpoint_dir": str(checkpoint_dir),
        "directory_exists": checkpoint_dir.is_dir(),
        "files": [],
        "adapter_config": None,
        "adapter_config_error": None,
        "train_log": None,
        "train_log_error": None,
    }

    if not checkpoint_dir.is_dir():
        return result

    for path in sorted(checkpoint_dir.rglob("*")):
        if path.is_file():
            result["files"].append({
                "relative_path": path.relative_to(checkpoint_dir).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            })

    for filename, key, error_key in [
        ("adapter_config.json", "adapter_config", "adapter_config_error"),
        ("train_log.json", "train_log", "train_log_error"),
    ]:
        path = checkpoint_dir / filename
        if path.exists():
            data, error = read_json(path)
            result[key] = data
            result[error_key] = error
        else:
            result[error_key] = "FILE_NOT_FOUND"

    return result

def scan_config_candidates():
    matches = []
    candidates = []

    for path in walk_files(P2):
        if path.suffix.lower() not in CONFIG_EXTENSIONS:
            continue

        name = path.name.lower()
        if not any(token in name for token in (
            "config", "args", "hparam", "training", "train"
        )):
            continue

        try:
            digest = sha256_file(path)
            item = {
                "path": str(path),
                "size_bytes": path.stat().st_size,
                "sha256": digest,
            }
            candidates.append(item)
            if digest == EXPECTED_CONFIG_SHA256:
                matches.append(item)
        except Exception as exc:
            candidates.append({
                "path": str(path),
                "error": f"{type(exc).__name__}: {exc}",
            })

    return matches, candidates

def scan_done_markers():
    markers = []

    for path in walk_files(P2):
        # Chỉ lấy file nằm trong thư mục .done
        if ".done" not in path.parts:
            continue

        try:
            text = path.read_text(encoding="utf-8-sig", errors="replace")
            try:
                parsed = json.loads(text)
                parse_error = None
            except Exception as exc:
                parsed = None
                parse_error = f"{type(exc).__name__}: {exc}"

            markers.append({
                "path": str(path),
                "content": text[:20000],
                "json": parsed,
                "json_parse_error": parse_error,
            })
        except Exception as exc:
            markers.append({
                "path": str(path),
                "error": f"{type(exc).__name__}: {exc}",
            })

    return markers

def scan_related_artifact_candidates():
    found = []
    tokens = (
        "train", "selection", "checkpoint", "manifest",
        "pool", "config", "lineage"
    )
    allowed = {
        ".json", ".jsonl", ".csv", ".txt", ".yaml",
        ".yml", ".toml", ".log"
    }

    for path in walk_files(P2):
        if path.suffix.lower() not in allowed:
            continue
        name = path.name.lower()
        if any(token in name for token in tokens):
            try:
                found.append({
                    "path": str(path),
                    "size_bytes": path.stat().st_size,
                })
            except OSError:
                pass

    return found

def main():
    report = {
        "audit_status": "STARTED",
        "p2_root": str(P2),
        "expected_config_sha256": EXPECTED_CONFIG_SHA256,
        "checkpoints": {},
    }

    for stage, directory in CHECKPOINTS.items():
        report["checkpoints"][stage] = inspect_checkpoint(stage, directory)

    config_matches, config_candidates = scan_config_candidates()
    report["config_sha256_matches"] = config_matches
    report["config_candidate_count"] = len(config_candidates)
    report["config_candidates"] = config_candidates

    report["done_markers"] = scan_done_markers()
    report["done_marker_count"] = len(report["done_markers"])

    report["related_artifact_candidates"] = scan_related_artifact_candidates()

    required_ok = all(
        report["checkpoints"][stage]["directory_exists"]
        and report["checkpoints"][stage]["adapter_config"] is not None
        and report["checkpoints"][stage]["train_log"] is not None
        and report["checkpoints"][stage]["adapter_config_error"] is None
        and report["checkpoints"][stage]["train_log_error"] is None
        for stage in ("S1", "S2", "S3")
    )

    report["all_checkpoint_metadata_readable"] = required_ok
    report["exact_config_hash_found"] = len(config_matches) > 0
    report["audit_status"] = "PASS_METADATA_READ" if required_ok else "METADATA_INCOMPLETE"

    output_json = AUDIT_DIR / "checkpoint_metadata_lineage_audit.json"
    output_json.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print("========== CHECKPOINT METADATA AUDIT ==========")
    print(f"CHECKPOINT_METADATA_READABLE={required_ok}")

    for stage in ("S1", "S2", "S3"):
        item = report["checkpoints"][stage]
        print(f"\n--- {stage} ---")
        print(f"DIRECTORY_EXISTS={item['directory_exists']}")
        print(f"FILE_COUNT={len(item['files'])}")
        print(f"ADAPTER_CONFIG_READ={'PASS' if item['adapter_config'] is not None and item['adapter_config_error'] is None else 'FAIL'}")
        print(f"TRAIN_LOG_READ={'PASS' if item['train_log'] is not None and item['train_log_error'] is None else 'FAIL'}")
        print("ADAPTER_CONFIG:")
        print(json.dumps(item["adapter_config"], indent=2, ensure_ascii=False))
        print("TRAIN_LOG:")
        print(json.dumps(item["train_log"], indent=2, ensure_ascii=False))

    print("\n========== CONFIG HASH SEARCH ==========")
    print(f"CONFIG_CANDIDATE_COUNT={len(config_candidates)}")
    print(f"EXACT_CONFIG_HASH_MATCH_COUNT={len(config_matches)}")
    for item in config_matches:
        print(f"CONFIG_HASH_MATCH={item['path']}")

    print("\n========== .DONE MARKERS ==========")
    print(f"DONE_MARKER_COUNT={len(report['done_markers'])}")
    for marker in report["done_markers"]:
        print(f"\nMARKER_PATH={marker['path']}")
        print(f"MARKER_CONTENT={marker.get('content', marker.get('error', ''))}")

    print("\n========== RELATED ARTIFACT CANDIDATES ==========")
    print(f"RELATED_ARTIFACT_COUNT={len(report['related_artifact_candidates'])}")
    for item in report["related_artifact_candidates"]:
        print(f"{item['path']} | {item['size_bytes']} bytes")

    print("\n========== SUMMARY ==========")
    print(f"AUDIT_STATUS={report['audit_status']}")
    print(f"EXACT_CONFIG_HASH_FOUND={report['exact_config_hash_found']}")
    print(f"OUTPUT_JSON={output_json}")

    return 0 if required_ok else 2

if __name__ == "__main__":
    sys.exit(main())
