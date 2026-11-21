from pathlib import Path

path = Path("scripts/test_capability_eval.py")
source = path.read_text(encoding="utf-8")

old = '''        rows = list(csv.DictReader(
            self.approval_path.open(
                "r", encoding="utf-8-sig", newline=""
            )
        ))
'''

new = '''        with self.approval_path.open(
            "r", encoding="utf-8-sig", newline=""
        ) as stream:
            rows = list(csv.DictReader(stream))
'''

count = source.count(old)

if count != 2:
    raise SystemExit(
        f"PATCH_ABORTED: expected exactly 2 occurrences, found {count}"
    )

backup = path.with_name("test_capability_eval.py.pre_resource_fix")
if backup.exists():
    raise SystemExit(f"BACKUP_ALREADY_EXISTS: {backup}")

backup.write_text(source, encoding="utf-8")
path.write_text(source.replace(old, new), encoding="utf-8")

print("RESOURCE_WARNING_FIX: PASS")
print(f"Backup: {backup}")
print("Replaced occurrences:", count)
