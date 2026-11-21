"""Verify, prepare and operate a bounded P1/P2 handoff using the sealed runtime."""
import argparse
import contextlib
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
MANUAL = Path("P2/experiments/week2September/manual")
AUDIT_CACHE = "97b5db3ae70d9a73a0961c2c56424eff49cb8da9324d455356c8c049adb31630"
INDEX_PIN = "dbe0d5bb0b2b80df5d0b4f41ff57b3318a543c264e2d5b20c5c7f818e0424f62"
SUMS_PIN = "bf0c50c301de9e2b78d9533a6a995733a431a6834d8ad019926e1c826af07798"
MODIFIABLE_PREFIXES = {
    f"{MANUAL.as_posix()}/runs/p1p2_integration/P1-DEFICIT_seed13/S2/eval_dev.jsonl",
    f"{MANUAL.as_posix()}/runs/p1p2_integration/P1-DEFICIT_seed13/checkpoint_log.jsonl",
    f"{MANUAL.as_posix()}/runs/p1p2_integration/P1P2_seed13/checkpoint_log.jsonl",
}
A_S2_PREFIX = next(x for x in MODIFIABLE_PREFIXES if x.endswith("/eval_dev.jsonl"))
EXPECTED_VERSIONS = {
    "torch": "2.13.0+cu126", "transformers": "5.15.0", "peft": "0.20.0",
    "accelerate": "1.14.0", "tokenizers": "0.22.2", "huggingface-hub": "1.27.0",
    "safetensors": "0.8.0", "PyYAML": "6.0.3", "matplotlib": "3.11.2",
}


def ensure(ok, reason):
    if not ok:
        raise ValueError(reason)


def sha(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path, data):
    with path.open("x", encoding="utf8", newline="\n") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def relative(name):
    path = PurePosixPath(name)
    ensure(path.parts and not path.is_absolute() and path.as_posix() == name
           and not any(p == ".." or p.endswith((".", " ")) or any(c in p for c in "\\:\r\n")
                       for p in path.parts), f"Invalid manifest path: {name}")
    return path


def reject_link(path):
    attrs = path.lstat()
    ensure(not path.is_symlink()
           and not getattr(attrs, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0),
           f"Symlink or reparse point at {path}")


def regular(base, name):
    p = base
    reject_link(p)
    for part in relative(name).parts:
        p = p / part
        reject_link(p)
    ensure(p.is_file(), f"Expected file: {p}")
    return p


def read_sums(path):
    entries = {}
    folded = set()
    for line in path.read_text(encoding="utf8").splitlines():
        digest, name = line.split("  ", 1)
        relative(name)
        ensure(name.casefold() not in folded and re.fullmatch("[a-f0-9]{64}", digest), f"Invalid SHA row: {name}")
        entries[name] = digest
        folded.add(name.casefold())
    return entries


def verify_package(package):
    reject_link(package)
    index = regular(package, "manifests/RUNPOD_PACKAGE_MANIFEST.json")
    sums_path = regular(package, "manifests/SHA256SUMS.txt")
    ensure(sha(index) == INDEX_PIN and sha(sums_path) == SUMS_PIN, "Package checksum index pin mismatch")
    index_data = read_json(index)
    ensure(index_data["schema"] == "p1p2.runpod-delivery.v1", "Unexpected release schema")
    indices = set(index_data["manifest_self_files_excluded"])
    ensure(indices == {"manifests/RUNPOD_PACKAGE_MANIFEST.json", "manifests/SHA256SUMS.txt",
                       "manifests/RUNPOD_SHA256.csv"}, "Unexpected release index membership")
    ensure(sha(regular(package, "manifests/RUNPOD_SHA256.csv")) == index_data["csv_manifest_sha256"],
           "Package CSV digest mismatch")
    sums = read_sums(sums_path)
    expected = {r["path"]: r for r in index_data["entries"]}
    ensure(len(expected) == len(index_data["entries"]) == len(sums) == 655 and set(expected) == set(sums),
           "Package payload set differs")
    actual = set()
    for parent, dirs, files in os.walk(package):
        for name in dirs + files:
            p = Path(parent) / name
            reject_link(p)
            if name in files:
                actual.add(p.relative_to(package).as_posix())
    ensure(actual == set(sums) | indices, "Package contains missing or extra files")
    for name, digest in sums.items():
        p = regular(package, name)
        ensure(expected[name]["bytes"] == p.stat().st_size and expected[name]["sha256"] == digest == sha(p),
               f"Package fingerprint mismatch: {name}")
    print(f"Package verified: {len(actual)} files")
    return sums


