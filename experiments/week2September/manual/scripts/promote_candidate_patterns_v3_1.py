import json
import re
import shutil
from datetime import datetime
from pathlib import Path

MANUAL = Path("experiments/week2September/manual")

CONFIG = MANUAL / "config/capability_rules_v3.1.json"

PATTERNS = {
    "multiplication": r"(?<!\w)\d+(?:\.\d+)?\s*%\s+of\b",
    "subtraction": (
        r"\bwhat\s+percentage\s+of\b[^.!?]*"
        r"\b(?:not|aren't|isn't|wasn't|weren't|doesn't|"
        r"don't|didn't|can't|cannot)\b"
    ),
}


def main():
    if not CONFIG.exists():
        raise FileNotFoundError(CONFIG)

    rules = json.loads(CONFIG.read_text(encoding="utf-8-sig"))

    if rules.get("schema_version") != "v3.1":
        raise ValueError("Expected v3.1 config.")

    # Validate candidate regexes before touching the config.
    for capability, pattern in PATTERNS.items():
        if capability not in rules["rules"]:
            raise KeyError(capability)

        re.compile(pattern, flags=re.IGNORECASE)

    backup_dir = MANUAL / "config/backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    backup_path = (
        backup_dir
        / f"capability_rules_v3.1_before_candidate_{timestamp}.json"
    )

    shutil.copy2(CONFIG, backup_path)

    added = []

    for capability, pattern in PATTERNS.items():
        existing = rules["rules"][capability].setdefault(
            "patterns",
            [],
        )

        if pattern not in existing:
            existing.append(pattern)
            added.append(capability)

    # Revalidate every configured regex.
    for capability, rule in rules["rules"].items():
        for pattern in rule.get("patterns", []):
            re.compile(pattern, flags=re.IGNORECASE)

        for pattern in rule.get("negative_patterns", []):
            re.compile(pattern, flags=re.IGNORECASE)

    CONFIG.write_text(
        json.dumps(rules, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("Promotion completed.")
    print("Backup:", backup_path)
    print("Updated config:", CONFIG)
    print("Added capabilities:", added)

    for capability in PATTERNS:
        print(
            capability,
            "pattern count:",
            len(rules["rules"][capability]["patterns"]),
        )


if __name__ == "__main__":
    main()
