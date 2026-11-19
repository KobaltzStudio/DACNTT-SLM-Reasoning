"""Check a source-only checkout or verify compatibility with an approved sealed bundle."""
import argparse
import ast
import csv
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
MANUAL = Path("P2/experiments/week2September/manual")
METHODS = ("B2", "B3", "B4", "B5", "P1-DEFICIT", "P1P2")
CONFIG_TESTS = {"test_p1p2_method_registry", "test_p1p2_unified_config"}
ENTRY_POINTS = {
    "run_p1_p2", "p1p2_controller", "run_p1p2_post_eval", "train_round", "eval_student",
    "compute_nll", "build_capability_learning_dynamics", "select_checkpoint_on_dev",
    "build_p1p2_analysis_figures", "run_final_d_test", "select_round", "p1p2_selector",
    # Also present as a source-only template dependency of student_common.check_prompt_template().
    "generate_teacher_trajectories_batch",
}
IMPORT_DISTRIBUTIONS = {"yaml": "pyyaml", "torch": "torch", "transformers": "transformers",
                        "peft": "peft", "matplotlib": "matplotlib"}


def sha(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def intake_manifest():
    by_name = {}
    with (ROOT / "manifests/runtime_payload.csv").open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            name = row["path"]
            path = PurePosixPath(name)
            if (not path.parts or path.is_absolute() or path.as_posix() != name or ".." in path.parts
                    or "\\" in name or ":" in name or name.casefold() in by_name):
                raise ValueError(f"Unsafe or duplicate runtime index path: {name}")
            by_name[name.casefold()] = row
    if len(by_name) != 658:
        raise ValueError("Runtime index membership differs from the 658-file release")
    return {row["path"]: row for row in by_name.values()}


def source_check():
    scripts = {path.stem: path for path in (ROOT / MANUAL / "scripts").glob("*.py")}
    expected_scripts = {PurePosixPath(name).stem for name in intake_manifest()
                        if f"{MANUAL.as_posix()}/scripts/" in name and name.endswith(".py")}
    missing = ENTRY_POINTS - scripts.keys()
    if missing:
        raise ValueError(f"Missing entry points: {sorted(missing)}")
    queue = list(ENTRY_POINTS)
    visited, external = set(), set()
    while queue:
        name = queue.pop()
        if name in visited:
            continue
        visited.add(name)
        tree = ast.parse(scripts[name].read_bytes())
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(item.name.partition(".")[0] for item in node.names)
            if isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.partition(".")[0])
        local = imports & expected_scripts
        if local - scripts.keys():
            raise ValueError(f"Missing local modules: {sorted(local - scripts.keys())}")
        queue.extend(local)
        external.update(imports - expected_scripts - sys.stdlib_module_names)
    unknown = external - IMPORT_DISTRIBUTIONS.keys() - {"vllm"}
    if unknown:
        raise ValueError(f"Undeclared imports: {sorted(unknown)}")
    pinned = {line.partition("==")[0].strip().lower()
              for line in (ROOT/"P2/requirements-lock.txt").read_text(encoding="utf-8-sig").splitlines()
              if "==" in line}
    required = {IMPORT_DISTRIBUTIONS[name] for name in external if name != "vllm"}
    if not required <= pinned:
        raise ValueError(f"Unpinned imports: {sorted(required - pinned)}")
    print(json.dumps({"source_modules": len(visited), "external_distributions": sorted(required),
                      "optional_backend": "vllm", "methods": METHODS}, indent=2))
    print("For scientific execution use the separately authorized sealed bundle and frozen configs (bundle mode).")


def public_tests():
    manual = ROOT / MANUAL
    directory = manual / "tests"
    sys.path[:0] = [str(directory), str(manual)]
    loader = unittest.TestLoader()
    suite = unittest.TestSuite(loader.loadTestsFromName(p.stem) for p in sorted(directory.glob("test_*.py"))
                               if p.stem not in CONFIG_TESTS)
    if not suite.countTestCases():
        raise ValueError("Public test suite is empty")
    print("Artifact-dependent classes excluded from source-only tests:", ", ".join(sorted(CONFIG_TESTS)), flush=True)
    return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1


def bundle_check(package):
    if package is None or not (package / "manifests/SHA256SUMS.txt").is_file():
        raise ValueError("BUNDLE_REQUIRED: obtain the authorized sealed runtime from the operator and pass "
                         "--bundle PATH. Frozen configs, data and checkpoints are private.")
    sys.path.insert(0, str(ROOT/"deployment"))
    import ops
    import yaml
    package = package.resolve()
    ops.verify_package(package)
    for name, row in intake_manifest().items():
        source = ops.regular(package, name)
        if source.stat().st_size != int(row["bytes"]) or sha(source) != row["sha256"]:
            raise ValueError(f"Public and sealed manifests disagree: {name}")
    # Only the release source/test/lock files that are present in this checkout are bound here.
    core = list((ROOT / MANUAL/"scripts").glob("*.py")) + list((ROOT / MANUAL/"tests").glob("*.py"))
    core.extend(ROOT/name for name in ("P2/requirements.txt","P2/requirements-lock.txt"))
    if len(core) != 37:
        raise ValueError("Expected 22 core modules, 13 test files and two locks")
    for path in core:
        rel = path.relative_to(ROOT)
        if sha(path) != sha(package/rel):
            raise ValueError(f"Source differs from the sealed release: {rel}. Rebuild and re-test before use.")
    manual = package / MANUAL
    for filename in ("p1p2_method_registry.yaml", "p1p2_unified_run.yaml", "experiment_config.json"):
        path = manual / "config" / filename
        payload = path.read_text(encoding="utf-8-sig")
        data = json.loads(payload) if path.suffix == ".json" else yaml.safe_load(payload)
        if not isinstance(data, dict) or not data:
            raise ValueError(f"Invalid frozen config: {filename}")
    legacy = ops.legacy_root(package)
    checks = (("P1-DEFICIT",[1]), ("P1P2",[1]), ("P1-DEFICIT",[2]), ("P1P2",[2,3]))
    plans = [ops.readonly_plan(manual, legacy, method, rounds) for method, rounds in checks]
    sizes = list(map(len, plans))
    if sizes != [0,0,4,16]:
        raise ValueError(f"Unexpected plan lengths: {sizes}")
    ops.guard_plan("P1-DEFICIT", 2, plans[2])
    def flags(actions, stage, arg):
        return [a["command"][a["command"].index(arg)+1] for a in actions if a["stage"].startswith(stage)]
    nll = flags(plans[3],"compute_nll","--adapter")
    if (flags(plans[3],"compute_nll","--tag") != ["S1","S2"]
            or nll != flags(plans[3],"train_","--init-adapter")
            or flags(plans[3],"eval_dev_","--split") != ["dev","dev"]):
        raise ValueError("B plan disagrees with parent NLL or evaluation split")
    print("PASS: 37 source/test/lock byte matches, 3 frozen configs, plans 0/0/4/16; subprocesses blocked")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("source", "tests", "bundle"))
    parser.add_argument("--bundle", type=Path)
    args = parser.parse_args()
    os.environ.update(CUDA_VISIBLE_DEVICES="", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", MPLBACKEND="Agg")
    try:
        source_check()
        if args.mode == "tests":
            return public_tests()
        if args.mode == "bundle":
            bundle_check(args.bundle)
        return 0
    except (ValueError, OSError, ImportError) as exc:
        print(f"PRECHECK FAILED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