def cache_hub():
    explicit = os.environ.get("HF_HUB_CACHE")
    if explicit:
        return Path(explicit).resolve()
    home = os.environ.get("HF_HOME")
    if not home:
        raise ValueError("Set HF_HUB_CACHE or HF_HOME to the dedicated offline snapshot")
    return Path(home).resolve() / "hub"


def verify_cache(hub, sums_path):
    ensure(sha(sums_path) == AUDIT_CACHE, "Student cache list is not the pinned manifest")
    rows = read_sums(sums_path)
    ensure(len(rows) == 7, "Expected seven cache entries")
    for name, digest in rows.items():
        target = hub.joinpath(*relative(name).parts)
        ensure(target.is_file() and target.resolve().is_relative_to(hub.resolve())
               and sha(target) == digest, f"Missing or mismatched cache entry: {name}")
    print("Seven offline Student cache files verified")


def verify_env(package):
    ensure(sys.version_info[:2] == (3,11), "Python 3.11 required by the dependency contract")
    for name, pin in EXPECTED_VERSIONS.items():
        ensure(importlib.metadata.version(name) == pin, f"Version mismatch: {name}, expected {pin}")
    subprocess.run([sys.executable, "-B", "-m", "pip", "check"], check=True)
    ensure((package / "P2/requirements-lock.txt").is_file(), "Missing dependency lock")


def verify_disk(path, minimum):
    ensure(minimum > 0, "Free-space minimum must be positive")
    free = shutil.disk_usage(path).free
    ensure(free >= minimum, f"Insufficient disk at {path}: {free} < {minimum}")


def verify_work(package, work, sums, *, fresh=False):
    ensure(work != package and not work.is_relative_to(package) and not package.is_relative_to(work),
           "Use a writable work copy separate from the sealed tree")
    for name, digest in sums.items():
        if not name.startswith("P2/"):
            continue
        target = regular(work, name)
        if name in MODIFIABLE_PREFIXES and not fresh:
            expected = regular(package, name).read_bytes()
            with target.open("rb") as f:
                ensure(f.read(len(expected)) == expected, f"Original append-only prefix differs: {name}")
        else:
            ensure(sha(target) == digest, f"Frozen work input differs: {name}")


def legacy_root(package):
    return read_json(regular(package, "manifests/path_mapping_manifest.json"))["windows_manual_root"]


def readonly_plan(manual, legacy, method, rounds):
    directory = str(manual / "scripts")
    sys.path.insert(0, directory)
    try:
        from p1p2_controller import Controller
        def blocked(*args, **kwargs):
            raise AssertionError("Plan attempted to call a subprocess")
        ctl = Controller(manual, dry_run=True, resume=True, backend="hf", dtype="bf16",
                         micro_batch=1, nll_batch=1, eval_batch=1, legacy_windows_root=legacy, runner=blocked)
        with contextlib.redirect_stdout(sys.stderr):
            ctl.run_method_seed(method, 13, rounds)
        for item in ctl.actions:
            cmd = item["command"]
            ensure("test" not in cmd and "--split=test" not in cmd, "Unexpected test split in plan")
        return ctl.actions
    finally:
        sys.path.remove(directory)


def guard_plan(method, round_no, actions):
    names = [item["stage"] for item in actions]
    if method == "P1-DEFICIT" and round_no == 2:
        allowed = ["eval_dev_P1-DEFICIT_seed13_S2", "checkpoint_log_P1-DEFICIT_seed13_S2",
                   "post_eval_P1-DEFICIT_seed13_S2", "capability_state_P1-DEFICIT_seed13_selection_3"]
        ensure([n for n in allowed if n in names] == names, "A S2 cannot retrain or act outside its eval/hook scope")
    nll = [i for i in actions if i["stage"].startswith("compute_nll")]
    if method == "P1-DEFICIT":
        ensure(not nll, "P1-DEFICIT cannot plan NLL")
    else:
        ensure(all(i["command"][i["command"].index("--tag") + 1] == f"S{round_no-1}" for i in nll),
               "Wrong planned learnability checkpoint")
    for action in actions:
        cmd = action["command"]
        if "eval_student.py" in (Path(cmd[1]).name if len(cmd) > 1 else ""):
            ensure(cmd[cmd.index("--split") + 1] == "dev", "Evaluation scope must be D_dev")


