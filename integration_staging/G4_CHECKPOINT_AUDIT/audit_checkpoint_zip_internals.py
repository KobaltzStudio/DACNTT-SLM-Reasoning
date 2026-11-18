import hashlib
import json
import zipfile
from pathlib import Path

root = Path(r"C:\Users\PC - NGHI\Desktop\Pipeline\P2")

zips = [
    root / "integration_staging/P1/models/task7/B4/seed_13/student_ckpt_001/student_ckpt_001.zip",
    root / "integration_staging/P1/models/task7/B4/seed_13/student_ckpt_002/student_ckpt_002.zip",
    root / "integration_staging/P1/models/task7/B4/seed_13/student_ckpt_003/student_ckpt_003.zip",
]

def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()

results = []

for path in zips:
    print(f"\n========== {path} ==========")

    if not path.is_file():
        print("MISSING")
        continue

    with zipfile.ZipFile(path) as z:
        bad = z.testzip()
        print("ZIP_INTEGRITY:", "OK" if bad is None else f"BAD: {bad}")

        for info in z.infolist():
            if info.is_dir():
                continue

            data = z.read(info.filename)
            name = Path(info.filename).name

            record = {
                "zip": str(path),
                "entry": info.filename,
                "size_bytes": len(data),
                "sha256": sha256_bytes(data),
            }

            if name in {
                "adapter_config.json",
                "train_log.json",
            }:
                try:
                    record["json"] = json.loads(data.decode("utf-8"))
                except Exception as exc:
                    record["json_parse_error"] = str(exc)

            results.append(record)
            print(json.dumps(record, ensure_ascii=False))

out = root / "integration_staging/G4_CHECKPOINT_AUDIT/zip_internal_hash_audit.json"
out.write_text(
    json.dumps(results, ensure_ascii=False, indent=2),
    encoding="utf-8"
)
print("\nOUTPUT:", out)
