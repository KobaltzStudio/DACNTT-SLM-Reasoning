from pathlib import Path
import hashlib
import json
import sys

P1_ROOT = Path(r"C:\Users\PC - NGHI\Desktop\Pipeline\P1")

CHECKPOINT_ROOT = Path(
    r"C:\Users\PC - NGHI\Desktop\Pipeline\P2"
    r"\integration_staging\P1\models\task7\B4\seed_13"
)

EXPECTED = {
    "student_ckpt_001": {
        "round": 0,
        "sha256": "614816f15b980f9958dd1747a3c0773171d8112ad167e116b7a7651d9623a006",
    },
    "student_ckpt_002": {
        "round": 1,
        "sha256": "cb82cb58ed58a92a8fd0dd33b09322e99191ecd048daf63a36b5ea4182898e1a",
    },
    "student_ckpt_003": {
        "round": 2,
        "sha256": "f16cb78cbdaf4ce5280d79c552adab5ec57f56ca26a3796b02995f0de2441e0e",
    },
}

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    all_pass = True

    for checkpoint, expected in EXPECTED.items():
        log_path = CHECKPOINT_ROOT / checkpoint / "train_log.json"

        print(f"\n=== {checkpoint} ===")

        if not log_path.is_file():
            print("TRAIN_LOG_MISSING:", log_path)
            all_pass = False
            continue

        log = json.loads(log_path.read_text(encoding="utf-8"))

        expected_round = expected["round"]
        expected_sha = expected["sha256"]

        train_set_name = f"round_{expected_round:03d}"
        matches = []

        for path in P1_ROOT.rglob("train_set.json"):
            if train_set_name not in str(path.parent):
                continue
            if "task7" not in str(path).lower():
                continue
            if "b4" not in str(path).lower():
                continue
            if "seed_13" not in str(path).lower():
                continue
            matches.append(path)

        if len(matches) != 1:
            print("TRAIN_SET_MATCH_COUNT:", len(matches))
            for path in matches:
                print("CANDIDATE:", path)
            all_pass = False
            continue

        train_set = matches[0]
        actual_sha = sha256(train_set)

        checks = {
            "log_train_set_sha_matches_expected":
                log.get("train_set_sha256") == expected_sha,
            "actual_train_set_sha_matches_expected":
                actual_sha == expected_sha,
            "log_seed_is_13":
                log.get("seed") == 13,
            "log_pool_sha_matches_frozen_pool":
                log.get("pool_sha256") ==
                "95f34cff848bfbd16305e5f0ecc2656525dc1e319ca2b1a404f9b75c8029cd04",
            "log_round_examples_positive":
                isinstance(log.get("n_examples"), int) and
                log["n_examples"] > 0,
            "log_steps_is_24":
                log.get("steps") == 24,
        }

        print("TRAIN_SET:", train_set)
        print("EXPECTED_SHA256:", expected_sha)
        print("ACTUAL_SHA256:", actual_sha)

        for name, passed in checks.items():
            print(f"{name.upper()}: {passed}")
            if not passed:
                all_pass = False

    print(
        "\nB4_SEED13_TRAINSET_LINEAGE:",
        "PASS" if all_pass else "REVIEW_REQUIRED"
    )

    if not all_pass:
        sys.exit(1)

if __name__ == "__main__":
    main()
