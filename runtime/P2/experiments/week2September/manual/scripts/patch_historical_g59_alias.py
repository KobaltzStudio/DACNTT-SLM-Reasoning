from pathlib import Path
import shutil

root = Path(__file__).resolve().parent.parent
target = root / "scripts" / "run_historical_g59_batch.py"
backup = target.with_name(
    target.name + ".pre_alias_fix_20261117.bak"
)

old = '''    marker_command = marker.get("command", "")
    if not marker_command or "--split dev" not in marker_command:
        raise ValueError(
            f"{run_name} S{round_no}: marker lacks dev evaluation command"
        )
'''

new = '''    marker_command = marker.get("command")
    reused_from = marker.get("reused_from")

    # B4 S1 is a declared alias of B5 S1 for the same seed.
    # Its marker records reuse provenance instead of an evaluation command.
    if method == "B4" and round_no == 1:
        if not isinstance(reused_from, str) or not reused_from.strip():
            raise ValueError(
                f"{run_name} S{round_no}: expected B5 S1 alias marker"
            )

        normalized_source = reused_from.strip().replace(chr(92), "/").rstrip("/")
        expected_suffix = f"B5_seed{seed}/S1"

        if not normalized_source.endswith(expected_suffix):
            raise ValueError(
                f"{run_name} S{round_no}: alias target is not "
                f"the matching B5 seed S1: {reused_from}"
            )

        if not isinstance(marker.get("reason"), str) or not marker["reason"].strip():
            raise ValueError(
                f"{run_name} S{round_no}: alias marker lacks reason"
            )

        if marker_command:
            raise ValueError(
                f"{run_name} S{round_no}: alias marker unexpectedly "
                "contains a command"
            )

    else:
        if reused_from:
            raise ValueError(
                f"{run_name} S{round_no}: unexpected evaluation alias"
            )

        if (
            not isinstance(marker_command, str)
            or (
                "--split dev" not in marker_command
                and "--split=dev" not in marker_command
            )
        ):
            raise ValueError(
                f"{run_name} S{round_no}: marker lacks dev evaluation command"
            )
'''

if not target.is_file():
    raise FileNotFoundError(target)

source = target.read_text(encoding="utf-8")
count = source.count(old)

if count != 1:
    raise RuntimeError(
        f"PATCH_ABORTED: expected exactly one target block, found {count}"
    )

if backup.exists():
    raise FileExistsError(
        f"Refusing to overwrite backup: {backup}"
    )

shutil.copy2(target, backup)
updated = source.replace(old, new, 1)
target.write_text(updated, encoding="utf-8", newline="\n")

check = target.read_text(encoding="utf-8")
if check.count(new) != 1 or old in check:
    shutil.copy2(backup, target)
    raise RuntimeError(
        "PATCH_VERIFY_FAILED: original file restored from backup"
    )

print("PATCH_STATUS=PASS")
print(f"PATCHED_FILE={target}")
print(f"BACKUP_FILE={backup}")
print("PATCH_REPLACEMENTS=1")