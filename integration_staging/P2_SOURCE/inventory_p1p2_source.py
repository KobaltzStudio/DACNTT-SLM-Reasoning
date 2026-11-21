from pathlib import Path
import hashlib

ROOT = Path(r"C:\Users\PC - NGHI\Desktop\Pipeline\P2")
MANUAL = ROOT / "experiments" / "week2September" / "manual"
OUT = MANUAL / "reports" / "p1p2_integration" / "local_rebuild" / "source_inventory.txt"

TARGET_NAMES = {
    "run_experiment.py",
    "select_round.py",
    "train_round.py",
    "student_common.py",
    "capability_eval.py",
    "experiment_config.json",
}

EXCLUDE = {
    ".git", ".venv", "__pycache__", "node_modules",
    "integration_staging", "runs", "models",
    "checkpoints", "outputs",
}

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

lines = []

for path in sorted(ROOT.rglob("*")):
    if not path.is_file():
        continue

    if any(part in EXCLUDE for part in path.parts):
        continue

    if path.name not in TARGET_NAMES:
        continue

    try:
        lines.append(
            f"FILE={path}\n"
            f"SIZE={path.stat().st_size}\n"
            f"SHA256={sha256(path)}\n"
        )
    except Exception as exc:
        lines.append(f"ERROR={path}: {exc}\n")

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(lines), encoding="utf-8")

print("\n".join(lines))
print(f"\nINVENTORY_SAVED={OUT}")
