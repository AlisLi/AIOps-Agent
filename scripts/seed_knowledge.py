"""Seed sample knowledge into vector + BM25 indexes (and Milvus if present)."""
from __future__ import annotations

import time

from aiops.core.config import settings
from aiops.core.logging import log
from aiops.llm.embedding import get_embedder
from aiops.rag.retriever_bm25 import get_bm25_retriever
from aiops.rag.retriever_vector import get_vector_retriever

KB = [
    ("kb-001", "chip-api 的 CPU 飙高常由上游 chip-auth 鉴权慢引起，先看 auth 的 redis 连接与 QPS。"),
    ("kb-002", "mysql-defect 出现慢查询时，优先检查 chip-db-proxy 的连接池配置与 slow_log。"),
    ("kb-003", "OutOfMemoryError 在 chip-worker 常与批量推理任务并发度过高相关，建议限流或临时扩容。"),
    ("kb-004", "redis-session 连接拒绝多为客户端未重连或 maxclients 满，先观察 redis-stack 的 CLIENT LIST。"),
    ("kb-005", "panic: nil pointer dereference 通常是上游推送了未初始化字段，回滚到上一个稳定版本并查看 diff。"),
    ("kb-006", "芯片缺陷告警流程：monitor -> kafka -> rca -> heal，全链路 trace_id 串联。"),
]


def main() -> None:
    bm25 = get_bm25_retriever()
    vec = get_vector_retriever()

    # local indexes always populated (BM25 is in-process; vector falls back to in-memory)
    for doc_id, content in KB:
        bm25.add(doc_id, content)
        vec.add_local(doc_id, content)

    # best-effort Milvus seed
    try:
        from pymilvus import MilvusClient  # type: ignore
        client = MilvusClient(uri=settings.milvus.uri)
        col = settings.milvus.collections["knowledge"]
        if client.has_collection(col):
            emb = get_embedder()
            rows = [
                {"doc_id": d, "content": c, "embedding": emb.embed_one(c)}
                for d, c in KB
            ]
            client.insert(collection_name=col, data=rows)
            log.info(f"inserted {len(rows)} docs into milvus {col}")
    except Exception as e:
        log.warning(f"milvus seed skipped ({e})")

    log.info(f"seeded {len(KB)} docs (bm25 + vector local)")
    time.sleep(0.2)


if __name__ == "__main__":
    main()
