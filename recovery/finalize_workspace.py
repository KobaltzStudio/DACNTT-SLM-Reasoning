"""Inventory the handoff, then seal the immutable workspace independently of recovery files."""
import argparse
import ast
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re
import stat

ROOT = Path(__file__).resolve().parents[1]
MANUAL = "P2/experiments/week2September/manual"
RECOVERY = {f"recovery/{n}" for n in ("CURRENT_STATE.md", "CURRENT_STATE.json", "TASK_CHECKLIST.md",
                                      "COMMAND_HISTORY.md", "RECOVERY_GUIDE.md")}
SUMS_NAME = "manifests/SHA256SUMS.txt"


def sha(p):
    with p.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def read_json(p):
    return json.loads(p.read_text(encoding="utf-8-sig"))


def files():
    tree = {}
    seen = set()
    for p in ROOT.rglob("*"):
        r = p.relative_to(ROOT).as_posix()
        if (p.is_symlink() or getattr(p.lstat(), "st_file_attributes", 0) & getattr(stat,"FILE_ATTRIBUTE_REPARSE_POINT",0)
                or r.casefold() in seen):
            raise ValueError(f"Unsafe or case-colliding path: {r}")
        seen.add(r.casefold())
        if p.is_file():
            tree[r] = p
    return dict(sorted(tree.items()))


