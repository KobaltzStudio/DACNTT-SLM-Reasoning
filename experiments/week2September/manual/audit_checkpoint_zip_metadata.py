import hashlib
import json
import zipfile
from pathlib import Path

root = Path(r"C:\Users\PC - NGHI\Desktop\Pipeline\P2\experiments\week2September\manual")

zips = [
    root / "integration_staging" / "P1" / "models" / "task7" / "B4" / "seed_13" / "student_ckpt_001" / "student_ckpt_001.zip",
    root / "integration_staging" / "P1" / "models" / "task7" / "B4" / "seed_13" / "student_ckpt_002" / "student_ckpt_002.zip",
    root / "integration_staging" / "P1" / "models" / "task7" / "B4" / "seed_13" / "student_ckpt_003" / "student_ckpt_003.zip",
]

out = root / "reports" / "p1p2_integration" / "checkpoint_zip_metadata_audit"
out.mkdir(parents=True, exist_ok=True)

def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()

def inspect_json(zf, name):
    try:
        raw = zf.read(name)
        return json.loads(raw.decode("utf-8-sig"))
    except KeyError:
        return None
    except Exception as exc:
        return {"_parse_error": str(exc)}

summary = []

for zip_path in zips:
    print("\n" + "=" * 80)
    print("ZIP:", zip_path)

    if not zip_path.is_file():
        print("ZIP_MISSING=True")
        summary.append({"zip": str(zip_path), "status": "MISSING"})
        continue

    zip_hash = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    print("ZIP_SHA256:", zip_hash)

    with zipfile.ZipFile(zip_path, "r") as zf:
        bad = zf.testzip()
        names = zf.namelist()

        print("ZIP_INTEGRITY:", "OK" if bad is None else f"BAD:{bad}")
        print("ENTRIES:")
        for name in names:
            info = zf.getinfo(name)
            print(f"  {name} | {info.file_size} bytes")

        train_logs = [n for n in names if n.endswith("train_log.json")]
        adapter_configs = [n for n in names if n.endswith("adapter_config.json")]

        record = {
            "zip": str(zip_path),
            "zip_sha256": zip_hash,
            "integrity": "OK" if bad is None else f"BAD:{bad}",
            "entries": names,
            "train_logs": [],
            "adapter_configs": [],
        }

        for name in train_logs:
            obj = inspect_json(zf, name)
            print(f"\n--- TRAIN LOG: {name} ---")
            print(json.dumps(obj, indent=2, ensure_ascii=False))
            record["train_logs"].append({"path": name, "data": obj})

        for name in adapter_configs:
            obj = inspect_json(zf, name)
            print(f"\n--- ADAPTER CONFIG: {name} ---")
            print(json.dumps(obj, indent=2, ensure_ascii=False))
            record["adapter_configs"].append({"path": name, "data": obj})

        summary.append(record)

report_path = out / "checkpoint_zip_metadata_audit.json"
report_path.write_text(
    json.dumps(summary, indent=2, ensure_ascii=False),
    encoding="utf-8"
)
print("\nREPORT_WRITTEN:", report_path)
