"""Placeholder metrics/log collector for demos."""
from __future__ import annotations

import random
from typing import Iterable


def sample_cpu_metrics(normal_mean: float = 40.0, n: int = 60) -> list[float]:
    return [max(0.0, random.gauss(normal_mean, 3.0)) for _ in range(n)]


def sample_log_lines() -> Iterable[str]:
    return [
        "2026-04-19 10:00:01 INFO chip-checker starting",
        "2026-04-19 10:00:05 WARN slow query on chip_defect",
        "2026-04-19 10:00:09 ERROR OutOfMemoryError in worker-3",
        "2026-04-19 10:00:10 FATAL panic: nil pointer dereference",
    ]
