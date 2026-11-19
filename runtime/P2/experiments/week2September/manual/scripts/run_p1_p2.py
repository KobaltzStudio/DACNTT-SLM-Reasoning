#!/usr/bin/env python3
"""Single public CLI entry point for the P1/P2 unified controller."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from p1p2_controller import main

if __name__ == "__main__":
    raise SystemExit(main())
