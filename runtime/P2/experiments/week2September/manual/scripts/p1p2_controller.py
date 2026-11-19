#!/usr/bin/env python3
"""Unified, no-overwrite controller for P2 B2-B5 and P1/P2 methods.

User-facing rounds are checkpoint numbers: 1 means train/evaluate S1.
P1 selector rounds are 1-based; select_round.py rounds are 0-based.
"""
from __future__ import annotations
import argparse, hashlib, json, math, os, subprocess, sys, time
from pathlib import Path
from typing import Any, Callable

from capability_eval import load_approved_gold, strict_correct, validate_manifest_count
from p1p2_artifact_manager import hash_path as sha256, publish_bytes_no_overwrite, publish_json_no_overwrite
from p1p2_capability_state import build_state, stable_state
from p1p2_paths import artifact_path, legacy_root

METHODS = ("B2", "B3", "B4", "B5", "P1-DEFICIT", "P1P2")
P1_METHODS = {"P1-DEFICIT", "P1P2"}
P2_METHODS = {"B2", "B3", "B4", "B5"}
REGISTERED_SEEDS = {13, 42, 2026}
FORBIDDEN = (Path("runs/main"), Path("models/task7"))


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8-sig") as f:
        for n, line in enumerate(f, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"Expected object at {path}:{n}")
            rows.append(row)
    return rows


def inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


