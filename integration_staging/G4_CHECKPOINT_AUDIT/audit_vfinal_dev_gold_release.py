from pathlib import Path
import csv
import json
import hashlib

P2 = Path(r"C:\Users\PC - NGHI\Desktop\Pipeline\P2")
M = P2 / "experiments" / "week2September" / "manual"
OUT = P2 / "integration_staging" / "G4_CHECKPOINT_AUDIT"

FILES = {
    "dev_all": M / "splits" / "d_dev_ids.txt",
    "dev_staged": P2 / "integration_staging" / "P1" / "splits" / "d_dev_ids.txt",
    "dev_select": M / "splits" / "p1p2_vfinal_2026-11-16" / "d_dev_select_ids.txt",
    "dev_graph": M / "splits" / "p1p2_vfinal_2026-11-16" / "d_dev_graph_ids.txt",
    "gold_confirmed": M / "data" / "gold_releases" / "vFinal_2026-11-16" / "adjudication_human_confirmed.csv",
    "gold_manifest": M / "data" / "gold_releases" / "vFinal_2026-11-16" / "gold_vfinal_manifest.json",
    "gold_provenance": M / "data" / "gold_releases" / "vFinal_2026-11-16" / "gold_release_provenance.json",
}

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def read_ids(path):
    values = [
        x.strip() for x in path.read_text(encoding="utf-8-sig").splitlines()
        if x.strip()
    ]
    return values

def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        return reader.fieldnames or [], rows

OUT.mkdir(parents=True, exist_ok=True)
report = []
id_sets = {}
gold_rows = []
gold_headers = []

for key, path in FILES.items():
    if not path.is_file():
        report.append({
            "name": key,
            "exists": False,
            "path": str(path),
            "rows": "",
            "unique_ids": "",
            "sha256": "",
            "details": "FILE_NOT_FOUND",
        })
        continue

    digest = sha256(path)

    if key.startswith("dev_"):
        ids = read_ids(path)
        id_sets[key] = ids
        report.append({
            "name": key,
            "exists": True,
            "path": str(path),
            "rows": len(ids),
            "unique_ids": len(set(ids)),
            "sha256": digest,
            "details": json.dumps({
                "duplicate_count": len(ids) - len(set(ids)),
                "first_5": ids[:5],
                "last_5": ids[-5:],
            }, ensure_ascii=False),
        })

    elif key == "gold_confirmed":
        gold_headers, gold_rows = read_csv(path)
        report.append({
            "name": key,
            "exists": True,
            "path": str(path),
            "rows": len(gold_rows),
            "unique_ids": "",
            "sha256": digest,
            "details": json.dumps({
                "columns": gold_headers,
                "first_row": gold_rows[0] if gold_rows else None,
            }, ensure_ascii=False),
        })

    else:
        try:
            obj = json.loads(path.read_text(encoding="utf-8-sig"))
            details = json.dumps(obj, ensure_ascii=False)
        except Exception as exc:
            details = f"JSON_ERROR: {exc}"
        report.append({
            "name": key,
            "exists": True,
            "path": str(path),
            "rows": "",
            "unique_ids": "",
            "sha256": digest,
            "details": details,
        })

comparisons = []
for left, right in (
    ("dev_all", "dev_staged"),
    ("dev_all", "dev_select"),
    ("dev_all", "dev_graph"),
):
    if left in id_sets and right in id_sets:
        a, b = set(id_sets[left]), set(id_sets[right])
        comparisons.append({
            "comparison": f"{left} vs {right}",
            "left_count": len(a),
            "right_count": len(b),
            "intersection": len(a & b),
            "left_only": len(a - b),
            "right_only": len(b - a),
            "identical": a == b,
        })

if "dev_select" in id_sets and "dev_graph" in id_sets:
    a, b = set(id_sets["dev_select"]), set(id_sets["dev_graph"])
    comparisons.append({
        "comparison": "dev_select vs dev_graph",
        "left_count": len(a),
        "right_count": len(b),
        "intersection": len(a & b),
        "left_only": len(a - b),
        "right_only": len(b - a),
        "identical": a == b,
    })

if "dev_all" in id_sets and "dev_select" in id_sets and "dev_graph" in id_sets:
    full = set(id_sets["dev_all"])
    union = set(id_sets["dev_select"]) | set(id_sets["dev_graph"])
    comparisons.append({
        "comparison": "dev_all vs union(select,graph)",
        "left_count": len(full),
        "right_count": len(union),
        "intersection": len(full & union),
        "left_only": len(full - union),
        "right_only": len(union - full),
        "identical": full == union,
    })

(OUT / "vfinal_dev_gold_file_audit.json").write_text(
    json.dumps({
        "files": report,
        "split_comparisons": comparisons,
    }, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

lines = ["VFINAL DEV / GOLD RELEASE AUDIT", ""]
for row in report:
    lines.append(f"[{row['name']}]")
    lines.append(json.dumps(row, ensure_ascii=False))
for row in comparisons:
    lines.append("")
    lines.append("[SPLIT COMPARISON]")
    lines.append(json.dumps(row, ensure_ascii=False))

lines += [
    "",
    "IMPORTANT:",
    "This audit inventories files and compares ID sets.",
    "It does not approve a Gold release or infer capability labels.",
    "Gold ID column must be identified from the actual CSV header.",
]

(OUT / "vfinal_dev_gold_file_audit.txt").write_text(
    "\n".join(lines), encoding="utf-8"
)

print("\n".join(lines))
