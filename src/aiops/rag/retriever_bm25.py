"""BM25 retriever with jieba tokenizer for Chinese."""
from __future__ import annotations

from aiops.core.logging import log
from aiops.core.types import RetrievedDoc


def _tokenize(text: str) -> list[str]:
    try:
        import jieba  # type: ignore
        return [t for t in jieba.lcut(text) if t.strip()]
    except Exception:
        return text.lower().split()


class BM25Retriever:
    def __init__(self) -> None:
        self._corpus_tokens: list[list[str]] = []
        self._docs: list[RetrievedDoc] = []
        self._bm25 = None

    def add(self, doc_id: str, content: str, metadata: dict | None = None) -> None:
        tokens = _tokenize(content)
        self._corpus_tokens.append(tokens)
        self._docs.append(RetrievedDoc(
            doc_id=doc_id, content=content, score=0.0, source="bm25", metadata=metadata or {}
        ))
        self._bm25 = None  # invalidate

    def _ensure_index(self) -> None:
        if self._bm25 is not None:
            return
        try:
            from rank_bm25 import BM25Okapi  # type: ignore
            self._bm25 = BM25Okapi(self._corpus_tokens or [[""]])
        except Exception as e:
            log.warning(f"rank-bm25 unavailable ({e}); bm25 disabled")

    async def search(self, query: str, top_k: int = 10) -> list[RetrievedDoc]:
        if not self._docs:
            return []
        self._ensure_index()
        if self._bm25 is None:
            return []
        tokens = _tokenize(query)
        scores = self._bm25.get_scores(tokens)
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:top_k]
        out = []
        for idx, s in ranked:
            d = self._docs[idx]
            out.append(RetrievedDoc(
                doc_id=d.doc_id, content=d.content, score=float(s),
                source="bm25", metadata=d.metadata,
            ))
        return out


_br: BM25Retriever | None = None


def get_bm25_retriever() -> BM25Retriever:
    global _br
    if _br is None:
        _br = BM25Retriever()
    return _br
