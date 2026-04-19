"""Tri-state circuit breaker (CLOSED / OPEN / HALF_OPEN)."""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Awaitable, Callable

from aiops.core.exceptions import CircuitOpenError
from aiops.core.logging import log


class State(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    name: str = "default"
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    half_open_max_calls: int = 1

    def __post_init__(self) -> None:
        self._state: State = State.CLOSED
        self._failures: int = 0
        self._opened_at: float = 0.0
        self._half_open_calls: int = 0
        self._lock = asyncio.Lock()

    def _can_try(self) -> bool:
        if self._state is State.CLOSED:
            return True
        if self._state is State.OPEN:
            if time.monotonic() - self._opened_at >= self.recovery_timeout:
                self._state = State.HALF_OPEN
                self._half_open_calls = 0
                log.info(f"[cb:{self.name}] -> HALF_OPEN")
                return True
            return False
        return self._half_open_calls < self.half_open_max_calls

    def _on_success(self) -> None:
        self._failures = 0
        if self._state is not State.CLOSED:
            log.info(f"[cb:{self.name}] -> CLOSED")
        self._state = State.CLOSED
        self._half_open_calls = 0

    def _on_failure(self) -> None:
        self._failures += 1
        if self._state is State.HALF_OPEN or self._failures >= self.failure_threshold:
            self._state = State.OPEN
            self._opened_at = time.monotonic()
            log.warning(f"[cb:{self.name}] -> OPEN (failures={self._failures})")

    def call(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        if not self._can_try():
            raise CircuitOpenError(f"circuit {self.name} is OPEN")
        try:
            if self._state is State.HALF_OPEN:
                self._half_open_calls += 1
            result = fn(*args, **kwargs)
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise

    async def acall(self, fn: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any) -> Any:
        async with self._lock:
            if not self._can_try():
                raise CircuitOpenError(f"circuit {self.name} is OPEN")
            if self._state is State.HALF_OPEN:
                self._half_open_calls += 1
        try:
            result = await fn(*args, **kwargs)
            async with self._lock:
                self._on_success()
            return result
        except Exception:
            async with self._lock:
                self._on_failure()
            raise
