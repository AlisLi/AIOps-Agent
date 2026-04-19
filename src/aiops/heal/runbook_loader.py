"""Load YAML runbooks from configs/runbooks/."""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
RUNBOOK_DIR = ROOT / "configs" / "runbooks"


def list_runbooks() -> list[str]:
    return [p.stem for p in RUNBOOK_DIR.glob("*.yaml")]


def load_runbook(name: str) -> dict:
    p = RUNBOOK_DIR / f"{name}.yaml"
    if not p.exists():
        raise FileNotFoundError(f"runbook not found: {name}")
    return yaml.safe_load(p.read_text(encoding="utf-8"))
