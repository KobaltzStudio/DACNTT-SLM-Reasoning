#!/usr/bin/env python3
"""Read-only G5.9 historical sidecar reconciliation.

The script never edits historical inputs, batch manifests, or sidecars.
It writes a new JSON/CSV/Markdown reconciliation report directory.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

EXPECTED_SCHEMA = "p1p2.capability-manifest.v1"
EXPECTED_STRICT_METRIC = "status == valid"
EXPECTED_GOLD_POLICY = "approved_85_primary"
EXPECTED_CAPABILITIES = 7
EXPECTED_CONTEXTS = 33
EXPECTED_ALIASES = {
    "B4_seed13_S1": "B5_seed13_S1",
    "B4_seed42_S1": "B5_seed42_S1",
    "B4_seed2026_S1": "B5_seed2026_S1",
}
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def add_check(checks: list[dict[str, str]], scope: str, name: str,
              status: str, detail: str = "") -> None:
    checks.append({
        "scope": scope,
        "check": name,
        "status": status,
        "detail": detail,
    })


def resolve_manifest_sidecar(root: Path, raw_path: str) -> Path:
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = root / candidate
    return candidate.resolve()


def expected_input_paths(root: Path, input_root: Path, run_id: str) -> dict[str, Path]:
    lineage = input_root / "lineage" / run_id
    return {
        "approval_csv": root / "data/gold_releases/vFinal_2026-11-16/gold_supplement_85_approved_review.csv",
        "checkpoint": input_root / "checkpoint_references" / f"{run_id}.json",
        "checkpoint_log": lineage / "checkpoint_log.jsonl",
        "config": root / "config/experiment_config.json",
        "dev_ids": root / "splits/d_dev_ids.txt",
        "dev_predictions": input_root / "predictions" / f"{run_id}.jsonl",
        "gold_labels": root / "data/gold_vfinal/supplement_annotations_vfinal.jsonl",
        "gold_manifest": root / "data/gold_vfinal/gold_vfinal_manifest.json",
        "selection_log": lineage / "selection_log.jsonl",
        "train_log": lineage / "train_log.json",
        "train_set": lineage / "train_set.json",
    }


def reconcile(args: argparse.Namespace) -> tuple[dict[str, Any], list[dict[str, str]]]:
    root = args.root.resolve()
    batch_path = args.batch_manifest.resolve()
    sidecar_root = args.sidecar_root.resolve()
    input_root = args.input_root.resolve()
    out_dir = args.out_dir.resolve()

    if not root.is_dir():
        raise FileNotFoundError(f"Project root missing: {root}")
    if not batch_path.is_file():
        raise FileNotFoundError(f"Batch manifest missing: {batch_path}")
    if not sidecar_root.is_dir():
        raise FileNotFoundError(f"Sidecar root missing: {sidecar_root}")
    if not input_root.is_dir():
        raise FileNotFoundError(f"Historical input root missing: {input_root}")
    if out_dir.exists():
        raise FileExistsError(f"Refusing to overwrite reconciliation output: {out_dir}")

    batch = load_json(batch_path)
    checks: list[dict[str, str]] = []
    context_rows: list[dict[str, Any]] = []
    errors: list[str] = []

    results = batch.get("results")
    aliases = batch.get("aliases")
    if not isinstance(results, list):
        raise ValueError("Batch manifest 'results' must be a list")
    if not isinstance(aliases, list):
        raise ValueError("Batch manifest 'aliases' must be a list")

    add_check(checks, "batch", "schema", "PASS" if batch.get("schema") == "p1p2.historical_g59_batch.v2" else "FAIL",
              str(batch.get("schema")))
    add_check(checks, "batch", "expected_context_count",
              "PASS" if len(results) == EXPECTED_CONTEXTS else "FAIL",
              f"observed={len(results)} expected={EXPECTED_CONTEXTS}")
    add_check(checks, "batch", "expected_alias_count",
              "PASS" if len(aliases) == len(EXPECTED_ALIASES) else "FAIL",
              f"observed={len(aliases)} expected={len(EXPECTED_ALIASES)}")

    result_by_id: dict[str, dict[str, Any]] = {}
    for item in results:
        if not isinstance(item, dict) or not item.get("run_id"):
            errors.append("Malformed batch result entry")
            continue
        run_id = str(item["run_id"])
        if run_id in result_by_id:
            errors.append(f"Duplicate batch run_id: {run_id}")
        result_by_id[run_id] = item

    if len(result_by_id) != EXPECTED_CONTEXTS:
        errors.append(f"Unique batch contexts={len(result_by_id)}, expected={EXPECTED_CONTEXTS}")

    alias_map: dict[str, str] = {}
    for item in aliases:
        if not isinstance(item, dict):
            errors.append("Malformed alias entry")
            continue
        alias_id = str(item.get("alias_run_id", ""))
        canonical_id = str(item.get("canonical_run_id", ""))
        alias_map[alias_id] = canonical_id
        expected_canonical = EXPECTED_ALIASES.get(alias_id)
        alias_ok = (
            expected_canonical == canonical_id
            and item.get("status") == "EXACT_ALIAS_CONFIRMED"
            and canonical_id in result_by_id
            and alias_id not in result_by_id
        )
        canonical = result_by_id.get(canonical_id, {})
        alias_ok = alias_ok and item.get("prediction_sha256") == canonical.get("prediction_sha256")
        alias_ok = alias_ok and item.get("train_log_sha256") == _input_hash_from_sidecar(
            sidecar_root, canonical_id, "train_log"
        )
        add_check(checks, "alias", alias_id, "PASS" if alias_ok else "FAIL",
                  f"canonical={canonical_id}; status={item.get('status')}")
        if not alias_ok:
            errors.append(f"Alias verification failed: {alias_id}")

    if alias_map != EXPECTED_ALIASES:
        errors.append("Alias mapping differs from the frozen expected B4/B5 S1 mapping")

    recovered_ids = set(args.recovered_run_id or [])
    if recovered_ids != {"B4_seed42_S3"}:
        errors.append(
            "For this batch, explicitly attest exactly --recovered-run-id B4_seed42_S3 "
            "because the old batch record is HOOK_FAILED but a successful retry was reported."
        )

    for run_id in sorted(result_by_id):
        item = result_by_id[run_id]
        sidecar_path = resolve_manifest_sidecar(root, str(item.get("sidecar_path", "")))
        manifest_path = sidecar_path / "student_capability_evaluation_manifest.json"
        row_errors: list[str] = []

        if not manifest_path.is_file():
            row_errors.append("sidecar manifest missing")
            sidecar = {}
        else:
            try:
                sidecar = load_json(manifest_path)
            except Exception as exc:
                row_errors.append(f"sidecar manifest invalid JSON: {exc}")
                sidecar = {}

        expected_identity = {
            "run_id": run_id,
            "method": item.get("method"),
            "seed": item.get("seed"),
            "round": item.get("round"),
        }
        for field, expected in expected_identity.items():
            if sidecar.get(field) != expected:
                row_errors.append(f"{field} mismatch: sidecar={sidecar.get(field)!r}, batch={expected!r}")

        if sidecar.get("schema_version") != EXPECTED_SCHEMA:
            row_errors.append(f"schema_version mismatch: {sidecar.get('schema_version')!r}")
        if sidecar.get("strict_metric") != EXPECTED_STRICT_METRIC:
            row_errors.append(f"strict_metric mismatch: {sidecar.get('strict_metric')!r}")
        if sidecar.get("gold_policy") != EXPECTED_GOLD_POLICY:
            row_errors.append(f"gold_policy mismatch: {sidecar.get('gold_policy')!r}")
        if len(sidecar.get("capabilities", [])) != EXPECTED_CAPABILITIES:
            row_errors.append(f"capability count mismatch: {len(sidecar.get('capabilities', []))}")

        input_hashes = sidecar.get("input_hashes")
        if not isinstance(input_hashes, dict):
            input_hashes = {}
            row_errors.append("input_hashes missing or invalid")

        if input_hashes.get("dev_predictions") != item.get("prediction_sha256"):
            row_errors.append("dev_predictions hash differs from batch prediction_sha256")
        if input_hashes.get("checkpoint") != item.get("checkpoint_reference_sha256"):
            row_errors.append("checkpoint hash differs from batch checkpoint_reference_sha256")

        expected_paths = expected_input_paths(root, input_root, run_id)
        for key, expected_path in expected_paths.items():
            recorded_hash = input_hashes.get(key)
            if not expected_path.is_file():
                row_errors.append(f"source input missing: {key} => {expected_path}")
                continue
            actual_hash = sha256_file(expected_path)
            if recorded_hash != actual_hash:
                row_errors.append(
                    f"input hash mismatch: {key}; recorded={recorded_hash}; actual={actual_hash}"
                )

        outputs = sidecar.get("outputs")
        if not isinstance(outputs, dict) or not outputs:
            row_errors.append("outputs missing or invalid")
            outputs = {}
        for output_name, metadata in outputs.items():
            output_path = sidecar_path / output_name
            if not output_path.is_file():
                row_errors.append(f"output file missing: {output_name}")
                continue
            if not isinstance(metadata, dict):
                row_errors.append(f"output metadata invalid: {output_name}")
                continue
            actual_hash = sha256_file(output_path)
            actual_size = output_path.stat().st_size
            if metadata.get("sha256") != actual_hash:
                row_errors.append(f"output hash mismatch: {output_name}")
            if metadata.get("size_bytes") != actual_size:
                row_errors.append(f"output size mismatch: {output_name}")

        original_status = str(item.get("status", ""))
        if run_id in recovered_ids and not row_errors:
            effective_status = "RECOVERED_AFTER_BATCH_FAILURE"
        elif original_status == "PASS" and not row_errors:
            effective_status = "PASS"
        else:
            effective_status = "FAIL"

        add_check(checks, "context", run_id, "PASS" if not row_errors else "FAIL",
                  "; ".join(row_errors) if row_errors else effective_status)
        if row_errors:
            errors.extend(f"{run_id}: {problem}" for problem in row_errors)

        context_rows.append({
            "run_id": run_id,
            "method": item.get("method"),
            "seed": item.get("seed"),
            "round": item.get("round"),
            "batch_status": original_status,
            "batch_returncode": item.get("returncode"),
            "reconciliation_status": effective_status,
            "sidecar_manifest_sha256": sha256_file(manifest_path) if manifest_path.is_file() else None,
            "prediction_sha256": item.get("prediction_sha256"),
            "checkpoint_reference_sha256": item.get("checkpoint_reference_sha256"),
            "error_count": len(row_errors),
            "errors": row_errors,
        })

    sidecar_dirs = sorted(p.name for p in sidecar_root.iterdir() if p.is_dir())
    expected_dirs = sorted(str(item.get("run_id")) for item in results if isinstance(item, dict))
    unexpected = sorted(set(sidecar_dirs) - set(expected_dirs))
    missing_dirs = sorted(set(expected_dirs) - set(sidecar_dirs))
    add_check(checks, "inventory", "sidecar_directory_set",
              "PASS" if not unexpected and not missing_dirs else "FAIL",
              f"observed={len(sidecar_dirs)} expected={len(expected_dirs)} "
              f"unexpected={unexpected} missing={missing_dirs}")
    if unexpected or missing_dirs:
        errors.append(f"Sidecar directory mismatch; unexpected={unexpected}, missing={missing_dirs}")

    passed = sum(1 for row in context_rows if row["reconciliation_status"] in ("PASS", "RECOVERED_AFTER_BATCH_FAILURE"))
    failed = len(context_rows) - passed
    overall = "PASS" if not errors and len(context_rows) == EXPECTED_CONTEXTS else "FAIL"

    report = {
        "schema": "p1p2.historical_g59_reconciliation.v1",
        "status": overall,
        "batch_manifest": str(batch_path),
        "batch_manifest_sha256": sha256_file(batch_path),
        "sidecar_root": str(sidecar_root),
        "input_root": str(input_root),
        "expected_contexts": EXPECTED_CONTEXTS,
        "reconciled_contexts": len(context_rows),
        "passed_or_recovered_contexts": passed,
        "failed_contexts": failed,
        "alias_policy": "B4/B5 S1 aliases are represented once by canonical B5 sidecars",
        "aliases": alias_map,
        "recovery_attestation": {
            "run_ids": sorted(recovered_ids),
            "basis": "Operator supplied successful retry CLI output; sidecar and all source/output hashes independently verified.",
            "historical_batch_manifest_modified": False,
        },
        "checks": checks,
        "contexts": context_rows,
        "errors": errors,
    }
    return report, checks


def _input_hash_from_sidecar(sidecar_root: Path, run_id: str, key: str) -> str | None:
    path = sidecar_root / run_id / "student_capability_evaluation_manifest.json"
    if not path.is_file():
        return None
    try:
        return load_json(path).get("input_hashes", {}).get(key)
    except Exception:
        return None


def write_report(report: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=False)
    json_path = out_dir / "historical_g59_reconciliation.json"
    csv_path = out_dir / "historical_g59_contexts.csv"
    md_path = out_dir / "historical_g59_reconciliation.md"

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with csv_path.open("w", newline="", encoding="utf-8-sig") as stream:
        fields = [
            "run_id", "method", "seed", "round", "batch_status",
            "batch_returncode", "reconciliation_status", "sidecar_manifest_sha256",
            "prediction_sha256", "checkpoint_reference_sha256", "error_count", "errors",
        ]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in report["contexts"]:
            row_copy = dict(row)
            row_copy["errors"] = " | ".join(row_copy["errors"])
            writer.writerow(row_copy)

    lines = [
        "# Historical G5.9 Reconciliation",
        "",
        f"- Status: **{report['status']}**",
        f"- Contexts reconciled: {report['reconciled_contexts']}/{report['expected_contexts']}",
        f"- PASS or recovered: {report['passed_or_recovered_contexts']}",
        f"- Failed: {report['failed_contexts']}",
        f"- Batch manifest SHA-256: `{report['batch_manifest_sha256']}`",
        "- Historical batch manifest modified: **No**",
        "- Alias policy: B4/B5 S1 represented once by canonical B5 sidecars.",
        "",
        "## Checks",
        "",
        "| Scope | Check | Status | Detail |",
        "|---|---|---|---|",
    ]
    for check in report["checks"]:
        detail = str(check["detail"]).replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {check['scope']} | {check['check']} | {check['status']} | {detail} |")
    lines.extend(["", "## Errors", ""])
    if report["errors"]:
        lines.extend(f"- {error}" for error in report["errors"])
    else:
        lines.append("No reconciliation errors.")
    lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--batch-manifest", type=Path, required=True)
    parser.add_argument("--sidecar-root", type=Path, required=True)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument(
        "--recovered-run-id", action="append", default=[],
        help="Explicit operator attestation for a context whose old batch record failed but was retried.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report, _ = reconcile(args)
        write_report(report, args.out_dir.resolve())
        print(f"G59_RECONCILIATION={report['status']}")
        print(f"CONTEXTS={report['reconciled_contexts']}/{report['expected_contexts']}")
        print(f"PASS_OR_RECOVERED={report['passed_or_recovered_contexts']}")
        print(f"FAILED={report['failed_contexts']}")
        print(f"REPORT_DIR={args.out_dir.resolve()}")
        print(f"JSON={args.out_dir.resolve() / 'historical_g59_reconciliation.json'}")
        print(f"CSV={args.out_dir.resolve() / 'historical_g59_contexts.csv'}")
        print(f"MARKDOWN={args.out_dir.resolve() / 'historical_g59_reconciliation.md'}")
        return 0 if report["status"] == "PASS" else 2
    except Exception as exc:
        print(f"G59_RECONCILIATION_ERROR={type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
