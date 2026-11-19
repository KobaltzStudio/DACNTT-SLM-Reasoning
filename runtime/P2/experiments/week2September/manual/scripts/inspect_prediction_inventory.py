import json
from pathlib import Path

manual = Path(r"C:\Users\PC - NGHI\Desktop\Pipeline\P2\experiments\week2September\manual")
stage = manual / "integration_staging" / "P1"

files = [
    stage / "reports" / "capability" / "student_eval_2026-11-17" / "checkpoint_prediction_inventory.json",
    stage / "reports" / "learning_curve" / "2026-11-17" / "B4_seed13_checkpoint_inventory.json",
]

def show_prediction_fields(obj, prefix=""):
    if isinstance(obj, dict):
        for key, value in obj.items():
            path = f"{prefix}.{key}" if prefix else key
            if "prediction" in key.lower():
                print(f"  {path} = {value}")
            if isinstance(value, (dict, list)):
                show_prediction_fields(value, path)
    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            show_prediction_fields(value, f"{prefix}[{i}]")

for file in files:
    print("\n" + "=" * 90)
    print("FILE:", file)
    print("EXISTS:", file.exists())
    if not file.exists():
        continue

    data = json.loads(file.read_text(encoding="utf-8-sig"))
    print("TOP_LEVEL_KEYS:", list(data.keys()) if isinstance(data, dict) else type(data).__name__)

    print("\nPREDICTION-RELATED FIELDS:")
    show_prediction_fields(data)

    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, list) and value and isinstance(value[0], dict):
                if any("checkpoint" in x for x in value):
                    print(f"\nCHECKPOINT RECORDS IN: {key}")
                    for item in value:
                        if "checkpoint" not in item:
                            continue
                        print({
                            k: v for k, v in item.items()
                            if any(t in k.lower() for t in (
                                "checkpoint", "method", "seed", "round",
                                "prediction", "eval", "split"
                            ))
                        })

print("\nINSPECTION_COMPLETE")
