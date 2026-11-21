#!/usr/bin/env python3
"""
Train one round of the Student with LoRA: S_t + B_t -> S_{t+1}.

Hyperparameters come from config/experiment_config.json "training" (LoRA r/alpha/dropout/targets,
AdamW, constant lr, no warmup, max_grad_norm, effective batch, 1 epoch, max_seq_len,
completion-only loss). Effective batch = --micro-batch x gradient accumulation.

Loss: token-level mean over all supervised (response) tokens of the effective batch;
prompt tokens are masked. Seeds: torch seed (LoRA init, dropout) = data order seed = --seed.

Pool: the trajectories are looked up in the pool named by the train set ("pool", checked against
"pool_sha256"), so the Task 5 smoke-test train sets still resolve to the preliminary pool; train sets
without that field use --pool (default: official pool v1).

Outputs:
  <adapter-dir>/                 LoRA adapter (safetensors) + tokenizer files
  <adapter-dir>/train_log.json   per-step loss, tokens, time; totals; config used

Usage (from experiments/week2September/manual/):
  python scripts/train_round.py --seed 13 \
      --train-set reports/task5/smoke_test/train_set_seed13.json \
      --adapter-dir models/smoke/student_ckpt_001_smoke_seed13
"""
import argparse
import json
import math
import random
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from student_common import (  # noqa: E402
    CONFIG_PATH, IGNORE_INDEX, MANUAL_DIR, POOL_VERIFIED, add_model_args, check_prompt_template, encode_example,
    environment_info, load_config, load_pool, pick_dtype, sha256_file, student_from_args, write_json,
)


