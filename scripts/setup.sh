#!/usr/bin/env bash
# One-shot bootstrap for AIOps-Agent infra.
# Usage:
#   bash scripts/setup.sh up        # start kafka/redis/milvus/neo4j
#   bash scripts/setup.sh down      # stop and remove
#   bash scripts/setup.sh init      # init neo4j + milvus + seed kb (requires .venv)
#   bash scripts/setup.sh logs      # tail compose logs
#   bash scripts/setup.sh ps        # compose status

set -euo pipefail

cd "$(dirname "$0")/.."

CMD="${1:-up}"

need() { command -v "$1" >/dev/null 2>&1 || { echo "[X] missing: $1"; exit 1; }; }

case "$CMD" in
  up)
    need docker
    echo "[+] starting infra: kafka, redis-stack, milvus, neo4j ..."
    docker compose up -d kafka redis etcd minio milvus neo4j
    echo "[+] waiting 15s for services to warm up ..."
    sleep 15
    docker compose ps
    cat <<EOT

[+] Ready. Service UIs:
    Kafka        -> localhost:9092
    Redis Stack  -> http://localhost:8001 (RedisInsight)
    Milvus       -> localhost:19530
    Neo4j UI     -> http://localhost:7474 (neo4j/test12345)

Next:
    cp .env.example .env
    pip install -e ".[dev]"
    bash scripts/setup.sh init
EOT
    ;;
  down)
    docker compose down -v
    ;;
  ps)
    docker compose ps
    ;;
  logs)
    docker compose logs -f --tail=200
    ;;
  init)
    need python
    python scripts/init_neo4j.py
    python scripts/init_milvus.py
    python scripts/seed_knowledge.py
    ;;
  *)
    echo "Usage: $0 {up|down|ps|logs|init}"
    exit 1
    ;;
esac
