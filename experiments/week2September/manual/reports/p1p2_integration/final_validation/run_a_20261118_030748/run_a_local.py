"""Execute the authorized Run A through the unified CLI, with independent gates."""
import csv
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

from safetensors import safe_open

EVIDENCE = Path(__file__).resolve().parent
ROOT = EVIDENCE.parents[3]
FINAL = EVIDENCE.parent
PRIOR = ROOT / "reports/p1p2_integration/final_validation/runtime_20261118_024353_resume"
RUN = ROOT / "runs/p1p2_integration/P1-DEFICIT_seed13"
MODEL = ROOT / "models/p1p2_integration/P1-DEFICIT_seed13"
REPORTS = ROOT / "reports/p1p2_integration"
METHOD, SEED = "P1-DEFICIT", 13
sys.path.insert(0, str(ROOT / "scripts"))
from p1p2_controller import Controller, read_json, read_jsonl, sha256
from select_checkpoint_on_dev import score, verified_prediction
from student_common import load_dev_rows

ENV = {**os.environ, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
       "PYTHONUNBUFFERED": "1", "PYTHONDONTWRITEBYTECODE": "1"}
CLI = [sys.executable, "-u", "-B", "scripts/run_p1_p2.py", "--method", METHOD, "--seed", str(SEED),
       "--resume", "--backend", "hf", "--dtype", "bf16", "--micro-batch", "1", "--nll-batch", "1", "--eval-batch", "1"]
ITEMS = {}
RESULTS = []


def replace_report(path, text):
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("x", encoding="utf-8") as output:
        output.write(text)
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, path)


def item(key, status, completed, proof=None, code=None, remaining="", next_action="", *, previous=False):
    proof = Path(proof).resolve() if proof else None
    ITEMS[key] = {"id": key, "status": status, "completed": completed, "evidence": str(proof) if proof else None,
                  "exit_code": code, "sha256": sha256(proof) if proof and proof.is_file() else None,
                  "remaining_work": remaining, "next_action": next_action,
                  "phase": "prior_task" if previous else "run_a_task"}


def progress():
    now = datetime.now(timezone.utc).isoformat()
    payload = {"updated_utc": now, "items": list(ITEMS.values()), "checkpoints": RESULTS}
    replace_report(FINAL / "p1p2_master_progress_seed13.json", json.dumps(payload, indent=2) + "\n")
    lines = ["# P1/P2 seed 13 master progress", "", f"Updated UTC {now}", "",
             "| Gate | Status | Phase | Evidence and result | Exit | SHA-256 | Remaining | Next |",
             "|---|---|---|---|---:|---|---|---|"]
    for row in ITEMS.values():
        proof = f"[evidence](<{Path(row['evidence']).as_posix()}>)" if row["evidence"] else ""
        parts = [row["id"], row["status"], row["phase"], f"{row['completed']} {proof}",
                 row["exit_code"], row["sha256"], row["remaining_work"], row["next_action"]]
        lines.append("| " + " | ".join(str(p).replace("|", "/") if p is not None else "" for p in parts) + " |")
    replace_report(FINAL / "p1p2_master_progress_seed13.md", "\n".join(lines) + "\n")


