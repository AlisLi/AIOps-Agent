"""RAG Agent — standalone service reachable via Kafka `rag.request`."""
from __future__ import annotations

from aiops.agents.base import AgentBase
from aiops.bus.topics import Topic
from aiops.core.types import RAGRequest
from aiops.rag.pipeline import get_pipeline


class RAGAgent(AgentBase):
    name = "rag"
    topics = [Topic.RAG_REQUEST]

    def __init__(self) -> None:
        super().__init__()
        self.pipeline = get_pipeline()

    async def on_message(self, topic: str, payload: dict) -> None:
        req = RAGRequest(**payload)
        resp = await self.pipeline.run(req)
        if self.producer is not None:
            await self.producer.send(Topic.RAG_RESPONSE, key=resp.trace_id, payload=resp.model_dump(mode="json"))
