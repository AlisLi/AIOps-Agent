"""Base Agent with Kafka consume-dispatch loop."""
from __future__ import annotations

import abc
import asyncio

from aiops.bus.kafka_consumer import KafkaConsumer
from aiops.bus.kafka_producer import KafkaProducer
from aiops.core.logging import log


class AgentBase(abc.ABC):
    name: str = "agent"
    topics: list[str] = []

    def __init__(self) -> None:
        self.producer: KafkaProducer | None = None
        self.consumer: KafkaConsumer | None = None
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        try:
            self.producer = KafkaProducer.get()
            self.consumer = KafkaConsumer(group_id=f"aiops-{self.name}", topics=self.topics)
            log.info(f"[{self.name}] started; topics={self.topics}")
            self._task = asyncio.create_task(self.consumer.run(self._dispatch))
        except Exception as e:
            log.warning(f"[{self.name}] start failed ({e}); running offline stub")

    async def _dispatch(self, topic: str, payload: dict) -> None:
        try:
            await self.on_message(topic, payload)
        except Exception as e:
            log.exception(f"[{self.name}] on_message failure: {e}")

    async def stop(self) -> None:
        if self.consumer is not None:
            self.consumer.stop()
        if self._task is not None:
            self._task.cancel()

    @abc.abstractmethod
    async def on_message(self, topic: str, payload: dict) -> None: ...
