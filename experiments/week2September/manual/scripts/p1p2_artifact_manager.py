from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Iterable, Mapping


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of a regular file."""
    source = Path(path).resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Input file not found: {source}")
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hash_path(path: Path) -> str:
    """Hash directory bytes with the case-insensitive order of archived Windows runs."""
    root = Path(path).resolve()
    if root.is_file():
        return sha256_file(root)
    if not root.is_dir():
        raise FileNotFoundError(root)
    files = [p.relative_to(root) for p in root.rglob("*") if p.is_file()]
    if not files:
        raise ValueError(f"Empty checkpoint directory: {root}")
    normalized = [tuple(part.lower() for part in relative.parts) for relative in files]
    if len(set(normalized)) != len(files):
        raise ValueError(f"Case-colliding checkpoint paths: {root}")
    digest = hashlib.sha256()
    for relative in sorted(files, key=lambda p: tuple(part.lower() for part in p.parts)):
        digest.update(relative.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha256_file(root / relative).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize JSON deterministically for stable fingerprints."""
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def fingerprint_files(paths: Mapping[str, Path]) -> dict[str, Any]:
    """Fingerprint named input files; names are stable logical identifiers."""
    if not paths:
        raise ValueError("At least one input file is required for a fingerprint")
    entries: dict[str, dict[str, Any]] = {}
    resolved_seen: dict[str, str] = {}
    for name in sorted(paths):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Fingerprint input names must be non-empty strings")
        path = Path(paths[name]).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Fingerprint input '{name}' not found: {path}")
        normalized = str(path).casefold()
        if normalized in resolved_seen:
            raise ValueError(f"Duplicate fingerprint path for '{name}' and '{resolved_seen[normalized]}'")
        resolved_seen[normalized] = name
        entries[name] = {
            "path": str(path),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
    payload = {"schema_version": "p1p2.input-fingerprint.v1", "files": entries}
    payload["fingerprint_sha256"] = sha256_json(payload)
    return payload


def verify_fingerprint(fingerprint: Mapping[str, Any]) -> bool:
    """Verify a fingerprint object's internal canonical digest."""
    if not isinstance(fingerprint, Mapping):
        raise TypeError("Fingerprint must be a mapping")
    if fingerprint.get("schema_version") != "p1p2.input-fingerprint.v1":
        raise ValueError("Unsupported fingerprint schema")
    files = fingerprint.get("files")
    digest = fingerprint.get("fingerprint_sha256")
    if not isinstance(files, Mapping) or not isinstance(digest, str):
        raise ValueError("Fingerprint is missing files or fingerprint_sha256")
    unsigned = {key: value for key, value in fingerprint.items() if key != "fingerprint_sha256"}
    actual = sha256_json(unsigned)
    if actual != digest:
        raise ValueError("Fingerprint digest mismatch")
    return True


def verify_fingerprint_files(fingerprint: Mapping[str, Any]) -> bool:
    """Verify that every recorded file still has its recorded size and hash."""
    verify_fingerprint(fingerprint)
    files = fingerprint["files"]
    for name, entry in files.items():
        if not isinstance(entry, Mapping):
            raise ValueError(f"Invalid fingerprint entry: {name}")
        path = Path(entry.get("path", ""))
        if not path.is_file():
            raise FileNotFoundError(f"Fingerprint source missing: {name}: {path}")
        if path.stat().st_size != entry.get("size_bytes"):
            raise ValueError(f"Fingerprint size mismatch: {name}")
        if sha256_file(path) != entry.get("sha256"):
            raise ValueError(f"Fingerprint SHA-256 mismatch: {name}")
    return True


def ensure_no_overwrite(paths: Iterable[Path]) -> list[Path]:
    """Resolve and preflight output paths without creating or changing them."""
    resolved: list[Path] = []
    seen: set[str] = set()
    for raw_path in paths:
        path = Path(raw_path).resolve()
        key = str(path).casefold()
        if key in seen:
            raise ValueError(f"Duplicate output path: {path}")
        seen.add(key)
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite existing artifact: {path}")
        resolved.append(path)
    if not resolved:
        raise ValueError("At least one output path is required")
    return resolved


def _write_temp_for_target(target: Path, content: bytes) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, raw_temp = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=str(target.parent))
    temp_path = Path(raw_temp)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise
    return temp_path


def publish_bytes_no_overwrite(target: Path, content: bytes) -> Path:
    """Atomically publish one file without replacing an existing path."""
    if not isinstance(content, bytes):
        raise TypeError("content must be bytes")
    destination = Path(target).resolve()
    ensure_no_overwrite([destination])
    temp_path = _write_temp_for_target(destination, content)
    try:
        # A same-filesystem hard link is atomic and fails if destination exists.
        os.link(temp_path, destination)
    finally:
        temp_path.unlink(missing_ok=True)
    return destination


def publish_json_no_overwrite(target: Path, value: Any) -> Path:
    return publish_bytes_no_overwrite(target, canonical_json_bytes(value))


def publish_pair_no_overwrite(first_path: Path, first_content: bytes,
                              second_path: Path, second_content: bytes) -> tuple[Path, Path]:
    """Publish two files; roll back the first if publishing the second fails."""
    first = Path(first_path).resolve()
    second = Path(second_path).resolve()
    ensure_no_overwrite([first, second])
    first_temp = _write_temp_for_target(first, first_content)
    second_temp: Path | None = None
    first_published = False
    try:
        second_temp = _write_temp_for_target(second, second_content)
        os.link(first_temp, first)
        first_published = True
        os.link(second_temp, second)
    except Exception:
        if first_published and first.exists():
            expected = hashlib.sha256(first_content).hexdigest()
            if sha256_file(first) == expected:
                first.unlink()
        raise
    finally:
        first_temp.unlink(missing_ok=True)
        if second_temp is not None:
            second_temp.unlink(missing_ok=True)
    return first, second


def publish_manifest_no_overwrite(target: Path, manifest: Mapping[str, Any],
                                   input_paths: Mapping[str, Path]) -> Path:
    """Attach a reproducible input fingerprint and publish a run manifest."""
    if not isinstance(manifest, Mapping):
        raise TypeError("manifest must be a mapping")
    payload = dict(manifest)
    if "input_fingerprint" in payload:
        raise ValueError("manifest must not supply input_fingerprint directly")
    payload["input_fingerprint"] = fingerprint_files(input_paths)
    return publish_json_no_overwrite(target, payload)
