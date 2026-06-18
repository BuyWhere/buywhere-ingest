#!/usr/bin/env bash
# Minimal in-place helper: PATCH /api/issues/$1 with status $2 and a markdown body from stdin
set -euo pipefail
ISSUE_ID="$1"
STATUS="$2"
shift 2
BODY="$(cat)"
exec curl -sS -X PATCH "$PAPERCLIP_API_URL/api/issues/$ISSUE_ID" \
  -H "Authorization: Bearer $PAPERCLIP_API_KEY" \
  -H "X-Paperclip-Run-Id: $PAPERCLIP_RUN_ID" \
  -H "Content-Type: application/json" \
  --data-raw "$(jq -nc --arg body "$BODY" --arg status "$STATUS" --arg run "$PAPERCLIP_RUN_ID" '{status:$status, comment:$body, runId:$run}')"
