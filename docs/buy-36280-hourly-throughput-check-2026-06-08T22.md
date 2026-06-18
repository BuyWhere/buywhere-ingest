# BUY-36280 — Hourly throughput check (2026-06-08 23:05 UTC fire, 22:00–23:00 UTC window)

**Result: FAIL — ~126,890 / 150,000 (84.6% of threshold; -23,110 below bar). Failure child [BUY-36292](/BUY/issues/BUY-36292) was filed under [BUY-29861](/BUY/issues/BUY-29861).**

## What was checked

- Rule from [BUY-29861](/BUY/issues/BUY-29861): if net products added to canonical PostgreSQL in the just-completed hour are below `150,000`, create a user-assigned failure issue. Otherwise do not create one.
- Canonical DB used: `maglev.proxy.rlwy.net:31310/railway` from `data/.catalog_db_url`.
- Intended check path: `scripts/hourly_throughput_dispatcher.py`.
- Actual execution path this fire: manual fallback, using the dispatcher's primary `n_tup_ins` signal directly after bounded verification probes timed out under maglev contention.

## Result

| Metric | Value |
|---|---|
| Window | `2026-06-08T22:00:00Z` → `2026-06-08T23:00:00Z` |
| Signal source | `n_tup_ins_delta` |
| Baseline `n_tup_ins` | `19,076,102` at `2026-06-08T22:03:30.693358+00:00` |
| Current `n_tup_ins` sample | `19,207,565` at `2026-06-08 23:05:40.444595 UTC` |
| Delta rows | `131,463` |
| Delta window | `1.0360420103h` |
| Computed rows/hour | **~126,890** |
| Threshold | `150,000` |
| Margin | **-23,110** |
| % of target | **84.6%** |
| Secondary verification | `MAX(created_at)` timed out after `20s`; hour-bucket `COUNT(*)` timed out after `45s` |
| `n_live_tup` current sample | `55,833,044` |
| `n_tup_upd` current sample | `33,338,777` |
| `n_tup_del` current sample | `2,011` |
| Failure child | [BUY-36292](/BUY/issues/BUY-36292) |

## Interpretation

The direct `MAX(created_at)` and hour-bucket `COUNT(*)` probes both timed out under maglev contention, so this report uses the dispatcher's primary signal: the delta of `pg_stat_user_tables.products.n_tup_ins` between the prior saved baseline and the current fire.

That measured rate is below the `150,000/hr` threshold, so the [BUY-29861](/BUY/issues/BUY-29861) rule is unambiguous: a failure child must be created. This run filed [BUY-36292](/BUY/issues/BUY-36292) and assigned it to the user owner.

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
 2026-06-08 23:05:40.444595 |   55833044 |  19207565 |  33338777 |      2011
```

```text
Baseline from data/.throughput_state.json before this fire:
  last_n_tup_ins    = 19,076,102
  last_n_tup_ins_at = 2026-06-08T22:03:30.693358+00:00

Computed rate:
  delta_rows        = 131,463
  delta_hours       = 1.0360420103
  rows_per_hour     = 126,890
```

## Bounded verification failures

```text
SET statement_timeout='20s';
SELECT MAX(created_at) AS max_created_at FROM products;
ERROR: canceling statement due to statement timeout
```

```text
SET statement_timeout='45s';
SELECT COUNT(*) AS total_rows, ...
FROM products
WHERE created_at >= '2026-06-08T22:00:00+00:00'
  AND created_at < '2026-06-08T23:00:00+00:00';
ERROR: canceling statement due to statement timeout
```

## State file after this fire

```json
{
  "last_n_tup_ins": 19207565,
  "last_n_tup_ins_at": "2026-06-08T23:05:40.444595+00:00",
  "last_hour_checked": "2026-06-08T22:00:00+00:00",
  "last_check_result": "FAIL",
  "last_check_real_rows": 126890,
  "last_check_source": "n_tup_ins_delta",
  "last_n_live_tup": 55833044,
  "last_db_host": "maglev.proxy.rlwy.net:31310/railway",
  "last_fire_buy": "BUY-36280",
  "last_fire_note": "FAIL ~126,890 rows (84.6% of 150K) on manual n_tup_ins delta fallback after MAX(created_at) and COUNT timeouts. Failure child BUY-36292 filed.",
  "last_fire_doc": "docs/buy-36280-hourly-throughput-check-2026-06-08T22.md"
}
```

## Disposition

**done** — the hourly rule was executed, DB proof was recorded, state was advanced for the next fire, and the required failure child [BUY-36292](/BUY/issues/BUY-36292) was created for the `22:00–23:00Z` window.
