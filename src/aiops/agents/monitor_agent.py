"""Monitor Agent — scans metrics + logs periodically, publishes AlertEvent."""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime

from aiops.bus.kafka_producer import KafkaProducer
from aiops.bus.topics import Topic
from aiops.core.config import settings
from aiops.core.logging import log
from aiops.core.types import AlertEvent
from aiops.monitor.collector import sample_cpu_metrics, sample_log_lines
from aiops.monitor.log_detector import LogRegexDetector
from aiops.monitor.metrics_detector import AnomalyDetector


class MonitorAgent:
    name = "monitor"

    def __init__(self) -> None:
        self.producer: KafkaProducer | None = None
        self.metrics = AnomalyDetector(window=60)
        self.logs = LogRegexDetector()
        self._running = False

    async def start(self) -> None:
        try:
            self.producer = KafkaProducer.get()
        except Exception as e:
            log.warning(f"[monitor] kafka unavailable ({e}); events logged only")
        self._running = True
        asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self._running = False

    async def _publish(self, alert: AlertEvent) -> None:
        log.info(f"[monitor] ALERT {alert.severity} {alert.service} {alert.metric}={alert.value}")
        if self.producer is None:
            return
        await self.producer.send(Topic.ALERT_RAW, key=alert.alert_id, payload=alert.model_dump(mode="json"))

    async def _loop(self) -> None:
        # bootstrap metric history
        for v in sample_cpu_metrics(40.0, 60):
            self.metrics.observe(v)
        while self._running:
            # inject occasional spike
            x = 95.0
            is_anom, tag = self.metrics.vote(x)
            if is_anom:
                await self._publish(AlertEvent(
                    alert_id=str(uuid.uuid4()), service="chip-api",
                    metric="cpu_usage", value=x, threshold=80.0,
                    severity="P1", detected_by=tag,  # type: ignore[arg-type]
                    ts=datetime.utcnow(),
                ))
            self.metrics.observe(x)

            for ev in self.logs.scan(sample_log_lines(), service="chip-worker"):
                await self._publish(ev)

            await asyncio.sleep(settings.monitor.interval_seconds)
