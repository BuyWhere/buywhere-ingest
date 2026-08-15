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
INHERITED_PAPERCLIP_API_KEY="${PAPERCLIP_API_KEY:-}"
INHERITED_PAPERCLIP_RUN_ID="${PAPERCLIP_RUN_ID:-}"
INHERITED_PAPERCLIP_AGENT_ID="${PAPERCLIP_AGENT_ID:-}"
if [ -f "$HOME/.throughput_dispatcher_env" ]; then
    set -a
    . "$HOME/.throughput_dispatcher_env"
    set +a
fi
if [ -n "$INHERITED_PAPERCLIP_API_KEY" ]; then
    export PAPERCLIP_API_KEY="$INHERITED_PAPERCLIP_API_KEY"
    export PAPERCLIP_RUN_ID="$INHERITED_PAPERCLIP_RUN_ID"
fi
# Always restore agent_id: heartbeat env wins; when empty (cron.d invocation),
# clear the stale value from ~/.throughput_dispatcher_env so the mint script
# uses the correct default agent.
if [ -n "$INHERITED_PAPERCLIP_AGENT_ID" ]; then
    export PAPERCLIP_AGENT_ID="$INHERITED_PAPERCLIP_AGENT_ID"
elif [ -n "${PAPERCLIP_AGENT_ID:-}" ] && [ -z "$INHERITED_PAPERCLIP_AGENT_ID" ]; then
    unset PAPERCLIP_AGENT_ID
fi

# Normalize any sourced credentials. A whitespace-only token would make the
# downstream HTTP client emit an invalid `Bearer ` header, so treat it as absent.
if [ -n "${PAPERCLIP_API_KEY:-}" ]; then
    NORMALIZED_API_KEY="$(printf '%s' "$PAPERCLIP_API_KEY" | tr -d '[:space:]')"
    if [ -n "$NORMALIZED_API_KEY" ]; then
        export PAPERCLIP_API_KEY="$NORMALIZED_API_KEY"
    else
        unset PAPERCLIP_API_KEY
    fi
fi

if [ -n "${PAPERCLIP_API_KEY:-}" ] && ! /usr/bin/python3 - "$PAPERCLIP_API_KEY" <<'PY'
import base64
import json
import sys
import time

try:
    payload = sys.argv[1].split('.')[1]
    payload += '=' * (-len(payload) % 4)
    exp = json.loads(base64.urlsafe_b64decode(payload.encode()))['exp']
except Exception:
    sys.exit(1)

sys.exit(0 if exp > time.time() + 60 else 1)
PY
then
    unset PAPERCLIP_API_KEY
fi

# Keep X-Paperclip-Run-Id aligned with the bearer token claim. Persisted
# heartbeat credentials can otherwise combine a fresh token with a stale run id,
# which the API rejects with agent_jwt_run_id_mismatch.
if [ -n "${PAPERCLIP_API_KEY:-}" ]; then
    TOKEN_RUN_ID="$(/usr/bin/python3 - "$PAPERCLIP_API_KEY" <<'PY'
import base64
import json
import sys

try:
    payload = sys.argv[1].split('.')[1]
    payload += '=' * (-len(payload) % 4)
    print(json.loads(base64.urlsafe_b64decode(payload.encode())).get('run_id', ''))
except Exception:
    pass
PY
)"
    if [ -n "$TOKEN_RUN_ID" ]; then
        export PAPERCLIP_RUN_ID="$TOKEN_RUN_ID"
    fi
fi

# Try to mint a token from the running server if PAPERCLIP_API_KEY isn't set
if [ -z "${PAPERCLIP_API_KEY:-}" ]; then
    MINTED=$(/usr/bin/python3 "$REPO/scripts/mint-throughput-dispatcher-token.py" 2>/dev/null)
    if [ -n "$MINTED" ]; then
        export PAPERCLIP_API_KEY="$(printf '%s' "$MINTED" | tr -d '[:space:]')"
        if [ -z "${PAPERCLIP_API_KEY:-}" ]; then
            unset PAPERCLIP_API_KEY
        fi
    else
        echo "[cron-wrapper] WARNING: No PAPERCLIP_API_KEY available. Child issues will not be filed." >&2
    fi
fi

exec /usr/bin/node "$REPO/scripts/dispatcher_v6_hourly.js" "$@" >> "$LOGDIR/throughput-dispatcher-cron.log" 2>&1