def collate(examples, pad_id):
    width = max(len(e["input_ids"]) for e in examples)
    ids, labels, mask = [], [], []
    for e in examples:
        pad = width - len(e["input_ids"])
        ids.append(e["input_ids"] + [pad_id] * pad)          # right padding for training
        labels.append(e["labels"] + [IGNORE_INDEX] * pad)
        mask.append([1] * len(e["input_ids"]) + [0] * pad)
    return torch.tensor(ids), torch.tensor(labels), torch.tensor(mask)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--train-set", required=True, type=Path, help="JSON with trajectory_ids (select_smoke_train_set.py)")
    ap.add_argument("--adapter-dir", required=True, type=Path)
    ap.add_argument("--init-adapter", default=None, help="continue from an existing adapter (round t > 0)")
    ap.add_argument("--micro-batch", type=int, default=4)
    ap.add_argument("--epochs", type=int, default=None, help="default: config training.epochs_per_round")
    ap.add_argument("--lr", type=float, default=None, help="default: config training.learning_rate")
    ap.add_argument("--no-gradient-checkpointing", action="store_true")
    ap.add_argument("--pool", type=Path, default=None,
                    help="pool for train sets without a 'pool' field (default: official pool v1)")
    ap.add_argument("--legacy-windows-root", help="Explicit archived Windows manual root")
    add_model_args(ap)
    args = ap.parse_args()

    if args.adapter_dir.exists():
        raise FileExistsError(
            f"refusing to train into an existing adapter directory: {args.adapter_dir}; "
            "if it is a complete checkpoint, reuse it; if incomplete, inspect manually"
        )
    check_prompt_template()
    cfg = load_config()
    tc = cfg["training"]
    if tc["loss"].split()[0] != "completion-only" or tc["lr_scheduler"] != "constant" or tc["warmup_steps"] != 0:
        raise ValueError("config training block differs from what this script implements")
    eff_batch = tc["batch_size"]
    if eff_batch % args.micro_batch:
        raise ValueError(f"--micro-batch must divide the effective batch {eff_batch}")
    accum = eff_batch // args.micro_batch
    epochs = args.epochs or tc["epochs_per_round"]
    lr = args.lr or tc["learning_rate"]
    model_name, revision = student_from_args(args, cfg)
    dtype = pick_dtype(torch, args.dtype)

    from peft import LoraConfig, PeftModel, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from capability_eval import hash_path

    if not args.train_set.exists():
        raise FileNotFoundError(args.train_set)
    train_set = json.loads(args.train_set.read_text(encoding="utf-8"))
    if "pool" in train_set:
        if args.legacy_windows_root:
            from p1p2_paths import artifact_path, legacy_root

            pool_path = artifact_path(MANUAL_DIR, train_set["pool"], legacy_root(args.legacy_windows_root))
            if not train_set.get("pool_sha256") or (args.pool and args.pool.resolve() != pool_path):
                raise ValueError("Mapped train-set pool must match the configured pool and have a recorded SHA-256")
        else:
            pool_path = MANUAL_DIR / train_set["pool"]
        if args.pool and args.pool.resolve() != pool_path.resolve():
            # Migrated runs may retain an absolute path from the original host.
            if pool_path.exists() or not train_set.get("pool_sha256"):
                raise ValueError(f"--pool {args.pool} differs from the train set's pool {train_set['pool']}")
            pool_path = args.pool
        if "pool_sha256" in train_set and sha256_file(pool_path) != train_set["pool_sha256"]:
            raise ValueError(f"{pool_path} changed since the train set was drawn")
    else:
        pool_path = args.pool or POOL_VERIFIED
    by_id = {r["trajectory_id"]: r for r in load_pool(pool_path)}
    rows = [by_id[t] for t in train_set["trajectory_ids"]]

    tok = AutoTokenizer.from_pretrained(model_name, revision=revision)
    examples = [encode_example(tok, r["question"], r["raw_generation"]) for r in rows]
    too_long = [r["trajectory_id"] for r, e in zip(rows, examples) if len(e["input_ids"]) > tc["max_seq_len"]]
    if too_long:
        raise ValueError(f"{len(too_long)} examples exceed max_seq_len {tc['max_seq_len']}: {too_long[:3]}")

    torch.manual_seed(args.seed)
    random.seed(args.seed)
    model = AutoModelForCausalLM.from_pretrained(model_name, revision=revision, dtype=dtype)
    if not args.no_gradient_checkpointing:
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
        model.enable_input_require_grads()
    parent_sha256 = hash_path(Path(args.init_adapter)) if args.init_adapter else None
    if args.init_adapter:
        model = PeftModel.from_pretrained(model, args.init_adapter, is_trainable=True)
    else:
        model = get_peft_model(model, LoraConfig(
            r=tc["lora_r"], lora_alpha=tc["lora_alpha"], lora_dropout=tc["lora_dropout"],
            target_modules=tc["lora_target_modules"], bias="none", task_type="CAUSAL_LM",
        ))
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    model.train()
    trainable = [p for p in model.parameters() if p.requires_grad]
    n_trainable = sum(p.numel() for p in trainable)
    opt = torch.optim.AdamW(trainable, lr=lr, betas=(tc["adam_beta1"], tc["adam_beta2"]),
                            weight_decay=tc["weight_decay"])  # fresh optimizer state each round (config)

    order_rng = random.Random(args.seed)  # data_order_seed = training_seed
    log, step, t0 = [], 0, time.time()
    total_sup, total_prompt = 0, 0
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
    for epoch in range(epochs):
        order = list(range(len(examples)))
        order_rng.shuffle(order)
        for start in range(0, len(order), eff_batch):
            eff = [examples[i] for i in order[start: start + eff_batch]]
            n_sup = sum(e["n_supervised"] for e in eff)
            loss_sum = 0.0
            opt.zero_grad(set_to_none=True)
            for m in range(0, len(eff), args.micro_batch):
                ids, labels, mask = (x.to(device) for x in collate(eff[m: m + args.micro_batch], tok.pad_token_id))
                logits = model(input_ids=ids, attention_mask=mask).logits[:, :-1]
                tgt = labels[:, 1:]
                sel = tgt != IGNORE_INDEX  # upcast only supervised positions (saves memory)
                tok_loss = torch.nn.functional.cross_entropy(logits[sel].float(), tgt[sel], reduction="sum")
                (tok_loss / n_sup).backward()
                loss_sum += tok_loss.item()
            grad_norm = torch.nn.utils.clip_grad_norm_(trainable, tc["max_grad_norm"]).item()
            opt.step()
            step += 1
            total_sup += n_sup
            total_prompt += sum(e["n_prompt"] for e in eff)
            log.append({"step": step, "epoch": epoch, "loss": loss_sum / n_sup, "grad_norm": grad_norm,
                        "n_examples": len(eff), "supervised_tokens": n_sup, "lr": lr,
                        "elapsed_s": round(time.time() - t0, 1)})
            print(f"step {step:3d}  loss {loss_sum / n_sup:.4f}  grad_norm {grad_norm:.3f}  "
                  f"tokens {n_sup}  {time.time() - t0:.0f}s", flush=True)
            if not math.isfinite(loss_sum):
                raise RuntimeError("non-finite loss")

    args.adapter_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(args.adapter_dir)
    tok.save_pretrained(args.adapter_dir)
    write_json(args.adapter_dir / "train_log.json", {
        "checkpoint_parent": args.init_adapter or "student_ckpt_000",
        "checkpoint_parent_sha256": parent_sha256,
        "seed": args.seed, "data_order_seed": args.seed,
        "train_set": str(args.train_set), "train_set_sha256": sha256_file(args.train_set),
        "pool": str(pool_path), "pool_sha256": sha256_file(pool_path),
        "n_examples": len(examples), "epochs": epochs, "steps": step,
        "effective_batch": eff_batch, "micro_batch": args.micro_batch, "grad_accum": accum,
        "learning_rate": lr, "lr_from_config": lr == tc["learning_rate"],
        "epochs_from_config": epochs == tc["epochs_per_round"],
        "model": model_name, "revision": revision, "dtype": str(dtype).replace("torch.", ""),
        "gradient_checkpointing": not args.no_gradient_checkpointing,
        "trainable_parameters": n_trainable,
        "cumulative_training_tokens": total_sup,
        "prompt_tokens_masked": total_prompt,
        "trajectory_tokens": sum(e["n_traj"] for e in examples) * epochs,
        "beta_round_tokens_config": cfg["budget"]["beta_round_tokens"],
        "elapsed_seconds": round(time.time() - t0, 1),
        "peak_gpu_memory_gb": round(torch.cuda.max_memory_allocated() / 2**30, 2) if torch.cuda.is_available() else None,
        "peak_gpu_reserved_bytes": torch.cuda.max_memory_reserved() if torch.cuda.is_available() else None,
        "config_sha256": sha256_file(CONFIG_PATH),
        "environment": environment_info(torch),
        "steps_log": log,
    })
    print(f"saved adapter -> {args.adapter_dir}  ({step} steps, {total_sup} supervised tokens)")


if __name__ == "__main__":
    main()
