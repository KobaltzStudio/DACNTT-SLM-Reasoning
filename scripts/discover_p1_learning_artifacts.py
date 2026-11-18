from pathlib import Path
import csv

ROOTS = [
    Path(r"C:\Users\PC - NGHI\Desktop\KLTN\New folder\DACNTT-SLM-Reasoning"),
    Path(r"C:\Users\PC - NGHI\Desktop\AI_Generate_Images\KLTN-SLM-Reasoning"),
    Path(r"C:\Users\PC - NGHI\Desktop\task4\Proposal1\DACNTT-SLM-Reasoning"),
    Path(r"C:\Users\PC - NGHI\Desktop\Pipeline\P2"),
]

TARGET_NAMES = {
    "B4_seed13_checkpoint_inventory.json",
    "build_checkpoint_inventory.py",
    "build_learning_dynamics_manifest.py",
    "build_student_learning_dynamics_report.py",
    "build_capability_learning_curves.py",
    "train_log.json",
}

OUTPUT = Path(
    r"C:\Users\PC - NGHI\Desktop\Pipeline\P2"
    r"\reports\p1p2_integration\p1_artifact_discovery.csv"
)

def main():
    rows = []

    for root in ROOTS:
        print("\nSEARCH_ROOT:", root)

        if not root.is_dir():
            print("ROOT_NOT_FOUND")
            continue

        for path in root.rglob("*"):
            if not path.is_file():
                continue

            if path.name not in TARGET_NAMES:
                continue

            try:
                size = path.stat().st_size
            except OSError:
                size = -1

            row = {
                "root": str(root),
                "file": str(path),
                "name": path.name,
                "bytes": size,
            }
            rows.append(row)

            print("FOUND:", path)
            print("BYTES:", size)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["root", "file", "name", "bytes"],
        )
        writer.writeheader()
        writer.writerows(rows)

    print("\nDISCOVERY_COMPLETE")
    print("FILES_FOUND:", len(rows))
    print("REPORT:", OUTPUT)

if __name__ == "__main__":
    main()
