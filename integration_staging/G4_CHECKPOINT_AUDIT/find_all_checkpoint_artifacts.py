from pathlib import Path
import hashlib
import csv
import zipfile
import json

ROOT = Path(r"C:\Users\PC - NGHI\Desktop\Pipeline\P2")
OUT = ROOT / "integration_staging" / "G4_CHECKPOINT_AUDIT"

SKIP_DIRS = {
    ".venv", "venv", "__pycache__", "node_modules",
    ".git", ".pytest_cache", ".mypy_cache"
}
WEIGHT_SUFFIXES = {".safetensors", ".bin", ".pt", ".pth", ".ckpt", ".gguf"}
CHECKPOINT_TOKENS = (
    "student_ckpt", "ckpt_000", "ckpt_001", "ckpt_002", "ckpt_003",
    "checkpoint", "adapter"
)
IMPORTANT_FILES = {
    "adapter_model.safetensors",
    "adapter_model.bin",
    "adapter_config.json",
    "train_log.json",
    "trainer_state.json",
    "training_args.bin",
    "config.json",
}

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def walk_files(root):
    for current, dirs, files in __import__("os").walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        base = Path(current)
        for name in files:
            yield base / name

def write_csv(path, rows):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

OUT.mkdir(parents=True, exist_ok=True)

file_rows = []
zip_rows = []
dirs_with_adapter = {}

for path in walk_files(ROOT):
    name_lower = path.name.lower()
    rel = path.relative_to(ROOT).as_posix()

    is_weight = path.suffix.lower() in WEIGHT_SUFFIXES
    is_important = path.name in IMPORTANT_FILES
    is_named = any(token in name_lower for token in CHECKPOINT_TOKENS)

    if is_weight or is_important or is_named:
        try:
            file_rows.append({
                "relative_path": rel,
                "file_name": path.name,
                "suffix": path.suffix.lower(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
                "is_weight": is_weight,
                "is_important_metadata": is_important,
            })
        except Exception as exc:
            file_rows.append({
                "relative_path": rel,
                "file_name": path.name,
                "suffix": path.suffix.lower(),
                "size_bytes": "",
                "sha256": "",
                "is_weight": is_weight,
                "is_important_metadata": is_important,
            })

    if path.name in {"adapter_config.json", "adapter_model.safetensors",
                     "adapter_model.bin", "train_log.json"}:
        dirs_with_adapter.setdefault(path.parent, set()).add(path.name)

    if path.suffix.lower() == ".zip" and is_named:
        try:
            with zipfile.ZipFile(path) as z:
                names = z.namelist()
                bad = z.testzip()
                interesting = [
                    n for n in names
                    if Path(n).name in IMPORTANT_FILES
                    or Path(n).suffix.lower() in WEIGHT_SUFFIXES
                    or "student_ckpt" in n.lower()
                ]
            zip_rows.append({
                "relative_path": rel,
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
                "zip_integrity": "OK" if bad is None else f"BAD:{bad}",
                "entry_count": len(names),
                "weight_or_metadata_count": len(interesting),
                "interesting_entries": " ; ".join(interesting[:100]),
            })
        except Exception as exc:
            zip_rows.append({
                "relative_path": rel,
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
                "zip_integrity": f"ERROR:{exc}",
                "entry_count": "",
                "weight_or_metadata_count": "",
                "interesting_entries": "",
            })

dir_rows = []
for folder, names in sorted(dirs_with_adapter.items(), key=lambda x: str(x[0])):
    dir_rows.append({
        "relative_path": folder.relative_to(ROOT).as_posix(),
        "files_found": " ; ".join(sorted(names)),
        "has_adapter_config": "adapter_config.json" in names,
        "has_safetensors": "adapter_model.safetensors" in names,
        "has_bin": "adapter_model.bin" in names,
        "has_train_log": "train_log.json" in names,
    })

write_csv(OUT / "all_checkpoint_related_files.csv", file_rows)
write_csv(OUT / "all_checkpoint_zip_contents.csv", zip_rows)
write_csv(OUT / "all_adapter_directories.csv", dir_rows)

lines = [
    "FULL P2 CHECKPOINT SEARCH",
    f"ROOT={ROOT}",
    f"CHECKPOINT_RELATED_FILE_COUNT={len(file_rows)}",
    f"CHECKPOINT_ZIP_COUNT={len(zip_rows)}",
    f"ADAPTER_METADATA_DIRECTORY_COUNT={len(dir_rows)}",
    "",
    "NAMED CHECKPOINT FILES:",
]
for row in file_rows:
    if any(x in row["file_name"].lower() for x in ("student_ckpt", "ckpt_000",
            "ckpt_001", "ckpt_002", "ckpt_003")):
        lines.append(json.dumps(row, ensure_ascii=False))

lines += ["", "CHECKPOINT ZIP FILES:"]
for row in zip_rows:
    lines.append(json.dumps(row, ensure_ascii=False))

lines += ["", "ADAPTER DIRECTORIES:"]
for row in dir_rows:
    lines.append(json.dumps(row, ensure_ascii=False))

(OUT / "full_checkpoint_search_summary.txt").write_text(
    "\n".join(lines), encoding="utf-8"
)

print("\n".join(lines))
print("\nOUTPUT FILES:")
for name in (
    "all_checkpoint_related_files.csv",
    "all_checkpoint_zip_contents.csv",
    "all_adapter_directories.csv",
    "full_checkpoint_search_summary.txt",
):
    print(OUT / name)
