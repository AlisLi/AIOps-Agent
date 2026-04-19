"""In-process E2E: alert -> RCA (offline LLM) -> heal runbook.

This does not require Kafka/Milvus/Neo4j; uses fallback local stores.
"""
from __future__ import annotations

import uuid
from datetime import datetime

import pytest

from aiops.core.types import AlertEvent, HealRequest
from aiops.heal.executor import get_executor
from aiops.rca.analyzer import RCAAnalyzer
from scripts.seed_knowledge import main as seed


@pytest.mark.asyncio
async def test_alert_to_heal_roundtrip():
    seed()
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
    rca = await RCAAnalyzer().analyze(alert)
    assert rca.alert_id == alert.alert_id
    assert rca.root_cause_service

    exec_ = get_executor()
    # Use a runbook we know exists to avoid LLM hallucinations breaking the test
    heal_req = HealRequest(
        alert_id=alert.alert_id,
        runbook="restart_pod",
        params={"service": rca.root_cause_service, "namespace": "default"},
    )
    result = await exec_.execute(heal_req)
    assert result.success
