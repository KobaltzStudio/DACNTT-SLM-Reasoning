from pathlib import Path
import csv
import re
import zipfile

P2 = Path(r"C:\Users\PC - NGHI\Desktop\Pipeline\P2")
MANUAL = P2 / "experiments/week2September/manual"

OUT = MANUAL / "reports/p1p2_integration/checkpoint_inventory_audit"
OUT.mkdir(parents=True, exist_ok=True)

ALL_CSV = OUT / "archive_member_inventory.csv"
RELEVANT_CSV = OUT / "archive_relevant_members.csv"
SUMMARY_CSV = OUT / "archive_summary.csv"

SKIP_PARTS = {
    ".venv",
    "__pycache__",
    "site-packages",
    "node_modules",
}

RELEVANT_PATTERN = re.compile(
    r"eval_student"
    r"|prediction"
    r"|adapter_model"
    r"|student_ckpt"
    r"|train_log"
    r"|checkpoint"
    r"|\.done"
    r"|eval_dev"
    r"|capability"
    r"|manifest"
    r"|lineage",
    re.IGNORECASE,
)

def should_skip(path: Path) -> bool:
    return any(part.lower() in SKIP_PARTS for part in path.parts)

def write_csv(path, rows, fields):
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

archives = sorted(
    p for p in P2.rglob("*.zip")
    if p.is_file() and not should_skip(p)
)

all_members = []
relevant_members = []
summaries = []

for archive in archives:
    summary = {
        "archive_path": str(archive),
        "archive_size_bytes": archive.stat().st_size,
        "status": "OK",
        "member_count": 0,
        "file_count": 0,
        "relevant_count": 0,
        "nested_archive_count": 0,
        "error": "",
    }

    try:
        with zipfile.ZipFile(archive, "r") as zf:
            infos = zf.infolist()
            summary["member_count"] = len(infos)

            for info in infos:
                if info.is_dir():
                    continue

                name = info.filename.replace("\\", "/")
                lower_name = name.lower()

                row = {
                    "archive_path": str(archive),
                    "member_path": name,
                    "size_bytes": info.file_size,
                    "compressed_size_bytes": info.compress_size,
                    "crc": f"{info.CRC:08x}",
                    "is_nested_archive": lower_name.endswith(
                        (".zip", ".7z", ".tar", ".gz")
                    ),
                }

                all_members.append(row)
                summary["file_count"] += 1

                if row["is_nested_archive"]:
                    summary["nested_archive_count"] += 1

                if RELEVANT_PATTERN.search(name):
                    relevant_members.append(row)
                    summary["relevant_count"] += 1

    except Exception as exc:
        summary["status"] = "ERROR"
        summary["error"] = repr(exc)

    summaries.append(summary)

write_csv(
    ALL_CSV,
    all_members,
    [
        "archive_path",
        "member_path",
        "size_bytes",
        "compressed_size_bytes",
        "crc",
        "is_nested_archive",
    ],
)

write_csv(
    RELEVANT_CSV,
    relevant_members,
    [
        "archive_path",
        "member_path",
        "size_bytes",
        "compressed_size_bytes",
        "crc",
        "is_nested_archive",
    ],
)

write_csv(
    SUMMARY_CSV,
    summaries,
    [
        "archive_path",
        "archive_size_bytes",
        "status",
        "member_count",
        "file_count",
        "relevant_count",
        "nested_archive_count",
        "error",
    ],
)

print("ARCHIVE_AUDIT=CREATED")
print(f"ARCHIVE_COUNT={len(archives)}")
print(f"ARCHIVE_MEMBER_COUNT={len(all_members)}")
print(f"RELEVANT_MEMBER_COUNT={len(relevant_members)}")
print(f"ARCHIVE_ERRORS={sum(x['status'] != 'OK' for x in summaries)}")
print(f"ALL_MEMBERS={ALL_CSV}")
print(f"RELEVANT_MEMBERS={RELEVANT_CSV}")
print(f"SUMMARY={SUMMARY_CSV}")
