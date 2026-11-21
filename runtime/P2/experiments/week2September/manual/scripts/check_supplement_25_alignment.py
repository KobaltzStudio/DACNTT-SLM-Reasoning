import json
from pathlib import Path

a1_path = Path("data/annotation/a1_supplement_agreement_25.jsonl")
a2_path = Path("data/annotation/a2_supplement_annotations.jsonl")

def load(path):
    with path.open("r", encoding="utf-8-sig") as f:
        return [json.loads(line) for line in f if line.strip()]

a1 = load(a1_path)
a2 = load(a2_path)

ids1 = [x["problem_id"] for x in a1]
ids2 = [x["problem_id"] for x in a2]

set1 = set(ids1)
set2 = set(ids2)

print("A1 records:", len(a1))
print("A2 records:", len(a2))
print("A1 unique IDs:", len(set1))
print("A2 unique IDs:", len(set2))
print("A1 duplicate IDs:", len(ids1) - len(set1))
print("A2 duplicate IDs:", len(ids2) - len(set2))
print("Missing in A2:", sorted(set1 - set2))
print("Unexpected in A2:", sorted(set2 - set1))

if (
    len(a1) == 25
    and len(a2) == 25
    and len(set1) == 25
    and len(set2) == 25
    and set1 == set2
):
    print("\nINDEPENDENT ALIGNMENT CHECK: PASS")
else:
    print("\nINDEPENDENT ALIGNMENT CHECK: FAIL")
