from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(
    r"C:\Users\PC - NGHI\Desktop\KLTN\New folder\DACNTT-SLM-Reasoning"
)

P2 = Path(r"C:\Users\PC - NGHI\Desktop\Pipeline\P2")

SOURCE = (
    ROOT
    / "experiments/week2September/manual/models/task7/B4/seed_13"
)

DESTINATION = P2 / "integration_staging/P1"

EXPECTED = {
    "student_ckpt_001": {
        "sha256": "8f50d3ab6772c7c01d0c244fd661348a0f61164916cf5396d4f916d7c38c6398",
        "round": 0,
    },
    "student_ckpt_002": {
        "sha256": "759ea14d7a3953b609a70b06b14515d2b309ee209f00843bff6d70c8508a71fc",
        "round": 1,
    },
    "student_ckpt_003": {
        "sha256": "22d99c60743ed2897586ff22601ff7e8491dbf6495bbac8e0edd5c88880b7106",
        "round": 2,
    },
}

REQUIRED_FILES = [
    "adapter_model.safetensors",
    "adapter_config.json",
]

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().lower()

def main():
    print("SOURCE:", SOURCE)
    print("DESTINATION:", DESTINATION)
    print("DESTINATION_EXISTS:", DESTINATION.exists())

    if not SOURCE.is_dir():
        raise FileNotFoundError(SOURCE)

    all_pass = True

    for name, expected in EXPECTED.items():
        folder = SOURCE / name
        print("\nCHECKPOINT:", name)
        print("FOLDER_EXISTS:", folder.is_dir())

        if not folder.is_dir():
            all_pass = False
            continue

        for filename in REQUIRED_FILES:
            path = folder / filename
            exists = path.is_file()
            print(f"{filename}_EXISTS:", exists)

            if not exists:
                all_pass = False

        weights = folder / "adapter_model.safetensors"

        if weights.is_file():
            actual_hash = sha256(weights)
            hash_ok = actual_hash == expected["sha256"]

            print("WEIGHTS_BYTES:", weights.stat().st_size)
            print("WEIGHTS_SHA256:", actual_hash)
            print("WEIGHTS_HASH_MATCH:", hash_ok)

            if not hash_ok:
                all_pass = False

        config = folder / "adapter_config.json"

        if config.is_file():
            try:
                data = json.loads(config.read_text(encoding="utf-8"))
                print("CONFIG_JSON_VALID:", True)
                print("CONFIG_KEYS:", sorted(data.keys()))
                print("BASE_MODEL_NAME_OR_PATH:",
                      data.get("base_model_name_or_path"))
                print("R:", data.get("r"))
                print("LORA_ALPHA:", data.get("lora_alpha"))
                print("TARGET_MODULES:", data.get("target_modules"))
            except Exception as exc:
                print("CONFIG_JSON_VALID:", False)
                print("CONFIG_ERROR:", repr(exc))
                all_pass = False

        print("EXPECTED_ROUND:", expected["round"])

        print("FILES:")
        for item in sorted(folder.iterdir()):
            if item.is_file():
                print(" ", item.name, item.stat().st_size, "bytes")
            elif item.is_dir():
                print(" ", item.name, "[directory]")

    print("\nDESTINATION_CHECK:")
    if DESTINATION.exists():
        target = DESTINATION / "models/task7/B4/seed_13"
        print("TARGET_EXISTS:", target.exists())

        for name in EXPECTED:
            existing = target / name
            print(name, "EXISTS:", existing.exists())
    else:
        print("P1_STAGING_DIRECTORY_NOT_CREATED")

    if all_pass:
        print("\nCHECKPOINT_SOURCE_AUDIT: PASS")
    else:
        print("\nCHECKPOINT_SOURCE_AUDIT: FAIL")
        sys.exit(1)

if __name__ == "__main__":
    main()
