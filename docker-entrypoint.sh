#!/bin/sh
# Select which process to run based on SERVICE_ROLE env var.
# Default to "server" so the old buywhere-ingest (cron producer) keeps
# its pre-BUY-33687 behavior unless explicitly overridden.
set -e

case "${SERVICE_ROLE:-server}" in
  worker)
    exec node src/worker.js
    ;;
  producer)
    exec node src/producer.js
    ;;
  server|*)
    exec npm start
    ;;
esac
