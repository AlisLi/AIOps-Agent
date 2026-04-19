import pytest

from aiops.core.types import HealRequest
from aiops.heal.executor import get_executor


@pytest.mark.asyncio
async def test_restart_pod_mock_runs():
    ex = get_executor()
    req = HealRequest(alert_id="a", runbook="restart_pod", params={"service": "chip-api", "namespace": "default"})
    res = await ex.execute(req)
    assert res.success
    assert any("rollout restart" in line for line in res.logs)
