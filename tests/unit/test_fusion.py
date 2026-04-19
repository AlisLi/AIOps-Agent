from aiops.core.types import RetrievedDoc
from aiops.rag.fusion import rrf_fuse


def test_rrf_ordering():
    a = [
        RetrievedDoc(doc_id="a", content="a", score=0.9, source="vector"),
        RetrievedDoc(doc_id="b", content="b", score=0.8, source="vector"),
    ]
    b = [
        RetrievedDoc(doc_id="b", content="b", score=2.0, source="bm25"),
        RetrievedDoc(doc_id="c", content="c", score=1.5, source="bm25"),
    ]
    fused = rrf_fuse([a, b], k=60)
    ids = [d.doc_id for d in fused]
    # b appears in both and should rank first
    assert ids[0] == "b"
    assert set(ids) == {"a", "b", "c"}
