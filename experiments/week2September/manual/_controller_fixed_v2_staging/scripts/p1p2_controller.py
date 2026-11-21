#!/usr/bin/env python3
"""Unified, no-overwrite controller for P2 B2-B5 and P1/P2 methods.

User-facing rounds are checkpoint numbers: 1 means train/evaluate S1.
P1 selector rounds are 1-based; select_round.py rounds are 0-based.
"""
from __future__ import annotations
import argparse, hashlib, json, os, shutil, subprocess, sys, tempfile, time
from pathlib import Path
from typing import Any, Callable

METHODS = ("B2", "B3", "B4", "B5", "P1-DEFICIT", "P1P2")
P1_METHODS = {"P1-DEFICIT", "P1P2"}
P2_METHODS = {"B2", "B3", "B4", "B5"}
REGISTERED_SEEDS = {13, 42, 2026}
FORBIDDEN = (Path("runs/main"), Path("models/task7"))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    if path.is_file():
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    if not path.is_dir():
        raise FileNotFoundError(path)
    files = sorted(x for x in path.rglob("*") if x.is_file())
    if not files:
        raise ValueError(f"Empty checkpoint directory: {path}")
    for item in files:
        h.update(item.relative_to(path).as_posix().encode())
        h.update(b"\0")
        h.update(sha256(item).encode())
        h.update(b"\n")
    return h.hexdigest()


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


