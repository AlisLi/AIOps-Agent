"""Reciprocal Rank Fusion."""
from __future__ import annotations

from aiops.core.types import RetrievedDoc


def rrf_fuse(lists: list[list[RetrievedDoc]], k: int = 60, weights: list[float] | None = None) -> list[RetrievedDoc]:
    """Fuse multiple ranked lists. score(d) = sum w_i / (k + rank_i)."""
    if weights is None:
        weights = [1.0] * len(lists)
    table: dict[str, tuple[float, RetrievedDoc]] = {}
    for wi, docs in zip(weights, lists):
        for rank, d in enumerate(docs, start=1):
            inc = wi / (k + rank)
            if d.doc_id in table:
                prev_score, prev_doc = table[d.doc_id]
                table[d.doc_id] = (prev_score + inc, prev_doc)
            else:
                table[d.doc_id] = (inc, d)
    merged = sorted(table.values(), key=lambda x: x[0], reverse=True)
    out = []
    for s, d in merged:
        out.append(RetrievedDoc(
            doc_id=d.doc_id, content=d.content, score=float(s),
            source="fused", metadata=d.metadata,
        ))
    return out
