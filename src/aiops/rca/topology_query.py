"""Graph topology helpers."""
from __future__ import annotations

from aiops.rca.graph_client import get_neo4j


def upstream(service: str, depth: int = 3) -> list[dict]:
    nc = get_neo4j()
    if nc._driver is None:
        return nc._mock.get(service, [])
    q = (
        "MATCH (s:Service)-[:DEPENDS_ON*1..$d]->(t:Service {name:$name}) "
        "RETURN DISTINCT s.name AS name, 'Service' AS kind, 'UPSTREAM' AS relation"
    )
    return nc.run_cypher(q, {"name": service, "d": depth})


def downstream(service: str, depth: int = 3) -> list[dict]:
    nc = get_neo4j()
    if nc._driver is None:
        return nc._mock.get(service, [])
    q = (
        "MATCH (s:Service {name:$name})-[:DEPENDS_ON*1..$d]->(t:Service) "
        "RETURN DISTINCT t.name AS name, 'Service' AS kind, 'DOWNSTREAM' AS relation"
    )
    return nc.run_cypher(q, {"name": service, "d": depth})


def neighbors(service: str) -> list[dict]:
    return get_neo4j().neighbors(service)
