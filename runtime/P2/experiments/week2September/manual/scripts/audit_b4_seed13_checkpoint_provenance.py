from pathlib import Path
import hashlib
import json
import subprocess
import datetime

REPO = Path(r"C:\Users\PC - NGHI\Desktop\Pipeline\P2")
MANUAL = REPO / "experiments" / "week2September" / "manual"
OUT = MANUAL / "reports" / "p1p2_integration" / "b4_seed13_checkpoint_provenance_audit.txt"

HASH_RUN = "332b2c4849a12dcf53ddb974b4152319ec140818c2c25baf7cb238a5a8b9abee"
HASH_STAGING = "17cf4b837dc42ac5145aea762847ca5dfba4bae58d253560b3b0dd6a254b73c5"

CHECKPOINT_ROOT = REPO / "integration_staging" / "P1" / "models" / "task7" / "B4" / "seed_13"
RUN_ROOT = MANUAL / "runs" / "main" / "B4_seed13"
STAGING_ROOT = MANUAL / "integration_staging" / "P1" / "reports" / "task7" / "B4" / "seed_13"

EXCLUDE = {".git", ".venv", "__pycache__", "node_modules"}

lines = []

def log(x=""):
    print(x)
    lines.append(str(x))

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def run_git(args):
    try:
        p = subprocess.run(
            ["git", *args],
            cwd=REPO,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except Exception as e:
        return 999, "", str(e)

def timestamp(path):
    st = path.stat()
    return datetime.datetime.fromtimestamp(
        st.st_mtime
    ).astimezone().isoformat(timespec="seconds")

log("=== REPOSITORY ===")
log(f"REPO={REPO}")
log(f"REPO_EXISTS={REPO.exists()}")
rc, out, err = run_git(["rev-parse", "--show-toplevel"])
log(f"GIT_ROOT={out}")
log(f"GIT_ROOT_EXIT={rc}")
rc, out, err = run_git(["rev-parse", "HEAD"])
log(f"GIT_HEAD={out}")
rc, out, err = run_git(["status", "--short"])
log("GIT_STATUS:")
log(out if out else "(clean)")
if err:
    log(f"GIT_STATUS_STDERR={err}")

log("\n=== CHECKPOINT DIRECTORY INVENTORY ===")
for ckpt in range(1, 4):
    name = f"student_ckpt_{ckpt:03d}"
    folder = CHECKPOINT_ROOT / name
    log(f"\n[{name}] PATH={folder} EXISTS={folder.exists()}")
    if not folder.exists():
        continue
    for p in sorted(folder.iterdir()):
        if p.is_file():
            log(
                f"FILE={p.name} SIZE={p.stat().st_size} "
                f"SHA256={sha256(p)} MTIME={timestamp(p)}"
            )

    train_log = folder / "train_log.json"
    if train_log.exists():
        try:
            obj = json.loads(train_log.read_text(encoding="utf-8-sig"))
            log("TRAIN_LOG_FIELDS:")
            for key in sorted(obj):
                value = obj[key]
                log(f"  {key} = {json.dumps(value, ensure_ascii=False)}")
        except Exception as e:
            log(f"TRAIN_LOG_PARSE_ERROR={e}")

log("\n=== WORKTREE CONFIG HASH SEARCH ===")
config_files = []
for p in REPO.rglob("*.json"):
    if any(part in EXCLUDE for part in p.parts):
        continue
    try:
        h = sha256(p)
    except Exception:
        continue
    if h in {HASH_RUN, HASH_STAGING} or "experiment_config" in p.name.lower():
        config_files.append((p, h))

if not config_files:
    log("NO_MATCHING_CONFIG_FILES_FOUND")
else:
    for p, h in sorted(config_files, key=lambda x: str(x[0]).lower()):
        log(f"CONFIG={p} SHA256={h} MTIME={timestamp(p)}")
        if h == HASH_RUN:
            log("  MATCHES_RUN_CONFIG_HASH=True")
        if h == HASH_STAGING:
            log("  MATCHES_STAGING_CONFIG_HASH=True")

log("\n=== OTHER TRAIN LOGS IN REPOSITORY ===")
train_logs = []
for p in REPO.rglob("train_log.json"):
    if any(part in EXCLUDE for part in p.parts):
        continue
    train_logs.append(p)

for p in sorted(train_logs, key=lambda x: str(x).lower()):
    try:
        obj = json.loads(p.read_text(encoding="utf-8-sig"))
        log(
            f"TRAIN_LOG={p} SHA256={sha256(p)} "
            f"CONFIG={obj.get('config_sha256', obj.get('config_hash'))} "
            f"TRAIN_SET={obj.get('train_set_sha256')} "
            f"N={obj.get('n_examples')} "
            f"SEED={obj.get('training_seed', obj.get('seed'))}"
        )
    except Exception as e:
        log(f"TRAIN_LOG={p} PARSE_ERROR={e}")

log("\n=== GIT HISTORY: EXPERIMENT CONFIG FILES ===")
rc, out, err = run_git([
    "log", "--all", "--date=iso-strict",
    "--format=COMMIT %H DATE %ad SUBJECT %s",
    "--name-only", "--", "experiment_config.json"
])
log(out if out else "(no experiment_config.json history found)")
if err:
    log(f"GIT_HISTORY_STDERR={err}")

log("\n=== GIT HISTORY: CONFIG UNDER MANUAL ===")
config_rel = "experiments/week2September/manual/integration_staging/P1/config/experiment_config.json"
rc, out, err = run_git([
    "log", "--all", "--follow", "--date=iso-strict",
    "--format=COMMIT %H DATE %ad SUBJECT %s",
    "--", config_rel
])
log(out if out else "(no history for expected config path)")
if err:
    log(f"GIT_CONFIG_HISTORY_STDERR={err}")

log("\n=== GIT TRACKED CONFIG CONTENT HASHES ===")
rc, out, err = run_git(["rev-list", "--all", "--", "experiment_config.json"])
commits = [x.strip() for x in out.splitlines() if x.strip()]
log(f"CONFIG_HISTORY_COMMITS={len(commits)}")

seen = set()
for commit in commits:
    rc2, paths, err2 = run_git([
        "ls-tree", "-r", "--name-only", commit
    ])
    if rc2 != 0:
        continue
    for rel in paths.splitlines():
        if not rel.lower().endswith("experiment_config.json"):
            continue
        key = (commit, rel)
        if key in seen:
            continue
        seen.add(key)
        rc3, content, err3 = run_git(["show", f"{commit}:{rel}"])
        if rc3 != 0:
            continue
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        # Git show text output may normalize line endings. Record this as
        # a content-level candidate, not proof of raw working-file identity.
        if digest in {HASH_RUN, HASH_STAGING}:
            log(
                f"GIT_CONFIG_HASH_CANDIDATE COMMIT={commit} "
                f"PATH={rel} SHA256_TEXT={digest}"
            )

log("\n=== RELATED RUN AND STAGING ARTIFACT HASHES ===")
for label, root in [
    ("RUN", RUN_ROOT),
    ("STAGING", STAGING_ROOT),
]:
    log(f"\n[{label}] {root}")
    for r in range(3):
        p = root / f"round_{r:03d}" / "train_set.json"
        if p.exists():
            log(f"ROUND={r} PATH={p} SHA256={sha256(p)}")

log("\n=== FINAL ===")
log("PROVENANCE_AUDIT_COMPLETE_READ_ONLY")
log("No training, checkpoint, config, prediction, or lineage files were modified.")

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"\nREPORT_SAVED={OUT}")
