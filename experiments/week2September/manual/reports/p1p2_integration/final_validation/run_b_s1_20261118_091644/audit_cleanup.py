"""Read-only Pipeline inventory with ZIP central-directory and extracted-copy checks."""
from collections import Counter
import csv
import hashlib
import importlib.util
from pathlib import Path, PurePosixPath
import stat
import zipfile
import zlib

evidence = Path(__file__).resolve().parent
pipeline = evidence.parents[7]


def classify(path):
    parts = {p.casefold() for p in path.relative_to(pipeline).parts}
    if path.suffix.lower() == ".zip":
        return "UNKNOWN / NEEDS REVIEW", "Archive may be original source, backup, handoff or evidence"
    if "__pycache__" in parts and path.suffix.lower() == ".pyc":
        try:
            source = Path(importlib.util.source_from_cache(str(path)))
        except ValueError:
            return "UNKNOWN / NEEDS REVIEW", "No verified source mapping"
        if source.is_file():
            return "DELETE CANDIDATE", f"Regenerable bytecode with existing source {source}"
    if any(part.startswith(("backup_", "_controller_fixed", "_b4b5_patch")) for part in parts):
        return "ARCHIVE", "Historical staging or backup; retain bytes and provenance"
    if path.suffix.lower() in {".py", ".md", ".txt", ".json", ".jsonl", ".csv", ".yaml", ".yml", ".docx",
                                ".pdf", ".safetensors", ".bin", ".pt", ".png", ".svg", ".ps1", ".sh", ".ipynb"}:
        return "KEEP", "Source, guide, dataset, model, experiment output or provenance"
    return "UNKNOWN / NEEDS REVIEW", "Type or ownership not established"


def archive_info(path):
    try:
        with zipfile.ZipFile(path) as archive:
            entries = [m for m in archive.infolist() if not m.is_dir()]
            with path.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            checked = matched = 0
            for member in entries:
                name = PurePosixPath(member.filename.replace("\\", "/"))
                if (name.is_absolute() or ".." in name.parts or any(":" in part for part in name.parts)
                        or member.file_size > 8 * 1024**2):
                    continue
                candidates = (path.parent.joinpath(*name.parts), path.with_suffix("").joinpath(*name.parts))
                candidates = [copy for copy in candidates if copy.resolve().is_relative_to(pipeline)
                              and copy.is_file() and copy.stat().st_size == member.file_size]
                if not candidates:
                    continue
                checked += 1
                if any(zlib.crc32(copy.read_bytes()) == member.CRC for copy in candidates):
                    matched += 1
            return {
                "zip_sha256": digest, "zip_entries": len(entries),
                "zip_first_members": " | ".join(m.filename for m in entries[:12]),
                "zip_total_uncompressed": sum(m.file_size for m in entries),
                "zip_members_compared": checked, "zip_members_crc_matched": matched,
                "zip_match_scope": "Sibling or same-stem extracted files up to 8 MiB each; no extraction",
            }
    except (zipfile.BadZipFile, OSError) as exc:
        return {"zip_match_scope": f"{type(exc).__name__}: {exc}"}


def walk(directory):
    for child in sorted(directory.iterdir()):
        if child.name in {".git", ".venv", "node_modules", ".codex", ".agents"} or child == evidence:
            continue
        if child.is_symlink() or getattr(child.lstat(), "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            continue
        if child.is_dir():
            yield from walk(child)
        elif child.is_file():
            yield child


fields = ("path", "type", "bytes", "disposition", "reason", "zip_sha256", "zip_entries",
          "zip_first_members", "zip_total_uncompressed", "zip_members_compared", "zip_members_crc_matched", "zip_match_scope")
counts = Counter()
with (evidence / "repository_cleanup_inventory.csv").open("x", encoding="utf-8-sig", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    for file in walk(pipeline):
        status, reason = classify(file)
        counts[status] += 1
        details = archive_info(file) if file.suffix.lower() == ".zip" else {}
        writer.writerow({"path": file.relative_to(pipeline).as_posix(), "type": file.suffix, "bytes": file.stat().st_size,
                         "disposition": status, "reason": reason, **details})
        if details:
            print(file.relative_to(pipeline), details, flush=True)
print(dict(counts))
