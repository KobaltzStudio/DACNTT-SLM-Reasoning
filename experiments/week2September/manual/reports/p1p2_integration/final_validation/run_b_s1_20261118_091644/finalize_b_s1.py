"""Publish post-run analysis and evidence after the S1-only controller audit."""
from collections import Counter
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

from run_b_s1 import A, E, FINAL, PRIOR, ROOT, R, AR, AM, BR, BM, ENV, file_record, progress, read_json, run, sha256, write
from p1p2_controller import Controller


def check_protected():
    initial = read_json(A / "preflight_provenance.json")["protected"]
    changed = []
    for relative, expected in initial["file_size_and_mtime"].items():
        path = ROOT / relative
        if not path.is_file():
            changed.append(relative)
            continue
        stat = path.stat()
        if [stat.st_size, stat.st_mtime_ns] != expected:
            changed.append(relative)
    for path, digest in initial["anchor_sha256"].items():
        if sha256(Path(path)) != digest:
            changed.append(path)
    assert not changed, f"Protected inputs changed: {changed[:12]}"
    write("protected_artifact_verification.json", {"status": "PASS",
          "checked_entry_metadata": len(initial["file_size_and_mtime"]),
          "checked_content_hashes": len(initial["anchor_sha256"]),
          "source": file_record(A / "preflight_provenance.json"), "changed": []})


def analysis():
    g6dir = E / "g6"
    code, log = run([sys.executable, "-B", "scripts/build_capability_learning_dynamics.py", "--manual", ROOT,
                     "--output", g6dir], "g6_build.log")
    assert code in (0, 4), log
    verdict = "DONE" if code == 0 else "PARTIAL"
    metrics = g6dir / ("capability_learning_dynamics_seed13.json" if code == 0 else "g6_partial_learning_dynamics_seed13.json")
    counts = read_json(metrics)
    code, log = run([sys.executable, "-B", "scripts/build_capability_learning_dynamics.py", "--manual", ROOT,
                     "--output", g6dir, "--inventory-only"], "g6_inventory.log")
    assert code == 0, log
    inv = read_json(g6dir / "g6_pretraining_inventory.json")
    progress("G6", verdict, metrics, f"{inv['raw_sidecars']} raw and {inv['logical_sidecars']} logical sidecars",
             "Complete missing S2/S3 sidecars" if verdict == "PARTIAL" else "", 4 if verdict == "PARTIAL" else 0)
    assert counts["g6_status"] == ("PASS" if verdict == "DONE" else "PARTIAL")
    code, log = run([sys.executable, "-B", "scripts/select_checkpoint_on_dev.py",
                     "--partial", "--output", E / "g7"], "g7_partial.log")
    assert code == 0, log
    g7 = E / "g7/checkpoint_selection_seed13_partial.json"
    partial = read_json(g7)
    assert all(row["selected_checkpoint"] is None and row["denominator"] == 415 for row in partial["rows"])
    progress("G7", "PARTIAL", g7, f"{len(partial['rows'])} observed checkpoint scores, 415 verified IDs each",
             "Both integrated method series still lack S2/S3", code)
    figdir = FINAL / "figures"
    figdir = figdir / E.name if figdir.exists() and any(figdir.iterdir()) else figdir
    code, log = run([sys.executable, "-B", "scripts/build_p1p2_analysis_figures.py", "--allow-partial", "--preflight"],
                     "figure_readiness_seed13.json")
    assert code == 0, log
    code, log = run([sys.executable, "-B", "scripts/build_p1p2_analysis_figures.py", "--allow-partial", "--output", figdir],
                     "figure_generation.log")
    assert code in (0, 4), log
    manifest = figdir / "figure_manifest.json"
    records = read_json(manifest)["figures"]
    generated = {name: row for name, row in records.items() if row["status"] == "GENERATED"}
    for name, row in generated.items():
        assert len(row["outputs"]) == 2
        assert {Path(filename).suffix for filename in row["outputs"]} == {".csv", ".png"}
        assert all(sha256(figdir / filename) == digest for filename, digest in row["outputs"].items())
    progress("G8", "DONE" if code == 0 else "PARTIAL", manifest, f"{len(generated)}/7 real-data PNG/CSV pairs",
             "Regenerate after all checkpoints validate" if code == 4 else "", code)
    return {"g6": {"raw": inv["raw_sidecars"], "logical": inv["logical_sidecars"], "missing": inv["missing_method_checkpoint_pairs"]},
            "g7": file_record(g7), "figures": file_record(manifest), "generated": list(generated)}


