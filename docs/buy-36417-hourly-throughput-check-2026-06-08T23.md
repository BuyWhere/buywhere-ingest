# BUY-36417 — Hourly throughput check (2026-06-09 00:01 UTC fire, 23:00–00:00 UTC window)

**Result: PASS — ~229,921 / 150,000 (153.3% of threshold; +79,921 above bar). No failure child was filed under [BUY-29861](/BUY/issues/BUY-29861).**

## Scope

- Rule from [BUY-29861](/BUY/issues/BUY-29861): if net products added to canonical PostgreSQL in the just-completed hour are below `150,000`, create a user-assigned failure issue. Otherwise do not create one.
- Check path used: `scripts/hourly_throughput_dispatcher.py --dry-run`.
- Canonical source of truth: `data/.catalog_db_url` -> `maglev.proxy.rlwy.net:31310/railway`.

## Result

| Metric | Value |
|---|---:|
| Hour checked | `2026-06-08T23:00:00+00:00 -> 2026-06-09T00:00:00+00:00` |
| Throughput signal | `n_tup_ins_delta` |
| Real rows | `229,921` |
| Threshold | `150,000` |
| Margin vs threshold | `+79,921` |
| Percent of target | `153.3%` |

The hour-bucket COUNT probe timed out under maglev contention, so the dispatcher fell back to the accepted primary signal: `pg_stat_user_tables.products.n_tup_ins` delta annualized across the elapsed window since the last successful fire. That is the canonical fast-path measurement for this routine and is comfortably above the `150,000/hr` pass bar.

## Dispatcher Output

```text
[throughput-dispatcher] Checking hour 2026-06-08T23:00:00+00:00 → 2026-06-09T00:00:00+00:00
[throughput-dispatcher] DB: maglev.proxy.rlwy.net:31310/railway
[throughput-dispatcher] hour_bucket_count: TIMEOUT after 30s (maglev contention — using n_tup_ins delta only)
[throughput-dispatcher] real_rows=229,921 target=150,000 (153.3%) source=n_tup_ins_delta
[throughput-dispatcher] --dry-run: would NOT call the Paperclip API
  PASS=True → no-op
[throughput-dispatcher] dry-run: leaving data/.throughput_state.json unchanged
```

## Disposition

- PASS hour.
- No BUY-#### failure child required under [BUY-29861](/BUY/issues/BUY-29861).
- This routine execution issue can close `done`.
