"""Neo4j client wrapper."""
from __future__ import annotations

from typing import Any

from aiops.core.config import settings
from aiops.core.logging import log


class Neo4jClient:
    def __init__(self) -> None:
        self._driver = None
        self._mock: dict[str, list[dict]] = {}  # service -> list of neighbor records
        try:
            from neo4j import GraphDatabase  # type: ignore
            self._driver = GraphDatabase.driver(
                settings.neo4j.uri,
                auth=(settings.neo4j.user, settings.neo4j.password),
            )
            self._driver.verify_connectivity()
            log.info("neo4j connected")
        except Exception as e:
            log.warning(f"neo4j unavailable ({e}); using in-memory mock graph")
            self._seed_mock()

    def _seed_mock(self) -> None:
        self._mock = {
            "chip-api": [
                {"kind": "Service", "name": "chip-auth", "relation": "DEPENDS_ON"},
                {"kind": "Service", "name": "chip-db-proxy", "relation": "DEPENDS_ON"},
            ],
            "chip-db-proxy": [
                {"kind": "DB", "name": "mysql-defect", "relation": "USES"},
            ],
            "chip-auth": [
                {"kind": "DB", "name": "redis-session", "relation": "USES"},
            ],
        }

    def close(self) -> None:
        if self._driver is not None:
            self._driver.close()

    def run_cypher(self, cypher: str, params: dict[str, Any] | None = None) -> list[dict]:
        if self._driver is None:
            return []
        with self._driver.session() as s:
            return [dict(r) for r in s.run(cypher, params or {})]

    def neighbors(self, service: str, depth: int = 1) -> list[dict]:
        if self._driver is None:
            return self._mock.get(service, [])
        q = (
            "MATCH (s:Service {name:$name})-[r]->(n) "
            "RETURN labels(n)[0] AS kind, n.name AS name, type(r) AS relation LIMIT 20"
        )
        return self.run_cypher(q, {"name": service})


_nc: Neo4jClient | None = None


def get_neo4j() -> Neo4jClient:
    global _nc
    if _nc is None:
        _nc = Neo4jClient()
    return _nc
