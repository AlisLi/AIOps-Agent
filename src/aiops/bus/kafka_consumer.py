"""Async Kafka consumer loop."""
from __future__ import annotations

import asyncio
import json
from typing import Awaitable, Callable

from aiops.core.config import settings
from aiops.core.logging import log

Handler = Callable[[str, dict], Awaitable[None]]


class KafkaConsumer:
    def __init__(self, group_id: str, topics: list[str]) -> None:
        from confluent_kafka import Consumer
        self._consumer = Consumer(
            {
                "bootstrap.servers": settings.kafka.bootstrap_servers,
                "group.id": group_id,
                "auto.offset.reset": "latest",
                "enable.auto.commit": True,
            }
        )
        self._consumer.subscribe(topics)
        self._running = False
        self._topics = topics

    async def run(self, handler: Handler, poll_interval: float = 0.5) -> None:
        self._running = True
        log.info(f"kafka consumer subscribed: {self._topics}")
        loop = asyncio.get_event_loop()
        while self._running:
            msg = await loop.run_in_executor(None, self._consumer.poll, poll_interval)
            if msg is None:
                continue
            if msg.error():
                log.warning(f"kafka consumer error: {msg.error()}")
                continue
            try:
                payload = json.loads(msg.value().decode("utf-8"))
                await handler(msg.topic(), payload)
            except Exception as e:
                log.exception(f"handler failure: {e}")

    def stop(self) -> None:
        self._running = False
        self._consumer.close()
