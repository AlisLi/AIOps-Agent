"""Differentiated retry policies via tenacity."""
from __future__ import annotations

from typing import Literal

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    stop_never,
    wait_exponential,
    wait_exponential_jitter,
    wait_fixed,
)

Kind = Literal["llm", "db", "kafka", "http"]


def retry_policy(kind: Kind):
    """Return a tenacity decorator pre-configured per kind."""
    if kind == "llm":
        return retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential_jitter(initial=1, max=4),
            reraise=True,
        )
    if kind == "db":
        return retry(
            stop=stop_after_attempt(5),
            wait=wait_fixed(0.5),
            reraise=True,
        )
    if kind == "kafka":
        return retry(
            stop=stop_never,
            wait=wait_exponential(multiplier=1, max=30),
            reraise=True,
        )
    if kind == "http":
        return retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=0.2, max=1),
            reraise=True,
        )
    raise ValueError(f"unknown retry kind: {kind}")
