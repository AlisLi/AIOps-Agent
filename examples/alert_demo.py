"""End-to-end alert -> RCA -> heal demo (in-process, no Kafka needed).

Run:
    python scripts/seed_knowledge.py
    python examples/alert_demo.py
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime

from aiops.core.types import AlertEvent, HealRequest
from aiops.heal.executor import get_executor
from aiops.rca.analyzer import RCAAnalyzer
from scripts.seed_knowledge import main as seed


async def main() -> None:
    seed()
    analyzer = RCAAnalyzer()
    executor = get_executor()

    alert = AlertEvent(
        alert_id=str(uuid.uuid4()),
        service="chip-api",
        metric="cpu_usage",
        value=95.0,
        threshold=80.0,
        severity="P1",
        detected_by="vote",
        ts=datetime.utcnow(),
    )
    print(f">>> ALERT: {alert.service} {alert.metric}={alert.value} (thr={alert.threshold})")

    rca = await analyzer.analyze(alert)
    print(f">>> RCA root_cause={rca.root_cause_service}")
    print(f"    reasoning   = {rca.reasoning}")
    print(f"    actions     = {rca.suggested_actions}")

    runbook = (rca.suggested_actions or ["restart_pod"])[0]
    # The LLM may emit a non-existent runbook; normalize to what we ship.
    if runbook not in ("restart_pod",):
        runbook = "restart_pod"
    heal_req = HealRequest(
        alert_id=alert.alert_id,
        runbook=runbook,
        params={"service": rca.root_cause_service, "namespace": "default"},
    )
    result = await executor.execute(heal_req)
    print(f">>> HEAL runbook={runbook} success={result.success}")
    for line in result.logs:
        print(f"    {line}")


if __name__ == "__main__":
    asyncio.run(main())
