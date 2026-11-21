from pathlib import Path
import hashlib
import sys

HERE = Path(__file__).resolve().parent
PIPELINE = HERE / "run_b4_b5.py"

if not PIPELINE.exists():
    raise FileNotFoundError(PIPELINE)

original_bytes = PIPELINE.read_bytes()
source = original_bytes.decode("utf-8")

if "LINEAGE_VALIDATION_V1" in source:
    raise RuntimeError("PATCH_ALREADY_APPLIED: refusing to patch twice")

lines = source.splitlines(keepends=True)

config_anchor = (
    "raise RuntimeError('experiment config does not match "
    "the frozen v2 B4/B5 protocol')"
)

config_matches = [
    i for i, line in enumerate(lines)
    if config_anchor in line
]

if len(config_matches) != 1:
    raise RuntimeError(
        f"EXPECTED_ONE_CONFIG_ANCHOR_FOUND_{len(config_matches)}"
    )

resume_start_matches = [
    i for i, line in enumerate(lines)
    if "logged=json.loads(train_log.read_text(encoding='utf-8'))" in line
]

resume_end_matches = [
    i for i, line in enumerate(lines)
    if "print(f'[RESUME] Reusing completed adapter" in line
]

if len(resume_start_matches) != 1:
    raise RuntimeError(
        f"EXPECTED_ONE_RESUME_START_FOUND_{len(resume_start_matches)}"
    )

if len(resume_end_matches) != 1:
    raise RuntimeError(
        f"EXPECTED_ONE_RESUME_END_FOUND_{len(resume_end_matches)}"
    )

config_index = config_matches[0]
resume_start = resume_start_matches[0]
resume_end = resume_end_matches[0]

if resume_end < resume_start:
    raise RuntimeError("INVALID_RESUME_BLOCK_ORDER")

if not any("cfg=json.loads(a.config.read_text" in line for line in lines[:config_index]):
    raise RuntimeError("CONFIG_LOAD_ANCHOR_NOT_FOUND")

if not any("if adapter_out.exists():" in line for line in lines):
    raise RuntimeError("ADAPTER_RESUME_BRANCH_NOT_FOUND")

if not any("cmd += ['--init-adapter',parent]" in line for line in lines):
    raise RuntimeError("PARENT_ADAPTER_ARGUMENT_NOT_FOUND")

config_indent = len(lines[config_index]) - len(lines[config_index].lstrip())

config_patch = [
    "\n",
    " " * config_indent + "# LINEAGE_VALIDATION_V1\n",
    " " * config_indent + "if a.micro_batch <= 0:\n",
    " " * (config_indent + 4) + "raise ValueError('--micro-batch must be a positive integer')\n",
    " " * config_indent + "effective_batch = int(cfg['training']['batch_size'])\n",
    " " * config_indent + "if effective_batch <= 0 or effective_batch % a.micro_batch != 0:\n",
    " " * (config_indent + 4) + "raise ValueError(\n",
    " " * (config_indent + 8) + "f'--micro-batch={a.micro_batch} must be positive and divide '\n",
    " " * (config_indent + 8) + "f'effective_batch={effective_batch}'\n",
    " " * (config_indent + 4) + ")\n",
    " " * config_indent + "grad_accum = effective_batch // a.micro_batch\n",
    " " * config_indent + "print(\n",
    " " * (config_indent + 4) + "f'[CONFIG] method={method} seed={seed} round={rnd} '\n",
    " " * (config_indent + 4) + "f'effective_batch={effective_batch} '\n",
    " " * (config_indent + 4) + "f'micro_batch={a.micro_batch} grad_accum={grad_accum}',\n",
    " " * (config_indent + 4) + "flush=True,\n",
    " " * config_indent + ")\n",
]

resume_indent = len(lines[resume_start]) - len(lines[resume_start].lstrip())

