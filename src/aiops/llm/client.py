"""LLM client wrapper using OpenAI-compatible HTTP API.

Features:
- async invoke / stream
- Wrapped by circuit breaker + retry
- Graceful offline fallback when api_key is empty (for demos)
"""
from __future__ import annotations

import json
from typing import AsyncIterator

import httpx

from aiops.core.config import settings
from aiops.core.exceptions import LLMError
from aiops.core.logging import log
from aiops.resilience.circuit_breaker import CircuitBreaker
from aiops.resilience.retry import retry_policy

_breaker = CircuitBreaker(name="llm", failure_threshold=5, recovery_timeout=30)


class LLMClient:
    def __init__(self) -> None:
        self.base_url = settings.llm.base_url.rstrip("/")
        self.api_key = settings.llm.api_key
        self.model = settings.llm.model
        self.timeout = settings.llm.timeout
        self._offline = not self.api_key or self.api_key.startswith("sk-xxx")

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    @retry_policy("llm")
    async def _raw_chat(self, messages: list[dict], temperature: float = 0.3) -> str:
        url = f"{self.base_url}/chat/completions"
        payload = {"model": self.model, "messages": messages, "temperature": temperature}
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            r = await c.post(url, headers=self._headers(), json=payload)
            if r.status_code >= 400:
                raise LLMError(f"llm http {r.status_code}: {r.text[:200]}")
            data = r.json()
            return data["choices"][0]["message"]["content"]

    async def ainvoke(self, prompt: str, system: str | None = None, temperature: float = 0.3) -> str:
        if self._offline:
            log.warning("LLM offline mode (no API key) — returning echo stub")
            return f"[offline-llm] echo: {prompt[:120]}"
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return await _breaker.acall(self._raw_chat, messages, temperature)

    async def astream(self, prompt: str, system: str | None = None) -> AsyncIterator[str]:
        if self._offline:
            for chunk in f"[offline-llm] echo: {prompt[:120]}".split():
                yield chunk + " "
            return
        url = f"{self.base_url}/chat/completions"
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {"model": self.model, "messages": messages, "stream": True}
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            async with c.stream("POST", url, headers=self._headers(), json=payload) as r:
                async for line in r.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        obj = json.loads(data)
                        delta = obj["choices"][0]["delta"].get("content")
                        if delta:
                            yield delta
                    except Exception:
                        continue


_client: LLMClient | None = None


def get_llm() -> LLMClient:
    global _client
    if _client is None:
        _client = LLMClient()
    return _client
