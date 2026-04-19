"""Regex-based log anomaly detector."""
from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Iterable

from aiops.core.config import settings
from aiops.core.types import AlertEvent


class LogRegexDetector:
    def __init__(self) -> None:
        self.rules: list[tuple[re.Pattern, str]] = [
            (re.compile(r.pattern), r.severity)
            for r in settings.monitor.log_rules
        ]

    def scan(self, lines: Iterable[str], service: str = "unknown") -> list[AlertEvent]:
        events: list[AlertEvent] = []
        for line in lines:
            for pat, sev in self.rules:
                if pat.search(line):
                    events.append(AlertEvent(
                        alert_id=str(uuid.uuid4()),
                        service=service,
                        metric="log_error",
                        value=1.0,
                        threshold=0.0,
                        severity=sev,  # type: ignore[arg-type]
                        detected_by="regex",
                        ts=datetime.utcnow(),
                        raw={"line": line[:500], "pattern": pat.pattern},
                    ))
                    break
        return events
