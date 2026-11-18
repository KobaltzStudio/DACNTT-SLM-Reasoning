from pathlib import Path
import json
import re
import hashlib

REPO = Path(r"C:\KLTN-SLM-Reasoning")
MANUAL = REPO / "experiments" / "week2September" / "manual"

EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
}

TRAINING_TERMS = [
    "Trainer(",
    "SFTTrainer(",
    "TrainingArguments(",
    "get_peft_model(",
    "PeftModel.from_pretrained",
    "from_pretrained(",
    "save_pretrained(",
    "checkpoint_parent",
    "train_set",
    "train_log.json",
    "adapter_model.safetensors",
    "gradient_accumulation_steps",
    "learning_rate",
    "num_train_epochs",
    "max_steps",
]

WEIGHT_NAMES = {
    "adapter_model.safetensors",
    "adapter_model.bin",
    "model.safetensors",
    "pytorch_model.bin",
}

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def should_skip(path):
    return any(part in EXCLUDE_DIRS for part in path.parts)

def inspect_python_files():
    print("\n" + "=" * 80)
    print("PYTHON TRAINING PIPELINE SEARCH")
    print("=" * 80)

    files = sorted(
        p for p in MANUAL.rglob("*.py")
        if p.is_file() and not should_skip(p)
    )

    matched_files = 0

    for path in files:
        try:
            lines = path.read_text(
                encoding="utf-8-sig"
            ).splitlines()
        except Exception as exc:
            print("READ_ERROR:", path, exc)
            continue

        matches = []

        for index, line in enumerate(lines, start=1):
            if any(term in line for term in TRAINING_TERMS):
                matches.append((index, line.strip()))

        if not matches:
            continue

        matched_files += 1
        print(f"\nFILE: {path}")
        print(f"TOTAL_LINES: {len(lines)}")
        print(f"MATCHES: {len(matches)}")

        for line_number, content in matches[:100]:
            print(f"  L{line_number}: {content[:300]}")

    print("\nPYTHON_FILES_SCANNED:", len(files))
    print("PYTHON_FILES_WITH_TRAINING_MATCHES:", matched_files)

def inspect_training_logs():
    print("\n" + "=" * 80)
    print("TRAIN LOG INVENTORY")
    print("=" * 80)

    logs = sorted(MANUAL.rglob("train_log.json"))

    for path in logs:
        if should_skip(path):
            continue

        print(f"\nTRAIN_LOG: {path}")

        try:
            data = json.loads(
                path.read_text(encoding="utf-8-sig")
            )
        except Exception as exc:
            print("JSON_ERROR:", exc)
            continue

        print("SHA256:", sha256(path))
        print("ALL_KEYS:", sorted(data.keys()))

        for key, value in data.items():
            if isinstance(value, (dict, list)):
                value = json.dumps(
                    value,
                    ensure_ascii=False
                )
            print(f"  {key}: {value}")

def inspect_model_weights():
    print("\n" + "=" * 80)
    print("MODEL WEIGHT INVENTORY")
    print("=" * 80)

    found = 0

    for path in sorted(MANUAL.rglob("*")):
        if not path.is_file() or should_skip(path):
            continue

        if path.name not in WEIGHT_NAMES:
            continue

        found += 1
        print(f"\nWEIGHT: {path}")
        print("SIZE:", path.stat().st_size)
        print("SHA256:", sha256(path))

    print("\nWEIGHT_FILES_FOUND:", found)

def inspect_round_directories():
    print("\n" + "=" * 80)
    print("ROUND / TRAIN SET INVENTORY")
    print("=" * 80)

    for path in sorted(MANUAL.rglob("*")):
        if not path.is_dir() or should_skip(path):
            continue

        if re.search(r"round[_-]?\d+|student_ckpt_\d+", path.name):
            print("DIRECTORY:", path)

    for path in sorted(MANUAL.rglob("*train_set*")):
        if not path.is_file() or should_skip(path):
            continue

        print(
            "TRAIN_SET:",
            path,
            "| SIZE:",
            path.stat().st_size
        )

def main():
    print("REPOSITORY:", REPO)
    print("MANUAL:", MANUAL)

    if not MANUAL.exists():
        raise SystemExit("MANUAL_DIRECTORY_NOT_FOUND")

    inspect_python_files()
    inspect_training_logs()
    inspect_model_weights()
    inspect_round_directories()

    print("\nPIPELINE_INSPECTION_STATUS: PASS")

if __name__ == "__main__":
    main()
