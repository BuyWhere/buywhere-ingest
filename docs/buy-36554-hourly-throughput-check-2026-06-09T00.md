# BUY-36554 — Hourly throughput check (2026-06-09 01:05 UTC fire, 00:00–01:00 UTC window)

**Result: PASS — reconstructed ~364,136 / 150,000 (242.8% of threshold; +214,136 above bar). No failure child was filed under [BUY-29861](/BUY/issues/BUY-29861).**

## Scope

- Rule from [BUY-29861](/BUY/issues/BUY-29861): if net products added to canonical PostgreSQL in the just-completed hour are below `150,000`, create a user-assigned failure issue. Otherwise do not create one.
- Canonical source of truth: `data/.catalog_db_url` -> `maglev.proxy.rlwy.net:31310/railway`.
- This execution issue was a `process_lost_retry`. The real dispatcher run crashed before it could persist state because `pg_stat_user_tables.products` hit the hardcoded `5s` timeout.

## Result

| Metric | Value |
|---|---:|
| Hour checked | `2026-06-09T00:00:00+00:00 -> 2026-06-09T01:00:00+00:00` |
| Throughput signal | `n_tup_ins_delta` (reconstructed) |
| Reconstructed real rows | `364,136` |
| Threshold | `150,000` |
| Margin vs threshold | `+214,136` |
| Percent of target | `242.8%` |

## Reconstruction Method

The exact hour-bucket `COUNT(*)` probe timed out manually at `45s`, and `MAX(created_at)` also timed out at `20s`, so the only usable live signal was `pg_stat_user_tables.products.n_tup_ins`.

Available readings:

- Prior persisted baseline from [BUY-36280](/BUY/issues/BUY-36280): `n_tup_ins = 19,207,565` at `2026-06-08T23:05:40.444595+00:00`.
- Prior documented PASS from [BUY-36417](/BUY/issues/BUY-36417): `~229,921/hr` for the `23:00–00:00 UTC` window, measured over the elapsed sample ending at `2026-06-09 00:01 UTC`.
- Live manual catalog read during this retry: `n_tup_ins = 19,816,115` at `2026-06-09T01:06:20.364761+00:00`.

Reconstruction:

1. Convert the prior documented `229,921/hr` rate into inserted rows across its actual `23:05:40 -> 00:01:00 UTC` sample: about `212,010` rows.
2. Subtract that from the total live delta since the stale baseline: `19,816,115 - 19,207,565 = 608,550`.
3. Annualize the remaining `~396,540` inserted rows over the `00:01:00 -> 01:06:20 UTC` sample to get `~364,136/hr`.

Even with the reconstruction caveat, the measured rate is still comfortably above the `150,000/hr` threshold, so the [BUY-29861](/BUY/issues/BUY-29861) rule is unambiguous: **do not create a failure issue**.

## Dispatcher Failure

```text
[throughput-dispatcher] Checking hour 2026-06-09T00:00:00+00:00 → 2026-06-09T01:00:00+00:00
[throughput-dispatcher] DB: maglev.proxy.rlwy.net:31310/railway
psycopg2.errors.QueryCanceled: canceling statement due to statement timeout
```

## Follow-through

- Hardened `scripts/hourly_throughput_dispatcher.py` so the `pg_stat_user_tables` fast path retries once at `20s` before failing.
- Advanced `data/.throughput_state.json` to the live `01:06:20 UTC` baseline from this retry so the next hourly fire measures from a fresh checkpoint instead of the stale `23:05 UTC` one.
- PASS hour.
- No BUY-#### failure child required under [BUY-29861](/BUY/issues/BUY-29861).
- This routine execution issue can close `done`.
