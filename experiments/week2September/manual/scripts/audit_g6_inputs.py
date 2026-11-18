#!/usr/bin/env python3
"""Read-only audit of verified G5.9 sidecars and G6 input schemas."""
from __future__ import annotations

import ast
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(r"C:\Users\PC - NGHI\Desktop\Pipeline\P2\experiments\week2September\manual")
RECON_DIR = ROOT / "reports/p1p2_integration/historical_g59_reconciliation/run_20261117_1712"
RECON_JSON = RECON_DIR / "historical_g59_reconciliation.json"
CAPABILITY_ROOT = ROOT / "reports/capability"
STATE_SCRIPT = ROOT / "scripts/p1p2_capability_state.py"
OUT_DIR = ROOT / "reports/p1p2_integration/g6_input_audit/run_20261117_1730"

EXPECTED_CAPABILITIES = {
    "addition", "subtraction", "multiplication", "division",
    "percentage", "fraction", "ratio",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return obj


def inspect_csv(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        return {
            "path": str(path),
            "sha256": sha256(path),
            "size_bytes": path.stat().st_size,
            "columns": reader.fieldnames or [],
            "row_count": len(rows),
            "sample_rows": rows[:3],
        }


def main() -> int:
    errors: list[str] = []
    report: dict[str, Any] = {
        "schema": "p1p2.g6_input_audit.v1",
        "root": str(ROOT),
        "reconciliation": {},
        "sidecars": [],
        "s0_candidates": [],
        "capability_csv_schemas": [],
        "state_api": {},
        "errors": errors,
    }

    if not RECON_JSON.is_file():
        raise FileNotFoundError(f"Reconciliation JSON missing: {RECON_JSON}")
    recon = load_json(RECON_JSON)
    report["reconciliation"] = {
        "status": recon.get("status"),
        "expected_contexts": recon.get("expected_contexts"),
        "reconciled_contexts": recon.get("reconciled_contexts"),
        "passed_or_recovered_contexts": recon.get("passed_or_recovered_contexts"),
        "failed_contexts": recon.get("failed_contexts"),
        "sha256": sha256(RECON_JSON),
    }
    if recon.get("status") != "PASS":
        errors.append("G5.9 reconciliation status is not PASS")

    manifests = sorted(CAPABILITY_ROOT.rglob("student_capability_evaluation_manifest.json"))
    if not manifests:
        errors.append("No capability sidecar manifests found")

    seen_contexts: set[str] = set()
    csv_by_schema: dict[str, dict[str, Any]] = {}

    for manifest_path in manifests:
        try:
            sidecar = load_json(manifest_path)
        except Exception as exc:
            errors.append(f"Invalid sidecar JSON {manifest_path}: {exc}")
            continue

        run_id = str(sidecar.get("run_id", ""))
        method = sidecar.get("method")
        seed = sidecar.get("seed")
        round_no = sidecar.get("round")
        if run_id in seen_contexts:
            errors.append(f"Duplicate sidecar run_id discovered: {run_id}")
        seen_contexts.add(run_id)

        capability_rows = sidecar.get("capabilities", [])
        cap_names = []
        for row in capability_rows:
            if isinstance(row, dict):
                cap_names.append(row.get("capability") or row.get("name") or row.get("capability_name"))
        cap_names = [str(x) for x in cap_names if x is not None]

        outputs = sidecar.get("outputs", {})
        csv_info = None
        if isinstance(outputs, dict) and "capability_metrics.csv" in outputs:
            csv_path = manifest_path.parent / "capability_metrics.csv"
            if csv_path.is_file():
                csv_info = inspect_csv(csv_path)
                schema_key = "|".join(csv_info["columns"])
                csv_by_schema.setdefault(schema_key, csv_info)
            else:
                errors.append(f"Capability CSV declared but missing: {csv_path}")

        is_s0 = (
            round_no == 0
            or str(sidecar.get("checkpoint", "")).upper() == "S0"
            or str(method).upper() == "SHARED"
            or "S0" in run_id.upper()
        )
        if is_s0:
            report["s0_candidates"].append({
                "run_id": run_id,
                "method": method,
                "seed": seed,
                "round": round_no,
                "checkpoint": sidecar.get("checkpoint"),
                "manifest": str(manifest_path),
                "manifest_sha256": sha256(manifest_path),
                "input_hashes": sidecar.get("input_hashes"),
                "csv": csv_info,
            })

        report["sidecars"].append({
            "run_id": run_id,
            "method": method,
            "seed": seed,
            "round": round_no,
            "checkpoint": sidecar.get("checkpoint"),
            "gold_policy": sidecar.get("gold_policy"),
            "strict_metric": sidecar.get("strict_metric"),
            "schema_version": sidecar.get("schema_version"),
            "capability_count": len(capability_rows),
            "capability_names": cap_names,
            "capability_names_match_taxonomy": set(cap_names) == EXPECTED_CAPABILITIES if cap_names else None,
            "manifest": str(manifest_path),
            "manifest_sha256": sha256(manifest_path),
            "csv": csv_info,
        })

    report["capability_csv_schemas"] = list(csv_by_schema.values())

    if STATE_SCRIPT.is_file():
        source = STATE_SCRIPT.read_text(encoding="utf-8-sig")
        tree = ast.parse(source, filename=str(STATE_SCRIPT))
        functions = []
        classes = []
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append({
                    "name": node.name,
                    "args": [arg.arg for arg in node.args.args],
                    "lineno": node.lineno,
                })
            elif isinstance(node, ast.ClassDef):
                classes.append({"name": node.name, "lineno": node.lineno})
        report["state_api"] = {
            "path": str(STATE_SCRIPT),
            "sha256": sha256(STATE_SCRIPT),
            "functions": functions,
            "classes": classes,
        }
    else:
        errors.append(f"Capability state script missing: {STATE_SCRIPT}")

    # Sidecar inventory in this audit may include S0 and unrelated capability runs.
    report["sidecar_manifest_count_under_capability_root"] = len(manifests)
    report["unique_run_id_count"] = len(seen_contexts)
    report["s0_candidate_count"] = len(report["s0_candidates"])

    OUT_DIR.mkdir(parents=True, exist_ok=False)
    json_path = OUT_DIR / "g6_input_audit.json"
    md_path = OUT_DIR / "g6_input_audit.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# G6 Input Audit",
        "",
        f"- G5.9 reconciliation: {report['reconciliation'].get('status')}",
        f"- Sidecar manifests under capability root: {len(manifests)}",
        f"- Unique run IDs: {len(seen_contexts)}",
        f"- S0 candidates: {len(report['s0_candidates'])}",
        "",
        "## S0 candidates",
        "",
    ]
    for item in report["s0_candidates"]:
        lines.append(
            f"- `{item['run_id']}` method={item['method']} seed={item['seed']} "
            f"round={item['round']} checkpoint={item['checkpoint']} "
            f"manifest=`{item['manifest']}`"
        )
    lines.extend(["", "## Capability CSV schemas", ""])
    for info in report["capability_csv_schemas"]:
        lines.append(f"- `{info['path']}`")
        lines.append(f"  - rows={info['row_count']}; columns={info['columns']}")
        lines.append(f"  - sha256={info['sha256']}")
    lines.extend(["", "## State API", ""])
    for fn in report["state_api"].get("functions", []):
        lines.append(f"- `{fn['name']}({', '.join(fn['args'])})` at line {fn['lineno']}")
    for cls in report["state_api"].get("classes", []):
        lines.append(f"- class `{cls['name']}` at line {cls['lineno']}")
    lines.extend(["", "## Errors", ""])
    lines.extend([f"- {e}" for e in errors] if errors else ["- None"])
    lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")

    print("G6_INPUT_AUDIT=COMPLETE" if not errors else "G6_INPUT_AUDIT=ISSUES_FOUND")
    print("G59_RECONCILIATION_STATUS:", recon.get("status"))
    print("SIDECAR_MANIFEST_COUNT:", len(manifests))
    print("UNIQUE_RUN_ID_COUNT:", len(seen_contexts))
    print("S0_CANDIDATE_COUNT:", len(report["s0_candidates"]))
    print("CAPABILITY_CSV_SCHEMA_COUNT:", len(report["capability_csv_schemas"]))
    for info in report["capability_csv_schemas"]:
        print("CSV:", info["path"])
        print("CSV_COLUMNS:", json.dumps(info["columns"], ensure_ascii=False))
        print("CSV_ROW_COUNT:", info["row_count"])
        print("CSV_SAMPLE_ROWS:", json.dumps(info["sample_rows"], ensure_ascii=False))
    print("STATE_FUNCTIONS:", json.dumps(report["state_api"].get("functions", []), ensure_ascii=False))
    print("REPORT_DIR:", OUT_DIR)
    print("JSON:", json_path)
    print("MARKDOWN:", md_path)
    for error in errors:
        print("ERROR:", error)
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
