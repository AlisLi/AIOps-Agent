"""RAG pipeline: adaptive strategy + hybrid retrieval + RRF + rerank + semantic cache."""
from __future__ import annotations

import asyncio

from aiops.core.logging import log
from aiops.core.types import QueryCategory, RAGRequest, RAGResponse
from aiops.llm.rerank import get_reranker
from aiops.rag.fusion import rrf_fuse
from aiops.rag.retriever_bm25 import get_bm25_retriever
from aiops.rag.retriever_vector import get_vector_retriever
from aiops.rag.semantic_cache import get_cache


class RAGPipeline:
    def __init__(self) -> None:
        self.vector = get_vector_retriever()
        self.bm25 = get_bm25_retriever()
        self.reranker = get_reranker()
        self.cache = get_cache()

    def _weights(self, cat: QueryCategory) -> tuple[float, float, bool]:
        """Return (vector_w, bm25_w, use_bm25)."""
        if cat is QueryCategory.QA:
            return 1.0, 1.0, True
        if cat is QueryCategory.RESOURCE_ALERT:
            return 1.0, 0.0, False  # vector-only
        # LOG_ERROR
        return 0.3, 1.0, True  # lexical-heavy

    async def run(self, req: RAGRequest) -> RAGResponse:
        with log.contextualize(trace_id=req.trace_id):
            cached = await self.cache.get(req.query)
            if cached is not None:
                log.info("RAG cache hit")
                cached.trace_id = req.trace_id
                return cached

            vw, bw, use_bm25 = self._weights(req.category)
            tasks = [self.vector.search(req.query, top_k=req.top_k)]
            if use_bm25:
                tasks.append(self.bm25.search(req.query, top_k=req.top_k))
            results = await asyncio.gather(*tasks)

            lists = [results[0]]
            weights = [vw]
            if use_bm25:
                lists.append(results[1])
                weights.append(bw)

            fused = rrf_fuse(lists, k=60, weights=weights)
            reranked = await self.reranker.rerank(req.query, fused)

            resp = RAGResponse(trace_id=req.trace_id, docs=reranked, from_cache=False)
            try:
                await self.cache.set(req.query, resp)
            except Exception as e:  # noqa
                log.warning(f"cache set failed: {e}")
            return resp


_pipeline: RAGPipeline | None = None


def get_pipeline() -> RAGPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = RAGPipeline()
    return _pipeline
