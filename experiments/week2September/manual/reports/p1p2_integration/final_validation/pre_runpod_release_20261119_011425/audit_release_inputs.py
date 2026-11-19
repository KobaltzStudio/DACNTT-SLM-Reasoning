"""Read-only release and pinned HF cache verification, without importing a model framework."""
import ast
import csv
import hashlib
import importlib.metadata as metadata
import json
import os
from collections import defaultdict
from pathlib import Path, PurePosixPath
import re
import stat
import sys
from huggingface_hub import try_to_load_from_cache
from huggingface_hub.constants import HF_HUB_CACHE

ROOT = Path.cwd().resolve()
WORKSPACE = ROOT.parents[3]
STAGE = Path("C:/Users/PC - NGHI/Desktop/Pipeline/p1p2_unified/runpod_package_20261119_004529")
PRIOR = ROOT / "reports/p1p2_integration/final_validation/final_local_20261119_004529"
EVIDENCE = Path(__file__).resolve().parent
MANUAL = "P2/experiments/week2September/manual"
INDEX = "manifests/RUNPOD_PACKAGE_MANIFEST.json"
SUMS = "manifests/SHA256SUMS.txt"
CSV = "manifests/RUNPOD_SHA256.csv"
PINS = {
    INDEX: "dbe0d5bb0b2b80df5d0b4f41ff57b3318a543c264e2d5b20c5c7f818e0424f62",
    SUMS: "bf0c50c301de9e2b78d9533a6a995733a431a6834d8ad019926e1c826af07798",
}
DERIVED = {
    "deployment/deployment_readme.md": "RUNPOD_DEPLOYMENT_GUIDE.md",
    "deployment/linux_acceptance_checklist.md": "RUNPOD_LINUX_ACCEPTANCE_CHECKLIST.md",
    "manifests/d_test_input_audit.json": "d_test_input_audit.json",
    "manifests/path_mapping_manifest.json": "path_mapping_manifest_final.json",
}
SEEDS = ("run_p1_p2", "run_p1p2_post_eval", "run_final_d_test", "eval_student", "compute_nll",
         "train_round", "select_round", "p1p2_selector", "build_capability_learning_dynamics",
         "select_checkpoint_on_dev", "build_p1p2_analysis_figures", "generate_teacher_trajectories_batch")

