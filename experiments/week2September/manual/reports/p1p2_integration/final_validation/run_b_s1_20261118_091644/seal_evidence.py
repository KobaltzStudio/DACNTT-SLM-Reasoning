"""Verify the reviewed figure revision and seal the final evidence index."""
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
from PIL import Image

from run_b_s1 import E, FINAL, ROOT, progress, read_json, sha256, file_record, write

figures = FINAL / "figures/seed13_v2_1"
manifest_path = figures / "figure_manifest.json"
manifest = read_json(manifest_path)
assert manifest["script_sha256"] == sha256(ROOT / "scripts/build_p1p2_analysis_figures.py")
assert len(manifest["figures"]) == 7
for name, record in manifest["figures"].items():
    assert record["status"] == "GENERATED" and record["partial"] and record["missing"]
    png, csv_file = figures / f"{name}.png", figures / f"{name}.csv"
    for path in (png, csv_file):
        assert sha256(path) == record["outputs"][path.name]
    with Image.open(png) as plot:
        assert plot.size[0] >= 2500 and plot.info["dpi"][0] > 210
        plot.verify()
    with csv_file.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == record["observations"]
    for row in rows:
        source = json.loads(row["source_paths_and_sha256"])
        assert source and all(record["inputs"][path] == digest for path, digest in source.items())
    assert all(sha256(Path(path)) == digest for path, digest in record["inputs"].items())
original = E / "runpod_sha256sums.txt"
verified = E / "runpod_sha256sums_v2.txt"
updates = []
checks = []
for line in original.read_text(encoding="utf-8").splitlines():
    expected, relative = line.split("  ", 1)
    actual = sha256(ROOT / relative)
    if actual != expected:
        assert relative == "scripts/build_p1p2_analysis_figures.py", relative
        updates.append({"path": relative, "previous": expected, "current": actual})
    checks.append(f"{actual}  {relative}\n")
with verified.open("x", encoding="utf-8", newline="\n") as stream:
    stream.writelines(checks)
write("runpod_staging_verification.json", {
    "status": "PASS_LOCAL_FILE_CHECKS", "runpod_status": "NOT RUN / DELEGATED",
    "staged_files_checked": len(checks), "staging_map": "Preserve each listed path relative to MANUAL_ROOT",
    "manifest": file_record(verified), "model_cache": file_record(E / "runpod_student_cache.json"),
    "maintained_source_updates": updates, "syntax_checks": file_record(E / "runpod_command_syntax.log"),
})
progress("G8", "PARTIAL", manifest_path, "Seven real-data PNG/CSV pairs checked; gaps explicit at S2/S3",
         "Complete S2/S3 before full regeneration", 4)
progress("Runtime tests", "DONE", E / "final_qa_tests.log", "91 tests passed on reviewed final source", code=0)
latest = read_json(E / "deliverables_index.json")
latest.update({"at": datetime.now(timezone.utc).isoformat(), "figures": file_record(manifest_path),
               "staging": file_record(E / "runpod_staging_verification.json"),
               "final_test_log": file_record(E / "final_qa_tests.log"),
               "guide": file_record(ROOT.parents[3] / "GPTGUIDE.txt")})
latest["deliverables"] = {path.name: file_record(path) for path in E.iterdir()
                          if path.is_file() and path.name not in {"commands.jsonl", "deliverables_index_final.json"}}
write("deliverables_index_final.json", latest)
print(f"Seven figure pairs and {len(checks)} staging hashes verified.", flush=True)