def write_csv(name, rows):
    with (ROOT / "manifests" / name).open("x", encoding="utf8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def scientific_role(name, inherited):
    if name.startswith("runtime/"):
        if "/splits/" in name: return "frozen_split"
        if "/config/" in name: return "frozen_config"
        if "/data/" in name or "/trajectory/pool/" in name: return "frozen_input_pool_or_gold"
        if "adapter_model.safetensors" in name: return "adapter_weights"
        if "/models/" in name or "extracted_checkpoints" in name: return "checkpoint_support"
        if "eval_dev.jsonl" in name or ("prediction" in name and name.endswith(".jsonl")): return "D_dev_prediction"
        if "nll" in name.lower() and not name.endswith(".py"): return "checkpoint_NLL_or_metadata"
        if "/tests/" in name: return "sealed_test"
        if name.endswith(".py"): return inherited["role"]
        return "sealed_provenance_or_runtime"
    if name.startswith("analysis/g8/"):
        return "observed_figure" if name.endswith(".png") else "observed_figure_data"
    if name.startswith("analysis/"): return "partial_internal_analysis"
    if name.startswith("github/"): return "publication_candidate"
    if name.startswith("deployment/"): return "bounded_operator_tool"
    return inherited.get("role", "handoff_evidence_or_documentation")


def inventory():
    copied = read_json(ROOT/"manifests/copied_inputs.json")
    public = read_json(ROOT/"manifests/github_candidate_audit.json")
    for rel, digest in public["files"].items():
        assert sha(ROOT/"github"/rel) == digest, rel
    candidates = {p for p in files() if p.startswith("github/")}
    assert candidates == {"github/"+p for p in public["files"]}
    graph = copied["graph"]
    scripts = ROOT/"runtime"/MANUAL/"scripts"
    for module, deps in graph.items():
        ast.parse((scripts/(module+".py")).read_bytes())
        assert all((scripts/(name+".py")).is_file() for name in deps), module
    assert len(graph) == 22
    listing = {r for r in files() if r.startswith(("runtime/","deployment/","future_research/"))}
    listing.update({"docs/HANDOFF_FOR_RUNPOD_OPERATOR.md","docs/SCIENTIFIC_PROTOCOL.md","docs/REMAINING_WORK.md",
                    "manifests/MODEL_CACHE_SHA256SUMS.txt","manifests/runpod_files.txt"})
    with (ROOT/"manifests/runpod_files.txt").open("x",encoding="utf8",newline="\n") as f:
        f.writelines(p+"\n" for p in sorted(listing))
    rows = []
    all_files=files()
    for name, p in all_files.items():
        if name in RECOVERY: continue
        inherit = copied["files"].get(name,{})
        src = inherit.get("source_path", public["copied_deployment"].get(name, "AUTHORED_IN_HANDOFF"))
        current = sha(p)
        if src!="AUTHORED_IN_HANDOFF":
            assert sha(Path(src)) == current and (not inherit or inherit["sha256"] == current), name
        rows.append({"source_path":src,"destination_path":name,"file_type":p.suffix or p.name,
                     "bytes":p.stat().st_size,"sha256":current,
                     "origin":inherit.get("origin","P1/P2 unified handoff"),
                     "scientific_role":scientific_role(name, inherit),
                     "github_eligibility":"CANDIDATE_RIGHTS_PENDING" if name in candidates else "KEPT_PRIVATE",
                     "runpod_requirement":"TRANSFER_ALLOWLIST" if name in listing else "LOCAL_ONLY",
                     "provenance_status":"BYTE_MATCH" if src!="AUTHORED_IN_HANDOFF" else "AUTHORED_OR_GENERATED"})
    with (ROOT/"manifests/MODEL_CACHE_TRANSFER_MANIFEST.csv").open(encoding="utf-8-sig",newline="") as f:
        cache = list(csv.DictReader(f))
    cache_rows = [{"source_path":r["windows_source"],"destination_path":"HF_HUB_CACHE/"+r["linux_hub_relative"],
                   "file_type":"external_cache","bytes":int(r["bytes"]),"sha256":r["sha256"],
                   "origin":r["model"]+"@"+r["revision"],"scientific_role":"pinned_offline_Student",
                   "github_eligibility":"KEPT_PRIVATE","runpod_requirement":"SEPARATE_TRANSFER",
                   "provenance_status":"EXTERNAL_SHA_VERIFIED"} for r in cache]
    write_csv("source_inventory.csv", [r for r in rows if r["file_type"] in {".py",".sh"}])
    write_csv("artifact_inventory.csv", [r for r in rows if r["file_type"] not in {".py",".sh"}] + cache_rows)
    write_csv("github_inclusion_manifest.csv", rows + cache_rows)
    write_csv("runpod_inclusion_manifest.csv", [r for r in rows if r["destination_path"] in listing]+cache_rows)
    write_csv("source_to_handoff_mapping.csv", [r for r in rows if r["provenance_status"]=="BYTE_MATCH"])
    runtime = [r for r in rows if r["destination_path"].startswith("runtime/")]
    fig=[p for r,p in all_files.items() if r.startswith("analysis/g8/") and p.suffix==".png"]
    stats={"runtime_files":len(runtime),"runtime_bytes":sum(r["bytes"] for r in runtime),
           "runtime_roles":dict(Counter(r["scientific_role"] for r in runtime)),
           "active_source_closure":len(graph),"source_rows": sum(r["file_type"] in {".py",".sh"} for r in rows),
           "github_candidates":len(candidates),"github_rights_approved":0,
           "git_adapters_or_data_files":0,"runpod_transfer_files":len(listing),"cache_external_files":len(cache),
           "cache_external_bytes":sum(r["bytes"] for r in cache_rows),"internal_figures":len(fig),
           "analysis_files":sum(p.startswith("analysis/") for p in all_files),
           "copied_byte_matches":sum(r["provenance_status"]=="BYTE_MATCH" for r in rows),
           "observed_workspace_size_before_seal":sum(p.stat().st_size for p in all_files.values())}
    with (ROOT/"manifests/inventory_counts.json").open("x",encoding="utf8") as f:
        json.dump(stats,f,indent=2)
    print(json.dumps(stats))


def seal():
    tree = files()
    assert SUMS_NAME not in tree
    with (ROOT / SUMS_NAME).open("x", encoding="utf8", newline="\n") as f:
        for name, p in tree.items():
            if name not in RECOVERY:
                f.write(f"{sha(p)}  {name}\n")


def verify():
    tree = files()
    pairs = {}
    for line in (ROOT/SUMS_NAME).read_text(encoding="utf8").splitlines():
        digest, name = line.split("  ", 1)
        assert name not in pairs and re.fullmatch("[a-f0-9]{64}",digest), name
        pairs[name] = digest
    assert set(pairs)==set(tree)-RECOVERY-{SUMS_NAME}
    for name, digest in pairs.items():
        assert sha(tree[name])==digest,name
    print(f"Workspace SHA PASS: {len(pairs)} immutable entries; {len(tree)} files; "
          f"{sum(p.stat().st_size for p in tree.values())} bytes; SHA256SUMS sha {sha(tree[SUMS_NAME])}")


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("inventory","seal","verify"))
    {"inventory":inventory,"seal":seal,"verify":verify}[p.parse_args().action]()
