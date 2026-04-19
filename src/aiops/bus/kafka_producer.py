"""Async Kafka producer wrapper (confluent-kafka)."""
from __future__ import annotations

import asyncio
import json
from typing import Any

from aiops.core.config import settings
from aiops.core.logging import log


class KafkaProducer:
    """Lightweight async wrapper over confluent_kafka.Producer."""

    _instance: "KafkaProducer | None" = None

    def __init__(self) -> None:
        from confluent_kafka import Producer  # local import to allow unit tests w/o kafka
        self._producer = Producer(
            {
                "bootstrap.servers": settings.kafka.bootstrap_servers,
                "acks": "all",
                "enable.idempotence": True,
                "linger.ms": 5,
            }
        )

    @classmethod
    def get(cls) -> "KafkaProducer":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _cb(self, err: Any, msg: Any) -> None:
        if err is not None:
            log.error(f"kafka produce error: {err}")

    async def send(self, topic: str, key: str, payload: dict) -> None:
        body = json.dumps(payload, default=str).encode("utf-8")
        self._producer.produce(topic, key=key.encode("utf-8"), value=body, callback=self._cb)
        # non-blocking poll
        self._producer.poll(0)
        await asyncio.sleep(0)

    def flush(self, timeout: float = 5.0) -> None:
        self._producer.flush(timeout)
