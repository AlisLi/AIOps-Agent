"""Create Milvus collections for knowledge base + user profile."""
from __future__ import annotations

from aiops.core.config import settings
from aiops.core.logging import log


def main() -> None:
    try:
        from pymilvus import DataType, MilvusClient  # type: ignore
    except Exception as e:
        log.error(f"pymilvus missing: {e}")
        return

    client = MilvusClient(uri=settings.milvus.uri)
    dim = settings.embedding.dim

    for name in (settings.milvus.collections["knowledge"], settings.milvus.collections["user_profile"]):
        if client.has_collection(name):
            log.info(f"collection {name} already exists")
            continue
        schema = client.create_schema(auto_id=True, enable_dynamic_field=True)
        schema.add_field("id", DataType.INT64, is_primary=True)
        if name == settings.milvus.collections["user_profile"]:
            schema.add_field("user_id", DataType.VARCHAR, max_length=64)
            schema.add_field("fact", DataType.VARCHAR, max_length=1024)
            schema.add_field("updated_at", DataType.INT64)
        else:
            schema.add_field("doc_id", DataType.VARCHAR, max_length=128)
            schema.add_field("content", DataType.VARCHAR, max_length=4096)
        schema.add_field("embedding", DataType.FLOAT_VECTOR, dim=dim)
        idx = client.prepare_index_params()
        idx.add_index(field_name="embedding", index_type="HNSW", metric_type="COSINE",
                      params={"M": 16, "efConstruction": 200})
        client.create_collection(name, schema=schema, index_params=idx)
        log.info(f"created {name}")


if __name__ == "__main__":
    main()
