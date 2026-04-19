"""RCA Agent — consume AlertEvent, analyze, publish RCAResult + HealRequest."""
from __future__ import annotations

from aiops.agents.base import AgentBase
from aiops.bus.topics import Topic
from aiops.core.logging import log
from aiops.core.types import AlertEvent, HealRequest
from aiops.rca.analyzer import RCAAnalyzer


class RCAAgent(AgentBase):
    name = "rca"
    topics = [Topic.ALERT_RAW]

    def __init__(self) -> None:
        super().__init__()
        self.analyzer = RCAAnalyzer()

    async def on_message(self, topic: str, payload: dict) -> None:
        alert = AlertEvent(**payload)
        result = await self.analyzer.analyze(alert)
        log.info(f"[rca] {alert.alert_id} -> {result.root_cause_service}: {result.reasoning[:100]}")
        if self.producer is not None:
            await self.producer.send(
                Topic.RCA_RESULT, key=alert.alert_id, payload=result.model_dump(mode="json")
            )
            if result.suggested_actions:
                heal = HealRequest(
                    alert_id=alert.alert_id,
                    runbook=result.suggested_actions[0],
                    params={"service": result.root_cause_service, "namespace": "default"},
                )
                await self.producer.send(
                    Topic.HEAL_REQUEST, key=alert.alert_id, payload=heal.model_dump(mode="json")
                )
