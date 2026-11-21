import importlib.util
import inspect
import json
from pathlib import Path

MANUAL = Path("experiments/week2September/manual")

RULES_PATH = MANUAL / "config/capability_rules_v3.1.json"
EXTRACTOR_PATH = MANUAL / "scripts/extract_capabilities_rule_based.py"

CAPABILITIES = [
    "addition",
    "subtraction",
    "multiplication",
    "division",
    "percentage",
    "fraction",
    "ratio",
]


def load_module(path):
    spec = importlib.util.spec_from_file_location(
        "extractor_rule_inspection",
        path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module: {path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    if not RULES_PATH.exists():
        raise FileNotFoundError(RULES_PATH)

    if not EXTRACTOR_PATH.exists():
        raise FileNotFoundError(EXTRACTOR_PATH)

    rules = json.loads(RULES_PATH.read_text(encoding="utf-8-sig"))
    module = load_module(EXTRACTOR_PATH)

    print("=" * 100)
    print("CONFIG:", RULES_PATH)
    print("SCHEMA VERSION:", rules.get("schema_version"))
    print("=" * 100)

    for capability in CAPABILITIES:
        rule = rules.get("rules", {}).get(capability)

        print("\n" + "=" * 100)
        print("CAPABILITY:", capability)

        if rule is None:
            print("RULE NOT FOUND")
            continue

        print("Description:", rule.get("description", ""))
        print("Notes:", rule.get("notes", ""))

        print("\nPOSITIVE PATTERNS:")
        for index, pattern in enumerate(rule.get("patterns", [])):
            print(f"  [{index}] {pattern}")

        print("\nNEGATIVE PATTERNS:")
        for index, pattern in enumerate(rule.get("negative_patterns", [])):
            print(f"  [{index}] {pattern}")

    print("\n" + "=" * 100)
    print("EXTRACTOR IMPLEMENTATION")
    print("=" * 100)

    for function_name in (
        "normalize_text",
        "compile_rules",
        "extract_capabilities",
    ):
        function = getattr(module, function_name, None)

        print("\n" + "-" * 100)
        print("FUNCTION:", function_name)

        if function is None:
            print("NOT FOUND")
            continue

        try:
            print(inspect.getsource(function))
        except (OSError, TypeError):
            print("Source code unavailable through inspect.")

    print("\nInspection completed. No files were modified.")


if __name__ == "__main__":
    main()