def receipt_matches(receipt, package, work):
    ensure(receipt == {"status": "PASS", "platform": "linux", "package": str(package), "work": str(work),
                       "index_sha256": INDEX_PIN, "python": sys.executable, "actions": [0, 0, 4, 16]},
           "A matching real Linux CPU preflight receipt is required")


def run_env(cpu):
    options = dict(os.environ, HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", PYTHONDONTWRITEBYTECODE="1")
    if cpu:
        options["CUDA_VISIBLE_DEVICES"] = ""
        options["MPLBACKEND"] = "Agg"
    return options


def run_scopes(manual, method):
    group = f"{method}_seed13"
    roots = [manual / "runs/p1p2_integration" / group, manual / "models/p1p2_integration" / group,
             manual / "reports/p1p2_integration/capability_state" / group]
    roots.extend((manual / "reports/p1p2_integration/capability_sidecars").glob(group + "_S*"))
    return roots


def result_inventory(work, method):
    files = {}
    for root in run_scopes(work / MANUAL, method):
        for p in root.rglob("*"):
            reject_link(p)
            if p.is_file() and p.name != ".controller.lock":
                files[p.relative_to(work).as_posix()] = {"sha256": sha(p), "bytes": p.stat().st_size}
    return files


def run_round(args, sums):
    scope = f"{args.method}:13:S{args.round}"
    if args.execute:
        ensure(args.approve == scope, f"Require explicit --approve {scope}")
        ensure(sys.platform == "linux", "Live execution is allowed only on the separately approved Linux host")
        ensure(args.receipt is not None and args.output is not None, "--receipt and --output required for execution")
        receipt_matches(read_json(args.receipt), args.package, args.work)
    verify_work(args.package, args.work, sums)
    manual = args.work / MANUAL
    lock = manual / "runs/p1p2_integration" / f"{args.method}_seed13" / ".controller.lock"
    ensure(not lock.exists() and not lock.is_symlink(), f"Controller lock exists: {lock}")
    legacy = legacy_root(args.package)
    parent = readonly_plan(manual, legacy, args.method, [args.round - 1])
    ensure(not parent, f"Parent S{args.round-1} must be complete before {scope}")
    actions = readonly_plan(manual, legacy, args.method, [args.round])
    guard_plan(args.method, args.round, actions)
    print(json.dumps({"scope": scope, "actions": actions}, indent=2))
    if not args.execute or not actions:
        return 0
    verify_env(args.package)
    verify_cache(cache_hub(), args.cache_sums)
    ensure(not args.output.is_relative_to(args.package) and not args.output.is_relative_to(args.work),
           "Execution evidence must be outside both runtime trees")
    verify_disk(args.work, args.min_free_bytes)
    verify_disk(args.output.parent, args.min_free_bytes)
    args.output.mkdir(exist_ok=False)
    before = result_inventory(args.work, args.method)
    argv = [sys.executable, "-B", "scripts/run_p1_p2.py", "--manual-root", str(manual),
            "--legacy-windows-root", legacy, "--seed", "13", "--method", args.method, "--round", str(args.round),
            "--resume", "--backend", "hf", "--dtype", "bf16", "--micro-batch", "1", "--nll-batch", "1",
            "--eval-batch", "1"]
    write_json(args.output / "intent.json", {"scope": scope, "work": str(args.work),
                                           "command": argv, "planned": actions, "index_sha256": INDEX_PIN})
    try:
        with (args.output / "execution.log").open("xb") as log:
            pre = subprocess.run([sys.executable, "-B", "-c",
                              "import torch; assert torch.cuda.is_available() and torch.cuda.is_bf16_supported()"],
                                 cwd=manual, stdout=log, stderr=subprocess.STDOUT, env=run_env(False))
            status = pre.returncode
            if status == 0:
                print(f"Running {scope}; log {args.output / 'execution.log'}", flush=True)
                status = subprocess.run(argv, cwd=manual, stdout=log, stderr=subprocess.STDOUT,
                                    env=run_env(False)).returncode
    except KeyboardInterrupt:
        status = 130
    post_error = ""
    try:
        verify_work(args.package, args.work, sums)
        if status == 0 and readonly_plan(manual, legacy, args.method, [args.round]):
            raise ValueError("Completion dry-run still has work")
    except Exception as exc:
        post_error = str(exc)
    after = result_inventory(args.work, args.method)
    if before.keys() - after.keys():
        post_error += " A pre-existing result disappeared during execution."
    files = {p: data for p, data in after.items() if sums.get(p) != data["sha256"]}
    changed = sorted(p for p, data in after.items() if before.get(p) != data)
    with (args.output / "exit_code.txt").open("x", encoding="ascii") as f:
        f.write(f"{status}\n")
    write_json(args.output / "execution.json",
               {"schema": "p1p2.handoff.execution.v1", "scope": scope, "index_sha256": INDEX_PIN,
                "work": str(args.work), "exit_code": status, "status": "PASS" if status == 0 and not post_error else "FAILED",
                "post_validation_error": post_error, "outputs": files, "changed_this_attempt": changed,
                "utc": datetime.now(timezone.utc).isoformat()})
    return status or int(bool(post_error))


def preflight(args, sums):
    verify_work(args.package, args.work, sums, fresh=True)
    manual = args.work / MANUAL
    verify_env(args.package)
    verify_cache(cache_hub(), args.cache_sums)
    verify_disk(args.work, args.min_free_bytes)
    ensure(not args.output.is_relative_to(args.package) and not args.output.is_relative_to(args.work),
           "Keep CPU receipt outside runtime trees")
    args.output.mkdir(exist_ok=False)
    counts = [len(readonly_plan(manual, legacy_root(args.package), m, r)) for m, r in
              (("P1-DEFICIT", [1]), ("P1P2", [1]), ("P1-DEFICIT",[2]), ("P1P2",[2,3]))]
    ensure(counts == [0, 0, 4, 16], f"Unexpected clean-root plan counts: {counts}")
    with (args.output / "unittest.log").open("xb") as log:
        tests = subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-v"],
                               cwd=manual, stdout=log, stderr=subprocess.STDOUT, env=run_env(True))
    ensure(tests.returncode == 0, f"CPU suite failed: {args.output / 'unittest.log'}")
    summary = (args.output / "unittest.log").read_text(encoding="utf-8", errors="replace")
    ensure(re.search(r"(?m)^Ran 103 tests in ", summary), "CPU suite count differs")
    receipt = {"status": "PASS", "platform": sys.platform, "package": str(args.package),
               "work": str(args.work), "index_sha256": INDEX_PIN, "python": sys.executable, "actions": counts}
    write_json(args.output / "preflight.json", receipt)


