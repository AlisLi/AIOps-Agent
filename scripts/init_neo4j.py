"""Seed a tiny microservice topology into Neo4j."""
from __future__ import annotations

from aiops.core.config import settings
from aiops.core.logging import log


def main() -> None:
    try:
        from neo4j import GraphDatabase  # type: ignore
    except Exception as e:
        log.error(f"neo4j driver missing: {e}")
        return

    driver = GraphDatabase.driver(
        settings.neo4j.uri, auth=(settings.neo4j.user, settings.neo4j.password)
    )
    with driver.session() as s:
        s.run("MATCH (n) DETACH DELETE n")
        s.run("""
            MERGE (api:Service {name:'chip-api', tier:'edge'})
            MERGE (auth:Service {name:'chip-auth', tier:'mid'})
            MERGE (proxy:Service {name:'chip-db-proxy', tier:'mid'})
            MERGE (worker:Service {name:'chip-worker', tier:'core'})
            MERGE (mysql:DB {name:'mysql-defect', engine:'mysql'})
            MERGE (redis:DB {name:'redis-session', engine:'redis'})
            MERGE (api)-[:DEPENDS_ON]->(auth)
            MERGE (api)-[:DEPENDS_ON]->(proxy)
            MERGE (auth)-[:USES]->(redis)
            MERGE (proxy)-[:USES]->(mysql)
            MERGE (worker)-[:DEPENDS_ON]->(proxy)
        """)
    driver.close()
    log.info("neo4j seeded.")


if __name__ == "__main__":
    main()
