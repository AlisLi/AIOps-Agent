"""Embedding wrapper: tries bge-m3 / sentence-transformers; falls back to deterministic hash embedding."""
from __future__ import annotations

import hashlib
from typing import Iterable

import numpy as np

from aiops.core.config import settings
from aiops.core.logging import log


class Embedder:
    def __init__(self) -> None:
        self.dim = settings.embedding.dim
        self._model = None
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
            self._model = SentenceTransformer(settings.embedding.model)
            self.dim = self._model.get_sentence_embedding_dimension() or self.dim
            log.info(f"loaded embedding model: {settings.embedding.model} dim={self.dim}")
        except Exception as e:
            log.warning(f"embedding model unavailable ({e}); using hash fallback")

    def _hash_embed(self, text: str) -> np.ndarray:
        # Deterministic pseudo-embedding so demos don't require a model download.
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        buf = (digest * (self.dim // len(digest) + 1))[: self.dim]
        vec = np.frombuffer(bytes(buf), dtype=np.uint8).astype(np.float32)
        vec = vec / (np.linalg.norm(vec) + 1e-9)
        return vec

    def embed(self, texts: Iterable[str]) -> list[list[float]]:
        texts = list(texts)
        if self._model is not None:
            vecs = self._model.encode(texts, normalize_embeddings=True)
            return [v.tolist() for v in vecs]
        return [self._hash_embed(t).tolist() for t in texts]

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]


_embedder: Embedder | None = None


def get_embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        _embedder = Embedder()
    return _embedder
