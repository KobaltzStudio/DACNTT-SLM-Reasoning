"""Validate the controlled stop and execute only the authorized P1P2 S1."""
from datetime import datetime, timezone
import csv
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

E = Path(__file__).resolve().parent
ROOT = E.parents[3]
FINAL = E.parent
A = ROOT / "reports/p1p2_integration/final_validation/run_a_20261118_030748"
PRIOR = ROOT / "reports/p1p2_integration/final_validation/runtime_20261118_024353_resume"
R = ROOT / "reports/p1p2_integration"
RUNS = ROOT / "runs/p1p2_integration"
MODELS = ROOT / "models/p1p2_integration"
AR, BR = RUNS / "P1-DEFICIT_seed13", RUNS / "P1P2_seed13"
AM, BM = MODELS / "P1-DEFICIT_seed13", MODELS / "P1P2_seed13"
sys.path.insert(0, str(ROOT / "scripts"))
from p1p2_controller import Controller, read_json, read_jsonl, sha256
from p1p2_capability_state import build_state, stable_state
from safetensors import safe_open
from select_checkpoint_on_dev import score

ENV = {**os.environ, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "PYTHONUNBUFFERED": "1",
       "PYTHONDONTWRITEBYTECODE": "1"}
CLI = [sys.executable, "-B", "scripts/run_p1_p2.py", "--method", "P1P2", "--seed", "13", "--round", "1",
       "--resume", "--dtype", "bf16", "--micro-batch", "1", "--nll-batch", "1", "--eval-batch", "1"]


def now():
    return datetime.now(timezone.utc).isoformat()


def write(name, data):
    with (E / name).open("x", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2)


def file_record(path):
    return {"path": str(path), "sha256": sha256(path)}


def progress(key, status, evidence, text, remaining="", code=None):
    path = FINAL / "p1p2_master_progress_seed13.json"
    data = read_json(path)
    row = {"id": key, "status": status, "completed": text, "evidence": str(evidence),
           "sha256": sha256(evidence) if evidence.is_file() else None, "exit_code": code,
           "remaining_work": remaining, "next_action": remaining, "phase": "controlled_run_b_s1"}
    data["items"] = [r if r["id"] != key else row for r in data["items"]]
    data["updated_utc"] = now()
    contents = ["# P1/P2 seed 13 master progress", "", data["updated_utc"], "",
                "| Gate | Status | Phase | Result and evidence | Exit | SHA-256 | Remaining |",
                "|---|---|---|---|---:|---|---|"]
    for r in data["items"]:
        link = f"[evidence](<{Path(r['evidence']).as_posix()}>)" if r["evidence"] else ""
        contents.append(f"| {r['id']} | {r['status']} | {r['phase']} | {r['completed']} {link} | "
                        f"{r['exit_code'] if r['exit_code'] is not None else ''} | {r['sha256'] or ''} | {r['remaining_work']} |")
    for dest, value in ((path, json.dumps(data, indent=2)), (path.with_suffix(".md"), "\n".join(contents))):
        tmp = E / f".{dest.name}.{os.getpid()}.tmp"
        with tmp.open("x", encoding="utf-8") as stream:
            stream.write(value + "\n")
        os.replace(tmp, dest)


