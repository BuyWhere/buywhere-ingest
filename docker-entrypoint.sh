#!/bin/sh
# Debug entrypoint — logs every step to stderr so Railway captures it.
exec 2>&1
LOG=/tmp/entrypoint.log
{
  echo "[entrypoint] === START $(date -u +%FT%TZ) ==="
  echo "[entrypoint] SERVICE_ROLE=${SERVICE_ROLE:-server} PORT=${PORT} args=$*"
  echo "[entrypoint] NODE_ENV=$NODE_ENV PWD=$(pwd)"
  echo "[entrypoint] whoami=$(id -u):$(id -g) hostname=$(hostname)"
  echo "[entrypoint] node: $(which node) ($(node --version 2>&1))"
  echo "[entrypoint] /app contents: $(ls /app 2>/dev/null | tr '\n' ' ')"
} >> "$LOG" 2>&1

set -e
case "${SERVICE_ROLE:-server}" in
  worker)
    echo "[entrypoint] routing to node src/worker.js" >> "$LOG" 2>&1
    cd /app
    exec node src/worker.js
    ;;
  producer)
    echo "[entrypoint] routing to node src/producer.js" >> "$LOG" 2>&1
    cd /app
    exec node src/producer.js
    ;;
  server)
    echo "[entrypoint] routing to npm start" >> "$LOG" 2>&1
    cd /app
    exec npm start
    ;;
  *)
    echo "[entrypoint] routing to npm start (default for SERVICE_ROLE=$SERVICE_ROLE)" >> "$LOG" 2>&1
    cd /app
    exec npm start
    ;;
esac
