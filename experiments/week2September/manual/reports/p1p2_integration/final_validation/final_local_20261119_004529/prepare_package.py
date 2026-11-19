"""Build a detached package from pinned transfer manifests; preserve source bytes."""
from collections import Counter
import ast
import csv
import hashlib
import importlib.metadata
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import shutil
import stat
import sys

MANUAL = Path.cwd().resolve()
PIPELINE = MANUAL.parents[3]
P2 = MANUAL.parents[2]
PREFIX = MANUAL.relative_to(PIPELINE).as_posix()
EVIDENCE = Path(__file__).resolve().parent
BASE = MANUAL / "reports/p1p2_integration/final_validation/post_validation_20261119"
PACKAGE = Path("C:/Users/PC - NGHI/Desktop/Pipeline/p1p2_unified/runpod_package_20261119_004529")
SOURCE_UPDATES = {"scripts/eval_student.py", "scripts/select_checkpoint_on_dev.py"}
SUPPLEMENT = f"{PREFIX}/reports/p1p2_integration/nll/P1P2_seed13/S0_nll.summary.json"
ENTRIES = ["run_p1_p2", "p1p2_selector", "select_round", "run_p1p2_post_eval", "p1p2_capability_state",
           "capability_eval", "train_round", "eval_student", "compute_nll", "run_final_d_test",
           "build_capability_learning_dynamics", "select_checkpoint_on_dev", "build_p1p2_analysis_figures",
           "generate_teacher_trajectories_batch"]
REQUIRED = ("config/experiment_config.json", "config/p1p2_method_registry.yaml", "config/p1p2_unified_run.yaml",
            "splits/d_dev_ids.txt", "splits/d_pool_ids.txt", "splits/d_test_ids.txt", "splits/split_manifest.json",
            "splits/p1p2_vfinal_2026-11-16/split_manifest.json",
            "splits/p1p2_vfinal_2026-11-16/d_dev_select_ids.txt",
            "splits/p1p2_vfinal_2026-11-16/d_dev_graph_ids.txt", "data/raw/gsm8k_train.jsonl",
            "data/raw/gsm8k_test.jsonl", "data/supplement/supplement_annotations_v2.jsonl",
            "data/gold_vfinal/gold_vfinal_manifest.json", "data/gold_vfinal/supplement_annotations_vfinal.jsonl",
            "data/gold_releases/vFinal_2026-11-16/gold_supplement_85_approved_review.csv",
            "trajectory/pool/pool_v1_verified.jsonl", "trajectory/pool/pool_v1_tokens.jsonl",
            "reports/p1p2_integration/source_review/s0_base_model_reference.json",
            "runs/p1p2_integration/P1-DEFICIT_seed13/S2/eval_dev.intent.json",
            "runs/p1p2_integration/P1-DEFICIT_seed13/S2/eval_dev.jsonl")


def sha(p):
    with p.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def read(p):
    return json.loads(p.read_text(encoding="utf-8-sig"))