def prepare_staging():
    c = Controller(ROOT, resume=True, dry_run=True)
    anchor_paths = [Path(p) for p in read_json(E / "run_b_s1_preflight.json")["input_sha256"]]
    items = [
        ROOT / "scripts", ROOT / "tests", ROOT / "config",
        ROOT / "splits", ROOT / "data/raw/gsm8k_train.jsonl", ROOT / "data/supplement/supplement_annotations_v2.jsonl",
        c.tokens.with_suffix(".summary.json"), c.s0_prediction.parent / ".done/eval_dev_S0.json",
        c.s0_prediction.with_suffix(".summary.json"),
        ROOT / "reports/p1p2_integration/capability_state/P1-DEFICIT_seed13",
        ROOT / "reports/p1p2_integration/capability_state/P1P2_seed13",
        ROOT / "reports/p1p2_integration/capability_sidecars/P1P2_seed13_S1",
        ROOT / "reports/p1p2_integration/capability_sidecars/P1-DEFICIT_seed13_S1",
        A / "S1_audit.json", E / "run_b_seed13_s1_validation.json", E / "run_a_stopped_verification.json",
        AR, BR, AM, BM,
    ]
    for name in ("B4_seed13", "B5_seed13"):
        hist = ROOT / "runs/main" / name
        items.extend(hist.glob("round_*"))
    items.extend((ROOT / "runs/main").glob("*_seed*/S*/eval_dev.jsonl"))
    items += [R / "derived_predictions/B4_seed13", ROOT / "reports/capability_g4_validation",
              ROOT / "reports/capability/g5_9_historical_20261117"]
    files = set()
    for path in [*items, *anchor_paths]:
        if path.is_dir():
            files.update(p for p in path.rglob("*") if p.is_file() and "__pycache__" not in p.parts
                         and p.suffix.lower() not in {".zip", ".pyc"} and ".staging" not in p.name)
        else:
            files.add(path)
    manifest = E / "runpod_sha256sums.txt"
    with manifest.open("x", encoding="utf-8", newline="\n") as stream:
        for path in sorted(files):
            stream.write(f"{sha256(path)}  {path.relative_to(ROOT).as_posix()}\n")
    package_weights = Path(read_json(E / "run_b_s1_preflight.json")["environment"]["cache_weights"])
    write("runpod_student_cache.json", {"student": read_json(c.config)["student"],
          "weights": file_record(package_weights), "requirements_lock": file_record(ROOT.parents[2] / "requirements-lock.txt"),
          "manifest": file_record(manifest), "manifest_file_count": len(files), "runpod_status": "NOT RUN / DELEGATED"})