def stop_audit():
    after = read_json(A / "control_stop_process_after.json")
    assert not any(after[key] for key in ("remaining_processes", "run_a_gpu_pids", "lock_present", "s3_started"))
    for artifact in read_json(A / "S1_audit.json")["artifacts"].values():
        assert sha256(Path(artifact["path"])) == artifact["sha256"], artifact
    assert not (AR / ".controller.lock").exists() and not (AM / "student_ckpt_003").exists()
    prediction = AR / "S2/eval_dev.jsonl"
    ids = set((ROOT / "splits/d_dev_ids.txt").read_text(encoding="utf-8-sig").split())
    raw = prediction.read_bytes()
    assert raw.endswith(b"\n"), "S2 JSONL does not end at a complete record, preserve for manual recovery"
    rows = [json.loads(line) for line in raw.splitlines()]
    names = [row["problem_id"] for row in rows]
    assert 0 < len(rows) < 500 and len(names) == len(set(names)) and set(names) <= ids
    assert all(row["checkpoint"] == "P1-DEFICIT_seed13_S2" and row["status"] in
               {"valid", "invalid_format", "invalid_answer"} for row in rows)
    c = Controller(ROOT, resume=True, dry_run=True, dtype="bf16", micro_batch=1, nll_batch=1, eval_batch=1)
    adapter = AM / "student_ckpt_002"
    c._validate_adapter(adapter, AM / "student_ckpt_001", 13, AR / "round_002/train_set.json")
    assert read_json(adapter / "train_log.json")["steps"] == 26
    assert read_json(AR / "S2/eval_dev.intent.json")["adapter_sha256"] == sha256(adapter)
    assert not prediction.with_suffix(".summary.json").exists()
    assert not (R / "capability_sidecars/P1-DEFICIT_seed13_S2").exists()
    assert not (R / "capability_state/P1-DEFICIT_seed13/selection_round_003.json").exists()
    assert [row["checkpoint"] for row in read_jsonl(AR / "checkpoint_log.jsonl")] == ["S1"]
    files = sorted(path for folder in (AR, AM) for path in folder.rglob("*") if path.is_file())
    inventory = [file_record(path) for path in files]
    write("run_a_stopped_verification.json", {"status": "S2_TRAINING_COMPLETE_EVALUATION_PARTIAL",
          "at_utc": now(), "stop": after, "s1_audit_sha256": sha256(A / "S1_audit.json"),
          "prediction_rows": len(rows), "prediction": file_record(prediction), "adapter": file_record(adapter),
          "artifacts": inventory, "resume": "Use --round 2 --resume with same hf, bf16 and batches. Then separately authorize S3."})
    with (E / "run_a_stopped_artifact_inventory.csv").open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["path", "sha256"])
        writer.writeheader()
        writer.writerows(inventory)
    with (E / "run_a_stopped_verification.md").open("x", encoding="utf-8") as stream:
        stream.write(f"# Run A controlled stop\n\nS2_TRAINING_COMPLETE_EVALUATION_PARTIAL\n\n"
                     f"Evaluator PID 52264 only. No remaining Run A processes, GPU PID, lock, or S3 launch. "
                     f"S1 audit hashes match. S2 adapter has 26 steps, validated predecessor and matching intent. "
                     f"{len(rows)} unique, valid JSONL records were preserved.\n\n"
                     "For later resumption use the unified controller with --method P1-DEFICIT --seed 13 "
                     "--round 2 --resume --backend hf --dtype bf16 --micro-batch 1 --nll-batch 1 --eval-batch 1. "
                     "Revalidate the preserved prefix before starting. Do not rerun S1.\n")
    progress("Run A S2", "PARTIAL", E / "run_a_stopped_verification.md",
             f"Controlled stop; 26 training steps, {len(rows)}/500 prediction rows", "Separate approval for evaluation resume", 1)
    return inventory


def run(args, log_name):
    path = E / log_name
    command = [str(a) for a in args]
    print(subprocess.list2cmdline(command), flush=True)
    start = now()
    began = time.monotonic()
    with path.open("xb") as log:
        p = subprocess.run(command, cwd=ROOT, env=ENV, stdout=log, stderr=subprocess.STDOUT)
    with (E / "commands.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"command": command, "started": start, "ended": now(),
                     "elapsed_s": time.monotonic() - began, "exit": p.returncode, **file_record(path)}) + "\n")
    return p.returncode, path


