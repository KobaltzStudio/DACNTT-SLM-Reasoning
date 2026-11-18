import csv
from pathlib import Path

source = Path(
    "reports/capability/d3_audit/adjudication_queue.csv"
)

output = Path(
    "reports/capability/d3_audit/adjudication_working.csv"
)

with source.open(
    "r",
    encoding="utf-8-sig",
    newline=""
) as f:
    rows = list(csv.DictReader(f))

if len(rows) != 22:
    raise ValueError(
        f"Expected 22 queue records, got {len(rows)}"
    )

columns = list(rows[0].keys())

extra_columns = [
    "ground_truth",
    "reference_solution",
    "decision_capabilities",
    "decision_difficulty",
    "decision_rationale",
    "guideline_reference",
    "adjudication_status",
    "reviewer",
]

for column in extra_columns:
    if column not in columns:
        columns.append(column)

for row in rows:
    for column in extra_columns:
        if column not in row:
            row[column] = ""

    row["adjudication_status"] = "pending"

output.parent.mkdir(
    parents=True,
    exist_ok=True
)

with output.open(
    "w",
    encoding="utf-8-sig",
    newline=""
) as f:
    writer = csv.DictWriter(
        f,
        fieldnames=columns
    )
    writer.writeheader()
    writer.writerows(rows)

print("ADJUDICATION WORKING FILE: PASS")
print("Records:", len(rows))
print("Output:", output)
