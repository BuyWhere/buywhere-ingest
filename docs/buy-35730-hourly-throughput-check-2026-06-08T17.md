# BUY-35730 — Hourly throughput check (2026-06-08 18:20 UTC failed fire, recovered at 18:43 UTC for the 17:00–18:00 UTC window)

**Result: PASS — ~3,646,104 / 150,000 (2430.7% of threshold). No failure child filed under [BUY-29861](/BUY/issues/BUY-29861).**

## Recovery context

- The original [BUY-35730](/BUY/issues/BUY-35730) heartbeat failed at 2026-06-08T18:20:20Z with upstream adapter quota exhaustion (`429 usage limit exceeded` on `claude_local`).
- The recovery run re-used the local dispatcher logic in `scripts/hourly_throughput_dispatcher.py` against the canonical maglev catalog DB from `data/.catalog_db_url`.
- The direct hour-bucket `COUNT(*)` timed out under maglev contention after 30s, so the dispatcher fell back to the existing primary signal: `pg_stat_user_tables.products.n_tup_ins` delta.

## Just-completed hour

| Metric | Value |
|---|---|
| Window | 2026-06-08T17:00:00Z → 2026-06-08T18:00:00Z |
| Real rows (dispatcher fallback) | **~3,646,104** |
| Threshold | 150,000 |
| Margin vs. threshold | **+3,496,104 (+2330.7%)** |
| % of target | **2430.7%** |
| Signal source | `n_tup_ins_delta` |
| Secondary verification | `COUNT(*)` timed out after 30s |

## DB proof

- Canonical DB: `maglev.proxy.rlwy.net:31310/railway` from `data/.catalog_db_url`
- Dispatcher output:

```text
[throughput-dispatcher] Checking hour 2026-06-08T17:00:00+00:00 → 2026-06-08T18:00:00+00:00
[throughput-dispatcher] DB: maglev.proxy.rlwy.net:31310/railway
[throughput-dispatcher] hour_bucket_count: TIMEOUT after 30s (maglev contention — using n_tup_ins delta only)
[throughput-dispatcher] real_rows=3,646,104 target=150,000 (2430.7%) source=n_tup_ins_delta
[throughput-dispatcher] --dry-run: would NOT call the Paperclip API
  PASS=True → no-op
```

## Follow-up fix

- Patched `scripts/hourly_throughput_dispatcher.py` so `--dry-run` no longer mutates `data/.throughput_state.json`.
- Verified after the patch that a forced dry-run leaves the state-file hash unchanged.

## Disposition

**done** — recovered the failed routine fire, verified the 17:00–18:00 UTC window is well above threshold, and confirmed no failure-report child is required under [BUY-29861](/BUY/issues/BUY-29861).