def initialize():
    base = read_json(PRIOR / "runtime_integration_validation.json")
    for key, proof, note in (
        ("Source audit", "source_sha256_manifest.json", "Reviewed source and frozen-protocol baseline"),
        ("Shared S0", "runtime_integration_validation.json", "Shared S0 verified during prior preflight"),
        ("Gold/split", "verified_analysis/g6_pretraining_inventory.json", "Approved Gold and split fingerprints inventoried"),
        ("Controller", "runtime_integration_validation.json", "Synthetic runtime S1 to S3 verified"),
        ("Unified CLI", "test_execution_log.md", "CLI and dry-run verified"),
        ("Post-evaluation hook", "runtime_integration_validation.json", "Real hook executed on fixtures"),
        ("Runtime tests", "verified_analysis/final_all_tests.log", "88 unit tests and seven runtime fixture tests passed"),
        ("Resume/no-overwrite", "resume_no_overwrite_validation.json", "Safe retry and verified fixture reuse"),
        ("LoRA smoke", "lora_smoke_test_report.json", "One real BF16 LoRA optimizer step, save, reload and inference"),
    ):
        item(key, "DONE", note, PRIOR / proof, 0, previous=True)
    for method in (METHOD, "P1P2"):
        plan = next(p for p in base["dry_runs"] if p["methods"] == [method])
        item(f"Dry-run {method}", "DONE", f"{plan['actions']} validated stages", plan["path"], plan["exit"], previous=True)
    item("Max-length preflight", "NOT RUN", "Awaiting validation of bounded probe")
    for round_no in (1, 2, 3):
        item(f"Run A S{round_no}", "NOT RUN", "No production validation in this task yet", remaining="Train, evaluate and audit")
    for round_no in (1, 2, 3):
        item(f"Run B S{round_no}", "NOT RUN", "Outside current authorization",
             remaining="Separate authorization", next_action="Stop after Run A", previous=True)
    item("G6", "PARTIAL", "37 raw and 35 logical sidecars at baseline", PRIOR / "verified_analysis/g6_pretraining_inventory.json",
         0, "New sidecars after training", "Refresh inventory after Run A", previous=True)
    item("G7", "BLOCKED", "Historical B4 lineage resolved", PRIOR / "g7_historical_lineage_forensics.md",
         1, "Complete four method series", "Verify Run A D_dev_select inputs", previous=True)
    item("G8", "BLOCKED", "Seven builders available; real inputs incomplete", PRIOR / "verified_analysis/g8_figure_readiness.json",
         0, "Complete real inputs", "Refresh preflight after Run A", previous=True)
    item("G9", "DELEGATED", "Local handoff documented; RunPod not executed", PRIOR / "runpod_portability_audit.md", previous=True)
    progress()