class Controller:
    def __init__(self, root: Path, *, resume: bool, dry_run: bool,
                 backend: str = "hf", micro_batch: int = 4, nll_batch: int = 4,
                 eval_batch: int | None = None, dtype: str = "auto",
                 runner: Callable[[list[str]], None] | None = None,
                 legacy_windows_root: str | None = None):
        self.root = root.resolve()
        self.legacy_windows_root = legacy_root(legacy_windows_root) if legacy_windows_root else None
        self.scripts = self.root / "scripts"
        self.resume, self.dry_run = resume, dry_run
        self.backend, self.micro_batch, self.nll_batch = backend, micro_batch, nll_batch
        self.eval_batch, self.dtype = eval_batch, dtype
        self.runner = runner or self._subprocess
        self.py = sys.executable
        self.config = self.root / "config/experiment_config.json"
        self.pool = self.root / "trajectory/pool/pool_v1_verified.jsonl"
        self.tokens = self.root / "trajectory/pool/pool_v1_tokens.jsonl"
        self.d_pool = self.root / "splits/d_pool_ids.txt"
        self.dev_ids = self.root / "splits/d_dev_ids.txt"
        self.s0_prediction = self.root / "runs/main/S0/eval_dev.jsonl"
        self.s0_reference = self.root / "reports/p1p2_integration/source_review/s0_base_model_reference.json"
        self.s0_sidecar = self.root / "reports/capability/g5_9_real_data_s0/SHARED_seed0_S0"
        self.gold_manifest = self.root / "data/gold_vfinal/gold_vfinal_manifest.json"
        self.gold_labels = self.root / "data/gold_vfinal/supplement_annotations_vfinal.jsonl"
        self.approval = self.root / "data/gold_releases/vFinal_2026-11-16/gold_supplement_85_approved_review.csv"
        self.actions: list[dict[str, Any]] = []
        self.generated_nll: set[str] = set()
        self._validate_root_inputs()

    def _subprocess(self, cmd: list[str]) -> None:
        subprocess.run(cmd, cwd=self.root, check=True)

    def _recorded_path(self, value: str) -> Path:
        return artifact_path(self.root, value, getattr(self, "legacy_windows_root", None))

    def _validate_root_inputs(self) -> None:
        from yaml import safe_load

        registry = safe_load((self.root / "config/p1p2_method_registry.yaml").read_text(encoding="utf-8-sig"))
        protocol = safe_load((self.root / "config/p1p2_unified_run.yaml").read_text(encoding="utf-8-sig"))
        if (registry["schema_version"] != "p1p2.method-registry.v1"
                or {name for name, entry in registry["methods"].items() if entry.get("enabled")} != set(METHODS)
                or set(registry["registered_seeds"]) != REGISTERED_SEEDS
                or registry["checkpoint_protocol"]["test_evaluation_during_rounds"] is not False
                or registry["checkpoint_protocol"]["p2_round_index_offset"] != -1
                or protocol["schema_version"] != "p1p2.unified-run.v1"
                or protocol["execution"]["rounds"]["checkpoint_by_round"] != {0: "S0", 1: "S1", 2: "S2", 3: "S3"}):
            raise ValueError("Frozen integration protocol or method registry does not match controller")
        for p in (self.config, self.pool, self.tokens, self.tokens.with_suffix(".summary.json"), self.d_pool, self.dev_ids):
            if not p.is_file():
                raise FileNotFoundError(f"Required integration input missing: {p}")
        cfg = read_json(self.config)
        if cfg.get("config_version") != "v2":
            raise ValueError("Only frozen experiment_config.json v2 is supported")
        if cfg.get("selection", {}).get("alpha") != 0.5 or cfg.get("selection", {}).get("alpha_tuned") is not False:
            raise ValueError("Frozen P1P2 alpha policy must remain 0.5 and untuned")
        if cfg.get("training", {}).get("method") != "LoRA":
            raise ValueError("Frozen training method is not LoRA")
        if cfg["training"]["batch_size"] % self.micro_batch:
            raise ValueError(f"--micro-batch must divide the frozen effective batch {cfg['training']['batch_size']}")
        pool_hash = sha256(self.pool)
        # Do not hard-code a collaborator-specific digest. The active pool hash
        # is canonicalized by verifying the token summary against these exact bytes.
        summary = read_json(self.tokens.with_suffix(".summary.json"))
        if summary.get("pool_sha256") != pool_hash:
            raise ValueError("Token summary does not match verified pool")
        pool_contract = protocol["data"]["verified_pool"]
        pool_rows = read_jsonl(self.pool)
        token_rows = read_jsonl(self.tokens)
        expected = {(row["trajectory_id"], row["problem_id"]) for row in pool_rows}
        actual = {(row["trajectory_id"], row["problem_id"]) for row in token_rows}
        if (pool_contract["expected_sha256"] != pool_hash
                or len(expected) != pool_contract["expected_records"]
                or len(expected) != len(pool_rows) or len(actual) != len(token_rows)
                or actual != expected
                or sum(row["response_tokens"] for row in token_rows) != summary["response_tokens_sum"]):
            raise ValueError(f"Pool/token provenance mismatch: {self.tokens}")
        dev = [x.strip() for x in self.dev_ids.read_text(encoding="utf-8-sig").splitlines() if x.strip()]
        if len(dev) != 500 or len(set(dev)) != 500:
            raise ValueError("D_dev must contain exactly 500 unique IDs")
        for required in (self.gold_manifest, self.gold_labels, self.approval):
            if not required.is_file():
                raise FileNotFoundError(f"Required Gold input missing: {required}")
        reference = read_json(self.s0_reference)
        student = cfg["student"]
        if (reference.get("schema") != "p1p2.base_model_reference.v1"
                or reference.get("adapter") is not None
                or reference.get("model_id") != student["model"]
                or reference.get("revision") != student["revision"]):
            raise ValueError(f"Invalid shared S0 model identity: {self.s0_reference}")
        for field, path in (
            ("evaluation_prediction_sha256", self.s0_prediction),
            ("evaluation_summary_sha256", self.s0_prediction.with_suffix(".summary.json")),
            ("evaluation_marker_sha256", self.s0_prediction.parent / ".done/eval_dev_S0.json"),
        ):
            if reference.get(field) != sha256(path):
                raise ValueError(f"Shared S0 fingerprint mismatch: {path}")
        if not self._valid_prediction(self.s0_prediction, "S0"):
            raise ValueError(f"Invalid shared S0 D_dev coverage: {self.s0_prediction}")
        split_root = self.root / "splits/p1p2_vfinal_2026-11-16"
        split = read_json(split_root / "split_manifest.json")
        partition = []
        for filename, count in (("d_dev_graph_ids.txt", 85), ("d_dev_select_ids.txt", 415)):
            path = split_root / filename
            ids = set(path.read_text(encoding="utf-8-sig").split())
            if len(ids) != count or split["files"][filename]["sha256"] != sha256(path):
                raise ValueError(f"Invalid D_dev partition: {path}")
            partition.append(ids)
        if partition[0] & partition[1] or partition[0] | partition[1] != set(dev):
            raise ValueError("Gold and selection splits must partition D_dev")
        validate_manifest_count(self.gold_manifest)
        if set(load_approved_gold(self.gold_labels, self.approval, set(dev))) != partition[0]:
            raise ValueError("Approved Gold IDs must match the frozen D_dev Gold partition")
        lineage = read_json(self.s0_sidecar / "checkpoint_lineage.json")
        for field, path in (
            ("checkpoint_sha256", self.s0_reference), ("prediction_sha256", self.s0_prediction),
            ("config_sha256", self.config), ("dev_ids_sha256", self.dev_ids),
            ("gold_manifest_sha256", self.gold_manifest), ("gold_labels_sha256", self.gold_labels),
            ("approval_csv_sha256", self.approval),
        ):
            if lineage.get(field) != sha256(path):
                raise ValueError(f"Shared S0 sidecar input mismatch: {path}")
        state = build_state(self.s0_sidecar, "P1P2", 13)
        if state["source"]["checkpoint"] != "S0":
            raise ValueError("Expected shared S0 capability sidecar")

    def _validate_adapter(self, path: Path, parent: Path | None, seed: int,
                          train_set: Path) -> None:
        weights = [path / name for name in ("adapter_model.safetensors", "adapter_model.bin")]
        if not any(file.is_file() and file.stat().st_size for file in weights):
            raise ValueError(f"Missing or empty LoRA weights: {path}")
        if read_json(path / "adapter_config.json").get("peft_type") != "LORA":
            raise ValueError(f"Adapter is not LoRA: {path}")
        log_path = path / "train_log.json"
        log = read_json(log_path)
        expected = {
            "seed": seed, "data_order_seed": seed,
            "train_set_sha256": sha256(train_set), "config_sha256": sha256(self.config),
            "pool_sha256": sha256(self.pool),
        }
        if any(log.get(key) != value for key, value in expected.items()):
            raise ValueError(f"Adapter training provenance mismatch: {log_path}")
        recorded_parent = log.get("checkpoint_parent")
        if parent is None:
            parent_matches = recorded_parent == "student_ckpt_000"
        else:
            parent_matches = (isinstance(recorded_parent, str) and self._recorded_path(recorded_parent) == parent.resolve()
                              and log.get("checkpoint_parent_sha256") == sha256(parent))
        if not parent_matches:
            raise ValueError(f"Adapter parent mismatch: {log_path}")

    def namespace(self, seed: int) -> tuple[Path, Path, Path]:
        suffix = "" if seed in REGISTERED_SEEDS else "_custom"
        return (self.root / f"runs/p1p2_integration{suffix}",
                self.root / f"models/p1p2_integration{suffix}",
                self.root / f"reports/p1p2_integration{suffix}")

    def safe_output(self, path: Path, kind: str) -> Path:
        path = path.resolve()
        for forbidden in FORBIDDEN:
            if inside(path, self.root / forbidden):
                raise ValueError(f"Forbidden output namespace: {path}")
        if kind == "run" and not (inside(path, self.root / "runs/p1p2_integration") or inside(path, self.root / "runs/p1p2_integration_custom")):
            raise ValueError(f"Run output outside approved namespace: {path}")
        if kind == "model" and not (inside(path, self.root / "models/p1p2_integration") or inside(path, self.root / "models/p1p2_integration_custom")):
            raise ValueError(f"Model output outside approved namespace: {path}")
        if kind == "report" and not (inside(path, self.root / "reports/p1p2_integration") or inside(path, self.root / "reports/p1p2_integration_custom")):
            raise ValueError(f"Report output outside approved namespace: {path}")
        return path

    def emit(self, label: str, cmd: list[str], *, outputs: list[Path] = ()) -> None:
        self.actions.append({"stage": label, "command": [str(x) for x in cmd], "outputs": [str(x) for x in outputs]})
        print(f"[{ 'PLAN' if self.dry_run else 'RUN' }] {label}")
        print("  " + subprocess.list2cmdline([str(x) for x in cmd]))
        if not self.dry_run:
            self.runner([str(x) for x in cmd])

    def _valid_prediction(self, path: Path, expected_tag: str | None = None) -> bool:
        summary_path = path.with_suffix(".summary.json")
        if not path.is_file() or not summary_path.is_file(): return False
        rows = read_jsonl(path)
        ids = [str(r.get("problem_id", "")).strip() for r in rows]
        expected = {x.strip() for x in self.dev_ids.read_text(encoding="utf-8-sig").splitlines() if x.strip()}
        summary = read_json(summary_path)
        tag_ok = expected_tag is None or all(r.get("checkpoint") == expected_tag for r in rows)
        summary_ok = (summary.get("split") == "dev" and summary.get("n_problems") == 500
                      and (expected_tag is None or summary.get("checkpoint") == expected_tag))
        correct = sum(strict_correct(row) for row in rows)
        return (len(rows) == 500 and len(set(ids)) == 500 and set(ids) == expected
                and tag_ok and summary_ok and summary.get("accuracy", correct / 500) == correct / 500)

    def _valid_nll(self, path: Path, tag: str, adapter: Path | None = None) -> bool:
        summary_path = path.with_suffix(".summary.json")
        if not path.is_file() or not summary_path.is_file(): return False
        rows = read_jsonl(path); summary = read_json(summary_path)
        token_rows = read_jsonl(self.tokens)
        expected = {r["trajectory_id"]: r["response_tokens"] for r in token_rows}
        student = read_json(self.config)["student"]
        expected_adapter = sha256(adapter) if adapter is not None else None
        return (summary.get("checkpoint") == tag and summary.get("pool_sha256") == sha256(self.pool)
                and summary.get("model") == student["model"] and summary.get("revision") == student["revision"]
                and summary.get("adapter_sha256") == expected_adapter
                and (self._recorded_path(summary.get("adapter")) == adapter.resolve()
                     if adapter is not None else summary.get("adapter") is None)
                and summary.get("n_trajectories") == len(expected)
                and len(rows) == len(expected) and len({r.get("trajectory_id") for r in rows}) == len(expected)
                and {r.get("trajectory_id") for r in rows} == set(expected)
                and all(r.get("checkpoint") == tag and r.get("n_tokens") == expected.get(r.get("trajectory_id"))
                        and isinstance(r.get("ell"), (int, float)) and math.isfinite(r["ell"]) and r["ell"] >= 0
                        for r in rows))

    def _ensure_nll(self, run_dir: Path, ckpt: int, adapter: Path | None, *, tag_override: str | None = None) -> Path:
        tag = tag_override or f"S{ckpt}"
        out_dir = run_dir / tag
        out = out_dir / "nll.jsonl"
        out_key = str(out.resolve()).casefold()
        if self._valid_nll(out, tag, adapter):
            if not self.resume and not self.dry_run and out_key not in self.generated_nll:
                raise FileExistsError(f"Validated NLL already exists; rerun with --resume to reuse: {out}")
            print(f"[REUSE] validated NLL {out}")
            return out
        if self.dry_run and out_key in self.generated_nll:
            return out
        if out.exists() or out.with_suffix(".summary.json").exists():
            raise RuntimeError(f"Partial or invalid NLL exists; preserve and investigate, do not overwrite: {out}")
        cmd = [self.py, self.scripts / "compute_nll.py", "--tag", tag, "--out", out,
               "--pool", self.pool, "--batch-size", str(self.nll_batch), "--dtype", self.dtype]
        if adapter is not None: cmd += ["--adapter", adapter]
        self.emit(f"compute_nll_{tag}", cmd, outputs=[out, out.with_suffix(".summary.json")])
        if not self.dry_run and not self._valid_nll(out, tag, adapter):
            raise ValueError(f"NLL stage did not publish matching results: {out}")
        self.generated_nll.add(out_key)
        return out

    def _ensure_selection_p1(self, method: str, seed: int, round_no: int, run_dir: Path,
                             report_dir: Path, state_path: Path, nll_path: Path | None,
                             adapter: Path | None = None, *, published: bool = False) -> tuple[Path, Path]:
        out_dir = run_dir / f"round_{round_no:03d}"
        train, log = out_dir / "train_set.json", out_dir / "selection_log.jsonl"
        if train.is_file() and log.is_file():
            if not self.resume and not self.dry_run and round_no != 1 and not published:
                raise FileExistsError(f"P1 selection artifacts already exist; use --resume: {out_dir}")
            data = read_json(train)
            recorded_state = self._recorded_path(data.get("state_file"))
            if not recorded_state.is_file():
                raise FileNotFoundError(f"Existing P1 selection references missing state: {recorded_state}")
            if recorded_state != state_path.resolve():
                raise ValueError(f"Existing P1 selection uses a different capability state: {train}")
            expected_fields = {"schema_version": "p1p2.train-set.v1", "method": method,
                               "training_seed": seed, "round": round_no,
                               "source_checkpoint": f"S{round_no-1}",
                               "pool_sha256": sha256(self.pool),
                               "tokens_sha256": sha256(self.tokens),
                               "config_sha256": sha256(self.config),
                               "state_sha256": sha256(recorded_state)}
            for key, expected in expected_fields.items():
                if data.get(key) != expected:
                    raise RuntimeError(f"Existing P1 train-set {key} mismatch: {train}")
            if method == "P1-DEFICIT":
                if data.get("nll_file") is not None or data.get("nll_sha256") is not None:
                    raise RuntimeError("P1-DEFICIT historical selection unexpectedly contains NLL provenance")
            else:
                recorded_nll = self._recorded_path(data.get("nll_file"))
                if (nll_path is None or recorded_nll != nll_path.resolve()
                        or not self._valid_nll(recorded_nll, f"S{round_no-1}", adapter)
                        or data.get("nll_sha256") != sha256(recorded_nll)):
                    raise RuntimeError("P1P2 historical selection NLL fingerprint/coverage mismatch")
            log_rows = read_jsonl(log)
            pool_ids = {row["trajectory_id"] for row in read_jsonl(self.pool)}
            if len(log_rows) != len(pool_ids) or {row.get("trajectory_id") for row in log_rows} != pool_ids:
                raise RuntimeError(f"Existing P1 selection log does not cover the full verified pool: {log}")
            selected_ids = {r.get("trajectory_id") for r in log_rows if r.get("selected") is True}
            ids = data.get("trajectory_ids", [])
            if not selected_ids or selected_ids != set(ids) or len(ids) != len(selected_ids):
                raise RuntimeError(f"Existing P1 train-set IDs differ from selection log: {train}")
            if any(r.get("method") != method or r.get("seed") != seed or r.get("round") != round_no
                   or r.get("source_checkpoint") != f"S{round_no-1}" for r in log_rows):
                raise RuntimeError(f"Existing P1 selection-log lineage mismatch: {log}")
            print(f"[REUSE] P1 selection round {round_no}: preserving validated train set/log")
            return train, log
        if train.exists() or log.exists():
            raise RuntimeError(f"Incomplete P1 selection pair exists; refusing overwrite: {out_dir}")
        if published:
            raise RuntimeError(f"Selector returned without publishing its output pair: {out_dir}")
        cmd = [self.py, self.scripts / "p1p2_selector.py", "--method", method, "--seed", str(seed),
               "--round", str(round_no), "--state", state_path, "--out-dir", out_dir,
               "--pool", self.pool, "--tokens", self.tokens, "--d-pool", self.d_pool, "--config", self.config]
        for previous in range(1, round_no): cmd += ["--previous-train-set", run_dir / f"round_{previous:03d}" / "train_set.json"]
        if nll_path is not None: cmd += ["--nll", nll_path]
        self.emit(f"select_{method}_round_{round_no}", cmd, outputs=[train, log])
        if not self.dry_run:
            return self._ensure_selection_p1(method, seed, round_no, run_dir, report_dir, state_path,
                                             nll_path, adapter, published=True)
        return train, log

    def _ensure_selection_p2(self, method: str, seed: int, target_ckpt: int, run_dir: Path,
                             source_nll: Path | None) -> tuple[Path, Path]:
        p2_round = target_ckpt - 1
        out_dir = run_dir / f"round_{p2_round:03d}"
        train, log = out_dir / "train_set.json", out_dir / "selection_log.jsonl"
        if train.is_file() and log.is_file():
            if not self.resume and not self.dry_run and target_ckpt != 1:
                raise FileExistsError(f"P1 selection artifacts already exist; use --resume: {out_dir}")
            data = read_json(train)
            if data.get("method") != method or data.get("training_seed") != seed or data.get("round") != p2_round:
                raise RuntimeError(f"Existing P2 selection artifact contract mismatch: {train}")
            print(f"[REUSE] P2 selection round {p2_round}: {train}")
            return train, log
        if train.exists() or log.exists():
            raise RuntimeError(f"Incomplete P2 selection pair exists; refusing overwrite: {out_dir}")
        cmd = [self.py, self.scripts / "select_round.py", "--method", method, "--seed", str(seed),
               "--round", str(p2_round), "--run-dir", run_dir, "--pool", self.pool, "--tokens", self.tokens]
        if source_nll is not None: cmd += ["--nll", source_nll]
        self.emit(f"select_{method}_p2round_{p2_round}", cmd, outputs=[train, log])
        return train, log

    def _hook(self, method: str, seed: int, ckpt: int, prediction: Path, checkpoint: Path,
              run_dir: Path, model_dir: Path, report_dir: Path, train_set: Path, selection_log: Path,
              shared_group: str | None = None) -> Path:
        run_id = f"{method}_seed{seed}_S{ckpt}"
        out_dir = self.safe_output(report_dir / "capability_sidecars" / run_id, "report")
        train_log = checkpoint / "train_log.json"
        checkpoint_log = run_dir / "checkpoint_log.jsonl"
        if out_dir.exists():
            self._validate_sidecar(out_dir, method, seed, ckpt, prediction, checkpoint,
                                   train_set, checkpoint_log)
            print(f"[REUSE] validated capability sidecar {out_dir}")
            return out_dir
        cmd = [self.py, self.scripts / "run_p1p2_post_eval.py", "--method", method, "--seed", str(seed),
               "--round", str(ckpt), "--prediction", prediction, "--checkpoint", checkpoint,
               "--output-dir", out_dir, "--manual-root", self.root,
               "--train-set", train_set, "--selection-log", selection_log,
               "--train-log", train_log, "--checkpoint-log", checkpoint_log,
               "--gold-manifest", self.gold_manifest,
               "--gold-labels", self.gold_labels,
               "--approval-csv", self.approval,
               "--dev-ids", self.dev_ids,
               "--config", self.config]
        required_hook_inputs = (self.gold_manifest, self.gold_labels, self.approval, self.dev_ids, self.config)
        missing_hook_inputs = [str(p) for p in required_hook_inputs if not Path(p).is_file()]
        if missing_hook_inputs:
            raise FileNotFoundError("Post-evaluation hook inputs missing: " + "; ".join(missing_hook_inputs))
        if shared_group:
            cmd += ["--shared-checkpoint-group", shared_group]
        self.emit(f"post_eval_{run_id}", cmd, outputs=[out_dir])
        if not self.dry_run:
            self._validate_sidecar(out_dir, method, seed, ckpt, prediction, checkpoint,
                                   train_set, checkpoint_log)
        return out_dir

    def _validate_sidecar(self, sidecar: Path, method: str, seed: int, ckpt: int,
                          prediction: Path, adapter: Path, train_set: Path, checkpoint_log: Path) -> None:
        state = build_state(sidecar, method, seed)
        source = state["source"]
        if (source["method"], source["seed"], source["round"]) != (method, seed, ckpt):
            raise ValueError(f"Unexpected capability sidecar identity: {sidecar}")
        lineage = read_json(sidecar / "checkpoint_lineage.json")
        for field, path in (
            ("prediction_sha256", prediction), ("config_sha256", self.config),
            ("gold_manifest_sha256", self.gold_manifest), ("gold_labels_sha256", self.gold_labels),
            ("approval_csv_sha256", self.approval), ("dev_ids_sha256", self.dev_ids),
        ):
            if lineage.get(field) != sha256(path):
                raise ValueError(f"Capability sidecar input mismatch: {path}")
        if source["checkpoint_sha256"] != sha256(adapter):
            raise ValueError(f"Capability sidecar adapter fingerprint mismatch: {sidecar}")
        inputs = read_json(sidecar / "input_fingerprint.json")["inputs"]
        for key, path in (
            ("train_set", train_set), ("selection_log", train_set.with_name("selection_log.jsonl")),
            ("train_log", adapter / "train_log.json"),
        ):
            if inputs.get(key) != sha256(path):
                raise ValueError(f"Capability sidecar lineage input mismatch: {path}")
        # Later checkpoints append to the same log. Verify the original prefix
        # through this checkpoint, not the whole file after subsequent rounds.
        digest = hashlib.sha256()
        with checkpoint_log.open("rb") as stream:
            for line in stream:
                digest.update(line)
                if json.loads(line).get("checkpoint") == f"S{ckpt}":
                    break
            else:
                raise ValueError(f"Checkpoint S{ckpt} is missing from {checkpoint_log}")
        if inputs.get("checkpoint_log") != digest.hexdigest():
            raise ValueError(f"Capability sidecar checkpoint log fingerprint mismatch: {sidecar}")

    def _state(self, sidecar: Path, method: str, seed: int, selection_round: int, report_dir: Path) -> Path:
        out = self.safe_output(report_dir / "capability_state" / f"{method}_seed{seed}"
                               / f"selection_round_{selection_round:03d}.json", "report")
        if selection_round == 1 and not out.exists():
            historical = out.with_name("S0_state.json")
            if historical.exists():
                out = historical
        if sidecar.exists():
            expected = build_state(sidecar, method, seed)
            if expected["target"]["selection_round"] != selection_round:
                raise ValueError(f"Capability sidecar has unexpected source checkpoint: {sidecar}")
            if out.exists():
                if stable_state(read_json(out)) != stable_state(expected):
                    raise ValueError(f"Capability state provenance mismatch: {out}")
                print(f"[REUSE] validated capability state {out}")
                return out
        elif out.exists() or not self.dry_run:
            raise ValueError(f"Capability state exists without its source sidecar: {out}")
        cmd = [self.py, self.scripts / "p1p2_capability_state.py", "--sidecar-dir", sidecar,
               "--target-method", method, "--target-seed", str(seed), "--out", out]
        self.emit(f"capability_state_{method}_seed{seed}_selection_{selection_round}", cmd, outputs=[out])
        if not self.dry_run and stable_state(read_json(out)) != stable_state(expected):
            raise ValueError(f"Published capability state provenance mismatch: {out}")
        return out

    def _checkpoint_log(self, run_dir: Path, method: str, seed: int, ckpt: int,
                        train_set: Path, model_dir: Path, train_log: Path, *, require_existing=False) -> Path:
        path = run_dir / "checkpoint_log.jsonl"
        row = {"record_type": "checkpoint", "checkpoint": f"S{ckpt}", "parent_checkpoint": f"S{ckpt-1}",
               "round": ckpt, "method": method, "training_seed": seed, "data_order_seed": seed,
               "train_set": str(train_set), "train_set_sha256": sha256(train_set),
               "selection_log_sha256": sha256(train_set.with_name("selection_log.jsonl")),
               "checkpoint_path": str(model_dir), "checkpoint_sha256": sha256(model_dir),
               "train_log": str(train_log), "train_log_sha256": sha256(train_log)}
        if path.exists():
            rows = read_jsonl(path)
            existing = [r for r in rows if r.get("checkpoint") == f"S{ckpt}"]
            if existing:
                if len(existing) != 1:
                    raise RuntimeError(f"Duplicate checkpoint log record: {path} S{ckpt}")
                comparison = existing[0].copy()
                for key in ("train_set", "checkpoint_path", "train_log"):
                    comparison[key] = str(self._recorded_path(comparison.get(key)))
                if comparison != row:
                    raise RuntimeError(f"Checkpoint log provenance collision: {path} S{ckpt}")
                return path
        if require_existing:
            raise ValueError(f"Missing prerequisite checkpoint log record: {path} S{ckpt}")
        if path.exists() and path.stat().st_size:
            with path.open("rb") as stream:
                stream.seek(-1, os.SEEK_END)
                if stream.read(1) != b"\n":
                    raise ValueError(f"Checkpoint log has an unterminated last record: {path}")
        if self.dry_run:
            self.actions.append({"stage": f"checkpoint_log_{method}_seed{seed}_S{ckpt}",
                                 "command": ["CONTROLLER_INTERNAL", "publish_checkpoint_log"],
                                 "outputs": [str(path)]})
            return path
        content = (json.dumps(row, ensure_ascii=False) + "\n").encode("utf-8")
        if path.exists():
            with path.open("ab") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
        else:
            publish_bytes_no_overwrite(path, content)
        return path

    def run_method_seed(self, method: str, seed: int, checkpoints: list[int]) -> None:
        runs_root, models_root, reports_root = self.namespace(seed)
        run_dir = self.safe_output(runs_root / f"{method}_seed{seed}", "run")
        model_run = self.safe_output(models_root / f"{method}_seed{seed}", "model")
        run_dir.mkdir(parents=True, exist_ok=True) if not self.dry_run else None
        model_run.mkdir(parents=True, exist_ok=True) if not self.dry_run else None
        # S0 reference is immutable and shared; it is never trained by this controller.
        state_s0 = None
        if method in P1_METHODS and 1 in checkpoints:
            if not self.s0_sidecar.is_dir() or not self.s0_reference.is_file():
                raise FileNotFoundError("P1 requires validated SHARED S0 sidecar and s0_base_model_reference.json")
            state_s0 = self._state(self.s0_sidecar, method, seed, 1, reports_root)
        planned = set()
        for ckpt in checkpoints:
            p2_round = ckpt - 1
            round_no = ckpt
            model_dir = self.safe_output(model_run / f"student_ckpt_{ckpt:03d}", "model")
            prediction = self.safe_output(run_dir / f"S{ckpt}" / "eval_dev.jsonl", "run")
            train_set = self.safe_output(run_dir / f"round_{(round_no if method in P1_METHODS else p2_round):03d}"
                                         / "train_set.json", "run")
            selection_log = train_set.with_name("selection_log.jsonl")
            adapter_parent = model_run / f"student_ckpt_{ckpt-1:03d}"
            if ckpt == 1:
                adapter_parent = None
            elif not (self.dry_run and ckpt - 1 in planned):
                self.safe_output(adapter_parent, "model")
                parent_parent = model_run / f"student_ckpt_{ckpt-2:03d}" if ckpt > 2 else None
                parent_selection = run_dir / f"round_{(ckpt - 1 if method in P1_METHODS else ckpt - 2):03d}" / "train_set.json"
                self._validate_adapter(adapter_parent, parent_parent, seed, parent_selection)
                if not self._valid_prediction(run_dir / f"S{ckpt-1}" / "eval_dev.jsonl",
                                              f"{method}_seed{seed}_S{ckpt-1}"):
                    raise ValueError(f"Missing or invalid prerequisite D_dev output for S{ckpt-1}")
                self._checkpoint_log(run_dir, method, seed, ckpt - 1, parent_selection, adapter_parent,
                                     adapter_parent / "train_log.json", require_existing=True)
                parent_sidecar = reports_root / "capability_sidecars" / f"{method}_seed{seed}_S{ckpt-1}"
                self._validate_sidecar(parent_sidecar, method, seed, ckpt - 1,
                                       run_dir / f"S{ckpt-1}" / "eval_dev.jsonl", adapter_parent,
                                       parent_selection, run_dir / "checkpoint_log.jsonl")
                if method in P1_METHODS:
                    parent_state = reports_root / "capability_state" / f"{method}_seed{seed}" / f"selection_round_{ckpt:03d}.json"
                    if stable_state(read_json(parent_state)) != stable_state(build_state(parent_sidecar, method, seed)):
                        raise ValueError(f"Invalid prerequisite capability state: {parent_state}")
            state_path = (state_s0 if ckpt == 1 else reports_root / "capability_state"
                          / f"{method}_seed{seed}" / f"selection_round_{ckpt:03d}.json")
            if model_dir.exists():
                train_log_existing = model_dir / "train_log.json"
                if not ((self.resume or self.dry_run) and train_log_existing.is_file()):
                    raise FileExistsError(f"Adapter directory collision or interrupted training; refusing to write: {model_dir}")
                self._validate_adapter(model_dir, adapter_parent, seed, train_set)
                if not selection_log.is_file():
                    raise ValueError(f"Existing adapter is missing its selection log: {selection_log}")
                if method in P1_METHODS:
                    nll_path = None
                    if method == "P1P2":
                        nll_path = (self._recorded_path(read_json(train_set).get("nll_file")) if ckpt == 1
                                    else run_dir / f"S{ckpt-1}" / "nll.jsonl")
                    self._ensure_selection_p1(method, seed, ckpt, run_dir, reports_root, state_path, nll_path, adapter_parent)
            else:
                if prediction.exists() or prediction.with_suffix(".summary.json").exists():
                    raise RuntimeError(f"Evaluation output has no adapter; preserve for audit: {prediction}")
                if method == "P1-DEFICIT":
                    nll_path = None
                elif method == "P1P2":
                    existing_round1 = run_dir / "round_001" / "train_set.json"
                    if ckpt == 1 and existing_round1.is_file():
                        recorded = read_json(existing_round1).get("nll_file")
                        if not recorded:
                            raise RuntimeError("Existing P1P2 round-1 train set has no recorded S0 NLL path")
                        nll_path = self._recorded_path(recorded)
                        if not self._valid_nll(nll_path, "S0"):
                            raise RuntimeError(f"Existing P1P2 round-1 NLL is not valid/full-coverage: {nll_path}")
                    else:
                        nll_path = self._ensure_nll(run_dir, ckpt - 1, adapter_parent)
                elif method == "B4":
                    nll_path = self._ensure_nll(run_dir, 0, None)
                elif method == "B5":
                    nll_path = self._ensure_nll(run_dir, ckpt - 1, adapter_parent)
                else:
                    nll_path = None
                if method in P1_METHODS:
                    if ckpt > 1 and not state_path.is_file() and not self.dry_run:
                        raise FileNotFoundError(f"Missing preceding checkpoint capability state: {state_path}")
                    train_set, selection_log = self._ensure_selection_p1(method, seed, ckpt, run_dir, reports_root, state_path, nll_path, adapter_parent)
                else:
                    train_set, selection_log = self._ensure_selection_p2(method, seed, ckpt, run_dir, nll_path)
                cmd = [self.py, self.scripts / "train_round.py", "--seed", str(seed), "--train-set", train_set,
                       "--adapter-dir", model_dir, "--micro-batch", str(self.micro_batch), "--dtype", self.dtype,
                       "--pool", self.pool]
                if adapter_parent is not None:
                    cmd += ["--init-adapter", adapter_parent]
                if self.legacy_windows_root is not None:
                    cmd += ["--legacy-windows-root", str(self.legacy_windows_root)]
                self.emit(f"train_{method}_seed{seed}_S{ckpt}", cmd, outputs=[model_dir])
                if not self.dry_run:
                    self._validate_adapter(model_dir, adapter_parent, seed, train_set)
            # Evaluate dev only. Never invoke run_experiment.py from this controller.
            prediction_tag = f"{method}_seed{seed}_S{ckpt}"
            eval_intent = prediction.with_name("eval_dev.intent.json")
            if self.dry_run and not eval_intent.exists():
                self.actions.append({"stage": f"eval_intent_{prediction_tag}",
                                     "command": ["CONTROLLER_INTERNAL", "publish_eval_intent"],
                                     "outputs": [str(eval_intent)]})
            if not self.dry_run or model_dir.is_dir():
                expected_intent = {
                    "checkpoint": prediction_tag, "adapter_sha256": sha256(model_dir),
                    "dev_ids_sha256": sha256(self.dev_ids), "config_sha256": sha256(self.config),
                    "backend": self.backend, "dtype": self.dtype,
                }
                if eval_intent.exists():
                    if read_json(eval_intent) != expected_intent:
                        raise ValueError(f"D_dev evaluation provenance mismatch: {eval_intent}")
                elif prediction.exists() or prediction.with_suffix(".summary.json").exists():
                    raise ValueError(f"Existing evaluation has no verified intent: {prediction}")
                elif not self.dry_run:
                    publish_json_no_overwrite(eval_intent, expected_intent)
            if not self._valid_prediction(prediction, prediction_tag):
                if prediction.with_suffix(".summary.json").exists():
                    raise RuntimeError(f"Existing evaluation summary conflicts with predictions: {prediction}")
                if prediction.exists():
                    # eval_student is resumable; permit continuation only under --resume.
                    if not self.resume:
                        raise FileExistsError(f"Existing prediction requires --resume: {prediction}")
                    old_rows = read_jsonl(prediction)
                    with prediction.open("rb") as stream:
                        if stream.seek(0, os.SEEK_END):
                            stream.seek(-1, os.SEEK_END)
                            if stream.read() != b"\n":
                                raise RuntimeError(f"Partial prediction lacks a complete line boundary: {prediction}")
                    for row in old_rows:
                        strict_correct(row)
                    ids = [r.get("problem_id") for r in old_rows]
                    expected_ids = set(self.dev_ids.read_text(encoding="utf-8-sig").split())
                    if (len(ids) != len(set(ids)) or not set(ids) <= expected_ids
                            or any(row.get("checkpoint") != prediction_tag for row in old_rows)):
                        raise RuntimeError(f"Invalid partial prediction; preserve for audit: {prediction}")
                cmd = [self.py, self.scripts / "eval_student.py", "--tag", f"{method}_seed{seed}_S{ckpt}",
                       "--split", "dev", "--out", prediction, "--backend", self.backend, "--dtype", self.dtype]
                if self.eval_batch is not None: cmd += ["--batch-size", str(self.eval_batch)]
                cmd += ["--adapter", model_dir]
                self.emit(f"eval_dev_{method}_seed{seed}_S{ckpt}", cmd,
                          outputs=[prediction, prediction.with_suffix(".summary.json")])
            elif self.resume:
                print(f"[REUSE] validated D_dev prediction {prediction}")
            if method in P1_METHODS or method in P2_METHODS:
                # Selection artifacts are mandatory lineage inputs for trained checkpoints.
                train_set = run_dir / (f"round_{round_no:03d}" if method in P1_METHODS else f"round_{p2_round:03d}") / "train_set.json"
                selection_log = train_set.with_name("selection_log.jsonl")
                if (not train_set.is_file() or not selection_log.is_file()) and not self.dry_run:
                    raise FileNotFoundError(f"Missing selection lineage for {method} S{ckpt}")
                train_log = model_dir / "train_log.json"
                if not train_log.is_file() and not self.dry_run:
                    raise FileNotFoundError(f"Training did not publish train_log: {train_log}")
                if not self.dry_run and not self._valid_prediction(prediction, prediction_tag):
                    raise RuntimeError(f"D_dev evaluation incomplete; hook is blocked: {prediction}")
                if train_log.is_file():
                    self._checkpoint_log(run_dir, method, seed, ckpt, train_set, model_dir, train_log)
                elif self.dry_run:
                    self.actions.append({"stage": f"checkpoint_log_{method}_seed{seed}_S{ckpt}",
                                         "command": ["CONTROLLER_INTERNAL", "publish_checkpoint_log"],
                                         "outputs": [str(run_dir / "checkpoint_log.jsonl")]})
                sidecar = self._hook(method, seed, ckpt, prediction, model_dir, run_dir, model_dir,
                                     reports_root, train_set, selection_log)
                if method in P1_METHODS:
                    state_s0 = self._state(sidecar, method, seed, ckpt + 1, reports_root)
            planned.add(ckpt)

    def write_dry_run_report(self, methods: list[str], seeds: list[int], checkpoints: list[int]) -> Path:
        report_root = self.root / "reports/p1p2_integration"
        out = self.safe_output(report_root / "integration_tests" / f"dry_run_{time.time_ns()}.json", "report")
        if out.parent != report_root / "integration_tests":
            raise ValueError(f"Redirected dry-run report directory: {out.parent}")
        payload = {"schema_version": "p1p2.controller-dry-run.v1", "dry_run": True,
                   "methods": methods, "seeds": seeds, "target_checkpoints": checkpoints,
                   "round_mapping": {f"S{k}": {"p1_selector_round": k, "p2_select_round_index": k-1} for k in checkpoints},
                   "actions": self.actions, "frozen_config_sha256": sha256(self.config),
                   "verified_inputs": {
                       path.relative_to(self.root).as_posix(): sha256(path)
                       for path in (self.config, self.pool, self.tokens, self.d_pool, self.dev_ids,
                                    self.s0_reference, self.s0_prediction, self.gold_manifest,
                                    self.gold_labels, self.approval,
                                    self.root / "config/p1p2_method_registry.yaml",
                                    self.root / "config/p1p2_unified_run.yaml")
                   },
                   "pool_sha256": sha256(self.pool), "note": "No model training/checkpoint writes were executed."}
        if self.dry_run:
            # Dry-run may write only to the integration_tests report namespace.
            if out.exists(): raise FileExistsError(out)
            publish_json_no_overwrite(out, payload)
        return out


