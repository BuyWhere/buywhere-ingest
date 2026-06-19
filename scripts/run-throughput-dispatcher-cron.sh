#!/usr/bin/env bash
# BUY-53390: Hourly throughput dispatcher cron wrapper.
#
# Sets PAPERCLIP_API_URL to the production URL so that file-child-issue API
# calls don't fall back to localhost:3000.
#
# API key strategy (tried in order):
#   0. Persisted env from ~/.throughput_dispatcher_env (updated by heartbeat)
#   1. Inherited from heartbeat env (PAPERCLIP_API_KEY already set)
#   2. Minted from the running server's AGENT_JWT_SECRET
#
# If neither works, the dispatcher gracefully degrades: it still checks the DB
# and saves state, but cannot file child issues for FAIL hours.

set -u

REPO="/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default"
LOGDIR="${LOGDIR:-$REPO/logs}"
mkdir -p "$LOGDIR"

export PAPERCLIP_API_URL="https://paperclip.richteo.com"
export PAPERCLIP_COMPANY_ID="177bc805-e3c8-4336-84cb-8e1e482d5a17"

# Step 0: source persisted credentials from ~/.throughput_dispatcher_env if available
if [ -f "$HOME/.throughput_dispatcher_env" ]; then
    set -a
    . "$HOME/.throughput_dispatcher_env"
    set +a
fi

# Try to mint a token from the running server if PAPERCLIP_API_KEY isn't set
if [ -z "${PAPERCLIP_API_KEY:-}" ]; then
    MINTED=$(/usr/bin/python3 "$REPO/scripts/mint-throughput-dispatcher-token.py" 2>/dev/null)
    if [ -n "$MINTED" ]; then
        export PAPERCLIP_API_KEY="$MINTED"
    else
        echo "[cron-wrapper] WARNING: No PAPERCLIP_API_KEY available. Child issues will not be filed." >&2
    fi
fi

exec /usr/bin/python3 "$REPO/scripts/hourly_throughput_dispatcher.py" >> "$LOGDIR/throughput-dispatcher-cron.log" 2>&1
