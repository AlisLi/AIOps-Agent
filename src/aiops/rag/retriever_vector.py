"""Milvus vector retriever with in-memory fallback for demos."""
from __future__ import annotations

from aiops.core.config import settings
from aiops.core.logging import log
from aiops.core.types import RetrievedDoc
from aiops.llm.embedding import get_embedder


class VectorRetriever:
    def __init__(self) -> None:
        self.collection_name = settings.milvus.collections["knowledge"]
        self.embedder = get_embedder()
        self._use_milvus = False
        self._local: list[tuple[str, str, list[float], dict]] = []  # (doc_id, content, vec, meta)
        try:
            from pymilvus import MilvusClient  # type: ignore
            self.client = MilvusClient(uri=settings.milvus.uri)
            if self.client.has_collection(self.collection_name):
                self._use_milvus = True
                log.info(f"using Milvus collection {self.collection_name}")
            else:
                log.warning(f"Milvus collection {self.collection_name} not found; fallback to local")
        except Exception as e:
            log.warning(f"Milvus unavailable ({e}); fallback to in-memory vector store")

    def add_local(self, doc_id: str, content: str, metadata: dict | None = None) -> None:
        vec = self.embedder.embed_one(content)
        self._local.append((doc_id, content, vec, metadata or {}))

    async def search(self, query: str, top_k: int = 10) -> list[RetrievedDoc]:
        vec = self.embedder.embed_one(query)
        if self._use_milvus:
            res = self.client.search(
                collection_name=self.collection_name,
                data=[vec],
                limit=top_k,
                output_fields=["content", "doc_id", "metadata"],
            )
            out = []
            for hit in res[0]:
                out.append(RetrievedDoc(
                    doc_id=str(hit.get("entity", {}).get("doc_id", hit.get("id", ""))),
                    content=hit.get("entity", {}).get("content", ""),
                    score=float(hit.get("distance", 0.0)),
                    source="vector",
                    metadata=hit.get("entity", {}).get("metadata", {}),
                ))
            return out
        # in-memory cosine
        import numpy as np
        q = np.array(vec, dtype=np.float32)
        scored: list[tuple[float, tuple]] = []
        for doc_id, content, v, meta in self._local:
            a = np.array(v, dtype=np.float32)
            sim = float(np.dot(q, a) / (np.linalg.norm(q) * np.linalg.norm(a) + 1e-9))
            scored.append((sim, (doc_id, content, meta)))
        scored.sort(reverse=True)
        out = []
        for sim, (doc_id, content, meta) in scored[:top_k]:
            out.append(RetrievedDoc(doc_id=doc_id, content=content, score=sim, source="vector", metadata=meta))
        return out


_vr: VectorRetriever | None = None


def get_vector_retriever() -> VectorRetriever:
    global _vr
    if _vr is None:
        _vr = VectorRetriever()
    return _vr
