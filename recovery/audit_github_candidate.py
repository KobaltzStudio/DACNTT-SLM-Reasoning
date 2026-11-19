"""Create and audit only the independent publication candidate, without Git mutations."""
import json
from pathlib import Path
import re
import shutil
import stat

from build_inputs import PRIVATE_PATTERN, sha

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "github"
LINK = re.compile(r"\[[^\]\n]+\]\(([^ )]+)\)")

def main():
    target = CANDIDATE / "deployment"
    target.mkdir(exist_ok=False)
    copies = {}
    for path in sorted((ROOT/"deployment").iterdir()):
        if path.suffix in {".py", ".sh"}:
            out = target / path.name
            with path.open("rb") as a, out.open("xb") as b:
                shutil.copyfileobj(a,b)
            if sha(out) != sha(path):
                raise ValueError(f"Tool copy differs: {out}")
            copies[out.relative_to(ROOT).as_posix()] = str(path)
    all_paths = sorted(p.relative_to(CANDIDATE).as_posix() for p in CANDIDATE.rglob("*") if p.is_file())
    list_file = CANDIDATE / "manifests/public_files.txt"
    all_paths.append(list_file.relative_to(CANDIDATE).as_posix())
    with list_file.open("x", encoding="utf8", newline="\n") as f:
        f.writelines(name + "\n" for name in sorted(all_paths))
    forbidden_dirs = {".git", "data", "splits", "runs", "models", "reports", "runtime", "analysis",
                      "artifacts", "__pycache__", "recovery", ".cache"}
    suffixes = {".py",".sh",".md",".txt",".csv"}
    filenames = {".gitignore", ".gitattributes"}
    sha_paths = {}
    for name in all_paths:
        p = CANDIDATE / name
        if (p.is_symlink() or getattr(p.lstat(), "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
                or any(x in forbidden_dirs or x.startswith(".env") for x in Path(name).parts)
                or p.suffix.lower() not in suffixes and p.name not in filenames):
            raise ValueError(f"Disallowed public candidate path: {name}")
        if p.stat().st_size >= 1024*1024:
            raise ValueError(f"Candidate too large: {name}")
        data = p.read_text(encoding="utf-8-sig")
        if PRIVATE_PATTERN.search(data) or re.search(
                r"""(?im)^\s*(?:api_key|password|secret|access_token)\s*=\s*["'][A-Za-z0-9_-]{22,}["']""", data):
            raise ValueError(f"Machine-specific path or potential secret: {name}")
        if p.suffix == ".md":
            for link in LINK.findall(data):
                target_path = link.split("#",1)[0]
                if target_path and not link.startswith(("https://","http://","mailto:")):
                    target_path = (p.parent / target_path).resolve()
                    if not target_path.is_relative_to(CANDIDATE) or not target_path.exists():
                        raise ValueError(f"Broken relative link in {name}")
        sha_paths[name] = sha(p)
    output = {"technical_candidate_audit": "PASS",
              "publication": "BLOCKED_RIGHTS_APPROVAL_REQUIRED", "count": len(sha_paths),
              "files": sha_paths, "copied_deployment": copies,
              "licensing": "No repository-level redistribution grant found; owner and third-party review pending"}
    with (ROOT / "manifests/github_candidate_audit.json").open("x", encoding="utf8") as f:
        json.dump(output,f,indent=2)
    print(f"{len(sha_paths)} technical candidates passed static inspection; publication BLOCKED pending rights")


if __name__ == "__main__":
    main()
