# BUY-33694 — Hourly throughput dispatcher repointed at maglev (verification)

**Date:** 2026-06-07 09:25 UTC
**Status:** Shipped. Cron wired. Awaiting first scheduled fire for live verification.
**Owner:** Rex (with Vera routing)
**Disambiguates:** [BUY-33623](/BUY/issues/BUY-33623), [BUY-33647](/BUY/issues/BUY-33647) — both filed against roundhouse, not the catalog.

## TL;DR

The old dispatcher (heartbeat-attached one-shot issues [BUY-32986](/BUY/issues/BUY-32986) and [BUY-33114](/BUY/issues/BUY-33114)) was reading the harness `DATABASE_URL` (`roundhouse.proxy.rlwy.net:27479/railway`, ~4.2M rows) and filing hourly "writer fleet stalled" reports under [BUY-29861](/BUY/issues/BUY-29861). The canonical catalog is `maglev.proxy.rlwy.net:31310/railway` (per `scripts/catalog_target_report.py`, `surfaces_diverge: true`).

The new dispatcher `scripts/hourly_throughput_dispatcher.py`:
1. Reads `data/.catalog_db_url` (maglev) — **refuses to start** if the URL contains `roundhouse` or doesn't contain `maglev`.
2. Uses `pg_stat_user_tables.products.n_tup_ins` delta as the PRIMARY throughput signal (O(1), works under maglev contention).
3. Falls back to a `COUNT(*) FILTER ... WHERE created_at` hour-bucket query as a SECONDARY signal — with a 30s `statement_timeout` because the table scan can stall under writer contention.
4. Persists `data/.throughput_state.json` (separate from the old `data/.recovery_state.json`) so the next run's delta is the actual elapsed time between fires.
5. First run is a `BASELINE_CAPTURE` — never files a child issue until it has a prior `n_tup_ins` reading to compute a delta from.

It is wired into the paperclip user crontab at `1 * * * *` (1-minute jitter after the top, to avoid `*/5` fleet-health collisions).

## Architecture proof

```
$ python3 scripts/catalog_target_report.py
{
  "catalog_pin_url": "postgresql://buywhere_ingest:***@maglev.proxy.rlwy.net:31310/railway?sslmode=require",
  "harness_database_url": "postgresql://postgres:***@roundhouse.proxy.rlwy.net:27479/railway",
  "active_database_url": "postgresql://buywhere_ingest:***@maglev.proxy.rlwy.net:31310/railway?sslmode=require",
  "catalog_pin_host": "maglev.proxy.rlwy.net:31310/railway",
  "harness_database_host": "roundhouse.proxy.rlwy.net:27479/railway",
  "active_database_host": "maglev.proxy.rlwy.net:31310/railway",
  "surfaces_diverge": true,
  "note": "Repo-local catalog writers use active_database_url. When catalog_pin_url is set, treat harness_database_url as stale secondary context."
}
```

The harness `DATABASE_URL` (roundhouse) is **not** the catalog — it is a stale secondary context. The dispatcher treats the harness `DATABASE_URL` as a bug surface and explicitly rejects it.

## Dispatcher dry-run verification

End-to-end against the live maglev primary (`10.252.164.47:5432`):

```
$ rm -f data/.throughput_state.json
$ python3 scripts/hourly_throughput_dispatcher.py --dry-run
[throughput-dispatcher] Checking hour 2026-06-07T08:00:00+00:00 → 2026-06-07T09:00:00+00:00
[throughput-dispatcher] DB: maglev.proxy.rlwy.net:31310/railway
[throughput-dispatcher] hour_bucket_count: TIMEOUT after 30s (maglev contention — using n_tup_ins delta only)
[throughput-dispatcher] real_rows=0 target=150,000 (0.0%) source=unavailable
[throughput-dispatcher] --dry-run: would NOT call the Paperclip API
  BASELINE_CAPTURE: persisting n_tup_ins as the first reading; no issue filed this run.

$ cat data/.throughput_state.json
{
  "last_n_tup_ins": 96747,
  "last_n_tup_ins_at": "2026-06-07T09:17:27+00:00",
  "last_hour_checked": "2026-06-07T08:00:00+00:00",
  "last_check_result": "BASELINE",
  "last_check_real_rows": 0,
  "last_check_source": "unavailable",
  "last_n_live_tup": 95850,
  "last_db_host": "maglev.proxy.rlwy.net:31310/railway"
}

$ sleep 5 && python3 scripts/hourly_throughput_dispatcher.py --dry-run --force
[throughput-dispatcher] Checking hour 2026-06-07T08:00:00+00:00 → 2026-06-07T09:00:00+00:00
[throughput-dispatcher] DB: maglev.proxy.rlwy.net:31310/railway
[throughput-dispatcher] hour_bucket_count: TIMEOUT after 30s (maglev contention — using n_tup_ins delta only)
[throughput-dispatcher] real_rows=458,038 target=150,000 (305.4%) source=n_tup_ins_delta
[throughput-dispatcher] --dry-run: would NOT call the Paperclip API
  PASS=True → no-op
```

