from pathlib import Path
from datetime import datetime
import sys

path = Path(r"scripts/p1p2_controller.py")
source = path.read_text(encoding="utf-8")

old_sidecar = 'self.s0_sidecar = self.root / "reports/p1p2_integration/capability_sidecars/SHARED_seed0_S0"'
new_sidecar = 'self.s0_sidecar = self.root / "reports/capability/g5_9_real_data_s0/SHARED_seed0_S0"'

old_p2 = '''        if train.is_file() and log.is_file():
            if not self.resume and not self.dry_run and round_no != 1:
                raise FileExistsError(f"P1 selection artifacts already exist; use --resume: {out_dir}")
            data = read_json(train)'''

new_p2 = '''        if train.is_file() and log.is_file():
            if not (self.resume or self.dry_run):
                raise FileExistsError(
                    f"Existing P2 selection artifacts require --resume: {out_dir}"
                )
            data = read_json(train)'''

if source.count(old_sidecar) != 1:
    raise SystemExit(
        "PATCH_ABORTED: Expected exactly one old S0 sidecar path; source unchanged."
    )

if source.count(old_p2) != 1:
    raise SystemExit(
        "PATCH_ABORTED: Expected exactly one old P2 selection block; source unchanged."
    )

backup = path.with_name(
    f"p1p2_controller.py.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
)
backup.write_bytes(path.read_bytes())

updated = source.replace(old_sidecar, new_sidecar)
updated = updated.replace(old_p2, new_p2)

compile(updated, str(path), "exec")
path.write_text(updated, encoding="utf-8", newline="\n")

compile(path.read_text(encoding="utf-8"), str(path), "exec")

print("CONTROLLER_PATCH=PASS")
print(f"BACKUP={backup}")
print("S0_SIDECAR_PATH=reports/capability/g5_9_real_data_s0/SHARED_seed0_S0")
print("P2_EXISTING_SELECTION_POLICY=RESUME_REQUIRED")
print("PYTHON_SYNTAX=PASS")
