#!/usr/bin/env python3
"""
Proposal 1 - Gold audit for 2026-11-14.

Run from:
experiments/week2September/manual/

Outputs:
  reports/capability/p1_gold_audit_2026-11-14/p1_gold_audit.md
  reports/capability/p1_gold_audit_2026-11-14/gold_review_queue.csv
  reports/capability/p1_gold_audit_2026-11-14/gold_inventory.json

Important:
- The 170-row priority_error_review_annotated.csv is an extractor-error
  review queue, NOT 170 unconfirmed Gold annotations.
- This script is read-only with respect to source annotation/Gold files.
- It never modifies Gold vFinal, vNext, annotations, rules, or split files.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

CAPABILITIES = {
    "addition", "subtraction", "multiplication", "division",
    "percentage", "fraction", "ratio"
}

def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8-sig") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"Invalid JSONL {path}:{line_no}: {exc}") from exc
            if not isinstance(obj, dict):
                raise RuntimeError(f"Expected JSON object at {path}:{line_no}")
            rows.append(obj)
    return rows

def read_ids(path: Path) -> set[str]:
    return {x.strip() for x in path.read_text(encoding="utf-8-sig").splitlines() if x.strip()}

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def norm_id(row: dict[str, Any]) -> str:
    value = row.get("problem_id", row.get("id", ""))
    return str(value).strip() if value is not None else ""

def parse_labels(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x).strip().lower() for x in value if str(x).strip()]
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return []
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(x).strip().lower() for x in parsed if str(x).strip()]
        except json.JSONDecodeError:
            pass
        return [x.strip().lower() for x in value.replace(";", ",").split(",") if x.strip()]
    return []

def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})

def require(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"Required source file not found: {path}")
    return path

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="manual project directory")
    args = parser.parse_args()
    root = Path(args.root).resolve()

    batch_path = require(root / "data/gold_vfinal/batch_100_annotations_vfinal.jsonl")
    supp_path = require(root / "data/gold_vfinal/supplement_annotations_vfinal.jsonl")
    gold_manifest_path = require(root / "data/gold_vfinal/gold_vfinal_manifest.json")
    vnext_manifest_path = require(root / "data/gold_vnext/gold_vnext_manifest.json")
    split_manifest_path = require(root / "splits/split_manifest.json")
    pool_ids_path = require(root / "splits/d_pool_ids.txt")
    dev_ids_path = require(root / "splits/d_dev_ids.txt")
    test_ids_path = require(root / "splits/d_test_ids.txt")
    confirmed_path = require(root / "reports/capability/d3_audit/adjudication_human_confirmed.csv")
    supplement_audit_path = root / "reports/capability/d3_audit/supplement_audit_summary.json"

    # Prefer the annotated queue (contains empty review fields ready for review).
    annotated_queue_path = root / "reports/capability/d3_final_regression/priority_error_review_annotated.csv"
    base_queue_path = root / "reports/capability/d3_final_regression/priority_error_review.csv"
    queue_path = annotated_queue_path if annotated_queue_path.exists() else require(base_queue_path)

    batch = read_jsonl(batch_path)
    supplement = read_jsonl(supp_path)
    gold_manifest = json.loads(gold_manifest_path.read_text(encoding="utf-8-sig"))
    vnext_manifest = json.loads(vnext_manifest_path.read_text(encoding="utf-8-sig"))
    split_manifest = json.loads(split_manifest_path.read_text(encoding="utf-8-sig"))

    pool_ids, dev_ids, test_ids = map(read_ids, [pool_ids_path, dev_ids_path, test_ids_path])
    split_union = pool_ids | dev_ids | test_ids
    split_overlap = {
        "pool_dev": sorted(pool_ids & dev_ids),
        "pool_test": sorted(pool_ids & test_ids),
        "dev_test": sorted(dev_ids & test_ids),
    }

    batch_ids = [norm_id(x) for x in batch]
    supp_ids = [norm_id(x) for x in supplement]
    all_gold_ids = batch_ids + supp_ids
    gold_id_set = set(all_gold_ids)
    batch_set, supp_set = set(batch_ids), set(supp_ids)
    duplicate_batch = sorted(x for x, n in Counter(batch_ids).items() if x and n > 1)
    duplicate_supp = sorted(x for x, n in Counter(supp_ids).items() if x and n > 1)
    duplicate_across = sorted(batch_set & supp_set)
    blank_gold_ids = sum(1 for x in all_gold_ids if not x)

    confirmed_rows = load_csv(confirmed_path)
    supplement_audit = (
        json.loads(supplement_audit_path.read_text(encoding="utf-8-sig"))
        if supplement_audit_path.exists() else {}
    )
    confirmed_ids = {str(x.get("problem_id", "")).strip() for x in confirmed_rows
                     if str(x.get("problem_id", "")).strip()}

    priority_rows = load_csv(queue_path)
    priority_ids = [str(x.get("problem_id", "")).strip() for x in priority_rows]
    duplicate_priority = sorted(x for x, n in Counter(priority_ids).items() if x and n > 1)
    blank_priority = sum(1 for x in priority_ids if not x)
    priority_set = {x for x in priority_ids if x}

    split_membership: dict[str, str] = {}
    for pid in gold_id_set:
        matches = [name for name, ids in (
            ("D_pool", pool_ids), ("D_dev", dev_ids), ("D_test", test_ids)
        ) if pid in ids]
        split_membership[pid] = matches[0] if len(matches) == 1 else (
            "UNKNOWN" if not matches else "SPLIT_OVERLAP"
        )

    # Create a lookup of Gold source and labels.
    gold_lookup: dict[str, dict[str, Any]] = {}
    for source, rows in (("batch_100_vFinal", batch), ("supplement_vFinal", supplement)):
        for row in rows:
            pid = norm_id(row)
            if pid:
                gold_lookup[pid] = row

    queue_out = []
    for row in priority_rows:
        pid = str(row.get("problem_id", "")).strip()
        gold_row = gold_lookup.get(pid, {})
        gold_labels = parse_labels(gold_row.get("capabilities_manual", gold_row.get("capabilities", gold_row.get("final_capabilities", []))))
        fn = parse_labels(row.get("false_negatives", row.get("priority_false_negatives", [])))
        fp = parse_labels(row.get("false_positives", []))
        focus = sorted((set(gold_labels) | set(fn) | set(fp)) & {"fraction", "division", "ratio"})
        semantic_text = " ".join([
            str(row.get("question", "")),
            str(row.get("evidence", "")),
            str(row.get("priority_false_negatives", "")),
            str(row.get("false_negatives", "")),
        ]).lower()
        if not focus:
            focus = [c for c in ("fraction", "division", "ratio") if c in semantic_text]
        if not focus:
            focus = ["other"]

        prior_status = str(row.get("review_status", "") or "").strip().lower()
        if prior_status in {"confirmed", "pending", "excluded", "unresolved"}:
            queue_status = prior_status
        else:
            queue_status = "pending"

        queue_out.append({
            "problem_id": pid,
            "split": split_membership.get(pid, "NOT_IN_SPLIT"),
            "gold_source": (
                "batch_100_vFinal" if pid in batch_set else
                "supplement_vFinal" if pid in supp_set else "NOT_IN_GOLD_VFINAL"
            ),
            "gold_membership": "in_gold_vFinal" if pid in gold_id_set else "not_in_gold_vFinal",
            "human_confirmed_adjudication": "yes" if pid in confirmed_ids else "no",
            "queue_status": (
                "unresolved" if split_membership.get(pid, "NOT_IN_SPLIT") in {"UNKNOWN", "SPLIT_OVERLAP", "NOT_IN_SPLIT"}
                else "confirmed" if pid in confirmed_ids
                else "pending" if split_membership.get(pid) == "D_dev"
                else "excluded"
            ),
            "extractor_error_review": "yes",
            "extractor_review_status": queue_status,
            "review_focus": ";".join(focus),
            "gold_capabilities": json.dumps(gold_labels, ensure_ascii=False),
            "predicted_capabilities": row.get("predicted_capabilities", ""),
            "false_negatives": row.get("false_negatives", ""),
            "false_positives": row.get("false_positives", ""),
            "exact_match": row.get("exact_match", ""),
            "error_classification": row.get("error_classification", ""),
            "gold_label_correct": row.get("gold_label_correct", ""),
            "extractor_rule_issue": row.get("extractor_rule_issue", ""),
            "proposed_action": row.get("proposed_action", ""),
            "review_notes": row.get("review_notes", ""),
            "reviewer": row.get("reviewer", ""),
        })

    # Add Gold records not present in the 170-row extractor priority queue.
    # The CSV is a one-row-per-Gold-record review inventory (185 rows).
    for pid in sorted(gold_id_set - priority_set):
        gold_row = gold_lookup.get(pid, {})
        labels = parse_labels(gold_row.get("capabilities_manual", gold_row.get("capabilities", [])))
        split_name = split_membership.get(pid, "NOT_IN_SPLIT")
        status = (
            "unresolved" if split_name in {"UNKNOWN", "SPLIT_OVERLAP", "NOT_IN_SPLIT"}
            else "confirmed" if pid in confirmed_ids
            else "pending" if split_name == "D_dev"
            else "excluded"
        )
        queue_out.append({
            "problem_id": pid,
            "split": split_name,
            "gold_source": "batch_100_vFinal" if pid in batch_set else "supplement_vFinal",
            "gold_membership": "in_gold_vFinal",
            "human_confirmed_adjudication": "yes" if pid in confirmed_ids else "no",
            "queue_status": status,
            "extractor_error_review": "no",
            "extractor_review_status": "not_in_priority_error_queue",
            "review_focus": "not_flagged",
            "gold_capabilities": json.dumps(labels, ensure_ascii=False),
            "predicted_capabilities": "",
            "false_negatives": "",
            "false_positives": "",
            "exact_match": "",
            "error_classification": "",
            "gold_label_correct": "",
            "extractor_rule_issue": "",
            "proposed_action": "",
            "review_notes": "",
            "reviewer": "",
        })

    queue_fields = [
        "problem_id", "split", "gold_source", "gold_membership",
        "human_confirmed_adjudication", "queue_status", "extractor_error_review",
        "extractor_review_status", "review_focus",
        "gold_capabilities", "predicted_capabilities", "false_negatives",
        "false_positives", "exact_match", "error_classification",
        "gold_label_correct", "extractor_rule_issue", "proposed_action",
        "review_notes", "reviewer"
    ]

    out_dir = root / "reports/capability/p1_gold_audit_2026-11-14"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(out_dir / "gold_review_queue.csv", queue_out, queue_fields)

    support = Counter()
    for row in batch + supplement:
        labels = parse_labels(row.get("capabilities_manual", row.get("capabilities", row.get("final_capabilities", []))))
        for label in labels:
            support[label] += 1

    annotation_files = []
    for folder in (root / "data",):
        for p in sorted(folder.rglob("*.jsonl")):
            try:
                rows = read_jsonl(p)
                ids = [norm_id(x) for x in rows]
                annotation_files.append({
                    "path": p.relative_to(root).as_posix(),
                    "records": len(rows),
                    "unique_nonempty_problem_ids": len({x for x in ids if x}),
                    "blank_problem_ids": sum(1 for x in ids if not x),
                    "sha256": sha256(p),
                })
            except Exception as exc:
                annotation_files.append({
                    "path": p.relative_to(root).as_posix(),
                    "error": str(exc),
                    "sha256": sha256(p),
                })

    inventory = {
        "audit_date": "2026-11-14",
        "project_root": str(root),
        "source_files": {
            "gold_batch": {"path": batch_path.relative_to(root).as_posix(),
                           "records": len(batch), "unique_ids": len(batch_set),
                           "sha256": sha256(batch_path)},
            "gold_supplement": {"path": supp_path.relative_to(root).as_posix(),
                                "records": len(supplement), "unique_ids": len(supp_set),
                                "sha256": sha256(supp_path)},
            "gold_manifest": {"path": gold_manifest_path.relative_to(root).as_posix(),
                              "declared_total": gold_manifest.get("total_count"),
                              "declared_unique_ids": gold_manifest.get("unique_problem_ids"),
                              "sha256": sha256(gold_manifest_path)},
            "vnext_manifest": {"path": vnext_manifest_path.relative_to(root).as_posix(),
                               "declared_records": vnext_manifest.get("records"),
                               "sha256": sha256(vnext_manifest_path)},
            "priority_error_review": {"path": queue_path.relative_to(root).as_posix(),
                                      "records": len(priority_rows),
                                      "unique_ids": len(priority_set),
                                      "sha256": sha256(queue_path)},
            "human_confirmed_adjudication": {"path": confirmed_path.relative_to(root).as_posix(),
                                             "records": len(confirmed_rows),
                                             "unique_ids": len(confirmed_ids),
                                             "sha256": sha256(confirmed_path)},
        },
        "gold_vfinal": {
            "batch_records": len(batch),
            "supplement_records": len(supplement),
            "total_records": len(batch) + len(supplement),
            "unique_ids": len(gold_id_set),
            "blank_ids": blank_gold_ids,
            "duplicate_ids_within_batch": duplicate_batch,
            "duplicate_ids_within_supplement": duplicate_supp,
            "duplicate_ids_across_batch_supplement": duplicate_across,
            "human_confirmed_adjudication_count": len(confirmed_ids),
            "human_confirmed_ids_by_split": {
                name: sum(1 for pid in confirmed_ids if split_membership.get(pid) == name)
                for name in ("D_pool", "D_dev", "D_test", "UNKNOWN", "SPLIT_OVERLAP")
            },
            "gold_ids_not_in_human_confirmed_adjudication_file": len(gold_id_set - confirmed_ids),
            "supplement_semantic_review": {
                "summary_file_exists": supplement_audit_path.exists(),
                "semantic_review_completed": supplement_audit.get("semantic_review_completed"),
                "audit_scope": supplement_audit.get("audit_scope"),
                "records": supplement_audit.get("input_records"),
                "pass_count": supplement_audit.get("pass_count"),
                "review_count": supplement_audit.get("review_count"),
            },
            "confirmed_ids_missing_from_gold": sorted(confirmed_ids - gold_id_set),
            "gold_ids_outside_all_splits": sorted(gold_id_set - split_union),
            "split_membership": {
                name: sum(1 for pid in gold_id_set if split_membership.get(pid) == name)
                for name in ("D_pool", "D_dev", "D_test", "UNKNOWN", "SPLIT_OVERLAP")
            },
            "capability_support_multi_label_assignments": dict(sorted(support.items())),
        },
        "priority_error_review": {
            "records": len(priority_rows),
            "unique_ids": len(priority_set),
            "blank_ids": blank_priority,
            "duplicate_ids": duplicate_priority,
            "ids_not_in_gold_vfinal": sorted(priority_set - gold_id_set),
            "ids_by_split": {
                name: sum(1 for pid in priority_set if split_membership.get(pid) == name)
                for name in ("D_pool", "D_dev", "D_test", "UNKNOWN", "SPLIT_OVERLAP")
            },
            "overlap_with_human_confirmed_adjudication": len(priority_set & confirmed_ids),
            "gold_review_status_counts": dict(Counter(x["queue_status"] for x in queue_out)),
            "priority_error_review_status_counts": dict(Counter(
                x["extractor_review_status"] for x in queue_out if x["extractor_error_review"] == "yes"
            )),
            "focus_counts": dict(Counter(
                focus for row in queue_out for focus in row["review_focus"].split(";")
            )),
            "interpretation": (
                "This is an extractor priority-error review queue, not a list of "
                "unconfirmed Gold annotations. Do not change Gold labels solely "
                "because a record appears here."
            ),
        },
        "split_manifest": {
            "path": split_manifest_path.relative_to(root).as_posix(),
            "split_version": split_manifest.get("split_version"),
            "counts": split_manifest.get("counts", {}),
            "sha256": sha256(split_manifest_path),
            "actual_id_counts": {
                "D_pool": len(pool_ids), "D_dev": len(dev_ids), "D_test": len(test_ids)
            },
            "overlap_ids": split_overlap,
        },
        "annotation_jsonl_inventory": annotation_files,
    }

    (out_dir / "gold_inventory.json").write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )

    lines = [
        "# Proposal 1 — Gold audit (2026-11-14)", "",
        "## Executive result", "",
        f"- Gold vFinal: {len(batch)} batch + {len(supplement)} supplement = {len(batch)+len(supplement)} records.",
        f"- Unique Gold problem IDs: {len(gold_id_set)}.",
        f"- Human-confirmed adjudication decisions: {len(confirmed_ids)} "
        f"(D_dev={sum(1 for pid in confirmed_ids if split_membership.get(pid) == 'D_dev')}).",
        f"- Supplement semantic review completed: {supplement_audit.get('semantic_review_completed', 'not recorded')}.",
        f"- Priority extractor-error review queue: {len(priority_rows)} records / {len(priority_set)} unique IDs.",
        f"- Gold review queue: {len(queue_out)} rows (one row per Gold vFinal ID).",
        "",
        "## Gold vFinal split coverage", "",
        "| Source | D_pool | D_dev | D_test |",
        "|---|---:|---:|---:|",
        f"| Batch 100 | {sum(x in pool_ids for x in batch_set)} | {sum(x in dev_ids for x in batch_set)} | {sum(x in test_ids for x in batch_set)} |",
        f"| Supplement 85 | {sum(x in pool_ids for x in supp_set)} | {sum(x in dev_ids for x in supp_set)} | {sum(x in test_ids for x in supp_set)} |",
        f"| Total | {sum(x in pool_ids for x in gold_id_set)} | {sum(x in dev_ids for x in gold_id_set)} | {sum(x in test_ids for x in gold_id_set)} |",
        "",
        "## Gold review status", "",
        "| Status | Records |",
        "|---|---:|",
        f"| confirmed (explicit human-confirmed adjudication) | {sum(1 for x in queue_out if x['queue_status'] == 'confirmed')} |",
        f"| pending (D_dev but not in human-confirmed adjudication file) | {sum(1 for x in queue_out if x['queue_status'] == 'pending')} |",
        f"| excluded from primary mastery evaluation (not D_dev) | {sum(1 for x in queue_out if x['queue_status'] == 'excluded')} |",
        f"| unresolved (split/ID issue) | {sum(1 for x in queue_out if x['queue_status'] == 'unresolved')} |",
        "",
        "## Priority error review split coverage", "",
        "| Split | Records |",
        "|---|---:|",
    ]
    for name in ("D_pool", "D_dev", "D_test", "UNKNOWN", "SPLIT_OVERLAP"):
        lines.append(f"| {name} | {sum(1 for pid in priority_set if split_membership.get(pid) == name)} |")
    lines += [
        "",
        "## Critical interpretation", "",
         "The 170-row file is `priority_error_review_annotated.csv`: an extractor-error review queue. "
        "It is not 170 Gold labels awaiting adjudication. The queue contains records already present "
        "in Gold vFinal. A record may have a human-confirmed Gold adjudication and still require "
        "extractor-error analysis.",
        "",
        "Do not edit Gold vFinal labels, split files, capability rules, or extractor code during this audit. "
        "If a genuine Gold-label defect is discovered, record the evidence and create a separately "
        "reviewed proposal; do not patch the frozen Gold release in place.",
        "",
        "## Integrity findings", "",
        f"- Blank Gold IDs: {blank_gold_ids}",
        f"- Duplicate IDs in batch: {len(duplicate_batch)}",
        f"- Duplicate IDs in supplement: {len(duplicate_supp)}",
        f"- IDs duplicated across batch/supplement: {len(duplicate_across)}",
        f"- Gold IDs outside all splits: {len(gold_id_set - split_union)}",
        f"- Priority queue IDs not in Gold vFinal: {len(priority_set - gold_id_set)}",
        f"- Duplicate priority queue IDs: {len(duplicate_priority)}",
        "",
        "Full ID lists, hashes, source inventory, support counts, and per-file counts are in `gold_inventory.json`.",
        "The row-level review queue is in `gold_review_queue.csv`.",
        "",
        "## Capability support (multi-label assignments)", "",
        "| Capability | Support |",
        "|---|---:|",
    ]
    for cap in sorted(CAPABILITIES):
        lines.append(f"| {cap} | {support.get(cap, 0)} |")
    lines += ["", "## Source file hashes", ""]
    for name, meta in inventory["source_files"].items():
        lines.append(f"- `{meta['path']}` — SHA-256 `{meta['sha256']}`")
    (out_dir / "p1_gold_audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"[PASS] Audit outputs written to: {out_dir}")
    print(f"Gold vFinal: {len(batch)+len(supplement)} records / {len(gold_id_set)} unique IDs")
    print(f"Gold split: D_pool={sum(x in pool_ids for x in gold_id_set)}, "
          f"D_dev={sum(x in dev_ids for x in gold_id_set)}, "
          f"D_test={sum(x in test_ids for x in gold_id_set)}")
    print(f"Priority review: {len(priority_rows)} rows / {len(priority_set)} unique IDs")
    print(f"Priority split: D_pool={sum(x in pool_ids for x in priority_set)}, "
          f"D_dev={sum(x in dev_ids for x in priority_set)}, "
          f"D_test={sum(x in test_ids for x in priority_set)}")
    print("NOTE: Gold source files were not modified.")

if __name__ == "__main__":
    main()