def sha(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()

def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def write_json(name, data):
    with (EVIDENCE / name).open("x", encoding="utf8") as out:
        json.dump(data, out, ensure_ascii=False, indent=2)

def write_csv(name, rows, fields=None):
    with (EVIDENCE / name).open("x", encoding="utf8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=fields or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

def reject_link(path):
    attrs = getattr(path.lstat(), "st_file_attributes", 0)
    if path.is_symlink() or attrs & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0):
        raise ValueError(f"Package contains a link or reparse point: {path}")

def package_paths(root):
    reject_link(root)
    names, folded = {}, {}
    for parent, dirs, files in os.walk(root):
        for child in dirs + files:
            p = Path(parent) / child
            reject_link(p)
            name = p.relative_to(root).as_posix()
            normalized = name.casefold()
            if normalized in folded:
                raise ValueError(f"Case collision: {name}, {folded[normalized]}")
            folded[normalized] = name
            if child in files:
                if not p.is_file():
                    raise ValueError(f"Not a regular file: {p}")
                names[name] = p
    return names

def validate_name(name):
    p = PurePosixPath(name)
    if (not p.parts or p.is_absolute() or p.as_posix() != name or ".." in p.parts
            or any(part.endswith((" ", ".")) or any(c in part for c in "\\:\r\n") for part in p.parts)):
        raise ValueError(f"Unsafe manifest path: {name}")

def parse_sums(path):
    items = {}
    for line in path.read_text(encoding="utf8").splitlines():
        digest, name = line.split("  ", 1)
        validate_name(name)
        if name in items or not re.fullmatch(r"[a-f0-9]{64}", digest):
            raise ValueError(f"Invalid or duplicate manifest entry: {name}")
        items[name] = digest
    return items

def closure():
    scripts = {p.stem: p for p in (STAGE / MANUAL / "scripts").glob("*.py")}
    originals = {p.stem for p in (ROOT / "scripts").glob("*.py")}
    nodes, external = {}, set()
    queue = list(SEEDS)
    while queue:
        name = queue.pop()
        if name in nodes:
            continue
        imports = set()
        tree = ast.parse(scripts[name].read_bytes(), filename=str(scripts[name]))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(a.name.split(".")[0] for a in node.names)
            if isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        local = imports & originals
        if local - scripts.keys():
            raise ValueError(f"Missing local imports: {sorted(local - scripts.keys())}")
        nodes[name] = sorted(local)
        queue.extend(local)
        external.update(imports - originals - sys.stdlib_module_names)
    return nodes, sorted(external)

def protected():
    rows = []
    with (PRIOR / "protected_artifact_inventory.csv").open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            path = Path(row["source"])
            observed = hash_path(path)
            if observed != row["expected_sha256"]:
                raise ValueError(f"Protected fingerprint changed: {path}")
            rows.append({"path": str(path), "sha256": observed})
    assert len(rows) == 52
    return rows

def package_and_cache():
    files = package_paths(STAGE)
    for name, digest in PINS.items():
        if sha(files[name]) != digest:
            raise ValueError(f"Trusted release index SHA mismatch: {name}")
    manifest = read(files[INDEX])
    if manifest["schema"] != "p1p2.runpod-delivery.v1" or manifest["manual_relative"] != MANUAL:
        raise ValueError("Unexpected delivery manifest schema or layout")
    assert set(manifest["manifest_self_files_excluded"]) == {INDEX, SUMS, CSV}
    assert sha(files[CSV]) == manifest["csv_manifest_sha256"]
    sums = parse_sums(files[SUMS])
    assert set(files) == set(sums) | {INDEX, SUMS, CSV}
    assert len(sums) == manifest["payload_files"] == 655 and len(files) == 658
    csv_rows = list(csv.DictReader(files[CSV].open(encoding="utf8", newline="")))
    assert len(csv_rows) == 655
    assert [(r["path"], r["sha256"], int(r["bytes"]), r["source_kind"]) for r in csv_rows] == [
        (r["path"], r["sha256"], r["bytes"], r["source_kind"]) for r in manifest["entries"]]
    unique = set()
    grouped = defaultdict(list)
    total = 0
    for row in manifest["entries"]:
        name = row["path"]
        validate_name(name)
        if name in unique:
            raise ValueError(f"Duplicate manifest entry: {name}")
        unique.add(name)
        target = files[name]
        observed = sha(target)
        size = target.stat().st_size
        if observed != sums[name] or observed != row["sha256"] or size != row["bytes"]:
            raise ValueError(f"Package entry mismatch: {name}")
        source = PRIOR / DERIVED[name] if name in DERIVED else WORKSPACE / name
        if sha(source) != observed or source.stat().st_size != size:
            raise ValueError(f"Source-to-stage mismatch: {source}")
        grouped[observed].append(name)
        total += size
    assert unique == set(sums)
    assert total == manifest["payload_bytes"] == 574994622
    assert sum(p.stat().st_size for p in files.values()) == 575403394
    debris = [name for name in files if re.search(
        r"(?i)(\.zip$|\.pyc$|\.tmp$|\.bak(?:$|_)|/__pycache__/|/eval_test[^/]*$)", name)]
    if debris:
        raise ValueError(f"Unexpected package exclusions: {debris}")
    graph, external = closure()
    mapped = read(files["manifests/path_mapping_manifest.json"])
    archive_only_unstaged = []
    for row in mapped["all_occurrences"]:
        relative = row["staging_relative"]
        if not relative:
            if row["use"].startswith("runtime"):
                raise ValueError(f"Unmapped runtime locator: {row}")
            continue
        base = {"package": "", "P2": "P2/", "manual": MANUAL + "/"}[row["staging_base"]]
        target = base + relative
        if target not in files and not any(f.startswith(target + "/") for f in files):
            if row["use"].startswith(("runtime", "analysis")):
                raise ValueError(f"Missing executable locator: {target}")
            archive_only_unstaged.append({"metadata": row["artifact"], "target": target,
                                          "local_exists": (WORKSPACE / target).exists()})
    packages = ("torch", "transformers", "peft", "accelerate", "tokenizers", "datasets", "bitsandbytes",
                "huggingface-hub", "safetensors", "PyYAML", "matplotlib")
    installed = {}
    for name in packages:
        try:
            installed[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            installed[name] = None
    config = read(STAGE / MANUAL / "config/experiment_config.json")
    student = config["student"]
    model, rev = student["model"], student["revision"]
    revision_dir = Path(HF_HUB_CACHE) / ("models--" + model.replace("/", "--")) / "snapshots" / rev
    cache_names = ("config.json", "generation_config.json", "merges.txt", "model.safetensors",
                   "tokenizer.json", "tokenizer_config.json", "vocab.json")
    cache_files = []
    for name in cache_names:
        cache = try_to_load_from_cache(model, name, revision=rev)
        if not isinstance(cache, str) or Path(cache) != revision_dir / name or not Path(cache).is_file():
            raise FileNotFoundError(f"Pinned HF cache has no usable {name}: {revision_dir}")
        p = Path(cache)
        resolved = p.resolve()
        if not resolved.is_relative_to(revision_dir.parent.parent.resolve()):
            raise ValueError(f"HF cache target escapes repository cache: {p}")
        cache_files.append({"classification": "SEPARATE_TRANSFER_REQUIRED", "model": model, "revision": rev,
            "linux_hub_relative": p.relative_to(Path(HF_HUB_CACHE)).as_posix(), "windows_source": str(p),
            "resolved_source": str(resolved), "bytes": p.stat().st_size, "sha256": sha(p)})
    weight = next(r for r in cache_files if r["linux_hub_relative"].endswith("/model.safetensors"))
    if weight["sha256"] != "dd924a11b4c220f385b51ffa522daea7c9f3d850e31b162bb5661df483c6d3ee":
        raise ValueError("Student base weights do not match the anchored SHA")
    model_config = read(revision_dir / "config.json")
    if model_config["model_type"] != "qwen2":
        raise ValueError("Pinned Student config model_type differs")
    with (revision_dir / "model.safetensors").open("rb") as f:
        header_size = int.from_bytes(f.read(8), "little")
        if not 2 <= header_size <= 4_000_000:
            raise ValueError("Invalid safetensors header size")
        tensors = json.loads(f.read(header_size))
        spans = [v["data_offsets"] for name, v in tensors.items() if name != "__metadata__"]
        assert spans and max(s[1] for s in spans) == weight["bytes"] - header_size - 8
    write_csv("MODEL_CACHE_TRANSFER_MANIFEST.csv", cache_files)
    linux_sums = "".join(f"{r['sha256']}  {r['linux_hub_relative']}\n" for r in cache_files)
    with (EVIDENCE / "MODEL_CACHE_SHA256SUMS.txt").open("x", encoding="utf8", newline="\n") as f:
        f.write(linux_sums)
    state = {"package": str(STAGE), "expected_fingerprints": PINS, "files": len(files),
             "payload_files": len(unique), "total_bytes": sum(p.stat().st_size for p in files.values()),
             "verified_source_correspondence": len(unique), "duplicate_content_groups": [
                 {"sha256": digest, "paths": aliases} for digest, aliases in grouped.items() if len(aliases) > 1],
             "path_collisions": 0, "reparse_points": 0, "package_debris": debris,
             "runtime_locators": mapped["runtime_occurrences"], "all_mapped_locators": len(mapped["all_occurrences"]),
             "audit_only_unstaged_locators": archive_only_unstaged,
             "ast_runtime_graph": graph, "external_entrypoint_imports": external, "windows_package_versions": installed,
             "student_model": model, "student_revision": rev, "snapshot": str(revision_dir),
             "cache_files": cache_files, "cache_bytes": sum(r["bytes"] for r in cache_files),
             "safetensors_count": len(spans), "cache_sumfile_sha256": sha(EVIDENCE / "MODEL_CACHE_SHA256SUMS.txt"),
             "protected": protected()}
    write_json("integrity_observation.json", state)
    print(f"Package {len(files)} files; 655 exact source matches; cache {len(cache_files)} files / {state['cache_bytes']} bytes; protected 52/52")

sys.path.insert(0, str(ROOT / "scripts"))
from p1p2_artifact_manager import hash_path
if __name__ == "__main__":
    package_and_cache()
