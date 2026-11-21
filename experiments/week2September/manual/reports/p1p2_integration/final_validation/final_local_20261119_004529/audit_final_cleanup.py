"""Read-only original workspace cleanup census and streaming ZIP audit."""
from collections import Counter
import csv
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
from zipfile import ZipFile

MANUAL = Path.cwd().resolve()
PIPELINE = MANUAL.parents[3]
EVIDENCE = Path(__file__).resolve().parent
BASE = MANUAL / "reports/p1p2_integration/final_validation/post_validation_20261119"
STAGE = Path("C:/Users/PC - NGHI/Desktop/Pipeline/p1p2_unified/runpod_package_20261119_004529")
MANUAL_ZIP = "P1/experiments/week2September/manual/manual.zip"
KNOWN_ARCHIVES = {
    "P1/experiments/week2September/manual/config/config_p1.zip",
    "P1/experiments/week2September/manual/scripts/scripts_p1_original.zip",
}


def sha(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def relative(path):
    return path.relative_to(PIPELINE).as_posix()


def regular_path(path):
    return path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(PIPELINE)


def csv_output(name, rows):
    with (EVIDENCE / name).open("x", encoding="utf-8-sig", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def walk(root):
    for path in sorted(root.iterdir()):
        if (path.name in {".git", ".venv", "node_modules", ".codex", ".agents"}
                or path in {STAGE.parent, EVIDENCE}):
            continue
        info = path.lstat()
        if path.is_symlink() or getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0):
            continue
        if path.is_dir():
            yield from walk(path)
        elif path.is_file():
            yield path


def git_paths(root, *options):
    raw = subprocess.check_output(["git", "--no-optional-locks", "ls-files", "-z", *options], cwd=root)
    return {f"{root.name}/{name}" for name in raw.decode("utf-8").split("\0") if name}


def manual_zip_audit(path):
    findings = []
    used = set()
    with ZipFile(path) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            member = PurePosixPath(info.filename.replace("\\", "/"))
            if (not member.parts or member.is_absolute() or ".." in member.parts
                    or any(":" in segment for segment in member.parts) or member.as_posix().casefold() in used):
                raise ValueError(f"ZIP unsafe or duplicate member: {info.filename}")
            used.add(member.as_posix().casefold())
            with archive.open(info) as stream:
                member_sha = hashlib.file_digest(stream, "sha256").hexdigest()
            candidates = (path.parent.joinpath(*member.parts), path.with_suffix("").joinpath(*member.parts))
            match = next((candidate for candidate in candidates if regular_path(candidate)
                          and candidate.stat().st_size == info.file_size and sha(candidate) == member_sha), None)
            findings.append({"archive": relative(path), "member": member.as_posix(), "bytes": info.file_size,
                             "archive_member_sha256": member_sha,
                             "matched_copy": relative(match) if match else "",
                             "source_sha256": member_sha if match else "",
                             "prior_8MiB_limit_excluded": info.file_size > 8 * 1024**2,
                             "status": "MATCH" if match else "UNKNOWN_REQUIRES_REVIEW"})
    csv_output("manual_zip_member_audit.csv", findings)
    return (len(findings), sum(row["status"] == "MATCH" for row in findings),
            sum(row["status"] == "MATCH" and row["prior_8MiB_limit_excluded"] for row in findings))


def main():
    with (BASE / "cleanup_inventory_updated.csv").open(encoding="utf-8-sig", newline="") as f:
        prior = {row["path"]: row for row in csv.DictReader(f)}
    package_files = {row["path"] for row in json.loads(
        (EVIDENCE / "staging_plan_final.json").read_text(encoding="utf8"))["files"]}
    tracked, untracked = set(), set()
    for repo in (PIPELINE / "P1", PIPELINE / "P2"):
        tracked.update(git_paths(repo, "--cached"))
        untracked.update(git_paths(repo, "--others", "--exclude-standard"))
    census, zips, bytecode = [], [], []
    manual_check = None
    for path in walk(PIPELINE):
        key = relative(path)
        item = prior.get(key, {})
        suffix = path.suffix.lower()
        file_git = ("TRACKED" if key in tracked else "UNTRACKED" if key in untracked
                    else "IGNORED_OR_OUTSIDE_REPO")
        status, reason = "UNKNOWN_REQUIRES_REVIEW", "Ownership or runtime relationship not established"
        if suffix == ".zip":
            digest = sha(path)
            before = item.get("zip_sha256")
            check = "MATCH_BASELINE" if before == digest else "NEW_OR_CHANGED"
            compared, matched, beyond = "", "", ""
            if key == MANUAL_ZIP:
                manual_check = manual_zip_audit(path)
                compared, matched, beyond = manual_check
            if key in KNOWN_ARCHIVES and before == digest:
                status, reason = "ARCHIVE_CANDIDATE", "Reviewed source archive; store only after approval"
            else:
                reason = "Original ZIP retained regardless of extracted-match counts"
            zips.append({"path": key, "bytes": path.stat().st_size, "sha256": digest,
                         "baseline_status": check, "prior_members": item.get("zip_members_at_baseline", ""),
                         "prior_crc_match": item.get("zip_crc_matches_at_baseline", ""),
                         "sha_members_compared_now": compared, "sha_members_matching_now": matched,
                         "sha_matches_previously_unchecked_large_members": beyond,
                         "cleanup_class": status, "action": "KEEP_ORIGINAL"})
        elif suffix == ".pyc" and "__pycache__" in path.parts:
            try:
                source = Path(importlib.util.source_from_cache(str(path)))
            except ValueError:
                source = None
            if source and regular_path(source) and key not in tracked:
                status, reason = "DELETE_SAFE_CANDIDATE", "Regenerable with verified source; original retained"
            bytecode.append({"path": key, "bytes": path.stat().st_size, "git_status": file_git,
                             "source": relative(source) if source and source.is_relative_to(PIPELINE) else "",
                             "classification": status, "original_action": "KEEP", "staging_action": "OMIT"})
        elif key in package_files and ("/scripts/" in key or "/tests/" in key or "/config/" in key
                                      or key in {"P2/requirements.txt", "P2/requirements-lock.txt"}):
            status, reason = "KEEP_ACTIVE", "Deployment script, test, config or dependency lock"
        elif item.get("disposition") == "ARCHIVE":
            status, reason = "ARCHIVE_CANDIDATE", "Historical copy or backup; hold for owner review"
        elif (key in package_files or suffix in {".py", ".md", ".txt", ".json", ".jsonl", ".csv", ".yaml",
                 ".toml", ".yml", ".docx", ".pdf", ".safetensors", ".bin", ".pt", ".png", ".svg", ".ps1", ".sh", ".ipynb"}):
            status, reason = "KEEP_REPRODUCIBILITY", "Source, research result, fixture or audit evidence"
        census.append({"path": key, "bytes": path.stat().st_size, "git_status": file_git, "classification": status,
                       "reason": reason, "in_package": key in package_files})
    staged_debris = [p for p in STAGE.rglob("*") if p.suffix.lower() in {".zip", ".pyc"} or p.name == "__pycache__"]
    if staged_debris:
        raise ValueError(f"Unexpected staging debris: {staged_debris}")
    csv_output("CLEANUP_FINAL_INVENTORY.csv", census)
    csv_output("zip_redundancy_audit.csv", zips)
    csv_output("bytecode_cleanup_audit.csv", bytecode)
    counts = Counter(row["classification"] for row in census)
    output = {"files": len(census), "classes": counts, "zips": len(zips),
              "zip_bytes": sum(row["bytes"] for row in zips), "bytecode_candidates": counts["DELETE_SAFE_CANDIDATE"],
              "bytecode_candidate_bytes": sum(row["bytes"] for row in bytecode
                                              if row["classification"] == "DELETE_SAFE_CANDIDATE"),
              "manual_zip": dict(zip(("files", "sha_matches", "previously_unchecked_matches"), manual_check)),
              "free_bytes_checked": shutil.disk_usage(PIPELINE).free, "original_deletions": 0,
              "original_moves": 0, "staging_debris": 0,
              "scope_excludes": [str(EVIDENCE), str(STAGE.parent), ".git", "virtualenvs",
                                 "tool caches", "reparse points"]}
    with (EVIDENCE / "cleanup_census.json").open("x", encoding="utf8") as f:
        json.dump(output, f, indent=2)
    print(output)


if __name__ == "__main__":
    main()
