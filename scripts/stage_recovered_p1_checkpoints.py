from pathlib import Path
import hashlib
import shutil
import sys

SOURCE = Path(
    r"C:\Users\PC - NGHI\Desktop\KLTN\New folder\DACNTT-SLM-Reasoning"
    r"\experiments\week2September\manual\models\task7\B4\seed_13"
)

DESTINATION = Path(
    r"C:\Users\PC - NGHI\Desktop\Pipeline\P2\integration_staging\P1"
    r"\models\task7\B4\seed_13"
)

EXPECTED = {
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
    if DESTINATION.exists():
        raise FileExistsError(
            f"Destination already exists; refusing to overwrite: {DESTINATION}"
        )

    # Validate all sources before copying any checkpoint.
    for name, expected_hash in EXPECTED.items():
        source_dir = SOURCE / name
        weights = source_dir / "adapter_model.safetensors"
        config = source_dir / "adapter_config.json"

        if not source_dir.is_dir():
            raise FileNotFoundError(source_dir)

        if not weights.is_file():
            raise FileNotFoundError(weights)

        if not config.is_file():
            raise FileNotFoundError(config)

        actual_hash = sha256(weights)
        if actual_hash != expected_hash:
            raise RuntimeError(
                f"Source hash mismatch for {name}: {actual_hash}"
            )

    DESTINATION.mkdir(parents=True, exist_ok=False)

    copied = []

    try:
        for name in EXPECTED:
            source_dir = SOURCE / name
            target_dir = DESTINATION / name

            shutil.copytree(source_dir, target_dir)
            copied.append(name)

            source_hash = sha256(
                source_dir / "adapter_model.safetensors"
            )
            target_hash = sha256(
                target_dir / "adapter_model.safetensors"
            )

            if source_hash != target_hash:
                raise RuntimeError(
                    f"Post-copy hash mismatch for {name}"
                )

            print("COPIED:", name)
            print("SHA256:", target_hash)
            print("POST_COPY_VERIFY: PASS")

    except Exception:
        print("COPY_FAILED; partial destination retained for inspection.")
        raise

    print("\nP1_CHECKPOINT_STAGING: PASS")
    print("DESTINATION:", DESTINATION)
    print("CHECKPOINTS_COPIED:", len(copied))

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("P1_CHECKPOINT_STAGING: FAIL")
        print(type(exc).__name__ + ":", exc)
        sys.exit(1)
