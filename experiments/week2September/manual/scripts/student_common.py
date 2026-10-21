"""
Shared helpers for Student evaluation, training and NLL scoring (Task 5 smoke test, reused in Task 7).

Everything that must be identical across scripts lives here:
  - paths and frozen values read from config/experiment_config.json;
  - prompt construction (prompt v1, Qwen chat template), shared with Teacher generation;
  - tokenization of (prompt, response) pairs with the response-only loss mask;
  - model loading (base model at the pinned revision, optional LoRA adapter) and dtype policy.

Run all scripts from experiments/week2September/manual/.
"""

import ast
import hashlib
import json
import platform
import sys
from pathlib import Path

MANUAL_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = MANUAL_DIR / "config" / "experiment_config.json"
GSM8K_TRAIN = MANUAL_DIR / "data" / "raw" / "gsm8k_train.jsonl"
DEV_IDS = MANUAL_DIR / "splits" / "d_dev_ids.txt"
TEST_IDS = MANUAL_DIR / "splits" / "d_test_ids.txt"
# Official pool (Task 6, task6_decisions.md): default for Task 7 onwards.
POOL_VERIFIED = MANUAL_DIR / "trajectory" / "pool" / "pool_v1_verified.jsonl"
# Preliminary pool (batch_100, HF): used by the Task 5 smoke test only; pass it explicitly to reproduce it.
POOL_PRELIMINARY = MANUAL_DIR / "trajectory" / "pool" / "batch_100_teacher_verified.jsonl"
SMOKE_DIR = MANUAL_DIR / "reports" / "task5" / "smoke_test"

# Same template the Teacher was prompted with (prompt v1). Copied verbatim from
# scripts/generate_teacher_trajectories_batch.py:PROMPT_TEMPLATE; check_prompt_template() guards drift.
PROMPT_TEMPLATE = """Solve the following math problem.

Provide a concise but complete reasoning trace followed by the final answer.

Problem:
{question}

Return exactly:

REASONING:
<step-by-step reasoning>

ANSWER:
<final answer>"""

IGNORE_INDEX = -100


def check_prompt_template():
    """Fail if the Teacher generation script's template differs from ours."""
    src = (MANUAL_DIR / "scripts" / "generate_teacher_trajectories_batch.py").read_text(encoding="utf-8")
    if 'PROMPT_TEMPLATE = """' + PROMPT_TEMPLATE + '"""' not in src:
        raise RuntimeError("PROMPT_TEMPLATE differs from generate_teacher_trajectories_batch.py")


def load_config():
    with CONFIG_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_jsonl(path):
    with Path(path).open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def append_jsonl(path, row):
    with Path(path).open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_json(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def load_dev_rows():
    """D_dev problems in d_dev_ids.txt order: problem_id, question, ground_truth."""
    ids = [x.strip() for x in DEV_IDS.read_text(encoding="utf-8").splitlines() if x.strip()]
    by_id = {r["problem_id"]: r for r in read_jsonl(GSM8K_TRAIN)}
    missing = [i for i in ids if i not in by_id]
    if missing:
        raise ValueError(f"{len(missing)} D_dev ids not found in {GSM8K_TRAIN}")
    return [by_id[i] for i in ids]


def load_pool(path=POOL_VERIFIED):
    """Verified pool (default: official pool v1); every row must be verification_status == valid."""
    rows = read_jsonl(path)
    for r in rows:
        meta = r["metadata"]
        if isinstance(meta, str):  # some preliminary-pool rows store metadata as a Python-repr string
            meta = ast.literal_eval(meta)
            r["metadata"] = meta
        if meta.get("verification_status") != "valid":
            raise ValueError(f"non-valid trajectory in pool: {r['trajectory_id']}")
    held_out = set(DEV_IDS.read_text(encoding="utf-8").split()) | set(TEST_IDS.read_text(encoding="utf-8").split())
    leaked = sorted({r["problem_id"] for r in rows} & held_out)
    if leaked:
        raise ValueError(f"pool problems found in D_dev/D_test: {leaked[:5]}")
    return rows


def build_prompt(tokenizer, question):
    """Chat-formatted prompt v1, ending with the assistant generation header."""
    messages = [{"role": "user", "content": PROMPT_TEMPLATE.format(question=question)}]
    return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)


def response_text(raw_generation):
    """Training/scoring target: the Teacher's raw output (REASONING: ... ANSWER: ...)."""
    return raw_generation.strip()


def encode_example(tokenizer, question, raw_generation, add_eos=True):
    """
    Token ids for prompt + response, labels masked (-100) on the prompt.

    Prompt and response are tokenized separately, which is exactly what the model sees at
    generation time. The end-of-turn token is appended to the supervised part when add_eos,
    so the Student learns to stop. n_traj counts only the trajectory tokens (no end-of-turn),
    matching L_bar in the config.
    """
    prompt_ids = tokenizer(build_prompt(tokenizer, question), add_special_tokens=False)["input_ids"]
    traj_ids = tokenizer(response_text(raw_generation), add_special_tokens=False)["input_ids"]
    resp_ids = traj_ids + ([end_of_turn_id(tokenizer)] if add_eos else [])
    input_ids = prompt_ids + resp_ids
    labels = [IGNORE_INDEX] * len(prompt_ids) + resp_ids
    return {
        "input_ids": input_ids,
        "labels": labels,
        "n_prompt": len(prompt_ids),
        "n_traj": len(traj_ids),
        "n_supervised": len(resp_ids),
    }


def end_of_turn_id(tokenizer):
    tid = tokenizer.convert_tokens_to_ids("<|im_end|>")
    if tid is None or tid == tokenizer.unk_token_id:
        raise ValueError("tokenizer has no <|im_end|> token")
    return tid


def pick_dtype(torch, requested="auto"):
    """bf16 when the GPU supports it (config), otherwise fp32 (fp16 is avoided: Qwen2.5 can overflow)."""
    if requested != "auto":
        return {"bf16": torch.bfloat16, "fp32": torch.float32, "fp16": torch.float16}[requested]
    if torch.cuda.is_available() and torch.cuda.is_bf16_supported():
        return torch.bfloat16
    return torch.float32


def load_tokenizer(model_name, revision):
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(model_name, revision=revision)
    tok.padding_side = "left"
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    return tok


def load_model(model_name, revision, dtype, adapter=None, merge=True):
    """Base Student at the pinned revision, optionally with a LoRA adapter (merged for speed)."""
    import torch
    from transformers import AutoModelForCausalLM
    model = AutoModelForCausalLM.from_pretrained(model_name, revision=revision, dtype=dtype)
    if adapter:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, adapter)
        if merge:
            model = model.merge_and_unload()
    model.to("cuda" if torch.cuda.is_available() else "cpu")
    model.eval()
    return model


def student_from_args(args, cfg):
    """(model_name, revision) honouring --model overrides used only for pipeline tests."""
    if args.model:
        return args.model, args.revision
    return cfg["student"]["model"], cfg["student"]["revision"]


def environment_info(torch):
    import transformers
    info = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "torch": torch.__version__,
        "transformers": transformers.__version__,
        "cuda": torch.version.cuda,
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "bf16_supported": bool(torch.cuda.is_available() and torch.cuda.is_bf16_supported()),
    }
    try:
        import peft
        info["peft"] = peft.__version__
    except ImportError:
        pass
    return info


def add_model_args(parser):
    parser.add_argument("--model", default=None,
                        help="override the Student model (pipeline tests only; default: config student.model)")
    parser.add_argument("--revision", default=None, help="revision for --model")
    parser.add_argument("--dtype", default="auto", choices=["auto", "bf16", "fp32", "fp16"])