def preflight():
    # Recheck actual runtime and the exact frozen input fingerprints before launching GPU work.
    from huggingface_hub import try_to_load_from_cache
    gpu = json.loads(subprocess.check_output([sys.executable, "-B", "-c",
        "import json,torch; assert torch.cuda.is_available() and torch.cuda.is_bf16_supported(); "
        "print(json.dumps(dict(memory=torch.cuda.mem_get_info(),name=torch.cuda.get_device_name(),"
        "torch=torch.__version__,cuda=torch.version.cuda)))"], cwd=ROOT, env=ENV, text=True))
    free, total = gpu["memory"]
    assert free >= 5 * 2**30, free
    assert subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip() == "codex/controller-dryrun-fix"
    hashes = read_json(PRIOR / "source_sha256_manifest.json")["source_sha256"]
    source = {path: sha256(Path(path)) for path in hashes if Path(path).suffix in {".py", ".yaml"} or Path(path).name == "experiment_config.json"}
    assert all(hashes[path] == digest for path, digest in source.items())
    code, trace = run([sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-v"], "unit_tests.log")
    assert code == 0, trace
    c = Controller(ROOT, resume=True, dry_run=True, dtype="bf16", micro_batch=1, nll_batch=1, eval_batch=1)
    student = read_json(c.config)["student"]
    cached = try_to_load_from_cache(student["model"], "model.safetensors", revision=student["revision"])
    assert isinstance(cached, str) and Path(cached).stat().st_size > 0
    assert {path.name for path in BR.iterdir()} == {"round_001"} and not BM.exists()
    assert not (R / "capability_sidecars/P1P2_seed13_S1").exists()
    assert not (R / "capability_state/P1P2_seed13/selection_round_002.json").exists()
    train, log = BR / "round_001/train_set.json", BR / "round_001/selection_log.jsonl"
    saved = read_json(train)
    nll = Path(saved["nll_file"])
    state = Path(saved["state_file"])
    assert saved["priority_policy"]["alpha"] == 0.5 and saved["source_checkpoint"] == "S0"
    # Run the existing CPU selector into new evidence paths to verify the frozen selection exactly.
    code, trace = run([sys.executable, "-B", "scripts/p1p2_selector.py", "--method", "P1P2", "--seed", "13", "--round", "1",
                       "--state", state, "--nll", nll, "--out-dir", E / "recomputed_selection"], "selector_recheck.log")
    assert code == 0, trace
    rebuilt = read_json(E / "recomputed_selection/train_set.json")
    assert rebuilt == saved, "Recomputed train set differs from frozen Run B selection"
    assert read_jsonl(E / "recomputed_selection/selection_log.jsonl") == read_jsonl(log)
    code, trace = run(CLI + ["--dry-run"], "run_b_s1_dry_run.log")
    assert code == 0, trace
    plan_path = Path(next(row.split("=", 1)[1] for row in trace.read_text(encoding="utf-8").splitlines() if row.startswith("DRY_RUN_REPORT=")))
    plan = read_json(plan_path)
    assert plan["methods"] == ["P1P2"] and plan["target_checkpoints"] == [1]
    assert not any("compute_nll" in a["stage"] or "_S2" in a["stage"] or "_S3" in a["stage"] for a in plan["actions"])
    evaluation = next(a["command"] for a in plan["actions"] if a["stage"].startswith("eval_dev"))
    assert evaluation[evaluation.index("--split") + 1] == "dev"
    anchors = [c.config, c.pool, c.tokens, c.d_pool, c.dev_ids, c.gold_manifest, c.gold_labels, c.approval,
               c.s0_prediction, c.s0_reference, c.s0_sidecar, train, log, nll, state]
    protection = {str(path): sha256(path) for path in anchors}
    write("run_b_s1_preflight.json", {"status": "PASS", "source": source, "input_sha256": protection,
          "plan": file_record(plan_path), "selected": saved["n_selected"], "tokens_used": saved["tokens_used"],
          "budget": saved["beta_round_tokens"], "gpu": gpu["name"], "free_bytes": free, "total_bytes": total,
          "environment": {"python": sys.version, "torch": gpu["torch"], "cuda": gpu["cuda"],
                          "student": student, "cache_weights": cached}, "at": now()})
    return protection


def validate(anchors, preserved):
    c = Controller(ROOT, resume=True, dry_run=True, dtype="bf16", micro_batch=1, nll_batch=1, eval_batch=1)
    c.run_method_seed("P1P2", 13, [1])
    assert not c.actions, c.actions
    for path, digest in anchors.items():
        assert sha256(Path(path)) == digest
    for entry in preserved:
        assert sha256(Path(entry["path"])) == entry["sha256"]
    assert not (AM / "student_ckpt_003").exists() and not (BR / ".controller.lock").exists()
    assert {folder.name for folder in BM.iterdir()} == {"student_ckpt_001"}
    assert {p.name for p in BR.iterdir()} == {"round_001", "S1", "checkpoint_log.jsonl"}
    assert not any(f.name.startswith("nll") for f in BR.rglob("*") if f.is_file())
    model = BM / "student_ckpt_001"
    out = BR / "S1/eval_dev.jsonl"
    sidecar = R / "capability_sidecars/P1P2_seed13_S1"
    state = R / "capability_state/P1P2_seed13/selection_round_002.json"
    weights = model / "adapter_model.safetensors"
    with safe_open(weights, framework="pt", device="cpu") as handle:
        assert any("lora_A" in key for key in handle.keys())
    trainlog = read_json(model / "train_log.json")
    assert trainlog["checkpoint_parent"] == "student_ckpt_000" and trainlog["checkpoint_parent_sha256"] is None
    assert trainlog["grad_accum"] == 8 and trainlog["effective_batch"] == 8 and trainlog["dtype"] == "bfloat16"
    assert trainlog["epochs_from_config"] and trainlog["lr_from_config"]
    assert trainlog["steps"] == math.ceil(trainlog["n_examples"] / 8)
    assert all(math.isfinite(step["loss"]) for step in trainlog["steps_log"])
    summary = read_json(out.with_suffix(".summary.json"))
    ids = set(c.dev_ids.read_text(encoding="utf-8-sig").split())
    result = score(out, ids)
    assert len(ids) == 500 and result["missing"] == 0 and result["accuracy"] == summary["accuracy"]
    assert summary["split"] == "dev" and summary["limit"] is None and Path(summary["adapter"]).resolve() == model
    assert stable_state(read_json(state)) == stable_state(build_state(sidecar, "P1P2", 13))
    paths = {"adapter": model, "adapter_weights": weights, "train_log": model / "train_log.json",
             "prediction": out, "summary": out.with_suffix(".summary.json"), "sidecar": sidecar,
             "sidecar_manifest": sidecar / "student_capability_evaluation_manifest.json",
             "capability_state": state, "checkpoint_log": BR / "checkpoint_log.jsonl",
             "train_set": BR / "round_001/train_set.json", "selection_log": BR / "round_001/selection_log.jsonl"}
    info = {"status": "PASS", "method": "P1P2", "seed": 13, "checkpoint": "S1", "command": CLI,
            "train_seconds": trainlog["elapsed_seconds"], "steps": trainlog["steps"], "examples": trainlog["n_examples"],
            "final_loss": trainlog["steps_log"][-1]["loss"], "peak_allocated_gib": trainlog["peak_gpu_memory_gb"],
            "peak_reserved_bytes": trainlog["peak_gpu_reserved_bytes"], "strict_d_dev": result,
            "eval_seconds": summary["elapsed_seconds_this_run"], "gold": 85, "capabilities": 7, "at": now(),
            "artifacts": {name: file_record(path) for name, path in paths.items()}}
    write("run_b_seed13_s1_validation.json", info)
    with (E / "run_b_seed13_s1_artifact_inventory.csv").open("x", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["artifact", "path", "sha256"])
        writer.writerows((name, entry["path"], entry["sha256"]) for name, entry in info["artifacts"].items())
    with (E / "run_b_seed13_s1_validation.md").open("x", encoding="utf-8") as stream:
        stream.write("# Run B P1P2 seed 13 S1\n\nPASS. Frozen S0 selection was verified and reused. "
                     f"LoRA steps {info['steps']}, strict D_dev {result['correct']}/500 "
                     f"({result['accuracy']:.1%}), Gold 85, seven capabilities. No pending resume action. "
                     "S2/S3 and D_test were outside execution.\n")
    progress("Run B S1", "DONE", E / "run_b_seed13_s1_validation.json",
             f"LoRA, D_dev {result['accuracy']:.1%}, Gold sidecar and next state verified", "", 0)


if __name__ == "__main__":
    preserved = stop_audit()
    if sys.argv[1:] == ["--stop-audit-only"]:
        raise SystemExit(0)
    anchor = preflight()
    progress("Run B S1", "PARTIAL", E / "run_b_s1_preflight.json", "Preflight passed; executing only S1", "Audit 500 D_dev and hook")
    code, log = run(CLI, "run_b_s1_controller.log")
    if code:
        progress("Run B S1", "FAILED", log, "Controller exited nonzero; preserved outputs", "Review traceback", code)
        raise SystemExit(code)
    validate(anchor, preserved)
