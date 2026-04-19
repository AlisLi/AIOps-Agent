"""Anomaly detection: 3-Sigma and EWMA voting."""
from __future__ import annotations

import math
from collections import deque
from typing import Iterable


class AnomalyDetector:
    def __init__(self, window: int = 60, ewma_alpha: float = 0.3, k: float = 3.0) -> None:
        self.window = window
        self.alpha = ewma_alpha
        self.k = k
        self._series: deque[float] = deque(maxlen=window)

    def observe(self, x: float) -> None:
        self._series.append(float(x))

    def history(self) -> list[float]:
        return list(self._series)

    def three_sigma(self, series: Iterable[float], x: float) -> bool:
        s = list(series)
        if len(s) < 5:
            return False
        mean = sum(s) / len(s)
        var = sum((v - mean) ** 2 for v in s) / len(s)
        std = math.sqrt(var)
        return abs(x - mean) > self.k * std

    def ewma(self, series: Iterable[float], x: float) -> bool:
        s = list(series)
        if len(s) < 5:
            return False
        ewma_val = s[0]
        for v in s[1:]:
            ewma_val = self.alpha * v + (1 - self.alpha) * ewma_val
        # residual std via simple diff
        diffs = [abs(v - ewma_val) for v in s]
        std = math.sqrt(sum(d * d for d in diffs) / len(diffs))
        return abs(x - ewma_val) > self.k * max(std, 1e-6)

    def vote(self, x: float) -> tuple[bool, str]:
        s = list(self._series)
        a = self.three_sigma(s, x)
        b = self.ewma(s, x)
        count = int(a) + int(b)
        tag = "vote" if count == 2 else ("3sigma" if a else ("ewma" if b else "none"))
        return count >= 1, tag
