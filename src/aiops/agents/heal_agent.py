"""Heal Agent — consume HealRequest, run runbook, publish HealResult."""
from __future__ import annotations

from aiops.agents.base import AgentBase
from aiops.bus.topics import Topic
from aiops.core.logging import log
from aiops.core.types import HealRequest
from aiops.heal.executor import get_executor


class HealAgent(AgentBase):
    name = "heal"
    topics = [Topic.HEAL_REQUEST]

    def __init__(self) -> None:
        super().__init__()
        self.exec = get_executor()

    async def on_message(self, topic: str, payload: dict) -> None:
        req = HealRequest(**payload)
        result = await self.exec.execute(req)
        log.info(f"[heal] {req.alert_id} runbook={req.runbook} success={result.success}")
        if self.producer is not None:
            await self.producer.send(
                Topic.HEAL_RESULT, key=req.alert_id, payload=result.model_dump(mode="json")
            )
