"""Read-only inventories for staging, preserved artifacts and cleanup review."""
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PureWindowsPath
import re
import shutil
import stat
import subprocess
import sys

MANUAL = Path.cwd()
PIPELINE = MANUAL.parents[3]
OUT = Path(__file__).resolve().parent
BASE = OUT.parent / "run_b_s1_20261118_091644"
sys.path.insert(0, str(MANUAL / "scripts"))
from p1p2_artifact_manager import hash_path, sha256_file
from p1p2_paths import artifact_path, legacy_root
from build_capability_learning_dynamics import mapped_checkpoint_path

SOURCE_CHANGES = {
    "scripts/build_capability_learning_dynamics.py", "scripts/capability_eval.py",
    "scripts/p1p2_artifact_manager.py", "scripts/p1p2_controller.py", "scripts/p1p2_paths.py",
    "scripts/run_p1p2_post_eval.py", "scripts/select_checkpoint_on_dev.py", "scripts/train_round.py",
    "tests/test_p1p2_analysis.py", "tests/test_p1p2_artifact_manager.py", "tests/test_p1p2_runtime.py",
}


def json_write(name, data):
    with (OUT / name).open("x", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def csv_write(name, rows):
    with (OUT / name).open("x", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def reference_strings(value, pointer=""):
    if isinstance(value, str):
        yield pointer, value
    elif isinstance(value, list):
        for i, item in enumerate(value):
            yield from reference_strings(item, f"{pointer}/{i}")
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from reference_strings(item, f"{pointer}/{key}")


def usage(name, key):
    if name == "train_set.json" and key in {"pool", "state_file", "nll_file"}:
        return "runtime: pool, capability or learnability validation"
    if name == "train_log.json" and key == "checkpoint_parent":
        return "runtime: parent adapter identity"
    if name == "checkpoint_log.jsonl" and key in {"train_set", "checkpoint_path", "train_log"}:
        return "runtime: normalized locator and original log-prefix SHA"
    if name in {"checkpoint_lineage.json", "prediction_coverage_report.json"} and key in {
            "prediction_path", "checkpoint_path", "dev_predictions", "checkpoint"}:
        return "analysis: canonical candidate / mapped locator plus SHA"
    if name == "nll.jsonl.meta.json" and key in {"adapter", "adapter_path"}:
        return "runtime: NLL adapter identity"
    return "audit/provenance; no locator used by mapped controller validation"


def staging():
    suffix = "_sealed" if "--seal" in sys.argv else "_final" if "--final" in sys.argv else ""
    expected = {}
    for line in (BASE / "runpod_sha256sums_v2.txt").read_text(encoding="utf-8-sig").splitlines():
        digest, path = line.split("  ", 1)
        if path in expected:
            raise ValueError(f"Duplicate transfer path: {path}")
        expected[path] = digest
    manifest = {}
    changed = {}
    mismatch = {}
    for name, digest in expected.items():
        path = artifact_path(MANUAL, name)
        current = sha256_file(path) if path.is_file() else None
        if current != digest:
            if name in SOURCE_CHANGES and current is not None:
                changed[name] = {"previous": digest, "current": current}
            else:
                mismatch[name] = {"expected": digest, "observed": current}
        if current:
            manifest[name] = current
    if mismatch:
        json_write("transfer_blockers.json", mismatch)
        raise SystemExit("Prior transfer evidence mismatch; no updated manifest published")
    for name in SOURCE_CHANGES:
        manifest[name] = sha256_file(MANUAL / name)

    prefix = legacy_root(str(MANUAL))
    rows = []
    added_analysis = set()
    g6 = OUT / "g6_mapped_verified/capability_sidecar_inventory_seed13.csv"
    with g6.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            if row["valid"] != "True":
                raise ValueError(f"Unverified sidecar: {row['sidecar_source']}")
            for key in ("checkpoint_path", "verified_prediction_path", "sidecar_source"):
                path = (mapped_checkpoint_path(MANUAL, row[key], prefix)
                        if key == "checkpoint_path" else artifact_path(MANUAL, row[key], prefix))
                if key == "sidecar_source":
                    added_analysis.update(p for p in path.iterdir() if p.is_file())
                elif path.is_file():
                    added_analysis.add(path)
                elif path.is_dir():
                    added_analysis.update(p for p in path.rglob("*") if p.is_file())
                else:
                    raise FileNotFoundError(path)
    auxiliary = {"requirements-lock.txt": sha256_file(MANUAL.parents[2] / "requirements-lock.txt")}
    for path in added_analysis:
        if not path.is_relative_to(MANUAL):
            auxiliary[path.relative_to(MANUAL.parents[2]).as_posix()] = sha256_file(path)
            continue
        name = path.relative_to(MANUAL).as_posix()
        if name not in manifest:
            manifest[name] = sha256_file(path)

    inventory_roots = {"runs", "models", "reports"}
    metadata_names = {"train_set.json", "train_log.json", "checkpoint_log.jsonl", "checkpoint_lineage.json",
                      "input_fingerprint.json", "prediction_coverage_report.json",
                      "s0_base_model_reference.json", "selection_round_002.json", "S0_state.json"}
    for name in sorted(manifest):
        path = MANUAL / name
        if name.split("/", 1)[0] not in inventory_roots:
            continue
        if path.name not in metadata_names and not path.name.endswith((".meta.json", ".intent.json", "_reference.json")):
            continue
        metadata = ([json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
                    if path.suffix == ".jsonl" else read_json(path))
        for pointer, recorded in reference_strings(metadata):
            win = PureWindowsPath(recorded)
            key = pointer.rsplit("/", 1)[-1]
            begins_path = win.is_absolute() or (len(recorded) < 260 and recorded.startswith(
                ("runs/", "models/", "reports/", "data/", "splits/", "trajectory/", "config/",
                 "runs\\", "models\\", "reports\\", "data\\", "splits\\", "trajectory\\", "config\\")))
            if not begins_path:
                continue
            mapped = None
            try:
                mapped = (mapped_checkpoint_path(MANUAL, recorded, prefix)
                          if path.name == "checkpoint_lineage.json" and key == "checkpoint_path"
                          else artifact_path(MANUAL, recorded, prefix))
                outcome = "PRESENT" if mapped.exists() else "MISSING"
            except ValueError:
                outcome = "OUTSIDE_MAPPED_ROOT"
            rows.append({"artifact": name, "json_pointer": pointer, "recorded_path": recorded,
                         "path_kind": "WINDOWS_ABSOLUTE" if win.is_absolute() else "MANUAL_RELATIVE",
                         "staging_relative": (mapped.relative_to(MANUAL).as_posix() if mapped.is_relative_to(MANUAL)
                                              else mapped.relative_to(MANUAL.parents[2]).as_posix()) if mapped else "",
                         "staging_base": ("manual" if mapped.is_relative_to(MANUAL) else "P2") if mapped else "",
                         "use": usage(path.name, key), "locator_status": outcome})
    csv_write(f"runpod_path_reference_inventory{suffix}.csv", rows)
    with (OUT / f"runpod_sha256sums{suffix}.txt").open("x", encoding="utf-8", newline="\n") as stream:
        stream.writelines(f"{digest}  {name}\n" for name, digest in sorted(manifest.items()))
    with (OUT / f"runpod_p2_sha256sums{suffix}.txt").open("x", encoding="utf-8", newline="\n") as stream:
        stream.writelines(f"{digest}  {name}\n" for name, digest in sorted(auxiliary.items()))
    deps = {}
    import importlib.metadata as metadata
    for package in ("torch", "transformers", "peft", "accelerate", "PyYAML", "safetensors",
                    "matplotlib", "numpy", "datasets", "huggingface-hub"):
        try:
            deps[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            deps[package] = None
    lock = MANUAL.parents[2] / "requirements-lock.txt"
    json_write(f"runpod_transfer_verification{suffix}.json", {
        "utc": datetime.now(timezone.utc).isoformat(), "prior_entries": len(expected),
        "prior_unchanged_sha256": len(expected) - len(changed), "updated_source_sha256": changed,
        "staging_files": len(manifest), "additional_files": sorted(set(manifest) - set(expected)),
        "total_bytes": sum((MANUAL / name).stat().st_size for name in manifest),
        "p2_auxiliary_files": len(auxiliary),
        "p2_auxiliary_bytes": sum((MANUAL.parents[2] / name).stat().st_size for name in auxiliary),
        "path_occurrences": len(rows),
        "path_status": dict(Counter((r["locator_status"] for r in rows))),
        "requirements_lock": {"path": lock.relative_to(PIPELINE).as_posix(), "sha256": sha256_file(lock)},
        "python_windows": sys.version, "dependency_versions_windows": deps,
    })


def git_files(root, *options):
    return set(subprocess.check_output(["git", "ls-files", "-z", *options], cwd=root)
               .decode("utf-8", "surrogateescape").strip("\0").split("\0"))


def walk(directory):
    for child in sorted(directory.iterdir()):
        if (child.name in {".git", ".venv", "node_modules", ".codex", ".agents"} or child == OUT
                or child.is_symlink() or child.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT):
            continue
        if child.is_dir():
            yield from walk(child)
        elif child.is_file():
            yield child


def cleanup():
    with (BASE / "repository_cleanup_inventory.csv").open(encoding="utf-8-sig", newline="") as stream:
        prior = {r["path"]: r for r in csv.DictReader(stream)}
    tracked, untracked = set(), set()
    for repo in (PIPELINE / "P1", PIPELINE / "P2"):
        tracked.update(f"{repo.name}/{rel}" for rel in git_files(repo, "--cached"))
        untracked.update(f"{repo.name}/{rel}" for rel in git_files(repo, "--others", "--exclude-standard"))
    items, references = [], []
    size = 0
    archive_targets = {
        "P1/experiments/week2September/manual/config/config_p1.zip",
        "P1/experiments/week2September/manual/scripts/scripts_p1_original.zip",
    }
    path_pattern = re.compile(r"(?:[A-Z]:[\\/]+Users[\\/]|\bweek2September[\\/]+manual\b|"
                              r"(?:\.\.[\\/])+|(?:[a-z][a-z0-9_.-]+)\.zip\b|"
                              r"\bPath\(__file__\)|\b\.parents\[\d+\])", re.I)
    docs = {".md", ".txt", ".rst"}
    source = {".ps1", ".sh", ".bat", ".cmd", ".py"}
    config = {".yaml", ".yml", ".toml", ".json"}
    for path in walk(PIPELINE):
        name = path.relative_to(PIPELINE).as_posix()
        info = prior.get(name, {})
        disposition = info.get("disposition", "UNKNOWN / NEEDS REVIEW")
        reason = info.get("reason", "New since baseline; review context")
        suffix = path.suffix.lower()
        nbytes = path.stat().st_size
        old_digest = info.get("zip_sha256", "")
        digest = ""
        archive_destination = ""
        if suffix == ".zip":
            digest = sha256_file(path)
            if name in archive_targets and old_digest == digest:
                disposition = "ARCHIVE"
                reason = "Verified proposal source archive; preserve bytes even if extracted copies match"
                archive_destination = f"<verified-backup>/Pipeline_archive_20261119/{name}"
            elif old_digest != digest:
                disposition = "UNKNOWN / NEEDS REVIEW"
                reason = "New or changed ZIP since baseline; keep in place"
        elif suffix == ".pyc" and "__pycache__" in path.parts:
            try:
                has_source = Path(importlib.util.source_from_cache(str(path))).is_file()
            except ValueError:
                has_source = False
            disposition = "DELETE CANDIDATE" if has_source and name not in tracked else "KEEP"
            reason = "Regenerable cache with source present" if disposition == "DELETE CANDIDATE" else "Source or Git ownership unresolved"
        elif name not in prior and suffix in docs | source | config | {".csv", ".jsonl", ".png", ".log"}:
            disposition = "KEEP"
            reason = "Current source, docs or evidence"
        if path.is_relative_to(MANUAL):
            size += nbytes
        metadata_log = path.name in {"checkpoint_log.jsonl", "train_log.json", "train_set.json", "checkpoint_lineage.json"}
        checked = suffix in docs | source | config or metadata_log
        if checked and 0 < nbytes <= 2 * 1024**2:
            category = ("checkpoint_metadata" if metadata_log else "source_or_shell" if suffix in source else
                        "configuration_or_json" if suffix in config else "documentation")
            matches = Counter()
            first_lines = {}
            try:
                for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
                    for match in path_pattern.finditer(line):
                        locator = match.group(0).lower()
                        matches[locator] += 1
                        first_lines.setdefault(locator, number)
            except (UnicodeError, OSError):
                checked = False
            for locator, count in sorted(matches.items()):
                references.append({"path": name, "artifact_type": category, "locator": locator,
                                   "first_line": first_lines[locator], "occurrences": count,
                                   "git": "TRACKED" if name in tracked else "UNTRACKED_OR_OUTSIDE_REPO"})
        items.append({"path": name, "bytes": nbytes, "git": "TRACKED" if name in tracked else
                      "UNTRACKED" if name in untracked else "IGNORED_OR_OUTSIDE_REPO",
                      "disposition": disposition, "reason": reason,
                      "zip_sha256": digest, "zip_members_at_baseline": info.get("zip_entries", "") if digest == old_digest else "",
                      "zip_crc_matches_at_baseline": info.get("zip_members_crc_matched", "") if digest == old_digest else "",
                      "zip_archive_proposal": archive_destination, "dependency_scan": (
                          "READ_TEXT" if checked and nbytes <= 2 * 1024**2 else "NOT_SCANNED")})
    csv_write("cleanup_inventory_updated.csv", items)
    csv_write("cleanup_dependency_references.csv", references)
    zip_rows = [item for item in items if item["zip_sha256"]]
    json_write("cleanup_summary.json", {
        "scope": str(PIPELINE), "files": len(items), "prior_files": len(prior),
        "dispositions": dict(Counter(item["disposition"] for item in items)),
        "dependence_entries": len(references), "dependency_files": len({item["path"] for item in references}),
        "windows_manual_references": len({item["path"] for item in references if "week2september" in item["locator"]}),
        "manual_bytes": size, "zip_count": len(zip_rows), "zip_bytes": sum(row["bytes"] for row in zip_rows),
        "bytecode_candidate_bytes": sum(item["bytes"] for item in items if item["disposition"] == "DELETE CANDIDATE"),
        "free_space": shutil.disk_usage(PIPELINE).free,
        "archival_candidates": [row for row in zip_rows if row["zip_archive_proposal"]],
        "manual_zip_records": [row for row in zip_rows if Path(row["path"]).name == "manual.zip"],
    })


def protected():
    expected = read_json(OUT / "protected_hashes_before.json")
    observed = {path: hash_path(Path(path)) if Path(path).exists() else None for path in expected}
    mismatches = {path: {"expected": digest, "observed": observed[path]}
                  for path, digest in expected.items() if observed[path] != digest}
    json_write("protected_hashes_after.json", {"observed": observed, "mismatches": mismatches})
    if mismatches:
        raise SystemExit("Protected inputs or artifacts failed integrity checks")


if __name__ == "__main__":
    {"staging": staging, "cleanup": cleanup, "protected": protected}[sys.argv[1]]()