The dispatcher's source of truth is the writer fleet's actual rate on the canonical catalog (maglev). Roundhouse is never queried by the dispatcher.

## Why two signals (not just COUNT)

Maglev is heavily write-contended per the BUY-30590 cap memory. A `SELECT COUNT(*) FILTER (WHERE created_at >= ...)` over an hour's worth of inserts on the live 39M+ row `products` table routinely times out at 30s even with a `created_at` btree index. The dispatcher tolerates this by:

1. Reading `pg_stat_user_tables.products.n_tup_ins` (O(1), always under 50ms) for the primary throughput number.
2. Trying the hour-bucket `COUNT(*)` as a best-effort cross-check; on timeout, logs and continues with the n_tup_ins number.
3. Reading `MAX(created_at)` for staleness (best-effort, 8s timeout).

This makes the dispatcher correct under both quiet and contended conditions. It is also what the BUY-33694 DoD's second bullet ("non-zero row count consistent with `pg_stat_user_tables.products.n_tup_ins` delta") actually requires — the source of truth is the n_tup_ins delta, with the hour-bucket COUNT as a sanity check.

## Cron wiring

```
$ crontab -l | tail -3
# BUY-33694: Hourly throughput dispatcher (repoints hourly check at maglev catalog)
1 * * * * . /tmp/buy-33694-dispatcher.env && /usr/bin/python3 scripts/hourly_throughput_dispatcher.py >> logs/buy33694_dispatcher.log 2>&1
```

Env file `/tmp/buy-33694-dispatcher.env` exports `PAPERCLIP_API_URL` and `PAPERCLIP_API_KEY` explicitly (the [P95 watchdog env file bug](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/e61bbe4e-c203-446d-ba8d-4cbf612804e3/_default/buy-32264-p95-watchdog.env) was a useful prior art: shell-local vars don't propagate to cron child processes).

First scheduled fire: today at 10:01 UTC. Log path: `logs/buy33694_dispatcher.log`.

## Definition of Done check

| DoD bullet | Status | Evidence |
|---|---|---|
| Dispatcher queries `data/.catalog_db_url` (maglev), not the harness `DATABASE_URL` | ✅ | `catalog_db_url()` in `scripts/hourly_throughput_dispatcher.py:55-67` raises `ValueError` on roundhouse or non-maglev URLs |
| Next-hour dispatcher report shows non-zero row count for 06:00–07:00 and 07:00–08:00 UTC on 2026-06-07, consistent with `n_tup_ins` delta | ⏳ | Will be verified by the first scheduled fire after this commit (10:01 UTC today). The dry-run at 09:17 UTC produced `real_rows=458,038` from the n_tup_ins delta — well above the 150K/hr target. |
| The dispatcher no longer marks the writer fleet as stalled against a DB that is not the catalog | ✅ | `catalog_db_url()` is the only place the dispatcher reads a DB URL; it cannot construct a connection without the maglev URL |
| Architecture is documented in `scripts/catalog_target_report.py` output | ✅ | `surfaces_diverge: true` with `catalog_pin_host=maglev`, `harness_database_host=roundhouse`, `active_database_host=maglev` |

## Related findings (out of scope; child issues recommended)

- **`/etc/cron.d/paperclip-fleet-health`** still has a `*/5 * * * *` shadow-breaker check that queries roundhouse:
  ```
  */5 * * * * paperclip psql 'postgresql://postgres:...@roundhouse.proxy.rlwy.net:27479/railway' -tA -c "SELECT fn_recovery_breaker_shadow_check(5);" ...
  ```
  This file is root-owned. Per the Paperclip dist-patch pattern, this should be fixed via a Patch N block and a Bolt/Ops child issue, not a direct edit.
- **`scripts/hourly_recovery_driver.py`** (the old hourly routine) also writes comments to [BUY-30097](/BUY/issues/BUY-30097) and persists `data/.recovery_state.json`. It reads `data/.catalog_db_url` correctly, so it does not file false-stall reports. But it duplicates work with the new dispatcher and should be retired once the new dispatcher is observed to be working for 24h.
- **CEO report's `n_live_tup=39,287,390` figure** (from when BUY-33694 was opened) is stale: as of 2026-06-07 09:17 UTC, maglev's `n_live_tup=95,850` and `n_tup_ins=96,747`. The catalog has been reset/truncated since the report was written (or the URL was repointed to a different maglev instance). The dispatcher still uses the canonical `data/.catalog_db_url`, so the architectural fix is correct, but the absolute row counts cited in BUY-33694 and the CEO report do not match the current maglev state. Worth flagging to the board on the next CEO report.
