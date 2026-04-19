import asyncio

import pytest

from aiops.core.exceptions import CircuitOpenError
from aiops.resilience.circuit_breaker import CircuitBreaker


@pytest.mark.asyncio
async def test_opens_after_threshold():
    cb = CircuitBreaker(name="t", failure_threshold=3, recovery_timeout=10)

    async def boom():
        raise RuntimeError("boom")

    for _ in range(3):
        with pytest.raises(RuntimeError):
            await cb.acall(boom)

    with pytest.raises(CircuitOpenError):
        await cb.acall(boom)


@pytest.mark.asyncio
async def test_half_open_recovers():
    cb = CircuitBreaker(name="t2", failure_threshold=1, recovery_timeout=0.05)

    async def boom():
        raise RuntimeError("boom")

    async def ok():
        return 42

    with pytest.raises(RuntimeError):
        await cb.acall(boom)
    with pytest.raises(CircuitOpenError):
        await cb.acall(ok)
    await asyncio.sleep(0.1)
    assert await cb.acall(ok) == 42
