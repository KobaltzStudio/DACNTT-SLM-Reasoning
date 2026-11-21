import copy
import json
import re
from pathlib import Path

RULES_V3 = Path(
    "experiments/week2September/manual/config/capability_rules_v3.json"
)

RULES_V31 = Path(
    "experiments/week2September/manual/config/capability_rules_v3.1.json"
)

DIVISION_NEGATIVE_PATTERN = (
    r"(?s)^(?=.*\bwhat percentage of\b)"
    r"(?=(?:.*?\b\d+(?:\.\d+)?\s*%){2})"
    r"(?=.*\bwhat percentage of\b[^.!?]*"
    r"\b(?:not|aren't|isn't|wasn't|weren't|doesn't|don't|didn't|can't|cannot)\b)"
    r".*$"
)

def main():
    if not RULES_V3.exists():
        raise FileNotFoundError(f"Missing source config: {RULES_V3}")

    source = json.loads(RULES_V3.read_text(encoding="utf-8-sig"))

    if source.get("schema_version") != "v3":
        raise ValueError(
            f"Expected schema_version=v3, got {source.get('schema_version')!r}"
        )

    if "division" not in source.get("rules", {}):
        raise ValueError("Missing rules.division")

    if r"\bwhat percentage of\b" not in source["rules"]["division"].get(
        "patterns", []
    ):
        raise ValueError(
            "Expected division positive pattern '\\bwhat percentage of\\b' "
            "was not found. Stop rather than patch an unexpected config."
        )

    updated = copy.deepcopy(source)
    updated["schema_version"] = "v3.1"

    division = updated["rules"]["division"]
    division["negative_patterns"] = [DIVISION_NEGATIVE_PATTERN]

    old_notes = division.get("notes", "")
    patch_note = (
        " v3.1 revision: suppress the broad part-to-whole division trigger "
        "only when a negation cue occurs inside the question clause after "
        "'what percentage of'; negation in preceding context does not suppress "
        "division."
    )

    if "v3.1 revision:" not in old_notes:
        division["notes"] = old_notes + patch_note

    # Validate all regex patterns before writing.
    for capability, rule in updated["rules"].items():
        for pattern in rule.get("patterns", []):
            re.compile(pattern, flags=re.IGNORECASE)
        for pattern in rule.get("negative_patterns", []):
            re.compile(pattern, flags=re.IGNORECASE)

    RULES_V31.parent.mkdir(parents=True, exist_ok=True)
    RULES_V31.write_text(
        json.dumps(updated, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # Verify that the source v3 file remains unchanged.
    source_after = json.loads(RULES_V3.read_text(encoding="utf-8-sig"))
    if source_after != source:
        raise RuntimeError("Source v3 unexpectedly changed.")

    # Verify the generated v3.1 file.
    generated = json.loads(RULES_V31.read_text(encoding="utf-8-sig"))

    if generated.get("schema_version") != "v3.1":
        raise RuntimeError("Generated schema version is incorrect.")

    if generated["rules"]["division"]["negative_patterns"] != [
        DIVISION_NEGATIVE_PATTERN
    ]:
        raise RuntimeError("Generated negative pattern does not match expected.")

    print("Created:", RULES_V31)
    print("schema_version:", generated["schema_version"])
    print(
        "division positive patterns:",
        len(generated["rules"]["division"]["patterns"]),
    )
    print(
        "division negative patterns:",
        len(generated["rules"]["division"]["negative_patterns"]),
    )
    print("Source v3 preserved: YES")
    print("Negative pattern updated: YES")

if __name__ == "__main__":
    main()
