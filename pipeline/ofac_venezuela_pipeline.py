"""
Backward-compatible entrypoint for OFAC-only runs.

Prefer: python pipeline/run_daily.py --ofac-only
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.run_daily import main

if __name__ == "__main__":
    # Default to OFAC-only when this legacy script is invoked directly.
    argv = sys.argv[1:]
    if "--funds-only" not in argv and "--ofac-only" not in argv:
        argv = ["--ofac-only", *argv]
    sys.exit(main(argv))
