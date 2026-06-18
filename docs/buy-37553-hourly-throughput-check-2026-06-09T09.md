# BUY-37553 — Hourly throughput check (2026-06-09 10:01 UTC fire, 09:00–10:00 UTC window)

**Result: PASS — 308,570 / 150,000 (205.7% of threshold; +158,570 above bar). No failure child was filed under [BUY-29861](/BUY/issues/BUY-29861).**

## Scope

- Rule from [BUY-29861](/BUY/issues/BUY-29861): if net products added to canonical PostgreSQL in the just-completed hour are below `150,000`, create a user-assigned failure issue. Otherwise do not create one.
- Check path used: `python3 scripts/hourly_throughput_dispatcher.py`
- Canonical source of truth: `data/.catalog_db_url` -> `maglev.proxy.rlwy.net:31310/railway`.

## Result

| Metric | Value |
|---|---:|
| Hour checked | `2026-06-09T09:00:00+00:00 -> 2026-06-09T10:00:00+00:00` |
| Throughput signal | `n_tup_ins_delta` |
| Real rows | `308,570` |
| Threshold | `150,000` |
| Margin vs threshold | `+158,570` |
| Percent of target | `205.7%` |
| Prior baseline `n_tup_ins` | `20,996,479 @ 2026-06-09T09:06:22.989025+00:00` |
| Current sample `n_tup_ins` | `21,280,750 @ 2026-06-09T10:01:39.500925+00:00` |
| Current `n_live_tup` | `57,758,149` |

The hour-bucket COUNT probe timed out under maglev contention, so the dispatcher used the accepted primary signal: `pg_stat_user_tables.products.n_tup_ins` delta annualized across the elapsed window since the prior saved sample. That still clears the `150,000/hr` threshold by a wide margin, so the BUY-29861 rule is unambiguous: do not file a failure child.

## Dispatcher Output

```text
[throughput-dispatcher] Checking hour 2026-06-09T09:00:00+00:00 → 2026-06-09T10:00:00+00:00
[throughput-dispatcher] DB: maglev.proxy.rlwy.net:31310/railway
[throughput-dispatcher] hour_bucket_count: TIMEOUT after 30s (maglev contention — using n_tup_ins delta only)
[throughput-dispatcher] real_rows=308,570 target=150,000 (205.7%) source=n_tup_ins_delta
[throughput-dispatcher] PASS — 308,570 >= 150,000. No issue filed.
```

## State Advance

```json
{
  "last_n_tup_ins": 21280750,
  "last_n_tup_ins_at": "2026-06-09T10:01:39.500925+00:00",
  "last_hour_checked": "2026-06-09T09:00:00+00:00",
  "last_check_result": "PASS",
  "last_check_real_rows": 308570,
  "last_check_source": "n_tup_ins_delta",
  "last_n_live_tup": 57758149,
  "last_db_host": "maglev.proxy.rlwy.net:31310/railway"
}
```

## Disposition

- PASS hour.
- No BUY-#### failure child required under [BUY-29861](/BUY/issues/BUY-29861).
- This routine execution issue can close `done`.
