"""Settings loader: YAML defaults + .env overrides."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]
CONFIG_FILE = ROOT / "configs" / "settings.yaml"
ENV_FILE = ROOT / ".env"

# 把 .env 里的值写进 os.environ，这样下面的 _apply_env_overrides 才能读到。
# pydantic-settings 的 env_file 只作用于 Settings 字段本身，不会注入全局环境变量。
try:
    from dotenv import load_dotenv

    if ENV_FILE.exists():
        load_dotenv(ENV_FILE, override=False)
except ImportError:  # python-dotenv 理论上是 pydantic-settings 的依赖，兜底一下
    pass


class AppCfg(BaseModel):
    env: str = "dev"
    log_level: str = "INFO"


class KafkaCfg(BaseModel):
    bootstrap_servers: str = "localhost:9092"
    security_protocol: str = "PLAINTEXT"


class MilvusCfg(BaseModel):
    uri: str = "http://localhost:19530"
    collections: dict = {"knowledge": "kb_main", "user_profile": "user_profile"}


class Neo4jCfg(BaseModel):
    uri: str = "bolt://localhost:7687"
    user: str = "neo4j"
    password: str = "test12345"


class RedisCfg(BaseModel):
    url: str = "redis://localhost:6379/0"


class LLMCfg(BaseModel):
    provider: str = "openai_compatible"
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-4o-mini"
    timeout: int = 30


class EmbeddingCfg(BaseModel):
    model: str = "bge-m3"
    dim: int = 1024


class RerankCfg(BaseModel):
    model: str = "bge-reranker-v2-m3"
    top_n: int = 5


class CacheCfg(BaseModel):
    ttl: int = 3600
    distance_threshold: float = 0.08


class BM25Cfg(BaseModel):
    analyzer: str = "jieba"


class RagCfg(BaseModel):
    bm25: BM25Cfg = BM25Cfg()
    cache: CacheCfg = CacheCfg()


class MemoryCfg(BaseModel):
    short_window: int = 10


class LogRule(BaseModel):
    pattern: str
    severity: str = "P2"


class MonitorCfg(BaseModel):
    interval_seconds: int = 30
    log_rules: list[LogRule] = []


class CircuitBreakerCfg(BaseModel):
    failure_threshold: int = 5
    recovery_timeout: int = 30


class ResilienceCfg(BaseModel):
    circuit_breaker: CircuitBreakerCfg = CircuitBreakerCfg()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app: AppCfg = AppCfg()
    kafka: KafkaCfg = KafkaCfg()
    milvus: MilvusCfg = MilvusCfg()
    neo4j: Neo4jCfg = Neo4jCfg()
    redis: RedisCfg = RedisCfg()
    llm: LLMCfg = LLMCfg()
    embedding: EmbeddingCfg = EmbeddingCfg()
    rerank: RerankCfg = RerankCfg()
    rag: RagCfg = RagCfg()
    memory: MemoryCfg = MemoryCfg()
    monitor: MonitorCfg = MonitorCfg()
    resilience: ResilienceCfg = ResilienceCfg()


def _apply_env_overrides(data: dict[str, Any]) -> dict[str, Any]:
    def _put(path: list[str], value: str) -> None:
        node = data
        for p in path[:-1]:
            node = node.setdefault(p, {})
        node[path[-1]] = value

    mapping = {
        "KAFKA_BOOTSTRAP": ["kafka", "bootstrap_servers"],
        "REDIS_URL": ["redis", "url"],
        "MILVUS_URI": ["milvus", "uri"],
        "NEO4J_URI": ["neo4j", "uri"],
        "NEO4J_USER": ["neo4j", "user"],
        "NEO4J_PASSWORD": ["neo4j", "password"],
        "LLM_BASE_URL": ["llm", "base_url"],
        "LLM_API_KEY": ["llm", "api_key"],
        "LLM_MODEL": ["llm", "model"],
        "APP_ENV": ["app", "env"],
        "LOG_LEVEL": ["app", "log_level"],
    }
    for k, path in mapping.items():
        v = os.getenv(k)
        if v:
            _put(path, v)
    return data


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    raw: dict[str, Any] = {}
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    raw = _apply_env_overrides(raw)
    return Settings(**raw)


settings = get_settings()
