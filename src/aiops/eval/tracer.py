"""Emits EvalTrace events to Kafka (or logs when unavailable)."""
from __future__ import annotations

import time

from aiops.bus.kafka_producer import KafkaProducer
from aiops.bus.topics import Topic
from aiops.core.logging import log
from aiops.core.types import EvalTrace


class Tracer:
    def __init__(self) -> None:
        self._producer = None
        try:
            self._producer = KafkaProducer.get()
        except Exception as e:
            log.warning(f"kafka unavailable for tracer ({e}); using log-only tracer")

    async def emit(
        self, stage: str, trace_id: str, input_: dict, output: dict, latency_ms: float, **extra
    ) -> None:
        trace = EvalTrace(
            trace_id=trace_id, stage=stage, input=input_, output=output,
            latency_ms=latency_ms, extra=extra,
        )
        if self._producer is None:
            log.debug(f"[trace] {trace.model_dump_json()}")
            return
        try:
            await self._producer.send(Topic.EVAL_TRACE, key=trace_id, payload=trace.model_dump(mode="json"))
        except Exception as e:
            log.warning(f"tracer emit failed: {e}")


class Timer:
    def __enter__(self):
        self.t = time.perf_counter()
        return self

    def __exit__(self, *a):
        self.elapsed_ms = (time.perf_counter() - self.t) * 1000


_tracer: Tracer | None = None


def get_tracer() -> Tracer:
    global _tracer
    if _tracer is None:
        _tracer = Tracer()
    return _tracer
