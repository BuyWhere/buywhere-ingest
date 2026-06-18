# BUY-37339 — Hourly throughput check (2026-06-09 08:04 UTC fire, 07:00–08:00 UTC window)

**Result: PASS — 165,578 / 150,000 (110.4% of threshold; +15,578 above bar). No failure child was filed under [BUY-29861](/BUY/issues/BUY-29861).**

## Scope

- Rule from [BUY-29861](/BUY/issues/BUY-29861): if net products added to canonical PostgreSQL in the just-completed hour are below `150,000`, create a user-assigned failure issue. Otherwise do not create one.
- Check path used: `python3 scripts/hourly_throughput_dispatcher.py`
- Canonical source of truth: `data/.catalog_db_url` -> `maglev.proxy.rlwy.net:31310/railway`.

## Result

| Metric | Value |
|---|---:|
| Hour checked | `2026-06-09T07:00:00+00:00 -> 2026-06-09T08:00:00+00:00` |
| Throughput signal | `n_tup_ins_delta` |
| Real rows | `165,578` |
| Threshold | `150,000` |
| Margin vs threshold | `+15,578` |
| Percent of target | `110.4%` |
| Prior baseline `n_tup_ins` | `20,366,597 @ 2026-06-09T07:04:26.106104+00:00` |
| Current sample `n_tup_ins` | `20,532,918 @ 2026-06-09T08:04:42.260056+00:00` |
| Current `n_live_tup` | `57,011,104` |

The hour-bucket COUNT probe timed out under maglev contention, so the dispatcher used the accepted primary signal: `pg_stat_user_tables.products.n_tup_ins` delta annualized across the elapsed window since the prior saved sample. That still clears the `150,000/hr` threshold, so the BUY-29861 rule is unambiguous: do not file a failure child.

## Dispatcher Output

```text
[throughput-dispatcher] Checking hour 2026-06-09T07:00:00+00:00 → 2026-06-09T08:00:00+00:00
[throughput-dispatcher] DB: maglev.proxy.rlwy.net:31310/railway
[throughput-dispatcher] hour_bucket_count: TIMEOUT after 30s (maglev contention — using n_tup_ins delta only)
[throughput-dispatcher] real_rows=165,578 target=150,000 (110.4%) source=n_tup_ins_delta
[throughput-dispatcher] PASS — 165,578 >= 150,000. No issue filed.
```

## State Advance

```json
{
  "last_n_tup_ins": 20532918,
  "last_n_tup_ins_at": "2026-06-09T08:04:42.260056+00:00",
  "last_hour_checked": "2026-06-09T07:00:00+00:00",
  "last_check_result": "PASS",
  "last_check_real_rows": 165578,
  "last_check_source": "n_tup_ins_delta",
  "last_n_live_tup": 57011104,
  "last_db_host": "maglev.proxy.rlwy.net:31310/railway"
}
```

## Disposition

- PASS hour.
- No BUY-#### failure child required under [BUY-29861](/BUY/issues/BUY-29861).
- This routine execution issue can close `done`.
