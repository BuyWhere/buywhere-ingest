# BUY-50591 — Hourly throughput check (2026-06-15 03:04 UTC fire, 02:00–03:00 UTC window)

**Result: FAIL — dispatcher filed [BUY-50597](/BUY/issues/BUY-50597) under [BUY-29861](/BUY/issues/BUY-29861), but the failure mode was a broken signal rather than a clean low-throughput measurement.**

## Rule

- From [BUY-29861](/BUY/issues/BUY-29861): if net products added to canonical PostgreSQL in the just-completed hour are below `150,000`, create a user-assigned failure issue with DB-proof numbers.

## Evidence

| Signal | Value |
|---|---|
| Throughput source selected by dispatcher | `unavailable` |
| Prior baseline `n_tup_ins` | `57,839,447 @ 2026-06-15T02:05:59.607842+00:00` |
| Current sample `n_tup_ins` | `43 @ 2026-06-15T03:04:56.202238+00:00` |
| Live recheck `n_tup_ins` | `63 @ 2026-06-15T03:06:03.484771+00:00` |
| `n_live_tup` at dispatcher sample | `0` |
| `n_live_tup` at live recheck | `0` |
| Delta rows vs prior baseline | `-57,839,404` |
| Delta hours | `0.983498` |
| Computed rate | unavailable; dispatcher reported `0/hr` |
| Threshold | `150,000/hr` |
| `pg_postmaster_start_time()` | `2026-06-08 10:21:09.112373+00:00` |
| Canonical DB | `maglev.proxy.rlwy.net:31310/railway` |

## What happened

- Canonical DB access succeeded against `data/.catalog_db_url` on maglev.
- The hour-bucket `COUNT(*)` verification timed out at `30s`.
- `SELECT MAX(created_at) FROM products` timed out at `8s`.
- The fast-path `pg_stat_user_tables.products.n_tup_ins` counter was non-monotonic: it dropped from `57,839,447` on the prior fire to `43` on this fire, while `pg_postmaster_start_time()` remained unchanged.
- A live recheck one minute later still showed `n_tup_ins=63` and `n_live_tup=0`, so this was not a one-sample parsing glitch.
- Because the primary signal became invalid and the secondary signal timed out, the dispatcher fell back to `source=unavailable`, treated the hour as failed, and filed [BUY-50597](/BUY/issues/BUY-50597).

## Assessment

- This heartbeat did leave the required failure-report child issue in place.
- The reported `0/hr` is not a trustworthy measurement of actual product ingest for `02:00–03:00 UTC`; it is a conservative outcome caused by a `pg_stat` counter reset/zeroing event on maglev.
- The dispatcher state was refreshed to the new low baseline (`n_tup_ins=43`), so the next hourly fire can resume monotonic delta measurements from the reset counter.

## Outcome

- Filed failure child: [BUY-50597](/BUY/issues/BUY-50597)
- Recorded the signal anomaly and DB-proof numbers in this execution artifact.
- This routine execution can close at `done`.
