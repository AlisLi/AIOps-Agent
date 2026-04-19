"""Long-term memory: user profile / preferences in Milvus."""
from __future__ import annotations

import json
import time

from aiops.core.config import settings
from aiops.core.logging import log
from aiops.core.types import ChatMessage
from aiops.llm.client import get_llm
from aiops.llm.embedding import get_embedder

EXTRACT_PROMPT = (
    "从对话中抽取用户画像或偏好（如角色、偏好语言、关心的服务模块等），"
    "每条一行，最多 5 条，若无则输出 NONE。\n对话：\n{}"
)


class LongTermMemory:
    def __init__(self) -> None:
        self.collection = settings.milvus.collections["user_profile"]
        self.embedder = get_embedder()
        self.llm = get_llm()
        self._client = None
        self._local: list[dict] = []
        try:
            from pymilvus import MilvusClient  # type: ignore
            self._client = MilvusClient(uri=settings.milvus.uri)
        except Exception as e:
            log.warning(f"milvus unavailable ({e}); long-term memory using in-proc list")

    async def extract_and_store(self, user_id: str, dialogue: list[ChatMessage]) -> None:
        dlg = "\n".join(f"[{m.role}] {m.content}" for m in dialogue)
        prompt = EXTRACT_PROMPT.format(dlg)
        text = await self.llm.ainvoke(prompt, temperature=0.0)
        lines = [ln.strip("-• ").strip() for ln in text.splitlines() if ln.strip()]
        lines = [ln for ln in lines if ln and ln.upper() != "NONE"]
        if not lines:
            return
        vectors = self.embedder.embed(lines)
        ts = int(time.time())
        rows = [
            {"user_id": user_id, "fact": fact, "embedding": vec, "updated_at": ts}
            for fact, vec in zip(lines, vectors)
        ]
        if self._client is not None and self._client.has_collection(self.collection):
            try:
                self._client.insert(collection_name=self.collection, data=rows)
                return
            except Exception as e:
                log.warning(f"milvus insert failed: {e}")
        self._local.extend(rows)

    async def recall(self, user_id: str, query: str, top_k: int = 5) -> list[str]:
        vec = self.embedder.embed_one(query)
        if self._client is not None and self._client.has_collection(self.collection):
            try:
                res = self._client.search(
                    collection_name=self.collection,
                    data=[vec],
                    limit=top_k,
                    filter=f'user_id == "{user_id}"',
                    output_fields=["fact"],
                )
                return [h.get("entity", {}).get("fact", "") for h in res[0]]
            except Exception as e:
                log.warning(f"milvus search failed: {e}")
        import numpy as np
        q = np.array(vec, dtype=np.float32)
        scored = []
        for row in self._local:
            if row["user_id"] != user_id:
                continue
            a = np.array(row["embedding"], dtype=np.float32)
            sim = float(np.dot(q, a) / (np.linalg.norm(q) * np.linalg.norm(a) + 1e-9))
            scored.append((sim, row["fact"]))
        scored.sort(reverse=True)
        return [f for _, f in scored[:top_k]]


_ltm: LongTermMemory | None = None


def get_long_term() -> LongTermMemory:
    global _ltm
    if _ltm is None:
        _ltm = LongTermMemory()
    return _ltm
