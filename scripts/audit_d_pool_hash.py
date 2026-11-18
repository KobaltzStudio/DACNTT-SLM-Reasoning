from pathlib import Path
import hashlib
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REL = "experiments/week2September/manual/splits/d_pool_ids.txt"
CURRENT = ROOT / REL

def sha256(data):
    return hashlib.sha256(data).hexdigest().upper()

def git(*args):
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

print("FILE:", CURRENT)
print("EXISTS:", CURRENT.is_file())

if not CURRENT.is_file():
    print("AUDIT: FAIL - current file is missing")
    sys.exit(1)

current_bytes = CURRENT.read_bytes()
current_hash = sha256(current_bytes)
print("CURRENT_SHA256:", current_hash)
print("CURRENT_BYTES:", len(current_bytes))
print("CURRENT_LINES:", len(current_bytes.splitlines()))

tracked = git("ls-files", "--error-unmatch", REL)
if tracked.returncode != 0:
    print("GIT_TRACKED: NO")
    print("GIT_HEAD_VERSION: unavailable")
    print("AUDIT: NEEDS INVESTIGATION")
    sys.exit(2)

print("GIT_TRACKED: YES")

head = git("show", f"HEAD:{REL}")
if head.returncode != 0:
    print("GIT_HEAD_VERSION: unavailable")
    print(head.stderr.decode("utf-8", errors="replace"))
    print("AUDIT: NEEDS INVESTIGATION")
    sys.exit(2)

head_bytes = head.stdout
head_hash = sha256(head_bytes)

print("HEAD_SHA256:", head_hash)
print("HEAD_BYTES:", len(head_bytes))
print("HEAD_LINES:", len(head_bytes.splitlines()))
print("CURRENT_EQUALS_HEAD:", current_bytes == head_bytes)

status = git("status", "--short", "--", REL)
print("GIT_STATUS:")
print(status.stdout.decode("utf-8", errors="replace").strip() or "(clean)")

print("AUDIT: COMPLETE")
