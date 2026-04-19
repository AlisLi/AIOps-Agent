import uuid

import pytest

from aiops.core.types import QueryCategory, RAGRequest
from aiops.rag.pipeline import get_pipeline
from aiops.rag.retriever_bm25 import get_bm25_retriever
from aiops.rag.retriever_vector import get_vector_retriever


@pytest.mark.asyncio
async def test_pipeline_hybrid_returns_docs():
    bm25 = get_bm25_retriever()
    vec = get_vector_retriever()
    docs = [
        ("k1", "chip-api CPU spike likely caused by chip-auth slowness"),
        ("k2", "mysql-defect slow query see chip-db-proxy"),
        ("k3", "OutOfMemoryError in chip-worker inference batch"),
    ]
    for d, c in docs:
        bm25.add(d, c)
        vec.add_local(d, c)

    pl = get_pipeline()
    req = RAGRequest(trace_id=str(uuid.uuid4()), query="chip-auth slowness", category=QueryCategory.QA, top_k=3)
    resp = await pl.run(req)
    assert len(resp.docs) > 0
    assert any("auth" in d.content.lower() for d in resp.docs)
