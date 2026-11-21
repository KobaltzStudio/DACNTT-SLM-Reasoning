"""Record evidence for this independent handoff workspace only."""
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import sys

HOME_DIR = Path(__file__).resolve().parent
ROOT = HOME_DIR.parent
ORDER = "ABCDEFGHIJ"
TOPICS = dict(zip(ORDER, ("Layout", "Source consolidation", "Artifact and visibility checks",
                         "Deployment", "Remaining analysis", "Future research", "GitHub",
                         "Acceptance", "Operator handoff", "Release report")))


def sha(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def write(path, content):
    temp = path.with_name(path.name + ".handoff_tmp")
    with temp.open("x", encoding="utf-8", newline="\n") as f:
        f.write(content)
    os.replace(temp, path)


def main():
    phase, result, code, command, blocker, *paths = sys.argv[1:]
    now = datetime.now(timezone.utc).isoformat()
    state_path = HOME_DIR / "CURRENT_STATE.json"
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
    else:
        state = {"worktree": ".", "runtime": "runtime", "package": "runpod_package_20261119_004529",
                 "inherited_source_branch": "codex/controller-dryrun-fix",
                 "inherited_source_head": "a26f420b0b4203890c2d86be1d3852a645aeb65d",
                 "phases": {}, "linux": "PENDING", "gpu": "NOT_RUN", "d_test": "NOT_RUN"}
    idx = ORDER.index(phase)
    evidence = {}
    for name in paths:
        path = ROOT / name
        if not path.resolve().is_relative_to(ROOT) or not path.is_file():
            raise ValueError(f"Invalid evidence: {name}")
        evidence[name] = sha(path)
    next_step = (TOPICS[ORDER[idx + 1]] if idx + 1 < len(ORDER)
                 else "Obtain publication/transfer approval; verify the Linux CPU working tree.")
    item = {"phase": phase, "topic": TOPICS[phase], "status": result,
            "exit_code": int(code), "command_or_check": command,
            "evidence_sha256": evidence, "blocker": blocker, "next": next_step, "utc": now}
    state["phases"][phase] = item
    state["last"] = item
    write(state_path, json.dumps(state, indent=2, ensure_ascii=False) + "\n")
    summary = [f"- {k} {TOPICS[k]} — {state['phases'].get(k, {}).get('status', 'PENDING')}"
               for k in ORDER]
    write(HOME_DIR / "CURRENT_STATE.md", "# Handoff state\n\n" +
          f"Last observed UTC {now}. Next: {next_step}\n\n" + "\n".join(summary) + "\n\n" +
          "See CURRENT_STATE.json for exact phase checks, exit codes, evidence hashes and blockers.\n")
    write(HOME_DIR / "TASK_CHECKLIST.md", "# Handoff checklist\n\n" + "\n".join(summary) + "\n")
    write(HOME_DIR / "RECOVERY_GUIDE.md", "# NEXT_SESSION_START_HERE\n\n" +
          "Open CURRENT_STATE.json and the operator handoff. Recheck live processes, locks, manifest and inputs. "
          "Preserve verified S1 checkpoints and the A S2 75-row D_dev prefix; keep logs and failed attempts. "
          "Verify the sealed package before preparing a new work tree. Release permission, host/upload, GPU, "
          "each checkpoint, D_test and cleanup require their respective approvals. No authorization is inherited.\n\n"
          f"Next step recorded at {now}: {next_step}\n")
    with (HOME_DIR / "COMMAND_HISTORY.md").open("a", encoding="utf-8") as f:
        f.write(f"\n- {now} phase {phase} {result}, exit {code}. {command}. Blocker: {blocker}. "
                f"Evidence: {', '.join(paths)}\n")
    print(f"{phase}: {result}; recovery updated")


if __name__ == "__main__":
    main()
