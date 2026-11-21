import hashlib
from pathlib import Path

EXPECTED = "17cf4b837dc42ac5145aea762847ca5dfba4bae58d253560b3b0dd6a254b73c5"

ROOTS = [
    Path("."),
    Path("integration_staging/P1"),
]

EXTENSIONS = {".json", ".yaml", ".yml", ".toml"}
seen = set()
matches = []
errors = []

for root in ROOTS:
    if not root.exists():
        continue

    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in EXTENSIONS:
            continue

        try:
            resolved = path.resolve()

            if resolved in seen:
                continue

            seen.add(resolved)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()

            if digest == EXPECTED:
                matches.append(path)

        except OSError as exc:
            errors.append(f"{path}: {exc}")

print("EXPECTED_CONFIG_SHA256:", EXPECTED)
print("SCANNED_FILES:", len(seen))
print("MATCH_COUNT:", len(matches))

for path in matches:
    print("\nCONFIG_MATCH:", path.resolve())
    print("SHA256:", hashlib.sha256(path.read_bytes()).hexdigest())
    print("SIZE_BYTES:", path.stat().st_size)
    print("CONTENT:")
    print(path.read_text(encoding="utf-8-sig", errors="replace"))

for error in errors:
    print("READ_ERROR:", error)

if len(matches) == 1:
    print("\nTRAINING_CONFIG_HASH_AUDIT: PASS")
elif len(matches) == 0:
    print("\nTRAINING_CONFIG_HASH_AUDIT: NOT_FOUND")
else:
    print("\nTRAINING_CONFIG_HASH_AUDIT: MULTIPLE_MATCHES")
