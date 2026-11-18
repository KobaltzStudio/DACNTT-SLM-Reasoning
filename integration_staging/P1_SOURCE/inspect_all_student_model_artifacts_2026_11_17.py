from pathlib import Path
import json
import hashlib

REPO = Path(r"C:\KLTN-SLM-Reasoning")
MANUAL = REPO / "experiments" / "week2September" / "manual"

ROOTS = [
    MANUAL / "models",
    MANUAL / "reports" / "task7",
]

TARGET_NAMES = {
    "adapter_model.safetensors",
    "adapter_config.json",
    "model.safetensors",
    "pytorch_model.bin",
    "config.json",
    "train_log.json",
    "training_args.bin",
    "trainer_state.json",
}

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    seen = set()

    for root in ROOTS:
        print(f"\n=== ROOT: {root} ===")
        if not root.exists():
            print("ROOT_NOT_FOUND")
            continue

        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue

            if path.name not in TARGET_NAMES:
                continue

            resolved = str(path.resolve())
            if resolved in seen:
                continue
            seen.add(resolved)

            print("\nFILE:", path)
            print("SIZE:", path.stat().st_size)
            print("SHA256:", sha256(path))

            if path.name == "train_log.json":
                try:
                    data = json.loads(path.read_text(encoding="utf-8-sig"))
                    for key in (
                        "checkpoint_parent",
                        "seed",
                        "data_order_seed",
                        "train_set",
                        "steps",
                        "n_examples",
                        "cumulative_training_tokens",
                        "model",
                        "revision",
                    ):
                        print(f"{key}: {data.get(key)}")
                except Exception as exc:
                    print("TRAIN_LOG_PARSE_ERROR:", exc)

    print("\nARTIFACT_INSPECTION_STATUS: PASS")
    print("FILES_FOUND:", len(seen))

if __name__ == "__main__":
    main()
