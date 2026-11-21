from pathlib import Path

HERE = Path(__file__).resolve().parent
PIPELINE = HERE / "run_b4_b5.py"

source = PIPELINE.read_text(encoding="utf-8")

required_source_fragments = [
    "a.models_dir/method/f'seed_{seed:02d}'/next_checkpoint",
    "a.models_dir/method/f'seed_{seed:02d}'/f'student_ckpt_{rnd:03d}'",
    "cmd += ['--init-adapter',parent]",
]

for fragment in required_source_fragments:
    if fragment not in source:
        raise AssertionError(f"PIPELINE_PATH_RULE_MISSING: {fragment}")

methods = ["B4", "B5"]
seeds = [13, 42, 2026]
rounds = [0, 1, 2]

model_root = Path("models")

all_checkpoint_paths = set()
rows = []

for method in methods:
    for seed in seeds:
        seed_dir = model_root / method / f"seed_{seed:02d}"

        for rnd in rounds:
            output_checkpoint = seed_dir / f"student_ckpt_{rnd + 1:03d}"

            if rnd == 0:
                parent = Path("student_ckpt_000")
            else:
                parent = seed_dir / f"student_ckpt_{rnd:03d}"

            if output_checkpoint in all_checkpoint_paths:
                raise AssertionError(f"DUPLICATE_CHECKPOINT_PATH: {output_checkpoint}")

            all_checkpoint_paths.add(output_checkpoint)

            if rnd > 0 and parent.parent != seed_dir:
                raise AssertionError(f"CROSS_LINEAGE_PARENT: {parent}")

            rows.append(
                (
                    method,
                    seed,
                    rnd,
                    str(output_checkpoint),
                    str(parent),
                )
            )

print("METHOD | SEED | ROUND | OUTPUT CHECKPOINT | EXPECTED PARENT")

for row in rows:
    print(" | ".join(map(str, row)))

if len(rows) != 18:
    raise AssertionError(f"EXPECTED_18_ROWS_FOUND_{len(rows)}")

if len(all_checkpoint_paths) != 18:
    raise AssertionError("CHECKPOINT_PATHS_NOT_UNIQUE")

print("LINEAGE_SOURCE_CHECK: PASS")
print("LINEAGE_MATRIX_CHECK: PASS")
print("METHOD_SEED_COMBINATIONS: 6")
print("ROUND_ENTRIES: 18")