"""Read-only ZIP, inventory and exact bytecode candidate approval list."""
import csv
import hashlib
import json
from pathlib import Path
import re
import stat
import subprocess
from zipfile import ZipFile

MANUAL = Path.cwd().resolve()
ROOT = MANUAL.parents[3]
HERE = Path(__file__).resolve().parent
PRIOR = MANUAL / "reports/p1p2_integration/final_validation/final_local_20261119_004529"
POST = MANUAL / "reports/p1p2_integration/final_validation/post_validation_20261119"
STAGE = Path("C:/Users/PC - NGHI/Desktop/Pipeline/p1p2_unified/runpod_package_20261119_004529")

def digest(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()

def rows(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def tracked(repo):
    return set(subprocess.check_output(["git", "--no-optional-locks", "ls-files", "-z", "--cached"],
                                      cwd=repo).decode("utf8").split("\0"))

def walk(p):
    for f in p.iterdir():
        if f in {PRIOR, HERE, STAGE.parent} or f.name in {".git", ".venv", "node_modules", ".codex", ".agents"}:
            continue
        if f.is_symlink() or getattr(f.lstat(), "st_file_attributes", 0) & getattr(stat,"FILE_ATTRIBUTE_REPARSE_POINT",0):
            continue
        if f.is_dir():
            yield from walk(f)
        elif f.is_file():
            yield f

inventory = rows(PRIOR / "CLEANUP_FINAL_INVENTORY.csv")
assert len(inventory) == 4919
prior_paths = {r["path"] for r in inventory}
current = {f.relative_to(ROOT).as_posix() for f in walk(ROOT)}
removed, added = sorted(prior_paths - current), sorted(current - prior_paths)
zip_inventory = rows(PRIOR / "zip_redundancy_audit.csv")
expected_zips = {r["path"] for r in zip_inventory}
assert len(expected_zips) == 65 and expected_zips == {x for x in current if x.lower().endswith(".zip")}
for r in zip_inventory:
    assert digest(ROOT / r["path"]) == r["sha256"], r["path"]
prior_members = rows(PRIOR / "manual_zip_member_audit.csv")
assert len(prior_members) == 735
with ZipFile(ROOT / prior_members[0]["archive"]) as archive:
    assert len([e for e in archive.infolist() if not e.is_dir()]) == 735
    for r in prior_members:
        with archive.open(r["member"]) as f:
            member_digest = hashlib.file_digest(f, "sha256").hexdigest()
        assert member_digest == r["archive_member_sha256"] == digest(ROOT / r["matched_copy"]), r["member"]
refs = rows(POST / "cleanup_dependency_references.csv")
referenced = {r["path"] for r in refs if "week2september" in r["locator"]}
assert len(referenced) == 596
reference_pattern = re.compile(r"week2September[\\/]+manual", re.I)
remaining_refs = {rel for rel in referenced if (ROOT / rel).is_file()
                  and reference_pattern.search((ROOT / rel).read_text(encoding="utf-8-sig"))}
dex = {name: tracked(ROOT / name) for name in ("P1", "P2")}
candidates = []
from importlib.util import source_from_cache
for r in rows(PRIOR / "bytecode_cleanup_audit.csv"):
    if r["classification"] != "DELETE_SAFE_CANDIDATE": continue
    relative = Path(r["path"])
    path = ROOT / relative
    source = ROOT / r["source"]
    assert path.is_file() and not path.is_symlink() and path.suffix==".pyc" and path.parent.name=="__pycache__"
    assert source.is_file() and Path(source_from_cache(str(path))) == source
    assert relative.parts[0] not in dex or Path(*relative.parts[1:]).as_posix() not in dex[relative.parts[0]]
    candidates.append({"workspace_relative": relative.as_posix(), "bytes": path.stat().st_size,
                       "sha256": digest(path), "source": source.relative_to(ROOT).as_posix(),
                       "source_sha256": digest(source), "action": "KEEP_UNTIL_APPROVED"})
assert len(candidates) == 213
assert not [f for f in STAGE.rglob("*") if f.name == "__pycache__" or re.search(
    r"(?i)(\.zip$|\.pyc$|\.tmp$|\.bak(?:$|_)|/eval_test[^/]*$)", f.as_posix())]
with (HERE / "CLEANUP_BYTECODE_CANDIDATES.csv").open("x", encoding="utf8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(candidates[0]))
    writer.writeheader()
    writer.writerows(candidates)
result = {"prior_inventory_count": len(inventory), "recount_same_scope": len(current),
          "added_since_snapshot": added, "removed_since_snapshot": removed,
          "zip_count": len(zip_inventory), "verified_zip_sha": 65, "manual_members_verified": 735,
          "bytecode_candidates": len(candidates), "bytecode_bytes": sum(r["bytes"] for r in candidates),
          "prior_reference_files": len(referenced), "same_reference_still_observed": len(remaining_refs),
          "prior_reference_changes": sorted(referenced - remaining_refs), "original_actions": 0}
with (HERE / "cleanup_observation.json").open("x", encoding="utf8") as f:
    json.dump(result, f, indent=2)
print({k:v for k,v in result.items() if k not in {"added_since_snapshot","removed_since_snapshot","prior_reference_changes"}})
