import json
from pathlib import Path

path = Path(
    "reports/capability/d3_audit/agreement_supplement_25.json"
)

report = json.loads(path.read_text(encoding="utf-8"))

print("ANNOTATION TYPE:", report.get("annotation_type"))
print("N RECORDS:", report.get("n_records"))
print("\nCAPABILITY AGREEMENT")

for capability, result in report["capabilities"].items():
    kappa = result["kappa"]
    kappa_text = "N/A" if kappa is None else f"{kappa:.4f}"

    print(
        f"{capability:15} "
        f"kappa={kappa_text:8} "
        f"status={result['status']:10} "
        f"agreement={result['agreement_count']}/{result['n']}"
    )

difficulty = report["difficulty"]
kappa = difficulty["kappa"]
kappa_text = "N/A" if kappa is None else f"{kappa:.4f}"

print("\nDIFFICULTY AGREEMENT")
print(
    f"kappa={kappa_text}, "
    f"status={difficulty['status']}, "
    f"agreement={difficulty['agreement_count']}/{difficulty['n']}"
)

print("\nDISAGREEMENT COUNT:", report["disagreement_count"])

print("\nDISAGREEMENT DETAILS")
for item in report["disagreements"]:
    print(json.dumps(item, ensure_ascii=False))
