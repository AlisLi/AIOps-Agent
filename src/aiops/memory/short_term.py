"""Sliding window + async incremental summary, persisted in Redis."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from jinja2 import Template

from aiops.core.config import settings
from aiops.core.logging import log
from aiops.core.types import ChatMessage
from aiops.llm.client import get_llm

ROOT = Path(__file__).resolve().parents[3]
SUMMARIZE_TPL = ROOT / "configs" / "prompts" / "summarize.jinja"


class SlidingWindowMemory:
    def __init__(self) -> None:
        self.window_size = settings.memory.short_window
        self.llm = get_llm()
        self._client = None
        self._mem: dict[str, dict] = {}  # fallback in-memory
        try:
            import redis  # type: ignore
            self._client = redis.Redis.from_url(settings.redis.url, decode_responses=True)
        except Exception as e:
            log.warning(f"redis unavailable for short-term memory ({e}); using in-proc dict")

    def _key(self, session_id: str) -> str:
        return f"mem:short:{session_id}"

    def _load(self, session_id: str) -> dict:
        if self._client is not None:
            raw = self._client.get(self._key(session_id))
            return json.loads(raw) if raw else {"summary": "", "messages": []}
        return self._mem.setdefault(session_id, {"summary": "", "messages": []})

    def _save(self, session_id: str, state: dict) -> None:
        if self._client is not None:
            self._client.set(self._key(session_id), json.dumps(state, default=str))
        else:
            self._mem[session_id] = state

    async def append(self, session_id: str, msg: ChatMessage) -> None:
        state = self._load(session_id)
        state["messages"].append(msg.model_dump(mode="json"))
        evicted: list[dict] = []
        while len(state["messages"]) > self.window_size:
            evicted.append(state["messages"].pop(0))
        self._save(session_id, state)
        if evicted:
            asyncio.create_task(self._async_summarize(session_id, evicted))

    async def get_context(self, session_id: str) -> tuple[str, list[ChatMessage]]:
        state = self._load(session_id)
        msgs = [ChatMessage(**m) for m in state["messages"]]
        return state.get("summary", ""), msgs

    async def _async_summarize(self, session_id: str, evicted: list[dict]) -> None:
        try:
            tpl = Template(SUMMARIZE_TPL.read_text(encoding="utf-8"))
            state = self._load(session_id)
            prompt = tpl.render(old_summary=state.get("summary", ""), evicted=evicted)
            new_summary = await self.llm.ainvoke(prompt, temperature=0.2)
            state["summary"] = new_summary.strip()
            self._save(session_id, state)
            log.info(f"updated summary for {session_id}: {len(new_summary)} chars")
        except Exception as e:
            log.warning(f"summary update failed: {e}")


_stm: SlidingWindowMemory | None = None


def get_short_term() -> SlidingWindowMemory:
    global _stm
    if _stm is None:
        _stm = SlidingWindowMemory()
    return _stm
