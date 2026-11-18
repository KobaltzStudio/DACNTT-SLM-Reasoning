from __future__ import annotations

import csv
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[4]
MANUAL_ROOT = REPO_ROOT / "experiments" / "week2September" / "manual"

OUTPUT_DIR = (
    MANUAL_ROOT
    / "reports"
    / "capability"
    / "student_eval_2026-11-17"
)

SKIP_DIRS = {
    ".git", ".venv", "venv", "__pycache__",
    "node_modules", ".pytest_cache", ".mypy_cache",
    "site-packages", "wandb", "runs",
}

RELEVANT_WORDS = (
    "checkpoint", "student", "prediction", "predict",
    "dev", "capability", "gold", "manifest",
    "evaluation", "evaluate", "inference",
)

DATA_EXTENSIONS = {
    ".json", ".jsonl", ".csv", ".yaml", ".yml",
    ".parquet", ".pt", ".pth", ".safetensors",
    ".bin",
}

SCRIPT_EXTENSIONS = {".py", ".ps1", ".sh"}

def is_relevant(path: Path) -> bool:
    text = str(path).lower()
    return any(word in text for word in RELEVANT_WORDS)

def read_json_preview(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as f:
            obj = json.load(f)

        if isinstance(obj, dict):
            return {
                "format": "json",
                "top_level_type": "object",
                "top_level_keys": list(obj.keys())[:100],
            }

        if isinstance(obj, list):
            first = obj[0] if obj else None
            return {
                "format": "json",
                "top_level_type": "array",
                "array_length": len(obj),
                "first_item_type": type(first).__name__,
                "first_item_keys": (
                    list(first.keys())[:100]
                    if isinstance(first, dict) else []
                ),
            }

        return {
            "format": "json",
            "top_level_type": type(obj).__name__,
        }
    except Exception as exc:
        return {"format": "json", "read_error": str(exc)}

def read_jsonl_preview(path: Path) -> dict[str, Any]:
    preview = []
    line_count = 0
    malformed = []

    try:
        with path.open("r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                if not line.strip():
                    continue

                line_count += 1

                if len(preview) < 3:
                    try:
                        obj = json.loads(line)
                        preview.append({
                            "type": type(obj).__name__,
                            "keys": (
                                list(obj.keys())[:100]
                                if isinstance(obj, dict) else []
                            ),
                        })
                    except Exception as exc:
                        malformed.append({
                            "line": line_no,
                            "error": str(exc),
                        })

                elif line_count <= 100000:
                    try:
                        json.loads(line)
                    except Exception as exc:
                        if len(malformed) < 20:
                            malformed.append({
                                "line": line_no,
                                "error": str(exc),
                            })

        return {
            "format": "jsonl",
            "nonempty_line_count": line_count,
            "first_records": preview,
            "malformed_samples": malformed,
        }
    except Exception as exc:
        return {"format": "jsonl", "read_error": str(exc)}

def read_csv_preview(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
            samples = []

            for row in reader:
                if len(samples) >= 3:
                    break
                samples.append({
                    key: value[:200] if isinstance(value, str) else value
                    for key, value in row.items()
                })

        return {
            "format": "csv",
            "headers": headers,
            "sample_rows": samples,
        }
    except Exception as exc:
        return {"format": "csv", "read_error": str(exc)}

def inspect_file(path: Path) -> dict[str, Any]:
    item: dict[str, Any] = {
        "path": str(path.relative_to(REPO_ROOT)),
        "size_bytes": path.stat().st_size,
        "suffix": path.suffix.lower(),
    }

    suffix = path.suffix.lower()

    if suffix == ".json":
        item["preview"] = read_json_preview(path)
    elif suffix == ".jsonl":
        item["preview"] = read_jsonl_preview(path)
    elif suffix == ".csv":
        item["preview"] = read_csv_preview(path)
    elif suffix in {".py", ".ps1", ".sh"}:
        item["preview"] = {"format": "source_code"}
    else:
        item["preview"] = {
            "format": "binary_or_unparsed",
            "note": "Không đọc nội dung nhị phân.",
        }

    return item

def main() -> int:
    if not REPO_ROOT.exists():
        raise FileNotFoundError(f"Repository root not found: {REPO_ROOT}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    matched_files = []
    matched_dirs = []
    errors = []

    for current_root, dirs, files in os.walk(REPO_ROOT):
        dirs[:] = [
            d for d in dirs
            if d not in SKIP_DIRS and not d.startswith(".")
        ]

        current = Path(current_root)

        if is_relevant(current):
            matched_dirs.append(
                str(current.relative_to(REPO_ROOT))
            )

        for filename in files:
            path = current / filename
            suffix = path.suffix.lower()

            if suffix not in DATA_EXTENSIONS | SCRIPT_EXTENSIONS:
                continue

            if not is_relevant(path):
                continue

            try:
                matched_files.append(inspect_file(path))
            except Exception as exc:
                errors.append({
                    "path": str(path),
                    "error": str(exc),
                })

    matched_files.sort(key=lambda x: x["path"].lower())
    matched_dirs = sorted(set(matched_dirs))

    extension_counts = Counter(
        Path(item["path"]).suffix.lower()
        for item in matched_files
    )

    result = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repository_root": str(REPO_ROOT),
        "manual_root": str(MANUAL_ROOT),
        "matched_directory_count": len(matched_dirs),
        "matched_file_count": len(matched_files),
        "extension_counts": dict(extension_counts),
        "directories": matched_dirs,
        "files": matched_files,
        "errors": errors,
        "warning": (
            "Inventory chỉ tìm file theo tên/path liên quan. "
            "Không khẳng định mọi checkpoint hoặc prediction đều đã được tìm thấy."
        ),
    }

    json_path = OUTPUT_DIR / "student_capability_input_inventory.json"
    md_path = OUTPUT_DIR / "student_capability_input_inventory.md"

    json_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = [
        "# Student Capability Input Inventory — 2026-11-17",
        "",
        f"- Repository: `{REPO_ROOT}`",
        f"- Matched directories: {len(matched_dirs)}",
        f"- Matched files: {len(matched_files)}",
        f"- Errors: {len(errors)}",
        "",
        "## Directories",
        "",
    ]

    lines.extend(f"- `{path}`" for path in matched_dirs)

    lines.extend(["", "## Files", ""])

    for item in matched_files:
        lines.append(
            f"### `{item['path']}`"
        )
        lines.append(f"- Size: {item['size_bytes']} bytes")
        lines.append(
            "```json\n"
            + json.dumps(
                item.get("preview", {}),
                ensure_ascii=False,
                indent=2,
            )
            + "\n```"
        )
        lines.append("")

    if errors:
        lines.extend(["## Read errors", ""])
        for error in errors:
            lines.append(f"- `{error['path']}`: {error['error']}")

    md_path.write_text("\n".join(lines), encoding="utf-8")

    print("INVENTORY_STATUS: PASS")
    print(f"REPOSITORY: {REPO_ROOT}")
    print(f"DIRECTORIES: {len(matched_dirs)}")
    print(f"FILES: {len(matched_files)}")
    print(f"ERRORS: {len(errors)}")
    print(f"JSON: {json_path}")
    print(f"MARKDOWN: {md_path}")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())