def collect(args):
    record = read_json(args.receipt)
    ensure(record.get("schema") == "p1p2.handoff.execution.v1" and record.get("status") == "PASS"
           and record.get("index_sha256") == INDEX_PIN and record.get("exit_code") == 0
           and re.fullmatch(r"(?:P1-DEFICIT|P1P2):13:S[23]", record.get("scope", "")),
           "Only a verified successful bounded execution can be collected")
    work = Path(record["work"]).resolve(strict=True)
    ensure(not args.output.is_relative_to(work) and not args.output.is_relative_to(args.package),
           "Use a fresh return directory outside runtime trees")
    files = {}
    allowed = run_scopes(work / MANUAL, record["scope"].split(":")[0])
    payload = record["outputs"]
    ensure(payload, "No execution outputs to collect")
    for name, meta in payload.items():
        p = regular(work, name)
        ensure(any(p.is_relative_to(scope) for scope in allowed), f"Output outside approved result scope: {name}")
        ensure(sha(p) == meta["sha256"] and p.stat().st_size == meta["bytes"], f"Output changed: {name}")
        files[name] = p
    for internal in ("intent.json", "execution.log", "exit_code.txt", "execution.json"):
        files["operator/" + internal] = regular(args.receipt.parent, internal)
    args.output.mkdir(exist_ok=False)
    sums = {}
    for name, src in sorted(files.items()):
        dest = args.output / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        with src.open("rb") as a, dest.open("xb") as b:
            shutil.copyfileobj(a, b)
        digest = sha(dest)
        ensure(digest == sha(src) and (name not in payload or digest == payload[name]["sha256"]),
               f"Copy mismatch: {name}")
        sums[name] = digest
    result = args.output / "RESULTS_SHA256SUMS.txt"
    with result.open("x", encoding="ascii", newline="\n") as f:
        f.writelines(f"{digest}  {name}\n" for name, digest in sums.items())
    print(f"Pin this result index out of band: {sha(result)}")