def write_json(path, data):
    with path.open("x", encoding="utf8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def write_csv(path, rows):
    with path.open("x", encoding="utf8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def valid_relative(name):
    path = PurePosixPath(name)
    if (path.is_absolute() or path.as_posix() != name or not path.parts or ".." in path.parts
            or any(part.endswith((".", " ")) or any(c in part for c in ":\\\r\n") for part in path.parts)):
        raise ValueError(f"Invalid transfer path: {name}")
    return path


def regular_path(root, relative):
    path = root
    for part in valid_relative(relative).parts:
        path = path / part
        info = path.lstat()
        if path.is_symlink() or getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0):
            raise ValueError(f"Symlink or reparse point: {path}")
    if not path.is_file() or not path.resolve().is_relative_to(root):
        raise ValueError(f"Expected a regular file under package root: {path}")
    return path


def ensure_case_safe(name, index):
    path = valid_relative(name)
    for i in range(1, len(path.parts) + 1):
        prefix = "/".join(path.parts[:i])
        normalized = prefix.casefold()
        existing = index.setdefault(normalized, prefix)
        if existing != prefix:
            raise ValueError(f"Case-colliding transfer paths: {existing}, {prefix}")


def dependency_graph():
    scripts = {p.stem: p for p in (MANUAL / "scripts").glob("*.py")}
    queue = list(ENTRIES)
    graph = {}
    external = set()
    while queue:
        name = queue.pop()
        if name in graph:
            continue
        tree = ast.parse(scripts[name].read_bytes(), filename=str(scripts[name]))
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        graph[name] = sorted(imports & scripts.keys())
        queue.extend(graph[name])
        external.update(imports - scripts.keys() - sys.stdlib_module_names)
    return graph, sorted(external)


def plan():
    revision = "_final" if "--supplement" in sys.argv else ""
    pins = {}
    excluded = []
    for filename, prefix in (("runpod_sha256sums_sealed.txt", PREFIX),
                             ("runpod_p2_sha256sums_sealed.txt", "P2")):
        for line in (BASE / filename).read_text(encoding="utf8").splitlines():
            expected, relative = line.split("  ", 1)
            valid_relative(relative)
            name = f"{prefix}/{relative}"
            if name in pins:
                raise ValueError(f"Duplicate transfer path: {name}")
            if re.search(r"(?i)(\.bak(?:_|$)|\.zip$|\.pyc$|/__pycache__/|\.tmp$|\.log$|/eval_test[^/]*$)", name):
                excluded.append({"path": name, "decision": "OMIT_FROM_PACKAGE",
                                 "reason": "backup, cache, temporary log or historical test output; original kept"})
                continue
            pins[name] = None if prefix == PREFIX and relative in SOURCE_UPDATES else expected
    dependency, external = dependency_graph()
    added = ["scripts/run_final_d_test.py", "tests/test_final_d_test.py", "data/raw/gsm8k_test.jsonl"]
    for name in added:
        pins[f"{PREFIX}/{name}"] = None
    pins["P2/requirements.txt"] = None
    if revision:
        pins[SUPPLEMENT] = None
    split = read(MANUAL / "splits/split_manifest.json")
    for value in (*split["sources"].values(), *split["files"].values()):
        relative = value["path"]
        source = regular_path(PIPELINE, f"{PREFIX}/{relative}")
        raw = source.read_bytes()
        raw_sha = hashlib.sha256(raw).hexdigest()
        lf_sha = hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()
        if value["sha256"] not in {raw_sha, lf_sha}:
            raise ValueError(f"Unverified split source: {source}")
        pins.setdefault(f"{PREFIX}/{relative}", raw_sha)
    g4 = "P2/integration_staging/G4_CHECKPOINT_AUDIT/original_train_sets"
    g4_manifest = f"{g4}/original_train_sets_manifest.json"
    pins[g4_manifest] = None
    for stage, metadata in read(PIPELINE / g4_manifest)["stages"].items():
        pins[f"{g4}/{stage}/train_set.json"] = metadata["expected_sha256"]
    b4_fingerprint = read(MANUAL / "reports/capability_g4_validation/B4_seed13_S1/input_fingerprint.json")["inputs"]
    pins[f"{PREFIX}/runs/main/B4_seed13/checkpoint_log.jsonl"] = b4_fingerprint["checkpoint_log"]
    needed = {f"{PREFIX}/{name}" for name in REQUIRED}
    needed.update(f"{PREFIX}/scripts/{name}.py" for name in dependency)
    if needed - pins.keys():
        raise ValueError(f"Unstaged runtime dependencies: {sorted(needed - pins.keys())}")
    for method, rounds in (("P1-DEFICIT", (1, 2)), ("P1P2", (1,))):
        for checkpoint in rounds:
            group = f"{method}_seed13"
            names = (f"models/p1p2_integration/{group}/student_ckpt_{checkpoint:03d}/adapter_model.safetensors",
                     f"models/p1p2_integration/{group}/student_ckpt_{checkpoint:03d}/adapter_config.json",
                     f"models/p1p2_integration/{group}/student_ckpt_{checkpoint:03d}/train_log.json",
                     f"runs/p1p2_integration/{group}/round_{checkpoint:03d}/train_set.json",
                     f"runs/p1p2_integration/{group}/checkpoint_log.jsonl")
            if not all(f"{PREFIX}/{name}" in pins for name in names):
                raise ValueError(f"Incomplete retained adapter/lineage: {group} S{checkpoint}")
    locator_rows = list(csv.DictReader((BASE / "runpod_path_reference_inventory_sealed.csv").open(
                                      encoding="utf-8-sig", newline="")))
    locators = Counter(row["locator_status"] for row in locator_rows)
    runtime = [r for r in locator_rows if r["use"].startswith("runtime")]
    if any(r["locator_status"] != "PRESENT" for r in runtime):
        raise ValueError("A required runtime locator is unresolved")
    for r in runtime:
        base = "P2" if r["staging_base"] == "P2" else PREFIX
        translated = f"{base}/{r['staging_relative']}"
        if translated not in pins and r["json_pointer"] == "/nll_file":
            # Old B4/B5 selections pin LF Git bytes; copy the verified worktree
            # bytes intact and record their canonical match. These are audit inputs.
            metadata = read(MANUAL / r["artifact"])
            source = regular_path(PIPELINE, translated)
            raw = source.read_bytes()
            raw_sha = hashlib.sha256(raw).hexdigest()
            lf_sha = hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()
            if metadata["nll_sha256"] not in {raw_sha, lf_sha}:
                raise ValueError(f"Historical NLL provenance mismatch: {source}")
            pins[translated] = raw_sha
            pins[str(PurePosixPath(translated).with_suffix(".summary.json"))] = None
            r["canonical_lf_sha256"] = lf_sha
        if translated not in pins and not any(name.startswith(translated + "/") for name in pins):
            raise ValueError(f"Mapped runtime locator not retained: {translated}")
    for row in locator_rows:
        if row["locator_status"] == "OUTSIDE_MAPPED_ROOT":
            translated = "P2/" + PureWindowsPath(row["recorded_path"]).relative_to(PureWindowsPath(P2)).as_posix()
            if translated not in pins:
                raise ValueError(f"Unstaged G4 audit reference: {translated}")
            row["staging_relative"] = translated
            row["staging_base"] = "package"
    write_json(EVIDENCE / f"path_mapping_manifest{revision}.json", {
        "windows_manual_root": str(MANUAL), "package_manual_relative": PREFIX,
        "g4_reference_root_under_p2": "integration_staging/G4_CHECKPOINT_AUDIT/extracted_checkpoints",
        "linux_manual": "<package>/" + PREFIX, "allow_unmapped_runtime": False,
        "locator_counts": dict(locators), "runtime_occurrences": len(runtime),
        "metadata_audit": "prior transfer inventory independently cross-checked for target presence",
        "all_occurrences": locator_rows,
    })
    index = {}
    files = []
    for name, expected in sorted(pins.items()):
        ensure_case_safe(name, index)
        source = regular_path(PIPELINE, name)
        actual = sha(source)
        if expected and expected != actual:
            raise ValueError(f"Unexpected transfer SHA mismatch: {source}")
        files.append({"path": name, "sha256": actual, "bytes": source.stat().st_size,
                      "source_kind": "sealed-baseline" if expected else "explicit-addition-or-reviewed-change"})
    listed = {row["path"] for row in files}
    old_inventory = BASE / "cleanup_inventory_updated.csv"
    exclusions = {r["path"]: r for r in excluded}
    with old_inventory.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            name = row["path"]
            if name not in listed and name not in exclusions:
                exclusions[name] = {"path": name, "decision": "OMIT_FROM_PACKAGE",
                                    "reason": "Outside deployment allowlist; original retained"}
    write_csv(EVIDENCE / f"excluded_files_report{revision}.csv", [exclusions[name] for name in sorted(exclusions)])
    write_csv(EVIDENCE / f"staging_inventory{revision}.csv", files)
    total = sum(row["bytes"] for row in files)
    free = shutil.disk_usage(PIPELINE).free
    if free < total:
        raise OSError(f"Insufficient local disk: {free} < {total}")
    installed = {}
    for name in ("torch", "transformers", "peft", "accelerate", "PyYAML", "safetensors", "matplotlib"):
        installed[name] = importlib.metadata.version(name)
    write_json(EVIDENCE / f"staging_plan{revision}.json", {"package": str(PACKAGE), "manual_relative": PREFIX,
               "files": files, "bytes": total, "free_bytes": free, "dependency_graph": dependency,
               "imports_external": external, "windows_dependency_versions": installed,
               "filtered_from_old_transfer": excluded, "required_static_files": len(needed)})
    print(f"Planned {len(files)} files ({total} bytes), {len(excluded)} prior backups excluded")


def copy_one(source, destination, expected):
    destination.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as a, destination.open("xb") as b:
        shutil.copyfileobj(a, b, 1024 * 1024)
    if sha(destination) != expected:
        raise ValueError(f"Copy verification failed: {destination}")


def copy():
    supplemental = "--supplement" in sys.argv
    revision = "_final" if supplemental else ""
    planned = read(EVIDENCE / f"staging_plan{revision}.json")
    if not PACKAGE.resolve().is_relative_to(PIPELINE) or PACKAGE.is_symlink():
        raise ValueError("Package path must be under the approved Pipeline parent")
    if not supplemental:
        PACKAGE.mkdir(parents=True, exist_ok=False)
    else:
        expected = {row["path"] for row in planned["files"]}
        actual = {p.relative_to(PACKAGE).as_posix() for p in PACKAGE.rglob("*") if p.is_file()}
        if actual != expected - {SUPPLEMENT}:
            raise ValueError(f"Staging has unexpected missing or extra files: {sorted(actual ^ expected)}")
    for row in planned["files"]:
        name = row["path"]
        source = regular_path(PIPELINE, name)
        if sha(source) != row["sha256"]:
            raise ValueError(f"Source changed after staging plan: {source}")
        if not supplemental or name == SUPPLEMENT:
            copy_one(source, PACKAGE / name, row["sha256"])
    verified = []
    for row in planned["files"]:
        copy_path = regular_path(PACKAGE.resolve(), row["path"])
        actual = sha(copy_path)
        if actual != row["sha256"] or copy_path.stat().st_size != row["bytes"]:
            raise ValueError(f"Copy failed independent recheck: {copy_path}")
        verified.append({"path": row["path"], "source_sha256": row["sha256"], "staged_sha256": actual,
                         "bytes": row["bytes"], "status": "MATCH"})
    write_csv(EVIDENCE / f"staging_sha256{revision}.csv", verified)
    write_json(EVIDENCE / f"staging_manifest{revision}.json", {"schema": "p1p2.clean-staging.v1", "package": str(PACKAGE),
        "manual_relative": PREFIX, "files": len(verified), "bytes": planned["bytes"],
        "verification": "SOURCE_AND_COPY_MATCH", "inventory_sha256": sha(EVIDENCE / f"staging_sha256{revision}.csv")})
    print(f"Copy verification PASS for {len(verified)} separate regular files")


def seal():
    plan = read(EVIDENCE / "staging_plan_final.json")
    documents = {"RUNPOD_DEPLOYMENT_GUIDE.md": "deployment/deployment_readme.md",
                 "RUNPOD_LINUX_ACCEPTANCE_CHECKLIST.md": "deployment/linux_acceptance_checklist.md",
                 "d_test_input_audit.json": "manifests/d_test_input_audit.json",
                 "path_mapping_manifest_final.json": "manifests/path_mapping_manifest.json"}
    files = list(plan["files"])
    for docs, name in documents.items():
        source = EVIDENCE / docs
        digest = sha(source)
        copy_one(source, PACKAGE / name, digest)
        files.append({"path": name, "sha256": digest, "bytes": source.stat().st_size,
                      "source_kind": "deployment-evidence"})
    files.sort(key=lambda row: row["path"])
    paths = {row["path"] for row in files}
    actual = {p.relative_to(PACKAGE).as_posix() for p in PACKAGE.rglob("*") if p.is_file()}
    if actual != paths:
        raise ValueError(f"Unexpected package membership: {sorted(actual ^ paths)}")
    for row in files:
        path = regular_path(PACKAGE.resolve(), row["path"])
        if sha(path) != row["sha256"]:
            raise ValueError(f"Sealing mismatch: {path}")
    sums = "".join(row["sha256"] + "  " + row["path"] + "\n" for row in files).encode("utf-8")
    checksums = PACKAGE / "manifests/SHA256SUMS.txt"
    with checksums.open("xb") as f:
        f.write(sums)
    csv_manifest = EVIDENCE / "RUNPOD_SHA256.csv"
    write_csv(csv_manifest, files)
    payload = {"schema": "p1p2.runpod-delivery.v1", "package": str(PACKAGE), "manual_relative": PREFIX,
               "payload_files": len(files), "payload_bytes": sum(row["bytes"] for row in files),
               "checksum_file": "manifests/SHA256SUMS.txt", "sha256sums_sha256": sha(checksums),
               "csv_manifest_sha256": sha(csv_manifest), "entries": files,
               "manifest_self_files_excluded": ["manifests/SHA256SUMS.txt",
                    "manifests/RUNPOD_PACKAGE_MANIFEST.json", "manifests/RUNPOD_SHA256.csv"]}
    manifest = EVIDENCE / "RUNPOD_PACKAGE_MANIFEST.json"
    write_json(manifest, payload)
    copy_one(manifest, PACKAGE / "manifests/RUNPOD_PACKAGE_MANIFEST.json", sha(manifest))
    copy_one(csv_manifest, PACKAGE / "manifests/RUNPOD_SHA256.csv", sha(csv_manifest))
    print(f"Sealed {len(files)} payload files and 3 manifest files: {sha(checksums)}")


if __name__ == "__main__":
    {"plan": plan, "copy": copy, "seal": seal}[sys.argv[1]]()
