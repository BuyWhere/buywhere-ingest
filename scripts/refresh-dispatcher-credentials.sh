#!/usr/bin/env bash
# BUY-53390: Persist the current heartbeat's Paperclip API credentials so the
# hourly throughput dispatcher cron can use them. Called from agent heartbeats.
#
# The cron reads ~/.throughput_dispatcher_env and uses its PAPERCLIP_API_KEY
# and PAPERCLIP_RUN_ID to mint valid API tokens for filing child issues.

set -u

ENV_FILE="$HOME/.throughput_dispatcher_env"

# Only write when PAPERCLIP_API_KEY is actually available and non-whitespace.
TRIMMED_API_KEY="$(printf '%s' "${PAPERCLIP_API_KEY:-}" | tr -d '[:space:]')"
TRIMMED_RUN_ID="$(printf '%s' "${PAPERCLIP_RUN_ID:-}" | tr -d '[:space:]')"

if [ -n "$TRIMMED_API_KEY" ]; then
    cat > "$ENV_FILE" <<- ENVEOF
	PAPERCLIP_API_KEY="${TRIMMED_API_KEY}"
	PAPERCLIP_RUN_ID="${TRIMMED_RUN_ID}"
	PAPERCLIP_AGENT_ID="${PAPERCLIP_AGENT_ID:-a29ac9dc-cf0a-455b-964c-e75bd2f5fc47}"
	ENVEOF
    chmod 600 "$ENV_FILE"
    echo "[refresh-dispatcher-credentials] Written to $ENV_FILE"
else
    echo "[refresh-dispatcher-credentials] WARNING: PAPERCLIP_API_KEY not set — not updating credentials" >&2
fi