def cleanup():
    code, log = run([sys.executable, "-B", E / "audit_cleanup.py"], "repository_cleanup_audit.log")
    assert code == 0, log
    with (E / "repository_cleanup_inventory.csv").open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    groups = Counter(row["disposition"] for row in rows)
    archives = [row for row in rows if row["type"].lower() == ".zip"]
    lines = ["# Đề xuất lưu trữ và dọn repository", "", f"Kiểm kê chỉ đọc {len(rows)} file ở Pipeline, P1 và P2.",
             "Bỏ qua metadata Git, venv, node_modules, junction và thư mục bằng chứng của chính lượt kiểm kê.", "",
             *[f"- {key}: {value}" for key, value in sorted(groups.items())], "",
             "Chỉ coi bytecode có source hiện hữu là ứng viên xóa. Không xóa file nào. "
             "Các archive có SHA-256, danh sách thành viên mẫu, phạm vi so với file giải nén và trường hợp chưa biết trong CSV.",
             "", "| ZIP | Members | Verified subset | Proposed disposition |", "|---|---:|---:|---|"]
    for row in archives:
        recommendation = ("ARCHIVE, all inspected members match extracted copies" if row["zip_entries"]
                          and row["zip_entries"] == row["zip_members_crc_matched"] else
                          "KEEP pending proof of a complete extracted equivalent")
        lines.append(f"| `{row['path']}` | {row['zip_entries'] or '?'} | {row['zip_members_crc_matched'] or '0'} | {recommendation} |")
    lines += ["", "ARCHIVE chỉ là đề xuất lưu giữ có thể khôi phục. Đối chiếu lại Git, source input và checksum trước khi "
              "duyệt di chuyển. Không đổi tên, không xóa, không extract ZIP."]
    with (E / "repository_cleanup_proposal.md").open("x", encoding="utf-8") as stream:
        stream.write("\n".join(lines) + "\n")


def update_guide(b, aggregate):
    guide = ROOT.parents[3] / "GPTGUIDE.txt"
    raw = guide.read_bytes()
    original = raw.decode("utf-8")
    marker = "### Cập nhật kiểm chứng local — 2026-11-18, G6–G8"
    assert original.count(marker) == 1
    newline = "\r\n" if b"\r\n" in raw else "\n"
    count = len(aggregate["generated"])
    new = "\n".join([
        "### Run A dừng có kiểm soát và Run B S1 đã xác minh", "",
        "- Run A S1 đã xác minh 83,2% strict D_dev. S2 đã huấn luyện 26 bước, evaluation dừng có kiểm soát. S3 chưa chạy.",
        f"- Run B P1P2 seed 13 S1 đã qua audit với {b['strict_d_dev']['correct']}/500 strict D_dev, "
        f"{b['steps']} optimizer steps, {b['train_seconds']} giây training và {b['peak_allocated_gib']} GiB peak allocated.",
        f"- G6 có {aggregate['g6']['raw']} sidecar và {aggregate['g6']['logical']} nhóm logic. "
        f"G7 chỉ là so sánh quan sát trên 415 ID, chưa chọn checkpoint cuối. G8 có {count}/7 figure từ dữ liệu quan sát, phạm vi còn thiếu được ghi trong manifest.",
        "- G9 chưa chạy và vẫn được bàn giao. Chờ duyệt riêng trước khi nối Run A S2/S3 hoặc Run B S2/S3. D_test chờ khóa chọn checkpoint.",
        f"- Hồ sơ bằng chứng `P2/experiments/week2September/manual/{E.relative_to(ROOT).as_posix()}`.", "", "",
    ])
    index = original.index(marker)
    tmp = guide.with_name(f".{guide.name}.{os.getpid()}.tmp")
    with tmp.open("xb") as output:
        output.write((original[:index] + new.replace("\n", newline) + original[index:]).encode("utf-8"))
    os.replace(tmp, guide)


