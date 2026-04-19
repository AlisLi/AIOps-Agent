"""Make tests runnable from repo root without install."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / "src", ROOT):
    s = str(p)
    if s not in sys.path:
        sys.path.insert(0, s)
