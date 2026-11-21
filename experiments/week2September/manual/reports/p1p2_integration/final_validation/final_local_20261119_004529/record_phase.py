"""Persist observed phase evidence without running workflows."""
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

MANUAL = Path.cwd()
EVIDENCE = Path(__file__).resolve().parent
RECOVERY = MANUAL / "reports/p1p2_integration/session_recovery"
STAGING = Path("C:/Users/PC - NGHI/Desktop/Pipeline/p1p2_unified/runpod_package_20261119_004529")
NEXT = {
    0: "Audit controller, hook and D_test history, then test the CPU guard.",
    1: "Reproduce read-only G6/G7/G8 against frozen outputs.",
    2: "Validate transfer dependency closure and path mappings.",
    3: "Copy the allowlist to a new detached package and verify each SHA.",
    4: "Record and syntax-check Linux commands without executing them.",
    5: "Classify source tree and audit ZIP members without extraction.",
    6: "Run final CPU acceptance and recheck protected files and Git.",
    7: "Use the deployment checklist on an approved Linux host; await separate execution approvals.",
}
APPROVALS = ["Linux/RunPod deployment and any GPU execution", "A S2/S3 and B S2/S3 scope",
             "Final D_test after G7 is explicitly frozen", "Original repository cleanup/migration"]


def read(path):
    return path.read_text(encoding="utf-8-sig")


def write(path, text):
    tmp = path.with_name(path.name + ".phase_tmp")
    with tmp.open("x", encoding="utf8", newline="\n") as stream:
        stream.write(text)
    tmp.replace(path)


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    phase, status, command, exit_code, *artifacts = sys.argv[1:]
    phase, exit_code = int(phase), int(exit_code)
    observed = datetime.now(timezone.utc).isoformat()
    branch = subprocess.check_output(["git", "branch", "--show-current"], text=True).strip()
    if branch != "codex/controller-dryrun-fix":
        raise ValueError(f"Unexpected branch: {branch}")
    git = subprocess.check_output(
        ["git", "--no-optional-locks", "status", "--short", "--branch"], text=True)
    with (EVIDENCE / f"git_phase_{phase}.txt").open("x", encoding="utf8") as f:
        f.write(git)
    paths = [EVIDENCE / path for path in [*artifacts, f"git_phase_{phase}.txt"]]
    record = {"status": status, "at_utc": observed, "command": command, "exit": exit_code,
              "evidence": [{"path": str(p), "sha256": sha(p)} for p in paths], "next": NEXT[phase]}
    state_path = RECOVERY / "CURRENT_STATE.json"
    data = json.loads(read(state_path))
    state = data.get("final_local_readiness", {})
    if state.get("report_root") != str(EVIDENCE):
        state = {"report_root": str(EVIDENCE), "staging_root": str(STAGING), "phases": {},
                 "manual_root": str(MANUAL), "branch": branch, "pending_approvals": APPROVALS,
                 "protected_inventory": str(EVIDENCE / "protected_artifact_inventory.csv"),
                 "execution": {"gpu": "NOT_RUN", "d_test": "NOT_RUN", "runpod": "NOT_RUN"},
                 "d_test_readiness": "PARTIAL", "runpod_readiness": "PENDING_LINUX"}
    state["phases"][str(phase)] = record
    state.update({"current_phase": phase, "last_milestone": command, "next_safe_action": NEXT[phase]})
    if phase == 7:
        state["windows_staging"] = "PASS"
        state["original_cleanup"] = "PENDING_APPROVAL"
        state["package_fingerprints"] = json.loads(read(EVIDENCE / "final_integrity.json"))
        state["d_test_readiness"] = "PARTIAL_G7_NOT_FINAL"
        state["evaluator_audit_sha256"] = sha(EVIDENCE / "d_test_input_audit.json")
        state["next_safe_commands"] = ["git --no-optional-locks status --short --branch",
            "Get-FileHash -Algorithm SHA256 <package>/manifests/SHA256SUMS.txt",
            "python -B scripts/run_final_d_test.py --audit-only"]
        data["observed_at_utc"] = observed
        data["git"] = {"exit_code": 0, "stdout": git, "report": str(EVIDENCE / f"git_phase_{phase}.txt")}
    data["final_local_readiness"] = state
    write(state_path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    summary = "\n".join(f"- Phase {p}: {r['status']} · {r['command']} · exit {r['exit']}"
                        for p, r in state["phases"].items())
    orientation = (f"# NEXT_SESSION_START_HERE\n\nWorking directory: `{MANUAL}`\n"
                   f"Branch: `{branch}`\nEvidence: `{EVIDENCE}`\nStaging: `{STAGING}`\n"
                   f"Last observed UTC: {observed}\nCurrent phase: {phase}\n"
                   f"Last command: `{command}`\nNext safe action: {NEXT[phase]}\n\n{summary}\n\n"
                   "Run A S1 and Run B S1 are verified. Preserve the 75/500 D_dev rows of A S2. "
                   "Read CURRENT_STATE.json for evidence paths and SHA, then recheck Git, processes, GPU, locks and files. "
                   "G7 must be FINAL and its SHA pinned before any authorized D_test. D_test, training and RunPod were NOT_RUN.\n")
    if phase == 7:
        package = state["package_fingerprints"]
        orientation += (f"\nWindows staging PASS. Linux PENDING. G9 NOT RUN / DELEGATED. "
            f"Package holds {package['package_total_files']} files / {package['package_total_bytes']} bytes. "
            f"SHA256SUMS.txt SHA-256: `{package['sha256sums_sha256']}`.\n"
            "D_TEST_READINESS=PARTIAL; D_TEST_EXECUTION=NOT_RUN. Cleanup of originals is PENDING APPROVAL.\n"
            f"Verified protected inventory: `{state['protected_inventory']}`.\n")
        with (EVIDENCE / "RECOVERY_FINAL_SNAPSHOT.md").open("x", encoding="utf8", newline="\n") as snapshot:
            snapshot.write(orientation)
    write(RECOVERY / "CURRENT_STATE.md", orientation)
    write(RECOVERY / "TASK_CHECKLIST.md", "# Final local readiness checkpoints\n\n" + summary + "\n")
    write(RECOVERY / "RECOVERY_GUIDE.md", orientation + "\n## Required approvals\n\n" +
          "\n".join("- " + item for item in APPROVALS) +
          "\n\nContinue from the first incomplete phase after revalidation. Do not run the previous Run B watcher.\n")
    with (RECOVERY / "COMMAND_HISTORY.md").open("a", encoding="utf8") as stream:
        stream.write(f"\n- {observed} final-local phase {phase} {status}, exit {exit_code}, `{command}`, "
                     f"evidence `{EVIDENCE}`.\n")
    print(f"phase {phase} {status}; recovery updated")


if __name__ == "__main__":
    main()
