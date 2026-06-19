# BUY-53341 — API 500 outage & retrospective failure child issue filing

## Incident

On 2026-06-19 between ~01:00Z and ~04:00Z, the Paperclip API at
`https://paperclip.richteo.com` returned HTTP 500 errors for child-issue
creation POST calls from the hourly throughput dispatcher.

## Impact

| Hour (UTC) | Rows | % of Threshold | Child Issue Filed | Note |
|---|---|---|---|---|
| 01:00–02:00 | 94,572 | 63.0% | ❌ (API 500) | → BUY-53359 (retrofiled) |
| 02:00–03:00 | 8,486 | 5.7% | ❌ (API 500) | → BUY-53360 (retrofiled) |
| 03:00–04:00 | 120,152 | 80.1% | ❌ (API 500) | → BUY-53361 (retrofiled) |

All three were retroactively filed once the API recovered (~04:50Z).

## Root cause

Unknown — API returned 500 for all `POST /api/companies/{id}/issues` calls.
The dispatcher correctly caught the `raise_for_status()` exception and logged
each failure, then continued saving state locally. No data was lost.

## Dispatcher resilience gap

The dispatcher has no retry or backfill queue. When the API is down, the
failure child issue is silently dropped. This heartbeat adds a pending-retry
buffer to `data/.throughput_state.json` so that un-filed failures can be
retried on the next successful fire.

## Resolution

- BUY-53359, BUY-53360, BUY-53361 filed as children of BUY-29861.
- Dispatcher patched to buffer un-filed failures and retry on next execution.