def atomic_json(path: Path, value: Any, *, replace: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not replace:
        raise FileExistsError(f"Refusing to overwrite: {path}")
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(value, f, ensure_ascii=False, indent=2)
            f.write("\n")
            f.flush(); os.fsync(f.fileno())
        if replace:
            os.replace(tmp, path)
        else:
            os.link(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


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
                 runner: Callable[[list[str]], None] | None = None):
        self.root = root.resolve()
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

    def _validate_root_inputs(self) -> None:
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
        pool_hash = sha256(self.pool)
        # Do not hard-code a collaborator-specific digest. The active pool hash
        # is canonicalized by verifying the token summary against these exact bytes.
        summary = read_json(self.tokens.with_suffix(".summary.json"))
        if summary.get("pool_sha256") != pool_hash:
            raise ValueError("Token summary does not match verified pool")
        dev = [x.strip() for x in self.dev_ids.read_text(encoding="utf-8-sig").splitlines() if x.strip()]
        if len(dev) != 500 or len(set(dev)) != 500:
            raise ValueError("D_dev must contain exactly 500 unique IDs")
        for required in (self.gold_manifest, self.gold_labels, self.approval):
            if not required.is_file():
                raise FileNotFoundError(f"Required Gold input missing: {required}")

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
        return (len(rows) == 500 and len(set(ids)) == 500 and set(ids) == expected
                and tag_ok and summary_ok)

    def _valid_nll(self, path: Path, tag: str) -> bool:
        summary_path = path.with_suffix(".summary.json")
        if not path.is_file() or not summary_path.is_file(): return False
        rows = read_jsonl(path); summary = read_json(summary_path)
        token_rows = read_jsonl(self.tokens)
        expected = {r["trajectory_id"]: r["response_tokens"] for r in token_rows}
        return (summary.get("checkpoint") == tag and summary.get("pool_sha256") == sha256(self.pool)
                and summary.get("n_trajectories") == len(expected)
                and len(rows) == len(expected) and len({r.get("trajectory_id") for r in rows}) == len(expected)
                and {r.get("trajectory_id") for r in rows} == set(expected)
                and all(r.get("checkpoint") == tag and r.get("n_tokens") == expected.get(r.get("trajectory_id")) for r in rows))

    def _ensure_nll(self, run_dir: Path, ckpt: int, adapter: Path | None, *, tag_override: str | None = None) -> Path:
        tag = tag_override or f"S{ckpt}"
        out_dir = run_dir / tag
        out = out_dir / "nll.jsonl"
        out_key = str(out.resolve()).casefold()
        if self._valid_nll(out, tag):
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
        self.generated_nll.add(out_key)
        return out

    def _ensure_selection_p1(self, method: str, seed: int, round_no: int, run_dir: Path,
                             report_dir: Path, state_path: Path, nll_path: Path | None) -> tuple[Path, Path]:
        out_dir = run_dir / f"round_{round_no:03d}"
        train, log = out_dir / "train_set.json", out_dir / "selection_log.jsonl"
        if train.is_file() and log.is_file():
            if not self.resume and not self.dry_run and target_ckpt != 1:
                raise FileExistsError(f"P1 selection artifacts already exist; use --resume: {out_dir}")
            data = read_json(train)
            recorded_state = Path(str(data.get("state_file", "")))
            if not recorded_state.is_absolute():
                recorded_state = (self.root / recorded_state).resolve()
            if not recorded_state.is_file():
                raise FileNotFoundError(f"Existing P1 selection references missing state: {recorded_state}")
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
                recorded_nll = Path(str(data.get("nll_file", "")))
                if not recorded_nll.is_absolute():
                    recorded_nll = (self.root / recorded_nll).resolve()
                if not self._valid_nll(recorded_nll, f"S{round_no-1}") or data.get("nll_sha256") != sha256(recorded_nll):
                    raise RuntimeError("P1P2 historical selection NLL fingerprint/coverage mismatch")
            log_rows = read_jsonl(log)
            if len(log_rows) != len(read_jsonl(self.pool)):
                raise RuntimeError(f"Existing P1 selection log does not cover the full verified pool: {log}")
            selected_ids = {r.get("trajectory_id") for r in log_rows if r.get("selected") is True}
            if selected_ids != set(data.get("trajectory_ids", [])):
                raise RuntimeError(f"Existing P1 train-set IDs differ from selection log: {train}")
            if any(r.get("method") != method or r.get("seed") != seed or r.get("round") != round_no
                   or r.get("source_checkpoint") != f"S{round_no-1}" for r in log_rows):
                raise RuntimeError(f"Existing P1 selection-log lineage mismatch: {log}")
            print(f"[REUSE] P1 selection round {round_no}: preserving validated train set/log")
            return train, log
        if train.exists() or log.exists():
            raise RuntimeError(f"Incomplete P1 selection pair exists; refusing overwrite: {out_dir}")
        cmd = [self.py, self.scripts / "p1p2_selector.py", "--method", method, "--seed", str(seed),
               "--round", str(round_no), "--state", state_path, "--out-dir", out_dir,
               "--pool", self.pool, "--tokens", self.tokens, "--d-pool", self.d_pool, "--config", self.config]
        for previous in range(1, round_no): cmd += ["--previous-train-set", run_dir / f"round_{previous:03d}" / "train_set.json"]
        if nll_path is not None: cmd += ["--nll", nll_path]
        self.emit(f"select_{method}_round_{round_no}", cmd, outputs=[train, log])
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
        out_dir = report_dir / "capability_sidecars" / run_id
        train_log = checkpoint / "train_log.json"
        checkpoint_log = run_dir / "checkpoint_log.jsonl"
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
        return out_dir

    def _state(self, sidecar: Path, method: str, seed: int, selection_round: int, report_dir: Path) -> Path:
        out = report_dir / "capability_state" / f"{method}_seed{seed}" / f"selection_round_{selection_round:03d}.json"
        cmd = [self.py, self.scripts / "p1p2_capability_state.py", "--sidecar-dir", sidecar,
               "--target-method", method, "--target-seed", str(seed), "--out", out]
        self.emit(f"capability_state_{method}_seed{seed}_selection_{selection_round}", cmd, outputs=[out])
        return out

    def _checkpoint_log(self, run_dir: Path, method: str, seed: int, ckpt: int,
                        train_set: Path, model_dir: Path, train_log: Path) -> Path:
        path = run_dir / "checkpoint_log.jsonl"
        row = {"record_type": "checkpoint", "checkpoint": f"S{ckpt}", "parent_checkpoint": f"S{ckpt-1}",
               "round": ckpt, "method": method, "training_seed": seed, "data_order_seed": seed,
               "train_set": str(train_set), "train_set_sha256": sha256(train_set),
               "checkpoint_path": str(model_dir), "checkpoint_sha256": sha256(model_dir),
               "train_log": str(train_log), "train_log_sha256": sha256(train_log)}
        if path.exists():
            rows = read_jsonl(path)
            existing = [r for r in rows if r.get("checkpoint") == f"S{ckpt}"]
            if existing:
                if existing[0] != row: raise RuntimeError(f"Checkpoint log provenance collision: {path} S{ckpt}")
                return path
            with path.open("a", encoding="utf-8") as f: f.write(json.dumps(row, ensure_ascii=False) + "\n")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("x", encoding="utf-8") as f: f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return path

    def _try_b4_s1_alias(self, seed: int, b4_train_set: Path, b4_model_dir: Path,
                         runs_root: Path, models_root: Path) -> bool:
        """Reuse B5 S1 only after exact selection and training provenance checks."""
        b5_run = runs_root / f"B5_seed{seed}"
        b5_train = b5_run / "round_000" / "train_set.json"
        b5_model = models_root / f"B5_seed{seed}" / "student_ckpt_001"
        b5_log = b5_model / "train_log.json"
        if not (b5_train.is_file() and b5_log.is_file() and b5_model.is_dir()):
            return False
        own, other, train_log = read_json(b4_train_set), read_json(b5_train), read_json(b5_log)
        required_equal = (own.get("trajectory_ids") == other.get("trajectory_ids")
                          and own.get("pool_sha256") == other.get("pool_sha256")
                          and own.get("config_sha256") == other.get("config_sha256")
                          and own.get("nll_sha256") == other.get("nll_sha256")
                          and own.get("source_checkpoint") == "S0"
                          and other.get("source_checkpoint") == "S0")
        train_provenance = (train_log.get("seed") == seed
                            and train_log.get("checkpoint_parent") == "student_ckpt_000"
                            and train_log.get("train_set_sha256") == sha256(b5_train))
        if not required_equal or not train_provenance:
            raise RuntimeError("B4/B5 S1 alias rejected: selection IDs, source provenance, or B5 train provenance differ")
        if b4_model_dir.exists():
            raise FileExistsError(f"B4 S1 adapter destination already exists: {b4_model_dir}")
        if self.dry_run:
            self.actions.append({"stage": "reuse_B5_S1_for_B4_S1_after_provenance_check",
                                 "command": ["CONTROLLER_INTERNAL", "copy_verified_B5_S1_adapter", str(b5_model), str(b4_model_dir)],
                                 "outputs": [str(b4_model_dir)]})
        else:
            b4_model_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(b5_model, b4_model_dir)
        print(f"[ALIAS] B4 seed {seed} S1 reuses B5 S1 after exact ID/provenance verification")
        return True

    def run_method_seed(self, method: str, seed: int, checkpoints: list[int]) -> None:
        runs_root, models_root, reports_root = self.namespace(seed)
        run_dir = self.safe_output(runs_root / f"{method}_seed{seed}", "run")
        model_run = self.safe_output(models_root / f"{method}_seed{seed}", "model")
        run_dir.mkdir(parents=True, exist_ok=True) if not self.dry_run else None
        model_run.mkdir(parents=True, exist_ok=True) if not self.dry_run else None
        # S0 reference is immutable and shared; it is never trained by this controller.
        state_s0 = None
        if method in P1_METHODS:
            if not self.s0_sidecar.is_dir() or not self.s0_reference.is_file():
                raise FileNotFoundError("P1 requires validated SHARED S0 sidecar and s0_base_model_reference.json")
            state_s0 = self._state(self.s0_sidecar, method, seed, 1, reports_root)
        for ckpt in checkpoints:
            p2_round = ckpt - 1
            round_no = ckpt
            model_dir = model_run / f"student_ckpt_{ckpt:03d}"
            prediction = run_dir / f"S{ckpt}" / "eval_dev.jsonl"
            adapter_parent = model_run / f"student_ckpt_{ckpt-1:03d}"
            if ckpt == 1:
                adapter_parent = None
            if model_dir.exists():
                train_log_existing = model_dir / "train_log.json"
                if not ((self.resume or self.dry_run) and train_log_existing.is_file()):
                    raise FileExistsError(f"Adapter directory collision or interrupted training; refusing to write: {model_dir}")
                if not any(model_dir.glob("adapter_model.*")) and not (model_dir / "adapter_model.safetensors").is_file():
                    raise RuntimeError(f"Existing adapter lacks adapter weights: {model_dir}")
            else:
                train_set = run_dir / (f"round_{round_no:03d}" if method in P1_METHODS else f"round_{p2_round:03d}") / "train_set.json"
                selection_log = train_set.with_name("selection_log.jsonl")
                if method == "P1-DEFICIT":
                    nll_path = None
                elif method == "P1P2":
                    existing_round1 = run_dir / "round_001" / "train_set.json"
                    if ckpt == 1 and existing_round1.is_file():
                        recorded = read_json(existing_round1).get("nll_file")
                        if not recorded:
                            raise RuntimeError("Existing P1P2 round-1 train set has no recorded S0 NLL path")
                        nll_path = Path(recorded)
                        if not nll_path.is_absolute(): nll_path = (self.root / nll_path).resolve()
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
                    state_path = state_s0 if ckpt == 1 else reports_root / "capability_state" / f"{method}_seed{seed}" / f"selection_round_{ckpt:03d}.json"
                    if ckpt > 1 and not state_path.is_file() and not self.dry_run:
                        raise FileNotFoundError(f"Missing preceding checkpoint capability state: {state_path}")
                    train_set, selection_log = self._ensure_selection_p1(method, seed, ckpt, run_dir, reports_root, state_path, nll_path)
                else:
                    train_set, selection_log = self._ensure_selection_p2(method, seed, ckpt, run_dir, nll_path)
                aliased = False
                if method == "B4" and ckpt == 1:
                    aliased = self._try_b4_s1_alias(seed, train_set, model_dir, runs_root, models_root)
                if not aliased:
                    cmd = [self.py, self.scripts / "train_round.py", "--seed", str(seed), "--train-set", train_set,
                           "--adapter-dir", model_dir, "--micro-batch", str(self.micro_batch), "--dtype", self.dtype]
                    if adapter_parent is not None: cmd += ["--init-adapter", adapter_parent]
                    self.emit(f"train_{method}_seed{seed}_S{ckpt}", cmd, outputs=[model_dir])
            # Evaluate dev only. Never invoke run_experiment.py from this controller.
            prediction_tag = f"{method}_seed{seed}_S{ckpt}"
            if not self._valid_prediction(prediction, prediction_tag):
                if prediction.exists():
                    # eval_student is resumable; permit continuation only under --resume.
                    if not self.resume:
                        raise FileExistsError(f"Existing prediction requires --resume: {prediction}")
                    old_rows = read_jsonl(prediction)
                    ids = [r.get("problem_id") for r in old_rows]
                    if len(ids) != len(set(ids)):
                        raise RuntimeError(f"Duplicate IDs in partial prediction; preserve for audit: {prediction}")
                cmd = [self.py, self.scripts / "eval_student.py", "--tag", f"{method}_seed{seed}_S{ckpt}",
                       "--split", "dev", "--out", prediction, "--backend", self.backend, "--dtype", self.dtype]
                if self.eval_batch is not None: cmd += ["--batch-size", str(self.eval_batch)]
                cmd += ["--adapter", model_dir]
                self.emit(f"eval_dev_{method}_seed{seed}_S{ckpt}", cmd, outputs=[prediction])
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
                if train_log.is_file():
                    self._checkpoint_log(run_dir, method, seed, ckpt, train_set, model_dir, train_log)
                elif self.dry_run:
                    self.actions.append({"stage": f"checkpoint_log_{method}_seed{seed}_S{ckpt}",
                                         "command": ["CONTROLLER_INTERNAL", "publish_checkpoint_log"],
                                         "outputs": [str(run_dir / "checkpoint_log.jsonl")]})
                if not self._valid_prediction(prediction, prediction_tag) and not self.dry_run:
                    raise RuntimeError(f"D_dev evaluation incomplete; hook is blocked: {prediction}")
                shared_group = None
                if method == "B4" and ckpt == 1:
                    b5_model = models_root / f"B5_seed{seed}" / "student_ckpt_001"
                    if b5_model.is_dir() and sha256(b5_model) == sha256(model_dir):
                        shared_group = "B4_B5_seed_scoped_S1"
                sidecar = self._hook(method, seed, ckpt, prediction, model_dir, run_dir, model_dir, reports_root, train_set, selection_log, shared_group)
                if method in P1_METHODS:
                    state_s0 = self._state(sidecar, method, seed, ckpt + 1, reports_root)

    def write_dry_run_report(self, methods: list[str], seeds: list[int], checkpoints: list[int]) -> Path:
        _, _, report_root = self.namespace(seeds[0])
        out = report_root / "integration_tests" / f"dry_run_{int(time.time())}.json"
        payload = {"schema_version": "p1p2.controller-dry-run.v1", "dry_run": True,
                   "methods": methods, "seeds": seeds, "target_checkpoints": checkpoints,
                   "round_mapping": {f"S{k}": {"p1_selector_round": k, "p2_select_round_index": k-1} for k in checkpoints},
                   "actions": self.actions, "frozen_config_sha256": sha256(self.config),
                   "pool_sha256": sha256(self.pool), "note": "No model training/checkpoint writes were executed."}
        if self.dry_run:
            # Dry-run may write only to the integration_tests report namespace.
            if out.exists(): raise FileExistsError(out)
            atomic_json(out, payload)
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
    rg.add_argument("--from-checkpoint", choices=("S0","S1","S2"))
    p.add_argument("--to-checkpoint", choices=("S1","S2","S3"))
    p.add_argument("--resume", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--manual-root", type=Path, default=Path(__file__).resolve().parents[1])
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
                            nll_batch=args.nll_batch, eval_batch=args.eval_batch, dtype=args.dtype)
    # Stable execution order makes B4/B5 shared-S1 verification possible in a later audited extension.
    execution_methods = sorted(methods, key=lambda m: (0 if m == "B5" else 1, methods.index(m)))
    for seed in seeds:
        for method in execution_methods:
            controller.run_method_seed(method, seed, checkpoints)
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
