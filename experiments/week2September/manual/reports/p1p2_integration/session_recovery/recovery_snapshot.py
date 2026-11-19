"""Passive recovery snapshots. This program never starts, stops or resumes a run."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

RECOVERY = Path(__file__).resolve().parent
ROOT = RECOVERY.parents[2]
E = ROOT / "reports/p1p2_integration/final_validation/run_b_s1_20261118_091644"
A = ROOT / "reports/p1p2_integration/final_validation/run_a_20261118_030748"
CMD = [r"C:\KLTN-SLM-Reasoning\.venv\Scripts\python.exe", "-B", "scripts/run_p1_p2.py",
       "--method", "P1P2", "--seed", "13", "--round", "1", "--resume", "--dtype", "bf16",
       "--micro-batch", "1", "--nll-batch", "1", "--eval-batch", "1"]
LOG = E / "run_b_s1_controller.log"
RUN = ROOT / "runs/p1p2_integration/P1P2_seed13"
ADAPTER = ROOT / "models/p1p2_integration/P1P2_seed13/student_ckpt_001"
SIDE = ROOT / "reports/p1p2_integration/capability_sidecars/P1P2_seed13_S1"
STATE = ROOT / "reports/p1p2_integration/capability_state/P1P2_seed13/selection_round_002.json"


def read(path, default=None):
    return json.loads(path.read_text(encoding="utf-8-sig")) if path.is_file() else default


def digest(path):
    if not path.is_file():
        return None
    with path.open("rb") as src:
        return hashlib.file_digest(src, "sha256").hexdigest()


def capture(args):
    try:
        p = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=12,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return {"exit_code": p.returncode, "stdout": p.stdout.strip(), "stderr": p.stderr.strip()}
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"exit_code": None, "error": str(error)}


def atomic(name, content):
    dest = RECOVERY / name
    tmp = RECOVERY / f".{name}.{os.getpid()}.tmp"
    with tmp.open("w", encoding="utf-8", newline="\n") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, dest)


def artifact(path, *, mutable=False):
    size = path.stat().st_size if path.is_file() else None
    return {"path": str(path), "exists": path.exists(), "bytes": size,
            "sha256": None if mutable else digest(path), "mutable_during_run": mutable}


def rows(path):
    if path.is_file():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def snapshot():
    with LOG.open("rb") as f:
        f.seek(max(0, os.fstat(f.fileno()).st_size - 32768))
        tail = f.read().decode("utf-8", errors="replace")
    matches = list(re.finditer(r"\[P1P2_seed13_S1\] (\d+)/500", tail))
    summary = RUN / "S1/eval_dev.summary.json"
    count = 500 if summary.is_file() else int(matches[-1].group(1)) if matches else 0
    audit = E / "run_b_seed13_s1_validation.json"
    commands = list(rows(E / "commands.jsonl"))
    command_result = next((command for command in reversed(commands)
                           if str(command.get("path", "")).endswith("run_b_s1_controller.log")), None)
    stages = {
        "training": "PASS" if (ADAPTER / "train_log.json").is_file() else "RUNNING",
        "d_dev": "PASS" if summary.is_file() else "RUNNING" if "[P1P2_seed13_S1] dev:" in tail or count else "NOT_STARTED",
        "hook": "PASS" if (SIDE / "student_capability_evaluation_manifest.json").is_file() else "NOT_STARTED",
        "capability_state": "PASS" if STATE.is_file() else "NOT_STARTED",
        "final_validation": "PASS" if read(audit, {}).get("status") == "PASS" else "NOT_STARTED",
    }
    # A completed stage with a published file is recorded as provisional evidence
    # until the independent checkpoint audit passes.
    if stages["final_validation"] != "PASS":
        for step in stages:
            if stages[step] == "PASS":
                stages[step] = "PARTIAL"
    live = capture(["powershell.exe", "-NoProfile", "-Command",
                    "$p=@(Get-CimInstance Win32_Process -ErrorAction Stop -Filter \"Name = 'python.exe'\" | "
                    "Where-Object {$_.CommandLine -match 'run_a_local\\.py|run_b_s1\\.py|run_p1_p2\\.py|train_round\\.py|eval_student\\.py'} | "
                    "Select-Object ProcessId,ParentProcessId,CommandLine,CreationDate); ConvertTo-Json -InputObject $p -Depth 4"])
    if live.get("exit_code") == 0:
        live["processes"] = json.loads(live.pop("stdout"))
    running = any("run_b_s1.py" in entry.get("CommandLine", "") for entry in live.get("processes", []))
    if stages["final_validation"] == "PASS":
        status, next_step = "PASS", "Complete analysis, cleanup audit and documentation only"
    elif command_result and command_result.get("exit") != 0:
        status, next_step = "FAILED", "Preserve artifacts and inspect nonzero command log before any resume"
    elif running:
        status, next_step = "RUNNING", "Monitor only, do not duplicate, stop or restart this process"
    else:
        status, next_step = "BLOCKED", "Refresh process tree and inspect log/audit boundary before authorizing any resume"
    final = E / "deliverables_index_final.json"
    if not final.is_file():
        final = E / "deliverables_index.json"
    ready = read(final, {})
    if status == "PASS" and ready:
        next_step = "Current scope complete; await separate authorization for another round"
    g6 = E / "g6/g6_pretraining_inventory.json"
    g7 = E / "g7/checkpoint_selection_seed13_partial.json"
    cleanup = E / "repository_cleanup_inventory.csv"
    docs = E / "post_validation_plan_update.md"
    stop = E / "run_a_stopped_verification.json"
    tasks = {
        "Run A S1": {"status": "PASS", "method": "P1-DEFICIT", "seed": 13, "round": 1, "checkpoint": "S1",
                     "validation": artifact(A / "S1_audit.json"), "next_action": "Reuse immutable verified artifacts"},
        "Run A S2": {"status": "PARTIAL", "method": "P1-DEFICIT", "seed": 13, "round": 2, "checkpoint": "S2",
                     "validation": artifact(stop), "details": read(stop, {}).get("status"),
                     "next_action": "Remain stopped, future evaluation requires separate authorization"},
        "Run A S3": {"status": "NOT_STARTED", "next_action": "Outside current authorization"},
        "Run B S1": {"status": status, "method": "P1P2", "seed": 13, "round": 1, "checkpoint": "S1",
                     "command": CMD, "cwd": str(ROOT), "log": str(LOG), "prediction_rows_observed": count,
                     "stages": stages, "preflight": artifact(E / "run_b_s1_preflight.json"),
                     "training_log": artifact(ADAPTER / "train_log.json"), "prediction": artifact(
                         RUN / "S1/eval_dev.jsonl", mutable=status != "PASS"),
                     "adapter_directory": str(ADAPTER), "hook_manifest": artifact(SIDE / "student_capability_evaluation_manifest.json"),
                     "capability_state": artifact(STATE), "validation": artifact(audit), "next_action": next_step},
        "Run B S2/S3": {"status": "NOT_STARTED", "next_action": "Outside current authorization"},
        "G6": {"status": "PARTIAL" if g6.is_file() else "BLOCKED", "evidence": artifact(g6),
               "next_action": "Refresh inventory on validated data, full matrix needs remaining checkpoints"},
        "G7": {"status": "PARTIAL" if g7.is_file() else "BLOCKED", "evidence": artifact(g7),
               "next_action": "No final checkpoint choice until complete S0 to S3"},
        "G8": {"status": "PARTIAL" if ready.get("figures") else "BLOCKED",
               "evidence": ready.get("figures"), "next_action": "Generate only real available observations, record gaps"},
        "RunPod handoff": {"status": "PARTIAL", "evidence": artifact(E / "runpod_handoff.md"),
                           "next_action": "Linux execution remains delegated; no RunPod jobs"},
        "Documentation": {"status": "PASS" if docs.is_file() and ready else "PARTIAL",
                          "evidence": artifact(docs), "next_action": "Preserve original DOCX, update guide with verified facts"},
        "Cleanup audit": {"status": "PASS" if (E / "repository_cleanup_proposal.md").is_file() else "NOT_STARTED",
                          "evidence": artifact(cleanup), "next_action": "Audit only, no delete or rename"},
    }
    info = {"observed_at_utc": datetime.now(timezone.utc).isoformat(), "repository": str(ROOT),
            "process_tree": live, "gpu": capture(["nvidia-smi", "--query-gpu=name,memory.used,memory.free,utilization.gpu",
                                                  "--format=csv,noheader"]),
            "git": capture(["git", "--no-optional-locks", "status", "--short", "--branch"]),
            "task_evidence_directory": str(E), "tasks": tasks, "required": "Revalidate live process/GPU/Git/file state before resume"}
    atomic("CURRENT_STATE.json", json.dumps(info, indent=2) + "\n")
    lines = ["# Persistent P1/P2 session state", "", f"Observed UTC {info['observed_at_utc']}", "",
             f"Working directory `{ROOT}`", "", f"Run B S1/status **{status}**", "",
             f"Observed D_dev predictions {count}/500. This is progress evidence until the independent audit passes.", "",
             "| Task | Status | Next |", "|---|---|---|"]
    lines.extend(f"| {key} | {value['status']} | {value['next_action']} |" for key, value in tasks.items())
    lines += ["", f"Exact Run B argv `{subprocess.list2cmdline(CMD)}`", "", f"Controller log `{LOG}`",
              "", "See CURRENT_STATE.json for paths, hashes, subprocess hierarchy and GPU/Git observations."]
    atomic("CURRENT_STATE.md", "\n".join(lines) + "\n")
    atomic("TASK_CHECKLIST.md", "# Current scope checklist\n\n" + "\n".join(
        f"- [{'x' if row['status'] == 'PASS' else ' '}] {key} — {row['status']}. {row['next_action']}"
        for key, row in tasks.items()) + "\n")
    all_commands = [*rows(A / "commands.jsonl"), *commands]
    command_lines = ["# Command history", "", "All controller invocations recorded by the active wrappers.", ""]
    for row in all_commands:
        code = row.get("exit_code", row.get("exit"))
        command_lines.append(f"- Exit `{code}` · `{subprocess.list2cmdline(row['command'])}` · log `{row.get('path', row.get('log'))}`")
    if command_result is None:
        command_lines.append(f"- Active or awaiting confirmation · `{subprocess.list2cmdline(CMD)}` · log `{LOG}`")
    command_lines.append("- Run A: controlled Windows stop of only verified S2 evaluator PID 52264. See run_a_stopped_verification.json.")
    atomic("COMMAND_HISTORY.md", "\n".join(command_lines) + "\n")
    print(info["observed_at_utc"], status, count, stages, flush=True)
    return status, bool(ready)


if __name__ == "__main__":
    if sys.argv[1:] != ["--watch"]:
        snapshot()
    else:
        last = None
        stop_at = time.monotonic() + 12 * 60 * 60
        while time.monotonic() < stop_at:
            key = tuple(path.is_file() for path in (
                ADAPTER / "train_log.json", RUN / "S1/eval_dev.summary.json",
                SIDE / "student_capability_evaluation_manifest.json", STATE, E / "run_b_seed13_s1_validation.json",
                E / "g6/g6_pretraining_inventory.json", E / "g7/checkpoint_selection_seed13_partial.json",
                E / "deliverables_index.json",
            ))
            # Refresh periodically while active for reconnect diagnosis, in addition to milestone transitions.
            slot = int(time.monotonic() // 300)
            marker = (key, slot)
            if marker != last:
                status, complete = snapshot()
                last = marker
                if status == "FAILED" or complete:
                    break
            time.sleep(45)
