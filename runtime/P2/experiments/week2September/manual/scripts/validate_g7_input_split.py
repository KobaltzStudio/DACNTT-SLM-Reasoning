from pathlib import Path
import hashlib
import json

ROOT = Path.cwd()

SPLIT = ROOT / "splits/p1p2_vfinal_2026-11-16"
GRAPH = SPLIT / "d_dev_graph_ids.txt"
SELECT = SPLIT / "d_dev_select_ids.txt"
MANIFEST = SPLIT / "split_manifest.json"

def ids(path):
    return [
        x.strip()
        for x in path.read_text(encoding="utf-8-sig").splitlines()
        if x.strip()
    ]

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

graph = ids(GRAPH)
select = ids(SELECT)
manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

assert len(graph) == 85
assert len(select) == 415
assert len(set(graph)) == 85
assert len(set(select)) == 415
assert not (set(graph) & set(select))

assert sha256(GRAPH) == manifest["files"][GRAPH.name]["sha256"]
assert sha256(SELECT) == manifest["files"][SELECT.name]["sha256"]

print("D_DEV_GRAPH:", len(graph))
print("D_DEV_SELECT:", len(select))
print("NO_OVERLAP:", True)
print("MANIFEST_HASHES:", "PASS")
print("G7_INPUT_SPLIT_AUDIT: PASS")
