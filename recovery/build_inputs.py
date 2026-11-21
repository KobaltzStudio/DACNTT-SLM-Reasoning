"""Create immutable runtime and candidate source copies from verified inputs."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import shutil
import stat

ROOT = Path(__file__).resolve().parents[1]
MANUAL = Path("P2/experiments/week2September/manual")
INDICES = {
    "SHA256SUMS.txt": "bf0c50c301de9e2b78d9533a6a995733a431a6834d8ad019926e1c826af07798",
    "RUNPOD_PACKAGE_MANIFEST.json": "dbe0d5bb0b2b80df5d0b4f41ff57b3318a543c264e2d5b20c5c7f818e0424f62",
}
PRIVATE_PATTERN = re.compile(
    r"(?i)(?:[A-Z]:[\\/]+Users[\\/]|/(?:home|Users)/[A-Za-z0-9_.-]+|"
    r"(?:ghp_|github_pat_|hf_|sk-)[A-Za-z0-9_-]{20,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----)")


def read(p):
    return json.loads(p.read_text(encoding="utf-8-sig"))


def sha(p):
    with p.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def safe(path):
    return (path.is_file() and not path.is_symlink()
            and not getattr(path.lstat(), "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sealed", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--prior-analysis", type=Path, required=True)
    args = parser.parse_args()
    sealed, audit, prior = (p.resolve(strict=True) for p in (args.sealed, args.audit, args.prior_analysis))
    for area in ("runtime", "github", "analysis"):
        if (ROOT / area).exists():
            raise FileExistsError(f"Refusing an existing destination: {area}")
    for filename, pin in INDICES.items():
        assert sha(sealed / "manifests" / filename) == pin
    package = read(sealed / "manifests/RUNPOD_PACKAGE_MANIFEST.json")
    assert sha(sealed / "manifests/RUNPOD_SHA256.csv") == package["csv_manifest_sha256"]
    all_rows = [{"path": r["path"], "sha256": r["sha256"], "bytes": r["bytes"]} for r in package["entries"]]
    for filename in (*INDICES, "RUNPOD_SHA256.csv"):
        p = sealed / "manifests" / filename
        all_rows.append({"path": f"manifests/{filename}", "sha256": sha(p), "bytes": p.stat().st_size})
    assert len({r["path"].casefold() for r in all_rows}) == len(all_rows) == 658
    assert sum(r["bytes"] for r in all_rows) == 575403394
    manifest_folder = ROOT / "manifests"
    manifest_folder.mkdir(exist_ok=True)
    provenance = {}

    def copy(source, name, expected, role, origin="P2 sealed release"):
        dest = ROOT / name
        assert not Path(name).is_absolute() and ".." not in Path(name).parts
        assert safe(source) and sha(source) == expected, source
        dest.parent.mkdir(parents=True, exist_ok=True)
        with source.open("rb") as a, dest.open("xb") as b:
            shutil.copyfileobj(a, b)
        assert sha(dest) == expected and dest.stat().st_size == source.stat().st_size, dest
        provenance[name] = {"source_path": str(source), "sha256": expected, "role": role, "origin": origin}

    graph = read(audit / "integrity_observation.json")["ast_runtime_graph"]
    closure = {f"{MANUAL.as_posix()}/scripts/{name}.py" for name in graph}
    for row in all_rows:
        name = row["path"]
        role = ("ACTIVE_SOURCE_CLOSURE" if name in closure else "SEALED_HISTORICAL_SOURCE" if "/scripts/" in name
                and name.endswith(".py") else "SEALED_TEST" if "/tests/" in name else "SEALED_RUNTIME_INPUT")
        origin = "Proposal 1 historical G4, preserved in P2 release" if "G4_CHECKPOINT_AUDIT" in name else "P1/P2 sealed P2 tree"
        copy(sealed / name, "runtime/" + name, row["sha256"], role, origin)

    public_candidates = closure | {"P2/requirements-lock.txt", "P2/requirements.txt"}
    public_candidates |= {p.relative_to(sealed).as_posix() for p in (sealed / MANUAL / "tests").glob("test_*.py")}
    excluded = []
    github = ROOT / "github"
    github.mkdir()
    by_path = {r["path"]: r for r in all_rows}
    for name in sorted(public_candidates):
        p = sealed / name
        contents = p.read_text(encoding="utf-8-sig")
        if PRIVATE_PATTERN.search(contents):
            excluded.append({"path": name, "reason": "machine-specific path or credential-like content"})
            continue
        copy(p, "github/" + name, by_path[name]["sha256"], "PUBLIC_SOURCE_CANDIDATE")

    observation = read(audit / "integrity_observation.json")
    for filename in ("MODEL_CACHE_TRANSFER_MANIFEST.csv", "MODEL_CACHE_SHA256SUMS.txt"):
        p = audit / filename
        copy(p, f"manifests/{filename}", sha(p), "STUDENT_CACHE_TRANSFER_METADATA", "Windows verified HF cache")
    offline = audit / "MODEL_CACHE_SHA256SUMS.txt"
    assert sha(offline) == observation["cache_sumfile_sha256"]
    assert len(observation["cache_files"]) == 7
    copy(offline, "github/manifests/MODEL_CACHE_SHA256SUMS.txt", sha(offline),
         "PUBLIC_CHECKSUM_CANDIDATE", "Pinned Student cache bytes")

    charts = read(prior / "g8/figure_manifest.json")
    assert len(charts["figures"]) == 7
    for item in charts["figures"].values():
        assert item["partial"]
        for filename, checksum in item["outputs"].items():
            copy(prior/"g8"/filename, f"analysis/g8/{filename}", checksum,
                 "PARTIAL_VERIFIED_FIGURE_OR_CSV", "P1/P2 seed13 existing observations")
    p = prior/"g8/figure_manifest.json"
    copy(p, "analysis/g8/figure_manifest.json", sha(p), "PARTIAL_FIGURE_PROVENANCE", "P1/P2 seed13")
    for group in ("g6", "g7"):
        for p in sorted((prior / group).iterdir()):
            if p.suffix.lower() in {".csv", ".json", ".md"}:
                copy(p, f"analysis/{group}/{p.name}", sha(p), "PARTIAL_ANALYSIS", "P1/P2 seed13")
    public_inputs = github / "manifests/runtime_payload.csv"
    with public_inputs.open("x", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["path", "sha256", "bytes"])
        w.writeheader()
        w.writerows(sorted(all_rows, key=lambda x:x["path"]))
    with (manifest_folder / "copied_inputs.json").open("x", encoding="utf-8") as f:
        json.dump({"files": provenance, "graph": graph, "candidate_source_exclusions": excluded,
                   "student_snapshot_bytes": observation["cache_bytes"],
                   "sealed_files": len(all_rows)}, f, indent=2, ensure_ascii=False)
    print(f"Copied {len(all_rows)} immutable runtime files; {len(graph)} active graph modules; "
          f"{len(public_candidates)-len(excluded)} candidate source/test/lock files; {len(excluded)} visibility exclusions")


if __name__ == "__main__":
    main()
