import hashlib
import json
from pathlib import Path

MANUAL = Path(
    r"C:\Users\PC - NGHI\Desktop\Pipeline\P2\experiments\week2September\manual"
)

RUN = MANUAL / "runs" / "main" / "B4_seed13"
AUDIT = Path(
    r"C:\Users\PC - NGHI\Desktop\Pipeline\P2\integration_staging\G4_CHECKPOINT_AUDIT"
)

STAGES = {
    "S1": {
        "train_set": RUN / "round_000" / "train_set.json",
        "checkpoint": AUDIT / "extracted_checkpoints" / "B4_seed13" / "S1",
    },
    "S2": {
        "train_set": RUN / "round_001" / "train_set.json",
        "checkpoint": AUDIT / "extracted_checkpoints" / "B4_seed13" / "S2",
    },
    "S3": {
        "train_set": RUN / "round_002" / "train_set.json",
        "checkpoint": AUDIT / "extracted_checkpoints" / "B4_seed13" / "S3",
    },
}

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def inspect_json(path):
    raw = path.read_text(encoding="utf-8-sig")
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            count = len(data)
            kind = "list"
            sample = data[:2]
        elif isinstance(data, dict):
            kind = "dict"
            count = len(data)
            sample = dict(list(data.items())[:10])
        else:
            kind = type(data).__name__
            count = None
            sample = data

        return {
            "parse": "PASS",
            "kind": kind,
            "top_level_count": count,
            "sample": sample,
        }
    except json.JSONDecodeError as exc:
        return {
            "parse": "FAIL",
            "error": str(exc),
            "line": exc.lineno,
            "column": exc.colno,
        }

report = {}

print("========== CURRENT TRAIN_SET AUDIT ==========")

for stage, paths in STAGES.items():
    train_set = paths["train_set"]
    checkpoint = paths["checkpoint"]
    log_path = checkpoint / "train_log.json"

    print(f"\n========== {stage} ==========")
    result = {
        "train_set_path": str(train_set),
        "train_log_path": str(log_path),
    }

    if not train_set.exists():
        print("TRAIN_SET_EXISTS=False")
        result["train_set_exists"] = False
        report[stage] = result
        continue

    digest = sha256(train_set)
    parsed = inspect_json(train_set)

    print("TRAIN_SET_EXISTS=True")
    print(f"TRAIN_SET_SIZE={train_set.stat().st_size}")
    print(f"TRAIN_SET_SHA256={digest}")
    print(f"JSON_PARSE={parsed['parse']}")
    print(f"JSON_KIND={parsed.get('kind')}")
    print(f"TOP_LEVEL_COUNT={parsed.get('top_level_count')}")

    if parsed["parse"] == "PASS":
        print("SAMPLE_CONTENT:")
        print(json.dumps(
            parsed["sample"],
            ensure_ascii=False,
            indent=2
        ))
    else:
        print(f"JSON_ERROR={parsed.get('error')}")

    log = {}
    if log_path.exists():
        try:
            log = json.loads(log_path.read_text(encoding="utf-8-sig"))
            print("TRAIN_LOG_PARSE=PASS")
            print(f"TRAIN_LOG_KEYS={list(log.keys())}")
            print(f"TRAIN_LOG_TRAIN_SET_HASH={log.get('train_set_sha256')}")
            print(f"TRAIN_LOG_TRAIN_SET_PATH={log.get('train_set')}")
        except Exception as exc:
            print(f"TRAIN_LOG_PARSE=FAIL | {exc}")
    else:
        print("TRAIN_LOG_EXISTS=False")

    result.update({
        "train_set_exists": True,
        "train_set_size": train_set.stat().st_size,
        "train_set_sha256": digest,
        "json_inspection": parsed,
        "train_log": log,
    })
    report[stage] = result

output = AUDIT / "g5_current_train_set_audit.json"
output.write_text(
    json.dumps(report, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print(f"\nREPORT={output}")
