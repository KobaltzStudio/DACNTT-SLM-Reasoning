from pathlib import Path

root = Path(".")
dev = set((root / "splits/d_dev_ids.txt").read_text(encoding="utf-8-sig").split())
select = set((root / "splits/p1p2_vfinal_2026-11-16/d_dev_select_ids.txt").read_text(encoding="utf-8-sig").split())
graph = set((root / "splits/p1p2_vfinal_2026-11-16/d_dev_graph_ids.txt").read_text(encoding="utf-8-sig").split())

print("D_dev:", len(dev))
print("D_dev_select:", len(select))
print("D_dev_graph:", len(graph))
print("Intersection:", len(select & graph))
print("Union:", len(select | graph))
print("Missing from union:", len(dev - (select | graph)))
print("Extra outside D_dev:", len((select | graph) - dev))

assert len(dev) == 500
assert len(select) == 415
assert len(graph) == 85
assert len(select & graph) == 0
assert select | graph == dev

print("P1/P2 DEV SPLIT: PASS")
