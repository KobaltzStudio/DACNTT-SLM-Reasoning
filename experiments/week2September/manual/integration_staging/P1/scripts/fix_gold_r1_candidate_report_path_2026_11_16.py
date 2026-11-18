from pathlib import Path
import shutil

REPORT = (
    Path(r"C:\KLTN-SLM-Reasoning")
    / "experiments/week2September/manual/reports/gold/review_2026-11-16"
    / "gold_review_63_final_adjudication.md"
)

PARENT = (
    r"C:\KLTN-SLM-Reasoning\experiments\week2September\manual\data"
    r"\gold_vnext_candidate_2026-11-16"
)

R1 = (
    r"C:\KLTN-SLM-Reasoning\experiments\week2September\manual\data"
    r"\gold_vnext_candidate_2026-11-16_r1"
)


def main():
    if not REPORT.is_file():
        raise FileNotFoundError(REPORT)

    content = REPORT.read_text(encoding="utf-8")
    lines = content.splitlines()

    matches = [
        i for i, line in enumerate(lines)
        if line.lstrip().startswith("- Candidate directory:")
        and "gold_vnext_candidate_2026-11-16" in line
        and "gold_vnext_candidate_2026-11-16_r1" not in line
    ]

    if len(matches) != 1:
        print("REPORT WAS NOT MODIFIED.")
        print("Matching parent candidate lines:", len(matches))
        print("Candidate-related lines:")
        for line in lines:
            if "Candidate" in line or "gold_vnext_candidate" in line:
                print(repr(line))
        raise RuntimeError(
            "Expected exactly one parent Candidate directory line. "
            "Inspect the report before making any change."
        )

    backup = REPORT.with_suffix(".md.pre_r1_path_fix.bak")

    if backup.exists():
        raise FileExistsError(
            f"Backup already exists. Inspect it first: {backup}"
        )

    index = matches[0]

    replacement = [
        "- Parent candidate directory: `" + PARENT + "`",
        "- Release candidate directory: `" + R1 + "`",
        "- Candidate version: `vNext-candidate-2026-11-16-r1`",
    ]

    shutil.copy2(REPORT, backup)
    lines[index:index + 1] = replacement

    REPORT.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8"
    )

    updated = REPORT.read_text(encoding="utf-8")

    required = [
        "Parent candidate directory:",
        "Release candidate directory:",
        "vNext-candidate-2026-11-16-r1",
        "Freeze status: **NOT FROZEN**",
    ]

    missing = [item for item in required if item not in updated]

    if missing:
        shutil.copy2(backup, REPORT)
        raise RuntimeError(
            f"Post-check failed. Original report restored. Missing: {missing}"
        )

    print("REPORT PATH CORRECTION: PASS")
    print("Report:", REPORT)
    print("Backup:", backup)
    print("Parent and release candidate paths are distinguished.")
    print("Freeze status remains NOT FROZEN.")


if __name__ == "__main__":
    main()
