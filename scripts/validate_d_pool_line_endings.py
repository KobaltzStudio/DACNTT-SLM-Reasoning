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

def read_ids(data):
    return [
        line.strip()
        for line in data.decode("utf-8-sig").splitlines()
        if line.strip()
    ]

def main():
    if not CURRENT.is_file():
        raise FileNotFoundError(CURRENT)

    current = CURRENT.read_bytes()

    head_result = git("show", f"HEAD:{REL}")
    if head_result.returncode != 0:
        raise RuntimeError(
            head_result.stderr.decode("utf-8", errors="replace")
        )

    head = head_result.stdout

    # Normalize Windows CRLF and standalone CR to LF.
    current_lf = current.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    head_lf = head.replace(b"\r\n", b"\n").replace(b"\r", b"\n")

    current_ids = read_ids(current)
    head_ids = read_ids(head)

    print("CURRENT_SHA256_RAW:", sha256(current))
    print("CURRENT_SHA256_LF:", sha256(current_lf))
    print("HEAD_SHA256_RAW:", sha256(head))
    print("HEAD_SHA256_LF:", sha256(head_lf))

    print("CURRENT_BYTES:", len(current))
    print("CURRENT_LF_BYTES:", len(current_lf))
    print("HEAD_BYTES:", len(head))

    print("CURRENT_LINES:", len(current_ids))
    print("CURRENT_UNIQUE_IDS:", len(set(current_ids)))
    print("HEAD_LINES:", len(head_ids))
    print("HEAD_UNIQUE_IDS:", len(set(head_ids)))

    print("CURRENT_EQUALS_HEAD_RAW:", current == head)
    print("CURRENT_EQUALS_HEAD_LF:", current_lf == head_lf)
    print("CURRENT_IDS_EQUAL_HEAD_IDS:", current_ids == head_ids)

    print("CURRENT_DUPLICATES:", len(current_ids) - len(set(current_ids)))

    if current_lf == head_lf and current_ids == head_ids:
        print("D_POOL_CONTENT_VALIDATION: PASS")
    else:
        print("D_POOL_CONTENT_VALIDATION: FAIL")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("D_POOL_CONTENT_VALIDATION: ERROR")
        print(type(exc).__name__ + ":", exc)
        sys.exit(1)