resume_patch_text = [
    " " * resume_indent + "logged = json.loads(train_log.read_text(encoding='utf-8'))\n",
    " " * resume_indent + "expected_train_hash = __import__('hashlib').sha256(train_set.read_bytes()).hexdigest()\n",
    " " * resume_indent + "if logged.get('train_set_sha256') != expected_train_hash:\n",
    " " * (resume_indent + 4) + "raise RuntimeError(f'existing checkpoint has a different train set: {adapter_out}')\n",
    " " * resume_indent + "if int(logged.get('seed', -1)) != seed:\n",
    " " * (resume_indent + 4) + "raise RuntimeError(f'checkpoint seed mismatch: expected={seed}, found={logged.get(\"seed\")}')\n",
    " " * resume_indent + "if int(logged.get('effective_batch', -1)) != effective_batch:\n",
    " " * (resume_indent + 4) + "raise RuntimeError(f'checkpoint effective batch mismatch: expected={effective_batch}, found={logged.get(\"effective_batch\")}')\n",
    " " * resume_indent + "if int(logged.get('micro_batch', -1)) != a.micro_batch:\n",
    " " * (resume_indent + 4) + "raise RuntimeError(f'checkpoint micro-batch mismatch: requested={a.micro_batch}, found={logged.get(\"micro_batch\")}')\n",
    " " * resume_indent + "if int(logged.get('grad_accum', -1)) != grad_accum:\n",
    " " * (resume_indent + 4) + "raise RuntimeError(f'checkpoint grad_accum mismatch: expected={grad_accum}, found={logged.get(\"grad_accum\")}')\n",
    " " * resume_indent + "expected_parent_name = f'student_ckpt_{rnd:03d}'\n",
    " " * resume_indent + "logged_parent = str(logged.get('checkpoint_parent', '')).strip()\n",
    " " * resume_indent + "if not logged_parent:\n",
    " " * (resume_indent + 4) + "raise RuntimeError('checkpoint_parent is missing from train_log.json')\n",
    " " * resume_indent + "if rnd == 0:\n",
    " " * (resume_indent + 4) + "parent_ok = Path(logged_parent).name == expected_parent_name\n",
    " " * resume_indent + "else:\n",
    " " * (resume_indent + 4) + "expected_parent = (a.models_dir / method / f'seed_{seed:02d}' / expected_parent_name).resolve()\n",
    " " * (resume_indent + 4) + "parent_ok = Path(logged_parent).resolve() == expected_parent\n",
    " " * resume_indent + "if not parent_ok:\n",
    " " * (resume_indent + 4) + "raise RuntimeError(f'checkpoint parent mismatch: expected={expected_parent_name if rnd == 0 else expected_parent}, found={logged_parent}')\n",
    " " * resume_indent + "print(f'[RESUME] Reusing verified adapter {adapter_out}')\n",
]

new_lines = (
    lines[:config_index + 1]
    + config_patch
    + lines[config_index + 1:resume_start]
    + resume_patch_text
    + lines[resume_end + 1:]
)

updated = "".join(new_lines)

compile(updated, str(PIPELINE), "exec")

if updated == source:
    raise RuntimeError("PATCH_NO_CHANGES")

temp_path = PIPELINE.with_suffix(".py.patch_tmp")
temp_path.write_text(updated, encoding="utf-8", newline="\n")

check = temp_path.read_text(encoding="utf-8")
compile(check, str(PIPELINE), "exec")

PIPELINE.write_text(check, encoding="utf-8", newline="\n")
temp_path.unlink(missing_ok=True)

new_hash = hashlib.sha256(PIPELINE.read_bytes()).hexdigest()

print("PATCH_STATUS: PASS")
print(f"PIPELINE: {PIPELINE}")
print(f"SHA256: {new_hash}")
print("CONFIG_VALIDATION: ADDED")
print("RESUME_SEED_CHECK: ADDED")
print("RESUME_BATCH_CHECK: ADDED")
print("RESUME_PARENT_CHECK: ADDED")