def capture(args, name):
    path = EVIDENCE / name
    command = [str(arg) for arg in args]
    print(subprocess.list2cmdline(command), flush=True)
    start = time.monotonic()
    with path.open("xb") as stream:
        result = subprocess.run(command, cwd=ROOT, env=ENV, stdout=stream, stderr=subprocess.STDOUT)
    record = {"command": command, "exit_code": result.returncode, "log": str(path), "seconds": round(time.monotonic() - start, 2)}
    with (EVIDENCE / "commands.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record) + "\n")
    print(json.dumps(record), flush=True)
    return result.returncode, path


def protection():
    trees = ("config", "splits", "data", "trajectory", "runs/main", "models/task7", "reports/capability",
             "reports/capability_g4_validation", "runs/p1p2_integration/P1P2_seed13",
             "models/p1p2_integration/P1P2_seed13", "reports/p1p2_integration/derived_predictions")
    snapshots = {}
    for name in trees:
        for path in sorted((ROOT / name).rglob("*")):
            if path.is_file():
                stat = path.stat()
                snapshots[path.relative_to(ROOT).as_posix()] = [stat.st_size, stat.st_mtime_ns]
    controller = Controller(ROOT, resume=True, dry_run=True, dtype="bf16", micro_batch=1, nll_batch=1, eval_batch=1)
    anchor_paths = (controller.config, controller.pool, controller.tokens, controller.dev_ids, controller.gold_manifest,
                    controller.gold_labels, controller.approval, controller.s0_reference, controller.s0_prediction,
                    controller.s0_sidecar, RUN / "round_001")
    return {"file_size_and_mtime": snapshots, "anchor_sha256": {str(path): sha256(path) for path in anchor_paths}}


def preflight():
    status = subprocess.check_output(["git", "--no-optional-locks", "branch", "--show-current"], cwd=ROOT, text=True).strip()
    assert status == "codex/controller-dryrun-fix"
    source = read_json(PRIOR / "source_sha256_manifest.json")["source_sha256"]
    checked = {path: sha256(Path(path)) for path in source if Path(path).suffix in {".py", ".yaml"} or Path(path).name == "experiment_config.json"}
    assert checked and all(source[path] == digest for path, digest in checked.items()), "Current source differs from verified baseline"
    probe_path = EVIDENCE / "max_length_probe.json"
    probe = read_json(probe_path)
    assert probe["status"] == "DONE" and probe["probe_sequence_tokens"] == 1024
    item("Max-length preflight", "DONE", "Eight 1024-token samples, one BF16 LoRA step at effective batch 8", probe_path, probe["exit"])
    progress()
    ids = load_dev_rows()
    assert len(ids) == len({row["problem_id"] for row in ids}) == 500
    assert {path.name for path in RUN.iterdir()} == {"round_001"}, f"Existing Run A outputs require separate classification: {RUN}"
    assert not MODEL.exists() or not any(MODEL.iterdir()), f"Existing Run A adapters require classification: {MODEL}"
    for checkpoint in (1, 2, 3):
        assert not (REPORTS / "capability_sidecars" / f"{METHOD}_seed{SEED}_S{checkpoint}").exists()
        assert not (REPORTS / "capability_state" / f"{METHOD}_seed{SEED}" / f"selection_round_{checkpoint+1:03d}.json").exists()
    code, log = capture(CLI + ["--rounds", "all", "--dry-run"], "run_a_preflight.log")
    assert code == 0, log
    marker = next(line.split("=", 1)[1] for line in log.read_text(encoding="utf-8").splitlines() if line.startswith("DRY_RUN_REPORT="))
    plan_path = Path(marker)
    plan = read_json(plan_path)
    commands = [a["command"] for a in plan["actions"]]
    assert not any("compute_nll.py" in str(cmd) or "graph" in str(cmd) or "eval_test" in str(cmd) for cmd in commands)
    evaluations = [cmd for cmd in commands if len(cmd) >= 2 and Path(cmd[1]).name == "eval_student.py"]
    hooks = [cmd for cmd in commands if len(cmd) >= 2 and Path(cmd[1]).name == "run_p1p2_post_eval.py"]
    required = {"--method", "--seed", "--round", "--prediction", "--checkpoint", "--output-dir", "--manual-root",
                "--train-set", "--selection-log", "--train-log", "--checkpoint-log", "--gold-manifest", "--gold-labels",
                "--approval-csv", "--dev-ids", "--config"}
    assert len(evaluations) == len(hooks) == 3
    assert all(cmd[cmd.index("--split") + 1] == "dev" for cmd in evaluations)
    assert all(required <= set(cmd) for cmd in hooks)
    shield = protection()
    replace_report(EVIDENCE / "preflight_provenance.json", json.dumps({"source_sha256": checked, "protected": shield,
                   "dry_run_report": str(plan_path), "dry_run_sha256": sha256(plan_path)}, indent=2))
    item("Source audit", "DONE", "Verified source bytes match earlier 88-test baseline", EVIDENCE / "preflight_provenance.json", 0)
    item("Shared S0", "DONE", "Shared S0 capability state validated by exact Run A preflight", plan_path, 0)
    item("Gold/split", "DONE", "Frozen Gold and D_dev inputs validated", plan_path, 0)
    item("Dry-run P1-DEFICIT", "DONE", "Three rounds, D_dev only, full hook CLI, no NLL", plan_path, code)
    progress()
    return shield


def audit(checkpoint, shield, log_path):
    guard = Controller(ROOT, resume=True, dry_run=True, dtype="bf16", micro_batch=1, nll_batch=1, eval_batch=1)
    guard.run_method_seed(METHOD, SEED, [checkpoint])
    assert not guard.actions, f"Resume would need additional work: {guard.actions}"
    adapter, sidecar = MODEL / f"student_ckpt_{checkpoint:03d}", REPORTS / "capability_sidecars" / f"{METHOD}_seed{SEED}_S{checkpoint}"
    train_set = RUN / f"round_{checkpoint:03d}/train_set.json"
    prediction = RUN / f"S{checkpoint}/eval_dev.jsonl"
    log = read_json(adapter / "train_log.json")
    weights = adapter / "adapter_model.safetensors"
    with safe_open(weights, framework="pt", device="cpu") as handle:
        keys = list(handle.keys())
        assert keys and any("lora_A" in key for key in keys)
        assert all(math.prod(handle.get_slice(key).get_shape()) > 0 for key in keys)
    cfg = read_json(guard.config)
    assert log["effective_batch"] == 8 and log["grad_accum"] == 8 and log["dtype"] == "bfloat16"
    assert log["epochs_from_config"] and log["lr_from_config"] and log["revision"] == cfg["student"]["revision"]
    assert log["gradient_checkpointing"] and log["steps"] == math.ceil(log["n_examples"] / 8)
    assert all(math.isfinite(row["loss"]) for row in log["steps_log"])
    train = read_json(train_set)
    assert train["nll_file"] is None and train["nll_sha256"] is None
    assert train["source_checkpoint"] == f"S{checkpoint-1}"
    selection_log = read_jsonl(train_set.with_name("selection_log.jsonl"))
    assert {row["trajectory_id"] for row in selection_log if row["selected"]} == set(train["trajectory_ids"])
    assert len(selection_log) == len(read_jsonl(guard.pool))
    state = REPORTS / "capability_state" / f"{METHOD}_seed{SEED}" / f"selection_round_{checkpoint+1:03d}.json"
    input_state_path = Path(train["state_file"])
    assert train["state_sha256"] == sha256(input_state_path)
    assert read_json(input_state_path)["source"]["checkpoint"] == f"S{checkpoint-1}"
    eval_summary = read_json(prediction.with_suffix(".summary.json"))
    assert eval_summary["split"] == "dev" and eval_summary["batch_size"] == 1 and eval_summary["limit"] is None
    assert Path(eval_summary["adapter"]).resolve() == adapter
    rows = read_jsonl(prediction)
    accuracy = sum(row["status"] == "valid" for row in rows) / 500
    assert accuracy == eval_summary["accuracy"]
    assert not any("eval_test" in path.name or "nll" in path.name for path in RUN.rglob("*") if path.is_file())
    assert protection() == shield, "Protected input metadata or byte fingerprints changed"
    record = {"checkpoint": f"S{checkpoint}", "status": "DONE", "exit_code": 0, "run_log": str(log_path),
              "train_seconds": log["elapsed_seconds"], "train_final_loss": log["steps_log"][-1]["loss"],
              "peak_gpu_allocated_gib": log["peak_gpu_memory_gb"], "peak_gpu_reserved_bytes": log["peak_gpu_reserved_bytes"],
              "d_dev_strict_accuracy": accuracy, "eval_seconds": eval_summary["elapsed_seconds_this_run"],
              "parent": log["checkpoint_parent"], "parent_sha256": log.get("checkpoint_parent_sha256"),
              "adapter_load_evidence": "SafeTensors header inspected and D_dev evaluation with this adapter succeeded",
              "resume": "No pending controller actions", "lineage": "verified", "protected_inputs": "verified",
              "artifacts": {name: {"path": str(path), "sha256": sha256(path)} for name, path in (
                  ("adapter", adapter), ("adapter_weights", weights), ("prediction", prediction), ("sidecar", sidecar),
                  ("sidecar_manifest", sidecar / "student_capability_evaluation_manifest.json"), ("train_set", train_set),
                  ("selection_log", train_set.with_name("selection_log.jsonl")), ("capability_state", state),
                  ("train_log", adapter / "train_log.json"), ("summary", prediction.with_suffix(".summary.json")),
              )}}
    replace_report(EVIDENCE / f"S{checkpoint}_audit.json", json.dumps(record, indent=2))
    return record


def finalize(shield):
    for ckpt in (1, 2, 3):
        audit(ckpt, shield, EVIDENCE / f"S{ckpt}_controller.log")
    code, log = capture(CLI + ["--rounds", "all", "--dry-run"], "run_a_resume_verify.log")
    assert code == 0, log
    report_path = Path(next(line.split("=", 1)[1] for line in log.read_text(encoding="utf-8").splitlines() if line.startswith("DRY_RUN_REPORT=")))
    assert read_json(report_path)["actions"] == [], "Expected no tasks when resuming completed Run A"
    payload = {"status": "DONE", "checkpoint_count": len(RESULTS), "checkpoints": RESULTS, "resume_plan": str(report_path),
               "resume_plan_sha256": sha256(report_path), "protected_snapshot": "preflight_provenance.json",
               "d_test_executed": False, "run_b_executed": False}
    replace_report(FINAL / "run_a_seed13_validation.json", json.dumps(payload, indent=2))
    lines = ["# Run A P1-DEFICIT seed 13", "", "DONE. Three completed checkpoints verified with no pending resume actions.", "",
             "| Checkpoint | Train seconds | Final loss | Allocated GiB | Reserved bytes | Strict D_dev |",
             "|---|---:|---:|---:|---:|---:|"]
    for row in RESULTS:
        lines.append("| " + " | ".join(str(row[key]) for key in ("checkpoint", "train_seconds", "train_final_loss",
                     "peak_gpu_allocated_gib", "peak_gpu_reserved_bytes", "d_dev_strict_accuracy")) + " |")
    replace_report(FINAL / "run_a_seed13_validation.md", "\n".join(lines) + "\n")
    with (FINAL / "run_a_seed13_artifact_inventory.csv").open("x", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("checkpoint", "artifact", "path", "sha256"))
        for result in RESULTS:
            for name, info in result["artifacts"].items():
                writer.writerow((result["checkpoint"], name, info["path"], info["sha256"]))
    progress()
    g6path = EVIDENCE / "g6"
    code, log = capture([sys.executable, "-B", "scripts/build_capability_learning_dynamics.py", "--manual", ROOT,
                         "--output", g6path, "--inventory-only"], "g6.log")
    if code == 0:
        inventory = read_json(g6path / "g6_pretraining_inventory.json")
        accepted = [row for row in inventory["sidecars"] if row.get("method") == METHOD and row.get("seed") == SEED
                    and row.get("valid") and row.get("canonical_source") == row.get("sidecar_source")]
        assert {row["checkpoint"] for row in accepted} == {"S1", "S2", "S3"}
        item("G6", "PARTIAL", f"{inventory['raw_sidecars']} raw, {inventory['logical_sidecars']} logical; three new Run A sidecars",
             g6path / "g6_pretraining_inventory.json", code, "Run B sidecars", "Wait for separate authorization")
    else:
        item("G6", "FAILED", "Post-run inventory failed", log, code)
    progress()
    split = ROOT / "splits/p1p2_vfinal_2026-11-16"
    select_ids = split / "d_dev_select_ids.txt"
    ids = set(select_ids.read_text(encoding="utf-8-sig").split())
    assert len(ids) == 415 and sha256(select_ids) == read_json(split / "split_manifest.json")["files"][select_ids.name]["sha256"]
    verified = []
    for ckpt in range(4):
        path, _ = verified_prediction(ROOT, METHOD, ckpt)
        scores = score(path, ids)
        assert not scores["missing"]
        verified.append({"checkpoint": f"S{ckpt}", "path": str(path), "sha256": sha256(path), "verified_ids": 415})
    g7proof = EVIDENCE / "g7_run_a_input_readiness.json"
    replace_report(g7proof, json.dumps({"status": "PARTIAL", "verified": verified, "split_sha256": sha256(select_ids),
                   "remaining": "Current G7 CLI needs Run B for joint choice"}, indent=2))
    item("G7", "PARTIAL", "Run A S0 to S3 verified on 415 D_dev_select IDs", g7proof, 0, "Run B inputs")
    progress()
    code, g8log = capture([sys.executable, "-B", "scripts/build_p1p2_analysis_figures.py", "--preflight"], "g8_preflight.json")
    if code == 0:
        available = sum(row["status"] == "AVAILABLE" for row in read_json(g8log)["figures"].values())
        if available:
            code, generation = capture([sys.executable, "-B", "scripts/build_p1p2_analysis_figures.py",
                                        "--output", EVIDENCE / "figures"], "g8_generation.log")
            assert code in (0, 4), generation
        item("G8", "PARTIAL" if available else "BLOCKED", f"{available}/7 figures have complete inputs", g8log, 0,
             "Run B inputs for full figure set")
    else:
        item("G8", "FAILED", "Figure preflight failed", g8log, code)
    progress()


def main():
    initialize()
    if sys.argv[1:] == ["--initialize-only"]:
        return
    active = "Preflight"
    try:
        shield = preflight()
        for ckpt in (1, 2, 3):
            active = f"Run A S{ckpt}"
            item(active, "PARTIAL", "Controller launched", EVIDENCE / "commands.jsonl", remaining="Awaiting audited completion")
            progress()
            code, path = capture(CLI + ["--round", str(ckpt)], f"S{ckpt}_controller.log")
            if code:
                item(active, "FAILED", "Controller exited before completing the checkpoint", path, code,
                     "Inspect subprocess traceback and preserve artifacts", "Resume only after diagnosis")
                raise RuntimeError(f"{active} exit {code}: {path}")
            RESULTS.append(audit(ckpt, shield, path))
            item(active, "DONE", "Real training, D_dev, hook, state and parent lineage verified", EVIDENCE / f"S{ckpt}_audit.json", code)
            progress()
        active = "Final verification"
        finalize(shield)
    except Exception:
        with (EVIDENCE / "failure_traceback.log").open("x", encoding="utf-8") as log:
            log.write(traceback.format_exc())
        if ITEMS.get(active, {}).get("status") != "FAILED":
            item(active, "BLOCKED" if active == "Preflight" else "FAILED", "Independent gate failed",
                 EVIDENCE / "failure_traceback.log", 1, "Inspect exception and preserve artifacts")
        progress()
        raise


if __name__ == "__main__":
    main()
