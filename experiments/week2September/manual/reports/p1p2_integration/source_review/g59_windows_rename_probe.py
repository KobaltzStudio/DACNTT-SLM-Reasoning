import os
import shutil
import tempfile
import traceback
from pathlib import Path

ROOT = Path(
    r"C:\Users\PC - NGHI\Desktop\Pipeline\P2\experiments\week2September\manual"
)
PARENT = ROOT / "reports" / "capability" / "g5_9_historical_20261117"

def main():
    print("G59_RENAME_PROBE_START")
    print(f"PARENT={PARENT}")
    print(f"PARENT_EXISTS={PARENT.is_dir()}")

    if not PARENT.is_dir():
        raise RuntimeError("SIDECAR_PARENT_NOT_FOUND")

    file_probe = PARENT / ".g59_write_probe.tmp"
    source = None
    destination = None

    try:
        file_probe.write_text("write_probe", encoding="utf-8")
        print("FILE_CREATE=PASS")
        file_probe.unlink()
        print("FILE_DELETE=PASS")

        source = Path(tempfile.mkdtemp(
            prefix=".g59_rename_source.",
            dir=str(PARENT),
        ))
        (source / "probe.txt").write_text(
            "directory_rename_probe",
            encoding="utf-8",
        )

        destination = PARENT / (source.name + ".renamed")

        print(f"SOURCE={source}")
        print(f"DESTINATION={destination}")
        print(f"DESTINATION_EXISTS={destination.exists()}")

        if destination.exists():
            raise RuntimeError("PROBE_DESTINATION_COLLISION")

        os.rename(source, destination)

        print("OS_RENAME=PASS")
        print(f"RENAMED_DIRECTORY_EXISTS={destination.is_dir()}")
        print(
            "RENAMED_FILE_CONTENT="
            + (destination / "probe.txt").read_text(encoding="utf-8")
        )

    except Exception as exc:
        print(f"PROBE_EXCEPTION={type(exc).__name__}: {exc}")
        traceback.print_exc()
        raise

    finally:
        if source is not None and source.exists():
            shutil.rmtree(source, ignore_errors=True)

        if destination is not None and destination.exists():
            shutil.rmtree(destination, ignore_errors=True)

        if file_probe.exists():
            file_probe.unlink()

        print("PROBE_CLEANUP=COMPLETE")

    print("G59_RENAME_PROBE=PASS")

if __name__ == "__main__":
    main()
