from pathlib import Path

path = Path("scripts/finalize_gold_and_dev_split.py")
source = path.read_text(encoding="utf-8")

old = 'gold_supplement_85_approved_review\\.csv'
new = 'gold_supplement_85_approved_review.csv'

if source.count(old) != 2:
    raise SystemExit(
        "PATCH_ABORTED: expected exactly 2 malformed filename occurrences; "
        f"found {source.count(old)}"
    )

backup = path.with_name("finalize_gold_and_dev_split.py.pre_filename_fix")
if backup.exists():
    raise SystemExit(f"BACKUP_ALREADY_EXISTS: {backup}")

backup.write_text(source, encoding="utf-8")
path.write_text(source.replace(old, new), encoding="utf-8")

print("SCRIPT_FILENAME_FIX: PASS")
print("Backup:", backup)
