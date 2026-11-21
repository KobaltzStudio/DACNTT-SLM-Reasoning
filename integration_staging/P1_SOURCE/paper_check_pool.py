import json
from pathlib import Path
from collections import Counter

pool_path = Path("trajectory/pool/pool_v1_verified.jsonl")
rows = [json.loads(x) for x in pool_path.read_text(encoding="utf-8").splitlines() if x.strip()]

ids = [r["trajectory_id"] for r in rows]
problems = {r["problem_id"] for r in rows}
status = Counter(r["metadata"]["verification_status"] for r in rows)

print("Trajectory count:", len(rows))
print("Unique trajectory IDs:", len(set(ids)))
print("Unique problem IDs:", len(problems))
print("Verification status:", dict(status))
print("Mean response tokens from metadata:",
      sum(r["metadata"].get("token_length", 0) for r in rows) / max(len(rows), 1))

assert len(rows) == 4353
assert len(set(ids)) == len(rows)
assert len(problems) == 1032
assert set(status) == {"valid"}
print("POOL CHECK: PASS")
