#!/usr/bin/env bash
# Hit the FastAPI endpoints once the server is up.
set -e

BASE="${BASE:-http://localhost:8000}"

echo "[1/3] /health"
curl -sS "$BASE/health" | python -m json.tool

echo; echo "[2/3] /chat"
curl -sS -X POST "$BASE/chat" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"demo","user_id":"alice","query":"chip-api CPU 飙高要看什么?","stream":false}' \
  | python -m json.tool

echo; echo "[3/3] /alert"
curl -sS -X POST "$BASE/alert" \
  -H "Content-Type: application/json" \
  -d '{"alert_id":"a-001","service":"chip-api","metric":"cpu_usage","value":95,"threshold":80,"severity":"P1","detected_by":"vote","ts":"2026-04-19T10:00:00Z"}' \
  | python -m json.tool
