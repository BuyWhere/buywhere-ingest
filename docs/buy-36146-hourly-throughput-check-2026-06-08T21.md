# BUY-36146 — Hourly throughput check (2026-06-08 22:02 UTC fire, 21:00–22:00 UTC window)

**Result: FAIL — ~117,438 / 150,000 (78.3% of threshold; -32,562 below bar). Failure child [BUY-36158](/BUY/issues/BUY-36158) was filed under [BUY-29861](/BUY/issues/BUY-29861).**

## What was checked

- Rule from [BUY-29861](/BUY/issues/BUY-29861): if net products added to canonical PostgreSQL in the just-completed hour are below `150,000`, create a user-assigned failure issue. Otherwise do not create one.
- Canonical DB used: `maglev.proxy.rlwy.net:31310/railway` from `data/.catalog_db_url`.
- Intended check path: `scripts/hourly_throughput_dispatcher.py`.
- Actual execution path this fire: manual fallback, because the dispatcher hit a `5s` timeout on its initial `pg_stat_user_tables` read before it could reach its own `n_tup_ins_delta` fallback path.

## Result

| Metric | Value |
|---|---|
| Window | `2026-06-08T21:00:00Z` → `2026-06-08T22:00:00Z` |
| Signal source | `n_tup_ins_delta` |
| Baseline `n_tup_ins` | `18,957,792` at `2026-06-08T21:03:03.949739+00:00` |
| Current `n_tup_ins` sample | `19,076,102` at `2026-06-08 22:03:30.693358 UTC` |
| Delta rows | `118,310` |
| Delta window | `1.0074287831h` |
| Computed rows/hour | **~117,438** |
| Threshold | `150,000` |
| Margin | **-32,562** |
| % of target | **78.3%** |
| Secondary verification | `MAX(created_at)` timed out after `20s`; hour-bucket `COUNT(*)` timed out after `45s` |
| `n_live_tup` current sample | `55,701,691` |
| `n_tup_upd` current sample | `32,572,464` |
| `n_tup_del` current sample | `2,011` |

## Interpretation

The direct hour-bucket count and `MAX(created_at)` probes both timed out under maglev contention, so this report uses the dispatcher's primary signal: the delta of `pg_stat_user_tables.products.n_tup_ins` between the prior saved baseline and the current fire.

That measured rate is below the `150,000/hr` threshold, so the [BUY-29861](/BUY/issues/BUY-29861) rule is unambiguous: a failure child must be created. This run filed [BUY-36158](/BUY/issues/BUY-36158) and assigned it to the user owner.

## Dispatcher failure output

```text
[throughput-dispatcher] Checking hour 2026-06-08T21:00:00+00:00 → 2026-06-08T22:00:00+00:00
[throughput-dispatcher] DB: maglev.proxy.rlwy.net:31310/railway
Traceback (most recent call last):
  ...
psycopg2.errors.QueryCanceled: canceling statement due to statement timeout
```

## Manual DB proof

```sql
SET statement_timeout='20s';
SELECT now() AT TIME ZONE 'utc' AS sampled_at_utc, n_live_tup, n_tup_ins, n_tup_upd, n_tup_del
FROM pg_stat_user_tables
WHERE relname='products';
```

```text
       sampled_at_utc       | n_live_tup | n_tup_ins | n_tup_upd | n_tup_del
----------------------------+------------+-----------+-----------+-----------
 2026-06-08 22:03:30.693358 |   55701691 |  19076102 |  32572464 |      2011
```

```text
Baseline from data/.throughput_state.json before this fire:
  last_n_tup_ins    = 18,957,792
  last_n_tup_ins_at = 2026-06-08T21:03:03.949739+00:00

Computed rate:
  delta_rows        = 118,310
  delta_hours       = 1.0074287831
  rows_per_hour     = 117,438
```

## State file after this fire

```json
{
  "last_n_tup_ins": 19076102,
  "last_n_tup_ins_at": "2026-06-08T22:03:30.693358+00:00",
  "last_hour_checked": "2026-06-08T21:00:00+00:00",
  "last_check_result": "FAIL",
  "last_check_real_rows": 117438,
  "last_check_source": "n_tup_ins_delta",
  "last_n_live_tup": 55701691,
  "last_db_host": "maglev.proxy.rlwy.net:31310/railway",
  "last_fire_buy": "BUY-36146",
  "last_fire_note": "FAIL ~117,438 rows (78.3% of 150K) on manual n_tup_ins delta fallback after dispatcher pg_stat timeout. Failure child BUY-36158 filed.",
  "last_fire_doc": "docs/buy-36146-hourly-throughput-check-2026-06-08T21.md"
}
```

## Disposition

**done** — the hourly rule was executed, DB proof was recorded, state was advanced for the next fire, and the required failure child [BUY-36158](/BUY/issues/BUY-36158) was created for the `21:00–22:00Z` window.