def parse_checkpoints(args: argparse.Namespace) -> list[int]:
    if args.round is not None:
        if args.from_checkpoint or args.to_checkpoint:
            raise ValueError("Do not combine --round with checkpoint range flags")
        return [args.round]
    if args.rounds != ["all"] and (args.from_checkpoint or args.to_checkpoint):
        raise ValueError("Do not combine --rounds with checkpoint range flags")
    if args.from_checkpoint or args.to_checkpoint:
        if not args.from_checkpoint or not args.to_checkpoint:
            raise ValueError("--from-checkpoint and --to-checkpoint must be supplied together")
        a, b = int(args.from_checkpoint[1:]), int(args.to_checkpoint[1:])
        if a not in (0,1,2,3) or b not in (1,2,3) or a >= b:
            raise ValueError("Checkpoint range must be increasing, e.g. S1 through S3")
        return list(range(a + 1, b + 1))
    if args.rounds == ["all"]: return [1,2,3]
    try: values = sorted({int(x) for x in args.rounds})
    except ValueError as exc: raise ValueError("--rounds accepts all or checkpoint numbers 1 2 3") from exc
    if not values or any(x not in (1,2,3) for x in values):
        raise ValueError("--rounds values must be 1, 2, or 3")
    return values


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Unified P1/P2 pipeline controller; user rounds identify target checkpoints S1-S3.")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--method", choices=METHODS)
    group.add_argument("--methods", nargs="+", choices=METHODS)
    sg = p.add_mutually_exclusive_group(required=True)
    sg.add_argument("--seed", type=int)
    sg.add_argument("--seeds", nargs="+", type=int)
    rg = p.add_mutually_exclusive_group()
    rg.add_argument("--round", type=int, choices=(1,2,3))
    rg.add_argument("--rounds", nargs="+", default=["all"])
    rg.add_argument("--from-checkpoint", choices=("S0","S1","S2"),
                    help="exclusive range start; verify this prerequisite without training it")
    p.add_argument("--to-checkpoint", choices=("S1","S2","S3"), help="inclusive range end")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--manual-root", type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument("--legacy-windows-root", help="Explicit archived Windows manual root for byte-preserving staging")
    p.add_argument("--backend", choices=("hf","vllm"), default="hf")
    p.add_argument("--micro-batch", type=int, default=4)
    p.add_argument("--nll-batch", type=int, default=4)
    p.add_argument("--eval-batch", type=int, default=None)
    p.add_argument("--dtype", choices=("auto","bf16","fp32","fp16"), default="auto")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    methods = [args.method] if args.method else args.methods
    seeds = [args.seed] if args.seed is not None else args.seeds
    try:
        checkpoints = parse_checkpoints(args)
        if args.from_checkpoint and not args.to_checkpoint:
            raise ValueError("--from-checkpoint requires --to-checkpoint")
        if args.to_checkpoint and not args.from_checkpoint:
            raise ValueError("--to-checkpoint requires --from-checkpoint")
        if args.micro_batch <= 0 or args.nll_batch <= 0 or (args.eval_batch is not None and args.eval_batch <= 0):
            raise ValueError("Batch sizes must be positive")
        if any(s < 0 for s in seeds): raise ValueError("Seeds must be non-negative")
    except ValueError as exc:
        parser.error(str(exc))
    controller = Controller(args.manual_root, resume=args.resume, dry_run=args.dry_run,
                            backend=args.backend, micro_batch=args.micro_batch,
                            nll_batch=args.nll_batch, eval_batch=args.eval_batch, dtype=args.dtype,
                            legacy_windows_root=args.legacy_windows_root)
    for seed in seeds:
        for method in methods:
            if args.dry_run:
                controller.run_method_seed(method, seed, checkpoints)
                continue
            run_root, _, _ = controller.namespace(seed)
            run_dir = controller.safe_output(run_root / f"{method}_seed{seed}", "run")
            run_dir.mkdir(parents=True, exist_ok=True)
            lock = run_dir / ".controller.lock"
            try:
                lock.touch(exist_ok=False)
            except FileExistsError as exc:
                raise RuntimeError(f"Run is locked: {lock}. Verify no controller owns this run before clearing a stale lock.") from exc
            try:
                controller.run_method_seed(method, seed, checkpoints)
            finally:
                lock.unlink()
    if args.dry_run:
        report = controller.write_dry_run_report(methods, seeds, checkpoints)
        print(f"DRY_RUN_REPORT={report}")
    print("P1P2_CONTROLLER=PASS" if not args.dry_run else "P1P2_CONTROLLER=DRY_RUN_PLAN_READY")
    return 0


if __name__ == "__main__":
    try: raise SystemExit(main())
    except Exception as exc:
        print(f"P1P2_CONTROLLER_ERROR={type(exc).__name__}: {exc}", file=sys.stderr)
        raise
