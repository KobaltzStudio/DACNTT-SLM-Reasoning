"""One frozen LoRA optimizer step on eight synthetic 1024-token examples."""
import importlib.metadata
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import torch
from transformers import AutoTokenizer
from huggingface_hub import try_to_load_from_cache

root = Path(__file__).resolve().parents[4]
evidence = Path(__file__).resolve().parent
sys.path.insert(0, str(root / "scripts"))
from student_common import encode_example

report = {"status": "FAILED"}
try:
    config = json.loads((root / "config/experiment_config.json").read_text(encoding="utf-8"))
    student, train = config["student"], config["training"]
    assert train["max_seq_len"] == 1024 and train["batch_size"] == 8
    assert train["epochs_per_round"] == 1 and train["precision"] == "bf16" and train["method"] == "LoRA"
    assert torch.cuda.is_available() and torch.cuda.is_bf16_supported()
    free, total = torch.cuda.mem_get_info()
    report.update(gpu=torch.cuda.get_device_name(), gpu_free_bytes=free, gpu_total_bytes=total,
                  disk_free_bytes=shutil.disk_usage(root).free, cuda=torch.version.cuda,
                  versions={p: importlib.metadata.version(p) for p in ("torch", "transformers", "peft", "accelerate", "PyYAML", "safetensors")})
    assert free >= 5 * 2**30, "Insufficient free VRAM for starting the bounded probe"
    assert report["disk_free_bytes"] >= 2 * 2**30
    weights = try_to_load_from_cache(student["model"], "model.safetensors", revision=student["revision"])
    assert isinstance(weights, str) and Path(weights).stat().st_size > 0
    report["student"] = {**student, "cached_weights": weights}
    tokenizer = AutoTokenizer.from_pretrained(student["model"], revision=student["revision"], local_files_only=True)
    trajectories = {row["trajectory_id"]: row for row in
                    map(json.loads, (root / "trajectory/pool/pool_v1_verified.jsonl").read_text(encoding="utf-8").splitlines())}
    lengths = {key: len(encode_example(tokenizer, row["question"], row["raw_generation"])["input_ids"])
               for key, row in trajectories.items()}
    selection = json.loads((root / "runs/p1p2_integration/P1-DEFICIT_seed13/round_001/train_set.json").read_text(encoding="utf-8"))
    picked = sorted(lengths[key] for key in selection["trajectory_ids"])
    report.update(round_1_lengths={"count": len(picked), "min": picked[0], "median": picked[len(picked)//2], "max": picked[-1]},
                  pool_lengths={"count": len(lengths), "max": max(lengths.values()),
                                "above_1024": sum(n > 1024 for n in lengths.values())})
    assert max(lengths.values()) <= 1024, "Eligible pool has overlength trajectories"
    question = "What is two plus three?"
    target = train["max_seq_len"]
    raw = next(text for n in range(target, 0, -1)
               if len(encode_example(tokenizer, question, text := (" repeat" * n).strip())["input_ids"]) == target)
    report["probe_sequence_tokens"] = target
    with tempfile.TemporaryDirectory(prefix="max_length_probe_", dir=evidence) as tmp:
        fixture = Path(tmp)
        pool, dataset, adapter = fixture / "pool.jsonl", fixture / "train.json", fixture / "adapter"
        rows = [{"trajectory_id": f"memory-probe-{i}", "problem_id": f"memory-probe-{i}", "question": question,
                 "raw_generation": raw, "metadata": {"verification_status": "valid"}} for i in range(train["batch_size"])]
        pool.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        dataset.write_text(json.dumps({"trajectory_ids": [row["trajectory_id"] for row in rows]}), encoding="utf-8")
        cmd = [sys.executable, "-u", "-B", "scripts/train_round.py", "--seed", "13", "--train-set", str(dataset),
               "--adapter-dir", str(adapter), "--pool", str(pool), "--micro-batch", "1", "--dtype", "bf16"]
        report["command"] = cmd
        with (evidence / "max_length_train.log").open("xb") as log:
            result = subprocess.run(cmd, cwd=root, stdout=log, stderr=subprocess.STDOUT, timeout=300)
        report["exit"] = result.returncode
        result.check_returncode()
        training = json.loads((adapter / "train_log.json").read_text(encoding="utf-8"))
        assert training["steps"] == 1 and training["grad_accum"] == 8 and training["effective_batch"] == 8
        assert math.isfinite(training["steps_log"][-1]["loss"])
        report.update(status="DONE", steps=1, effective_batch=8,
                      loss=training["steps_log"][-1]["loss"], seconds=training["elapsed_seconds"],
                      peak_allocated_gib=training["peak_gpu_memory_gb"], peak_reserved_bytes=training["peak_gpu_reserved_bytes"])
except Exception as exc:
    report["error"] = f"{type(exc).__name__}: {exc}"
    raise
finally:
    with (evidence / "max_length_probe.json").open("x", encoding="utf-8") as output:
        json.dump(report, output, indent=2)
    print(json.dumps(report), flush=True)
