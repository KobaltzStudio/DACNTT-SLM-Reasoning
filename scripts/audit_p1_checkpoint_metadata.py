from pathlib import Path
import hashlib
import json
import sys

BASE = Path(
    r"C:\Users\PC - NGHI\Desktop\Pipeline\P2"
    r"\integration_staging\P1\models\task7\B4\seed_13"
)

EXPECTED_BASE = "Qwen/Qwen2.5-1.5B-Instruct"
EXPECTED_REVISION = "989aa7980e4cf806f80c7fef2b1adb7bc71aa306"

EXPECTED_HASHES = {
    "student_ckpt_001":
        "8f50d3ab6772c7c01d0c244fd661348a0f61164916cf5396d4f916d7c38c6398",
    "student_ckpt_002":
        "759ea14d7a3953b609a70b06b14515d2b309ee209f00843bff6d70c8508a71fc",
    "student_ckpt_003":
        "22d99c60743ed2897586ff22601ff7e8491dbf6495bbac8e0edd5c88880b7106",
}

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().lower()

def main():
    all_pass = True

    for name, expected_hash in EXPECTED_HASHES.items():
        folder = BASE / name
        config_path = folder / "adapter_config.json"
        weights_path = folder / "adapter_model.safetensors"
        log_path = folder / "train_log.json"

        print("\nCHECKPOINT:", name)

        config = json.loads(config_path.read_text(encoding="utf-8"))
        actual_hash = sha256(weights_path)

        checks = {
            "weights_hash": actual_hash == expected_hash,
            "base_model": config.get("base_model_name_or_path") == EXPECTED_BASE,
            "lora_rank": config.get("r") == 16,
            "lora_alpha": config.get("lora_alpha") == 32,
            "target_modules_count": (
                isinstance(config.get("target_modules"), list)
                and len(config["target_modules"]) == 7
            ),
        }

        for key, value in checks.items():
            print(f"{key.upper()}:", value)
            if not value:
                all_pass = False

        print("CONFIG_REVISION:", config.get("revision"))
        print("CONFIG_INFERENCE_MODE:", config.get("inference_mode"))
        print("CONFIG_PEFT_TYPE:", config.get("peft_type"))
        print("CONFIG_TASK_TYPE:", config.get("task_type"))

        if log_path.is_file():
            try:
                log = json.loads(log_path.read_text(encoding="utf-8"))
                print("TRAIN_LOG_JSON_VALID:", True)
                print("TRAIN_LOG_TOP_LEVEL_TYPE:", type(log).__name__)

                if isinstance(log, dict):
                    print("TRAIN_LOG_KEYS:", sorted(log.keys()))
                elif isinstance(log, list):
                    print("TRAIN_LOG_RECORDS:", len(log))
            except Exception as exc:
                print("TRAIN_LOG_JSON_VALID:", False)
                print("TRAIN_LOG_ERROR:", repr(exc))
                all_pass = False
        else:
            print("TRAIN_LOG_MISSING")
            all_pass = False

    print("\nMETADATA_STRUCTURE_AUDIT:",
          "PASS" if all_pass else "REVIEW_REQUIRED")

    if not all_pass:
        sys.exit(1)

if __name__ == "__main__":
    main()
