"""Redis-Stack-based semantic cache using RediSearch + HNSW."""
from __future__ import annotations

import json

import numpy as np

from aiops.core.config import settings
from aiops.core.logging import log
from aiops.core.types import RAGResponse
from aiops.llm.embedding import get_embedder


class SemanticCache:
    INDEX = "aiops:semcache:idx"
    PREFIX = "aiops:semcache:doc:"

    def __init__(self) -> None:
        self.embedder = get_embedder()
        self.ttl = settings.rag.cache.ttl
        self.threshold = settings.rag.cache.distance_threshold
        self._client = None
        self._ok = False
        try:
            import redis  # type: ignore
            self._client = redis.Redis.from_url(settings.redis.url, decode_responses=False)
            self._ensure_index()
            self._ok = True
        except Exception as e:
            log.warning(f"redis unavailable ({e}); semantic cache disabled")

    def _ensure_index(self) -> None:
        from redis.commands.search.field import VectorField, TagField, TextField
        from redis.commands.search.indexDefinition import IndexDefinition, IndexType
        try:
            self._client.ft(self.INDEX).info()
            return
        except Exception:
            pass
        schema = (
            TagField("kind"),
            TextField("query"),
            VectorField(
                "embedding",
                "HNSW",
                {"TYPE": "FLOAT32", "DIM": self.embedder.dim, "DISTANCE_METRIC": "COSINE"},
            ),
        )
        self._client.ft(self.INDEX).create_index(
            schema,
            definition=IndexDefinition(prefix=[self.PREFIX], index_type=IndexType.HASH),
        )
        log.info(f"created semantic cache index {self.INDEX}")

    async def get(self, query: str) -> RAGResponse | None:
        if not self._ok:
            return None
        vec = np.array(self.embedder.embed_one(query), dtype=np.float32).tobytes()
        from redis.commands.search.query import Query
        q = (
            Query("*=>[KNN 1 @embedding $vec AS dist]")
            .return_fields("payload", "dist")
            .dialect(2)
            .paging(0, 1)
        )
        try:
            res = self._client.ft(self.INDEX).search(q, query_params={"vec": vec})
        except Exception as e:
            log.warning(f"semantic cache search failed: {e}")
            return None
        if not res.docs:
            return None
        doc = res.docs[0]
        dist = float(doc.dist)
        if dist > self.threshold:
            return None
        payload = json.loads(doc.payload)
        resp = RAGResponse(**payload)
        resp.from_cache = True
        return resp

    async def set(self, query: str, resp: RAGResponse) -> None:
        if not self._ok:
            return
        vec = np.array(self.embedder.embed_one(query), dtype=np.float32).tobytes()
        key = f"{self.PREFIX}{abs(hash(query))}"
        mapping = {
            "kind": "rag",
            "query": query,
            "embedding": vec,
            "payload": resp.model_dump_json(),
        }
        self._client.hset(key, mapping=mapping)
        self._client.expire(key, self.ttl)


_sc: SemanticCache | None = None


def get_cache() -> SemanticCache:
    global _sc
    if _sc is None:
        _sc = SemanticCache()
    return _sc
