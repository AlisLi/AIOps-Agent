// Raw Cypher equivalent of scripts/init_neo4j.py — can be pasted into Neo4j Browser.
MATCH (n) DETACH DELETE n;

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
MERGE (worker)-[:DEPENDS_ON]->(proxy);