def plan_update(b, aggregate):
    workspace = ROOT.parents[3]
    docs = [workspace / "KeHoachTichHop_P1_P2_RunPod_BoSungSauValidation.docx",
            workspace / "P1_P2_RunPod_Merge_Plan_With_PostValidation.docx",
            workspace / "KeHoachPhanCong_DieuChinh_Proposal1_14-20_11_2026.docx"]
    lines = ["# Đề xuất cập nhật kế hoạch sau kiểm chứng P1 P2", "",
             "Đề xuất bổ sung cho các tài liệu kế hoạch gốc. Các file DOCX được giữ nguyên.", "",
             *[f"- `{path}` — SHA-256 `{sha256(path)}`" for path in docs], "",
             "| Mục của kế hoạch | Hiện trạng và bằng chứng | Điều kiện cập nhật tiếp |",
             "|---|---|---|",
             "| Kế hoạch tích hợp, Bước 11 / RunPod integration | Hook và resume đã kiểm tra local, RunPod chưa chạy | GPU/image Linux, resolver path, dry-run và smoke/resume trên RunPod |",
             f"| Kế hoạch phân công, P1-F | Run A S1 83,2%; Run B S1 {b['strict_d_dev']['accuracy']:.1%}; "
             "Gold hook 85 ID và bảy capability đã xác minh | Run A S2 eval và S3, Run B S2/S3, phê duyệt riêng |",
             f"| Learning dynamics và final freeze | G6 {aggregate['g6']['logical']} nhóm logic; G7 partial; "
             f"G8 {len(aggregate['generated'])} figure dữ liệu quan sát | Phải có đủ sidecar/prediction và kiểm tra canonical |",
             "| Phần 14.1 sau Final Validation | Các nghiên cứu bổ sung giữ trạng thái chờ | Hoàn tất validation, khóa checkpoint D_dev_select, đăng ký method/config/manifest riêng |",
             "| Kết quả held-out và graph | D_test chưa chạy. Chưa suy ra cạnh prerequisite từ capability co-occurrence | Cần chọn checkpoint đã khóa và phê duyệt D_test; graph cần bằng chứng transfer độc lập |",
             "", "## Checklist cập nhật", "",
             "- [ ] Nối lại Run A S2 bằng prefix hợp lệ, kiểm tra adapter S1→S2 rồi chạy S3 nếu được duyệt.",
             "- [ ] Duyệt Run B S2–S3, kiểm tra NLL theo checkpoint, lineage và sidecar từng lượt.",
             "- [ ] Sinh lại bảng strict 415 ID, bảng động học và đúng bảy PNG/CSV ở namespace version mới.",
             "- [ ] Ghi hash, GPU/CUDA, thời gian, run log, coverage và kết quả resume Linux. Chỉ khóa Final Validation sau đủ gate.",
             "", "Bằng chứng chi tiết trong [audit S1](run_b_seed13_s1_validation.json), [dừng Run A](run_a_stopped_verification.json), "
             "[readiness figure](figure_readiness_seed13.json) và [handoff RunPod](runpod_handoff.md)."]
    with (E / "post_validation_plan_update.md").open("x", encoding="utf-8") as stream:
        stream.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    b = read_json(E / "run_b_seed13_s1_validation.json")
    assert b["status"] == "PASS" and b["checkpoint"] == "S1" and b["method"] == "P1P2"
    for item in b["artifacts"].values():
        assert sha256(Path(item["path"])) == item["sha256"]
    check_protected()
    status, tests = run([sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-v"], "final_all_tests.log")
    assert status == 0, tests
    progress("Runtime tests", "DONE", tests, "Current source unit and integration fixtures passed", code=status)
    aggregate = analysis()
    prepare_staging()
    cleanup()
    plan_update(b, aggregate)
    update_guide(b, aggregate)
    # Check the final Git state without mutating any index, branch or tracked experiment output.
    for command, log in ((["diff", "--check"], "git_diff_check.log"), (["diff", "--stat"], "git_diff_stat.log"),
                         (["status", "--short", "--branch"], "git_status.log")):
        status, evidence = run(["git", "--no-optional-locks", *command], log)
        assert status == 0, evidence
    aggregate["at"] = datetime.now(timezone.utc).isoformat()
    aggregate["run_b"] = file_record(E / "run_b_seed13_s1_validation.json")
    aggregate["deliverables"] = {path.name: file_record(path) for path in E.iterdir()
                                 if path.is_file() and path.name != "commands.jsonl"}
    write("deliverables_index.json", aggregate)