def verify_results(path, expected):
    manifest = regular(path, "RESULTS_SHA256SUMS.txt")
    ensure(sha(manifest) == expected, "Returned result checksum index differs from the trusted pin")
    sums = read_sums(manifest)
    ensure(sums and set(sums) | {manifest.name} == {
        p.relative_to(path).as_posix() for p in path.rglob("*") if p.is_file()},
        "Unexpected result file membership")
    for name, digest in sums.items():
        ensure(sha(regular(path, name)) == digest, f"Result SHA mismatch: {name}")
    print(f"Return bundle verified: {len(sums)} files")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="action", required=True)
    for name in ("verify-package", "verify-cache", "setup", "preflight", "plans", "run", "collect", "verify-results"):
        command = subs.add_parser(name)
        command.add_argument("--package", type=Path, default=Path(os.environ.get("P1P2_PACKAGE", ROOT / "runtime")))
        if name in ("verify-cache", "setup", "preflight", "run"):
            command.add_argument("--cache-sums", type=Path, default=ROOT/"manifests/MODEL_CACHE_SHA256SUMS.txt")
        if name in ("setup", "preflight", "run"):
            command.add_argument("--min-free-bytes", type=int, default=2*1024**3)
        if name in ("setup", "preflight", "run"):
            command.add_argument("--work", type=Path, required=True)
        if name == "setup":
            command.add_argument("--install-offline", type=Path, metavar="WHEELHOUSE")
        if name in ("preflight", "run", "collect"):
            command.add_argument("--output", type=Path, required=name != "run")
        if name in ("run", "collect"):
            command.add_argument("--receipt", type=Path, required=name=="collect")
        if name == "run":
            command.add_argument("method", choices=("P1-DEFICIT","P1P2"))
            command.add_argument("round", type=int, choices=(2,3))
            command.add_argument("--execute", action="store_true")
            command.add_argument("--approve")
        if name == "verify-results":
            command.add_argument("--results", type=Path, required=True)
            command.add_argument("--expected-sha", required=True)
    args = parser.parse_args(argv)
    for attr in ("package", "work", "output", "receipt", "results"):
        if getattr(args, attr, None) is not None:
            p = getattr(args, attr).absolute()
            ensure(not p.is_symlink(), f"Unexpected path alias: {p}")
            setattr(args, attr, p.resolve())
    if args.action == "verify-cache":
        verify_cache(cache_hub(), args.cache_sums)
        return 0
    if args.action == "verify-results":
        verify_results(args.results, args.expected_sha)
        return 0
    if args.action == "collect":
        collect(args)
        return 0
    if args.action == "run" and args.execute and args.approve != f"{args.method}:13:S{args.round}":
        parser.error("Live run requires exact --approve METHOD:13:CHECKPOINT")
    sums = verify_package(args.package)
    if args.action == "setup":
        ensure(not args.work.resolve().is_relative_to(args.package.resolve()), "Work copy must be separate")
        if args.work.exists() or args.work.is_symlink():
            raise FileExistsError(args.work)
        if args.install_offline:
            ensure(sys.platform == "linux" and sys.version_info[:2] == (3,11)
                   and sys.prefix != sys.base_prefix, "Offline installation requires the approved Linux Python 3.11 venv")
            subprocess.run([sys.executable, "-B", "-m", "pip", "install", "--no-index", "--find-links",
                str(args.install_offline), "-r", str(args.package/"P2/requirements-lock.txt")], check=True)
        verify_env(args.package)
        verify_cache(cache_hub(), args.cache_sums)
        verify_disk(args.work.parent, args.min_free_bytes)
        args.work.mkdir(exist_ok=False)
        shutil.copytree(args.package/"P2", args.work/"P2")
        verify_work(args.package, args.work, sums, fresh=True)
    elif args.action == "plans":
        legacy = legacy_root(args.package)
        counts = [len(readonly_plan(args.package / MANUAL, legacy, m, r)) for m,r in
                  (("P1-DEFICIT",[1]), ("P1P2",[1]), ("P1-DEFICIT",[2]), ("P1P2",[2,3]))]
        ensure(counts == [0,0,4,16], f"Unexpected release plans: {counts}")
        print("100% read-only, action counts:", counts)
    elif args.action == "preflight":
        preflight(args, sums)
    elif args.action == "run":
        return run_round(args, sums)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
