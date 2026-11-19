"""Resolve archived path locators without rewriting fingerprinted artifacts."""
from pathlib import Path, PureWindowsPath


def legacy_root(value: str) -> PureWindowsPath:
    path = PureWindowsPath(value)
    if (not path.is_absolute() or len(path.drive) != 2 or path.drive[1] != ":"
            or ".." in path.parts or not path.name):
        raise ValueError(f"Expected an absolute Windows manual directory: {value!r}")
    return path


def artifact_path(root: Path, recorded: str, source: PureWindowsPath | None = None) -> Path:
    """Resolve native paths or an explicitly permitted Windows prefix under root."""
    if not isinstance(recorded, str) or not recorded.strip():
        raise ValueError("Missing artifact path")
    root = root.resolve()
    native = Path(recorded)
    windows = PureWindowsPath(recorded)
    if ".." in native.parts or ".." in windows.parts:
        raise ValueError(f"Traversal in artifact path: {recorded}")
    parts = windows.parts[1:] if windows.anchor else windows.parts
    if not parts or any(":" in part or part.endswith((".", " ")) for part in parts):
        raise ValueError(f"Invalid artifact path: {recorded}")
    if native.is_absolute():
        resolved = native.resolve()
        if resolved != root and resolved.is_relative_to(root):
            return resolved
    if windows.drive or windows.root or native.is_absolute():
        if source is None or not windows.is_absolute() or not windows.is_relative_to(source):
            raise ValueError(f"Artifact path does not match the manual root or mapped Windows root: {recorded}")
        tail = windows.relative_to(source).parts
        if not tail:
            raise ValueError(f"Invalid mapped artifact path: {recorded}")
        native = Path(*tail)
    elif "\\" in recorded:
        native = Path(*windows.parts)
    result = (root / native).resolve()
    if result == root or not result.is_relative_to(root):
        raise ValueError(f"Artifact path escapes the manual root: {recorded}")
    return result
