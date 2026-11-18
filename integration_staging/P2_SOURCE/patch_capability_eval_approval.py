from pathlib import Path

path = Path("scripts/capability_eval.py")
source = path.read_text(encoding="utf-8")

old = '''        if review_status != "APPROVED_NO_LABEL_CHANGE":
            raise ValueError(
                f"Gold review status is not approved: "
                f"{problem_id}={review_status!r}"
            )
'''

new = '''        approved_review_statuses = {
            "APPROVED_NO_LABEL_CHANGE",
            "APPROVED_WITH_SOURCE_CLARIFICATION",
        }

        if review_status not in approved_review_statuses:
            raise ValueError(
                f"Gold review status is not approved: "
                f"{problem_id}={review_status!r}"
            )
'''

if source.count(old) != 1:
    raise SystemExit(
        "PATCH_ABORTED: expected approval validation block exactly once; "
        f"found {source.count(old)}"
    )

source = source.replace(old, new, 1)
path.write_text(source, encoding="utf-8")

print("PATCH_PASS: approval allowlist updated")
print("Accepted statuses:")
print(" - APPROVED_NO_LABEL_CHANGE")
print(" - APPROVED_WITH_SOURCE_CLARIFICATION")
