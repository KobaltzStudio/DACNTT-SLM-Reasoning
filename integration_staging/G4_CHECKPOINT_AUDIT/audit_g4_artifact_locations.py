from pathlib import Path
import hashlib
import csv
import json
import zipfile

P2 = Path(r"C:\Users\PC - NGHI\Desktop\Pipeline\P2")
MANUAL = P2 / "experiments" / "week2September" / "manual"
MAIN = MANUAL / "runs" / "main"
MODELS = MANUAL / "models"
STAGE = P2 / "integration_staging"
P1_STAGE = STAGE / "P1"
OUT = STAGE / "G4_CHECKPOINT_AUDIT"

WEIGHT_SUFFIXES = {
    ".safetensors", ".bin", ".pt", ".pth", ".ckpt", ".gguf"
}
WEIGHT_NAMES = {
    "adapter_model.safetensors",
    "adapter_model.bin",
    "pytorch_model.bin",
    "model.safetensors",
    "model.safetensors.index.json",
}

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def write_csv(path, rows):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

OUT.mkdir(parents=True, exist_ok=True)

roots = [
    ("manual_models", MODELS),
    ("main_runs", MAIN),
]

weight_rows = []
for label, root in roots:
    if not root.is_dir():
        weight_rows.append({
            "source": label,
            "root_exists": False,
            "relative_path": "",
            "file_name": "",
            "size_bytes": "",
            "sha256": "",
        })
        continue

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in WEIGHT_SUFFIXES and path.name not in WEIGHT_NAMES:
            continue
        weight_rows.append({
            "source": label,
            "root_exists": True,
            "relative_path": path.relative_to(root).as_posix(),
            "file_name": path.name,
            "size_bytes": path.stat().st_size,
            "sha256": sha256(path),
        })

write_csv(OUT / "g4_weight_inventory_all_locations.csv", weight_rows)

zip_rows = []
if P1_STAGE.is_dir():
    for path in sorted(P1_STAGE.glob("*.zip")):
        try:
            with zipfile.ZipFile(path) as z:
                names = z.namelist()
                weight_entries = [
                    n for n in names
                    if Path(n).suffix.lower() in WEIGHT_SUFFIXES
                    or Path(n).name in WEIGHT_NAMES
                ]
                bad = z.testzip()
            zip_rows.append({
                "zip_file": path.name,
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
                "zip_integrity": "OK" if bad is None else f"BAD:{bad}",
                "entry_count": len(names),
                "weight_entry_count": len(weight_entries),
                "weight_entries": " ; ".join(weight_entries[:30]),
            })
        except Exception as exc:
            zip_rows.append({
                "zip_file": path.name,
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
                "zip_integrity": "ERROR",
                "entry_count": "",
                "weight_entry_count": "",
                "weight_entries": str(exc),
            })

write_csv(OUT / "g4_checkpoint_zip_inventory.csv", zip_rows)

done_rows = []
if MAIN.is_dir():
    for path in sorted(MAIN.glob("*/.done/eval_dev_*.json")):
        try:
            obj = json.loads(path.read_text(encoding="utf-8-sig"))
            done_rows.append({
                "relative_path": path.relative_to(MAIN).as_posix(),
                "size_bytes": path.stat().st_size,
                "valid_json": True,
                "keys": json.dumps(
                    sorted(obj.keys()) if isinstance(obj, dict) else [],
                    ensure_ascii=False
                ),
                "content": json.dumps(obj, ensure_ascii=False),
                "error": "",
            })
        except Exception as exc:
            done_rows.append({
                "relative_path": path.relative_to(MAIN).as_posix(),
                "size_bytes": path.stat().st_size,
                "valid_json": False,
                "keys": "",
                "content": "",
                "error": str(exc),
            })

write_csv(OUT / "g4_done_marker_full_content.csv", done_rows)

sample_path = OUT / "main_eval_dev_schema_samples.json"
schema_preview = {}
if sample_path.exists():
    try:
        schema_preview = json.loads(sample_path.read_text(encoding="utf-8"))
    except Exception as exc:
        schema_preview = {"_read_error": str(exc)}

summary = []
summary.append("G4 ARTIFACT LOCATION AUDIT")
summary.append(f"MODELS_DIR_EXISTS={MODELS.is_dir()}")
summary.append(f"MAIN_RUNS_DIR_EXISTS={MAIN.is_dir()}")
summary.append(f"P1_STAGE_DIR_EXISTS={P1_STAGE.is_dir()}")
summary.append(f"WEIGHT_FILE_COUNT={sum(1 for r in weight_rows if r.get('file_name'))}")
summary.append(f"CHECKPOINT_ZIP_COUNT={len(zip_rows)}")
summary.append(f"DONE_MARKER_COUNT={len(done_rows)}")
summary.append("")
summary.append("WEIGHT INVENTORY:")
for row in weight_rows:
    summary.append(json.dumps(row, ensure_ascii=False))
summary.append("")
summary.append("CHECKPOINT ZIP INVENTORY:")
for row in zip_rows:
    summary.append(json.dumps(row, ensure_ascii=False))
summary.append("")
summary.append("DONE MARKERS:")
for row in done_rows:
    summary.append(json.dumps(row, ensure_ascii=False))
summary.append("")
summary.append("SCHEMA SAMPLE:")
summary.append(json.dumps(schema_preview, ensure_ascii=False, indent=2)[:12000])

(OUT / "g4_artifact_location_audit.txt").write_text(
    "\n".join(summary), encoding="utf-8"
)

print("\n".join(summary))
print("\nOUTPUT:")
for name in (
    "g4_weight_inventory_all_locations.csv",
    "g4_checkpoint_zip_inventory.csv",
    "g4_done_marker_full_content.csv",
    "g4_artifact_location_audit.txt",
):
    print(OUT / name)
