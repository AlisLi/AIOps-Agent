"""Reranker wrapper: bge-reranker-v2-m3 + lexical-overlap fallback."""
from __future__ import annotations

from aiops.core.config import settings
from aiops.core.logging import log
from aiops.core.types import RetrievedDoc


class Reranker:
    def __init__(self) -> None:
        self._model = None
        try:
            from FlagEmbedding import FlagReranker  # type: ignore
            self._model = FlagReranker(settings.rerank.model, use_fp16=True)
            log.info(f"loaded reranker: {settings.rerank.model}")
        except Exception as e:
            log.warning(f"reranker unavailable ({e}); using lexical overlap fallback")

    def _fallback_score(self, query: str, text: str) -> float:
        q = set(query.lower().split())
        t = set(text.lower().split())
        if not q or not t:
            return 0.0
        return len(q & t) / max(len(q), 1)

    async def rerank(self, query: str, docs: list[RetrievedDoc], top_n: int | None = None) -> list[RetrievedDoc]:
        top_n = top_n or settings.rerank.top_n
        if not docs:
            return []
        pairs = [[query, d.content] for d in docs]
        if self._model is not None:
            scores = self._model.compute_score(pairs, normalize=True)
            if not isinstance(scores, list):
                scores = [float(scores)]
        else:
            scores = [self._fallback_score(query, d.content) for d in docs]
        ranked = sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)[:top_n]
        out = []
        for d, s in ranked:
            out.append(RetrievedDoc(
                doc_id=d.doc_id, content=d.content, score=float(s),
                source="rerank", metadata=d.metadata,
            ))
        return out


_reranker: Reranker | None = None


def get_reranker() -> Reranker:
    global _reranker
    if _reranker is None:
        _reranker = Reranker()
    return _reranker
