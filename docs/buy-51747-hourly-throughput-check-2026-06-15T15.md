# BUY-51747 — Hourly throughput check (2026-06-15 15:07 UTC fire, 14:00–15:00 UTC window)

**Result: PASS — 2,803,902 / 150,000 (1869.3% of threshold) via the canonical maglev `n_tup_ins` fast path. No failure child was filed under [BUY-29861](/BUY/issues/BUY-29861).**

## Rule

- From [BUY-29861](/BUY/issues/BUY-29861): if net products added to canonical PostgreSQL in the just-completed hour are below `150,000`, create a user-assigned failure issue with DB-proof numbers. Otherwise do not create one.

## DB-proof numbers

| Signal | Value |
|---|---|
| Canonical DB | `maglev.proxy.rlwy.net:31310/railway` via `data/.catalog_db_url` |
| Prior baseline timestamp | `2026-06-15T14:06:36.824184+00:00` |
| Prior baseline `n_tup_ins` | `16,689` |
| Current sample timestamp | `2026-06-15T15:07:25.834623+00:00` |
| Current sample `n_tup_ins` | `2,858,763` |
| Current sample `n_live_tup` | `2,857,635` |
| Delta rows | `2,842,074` |
| Delta window | `1.013614h` |
| Implied rate | `2,803,902/hr` |
| Threshold | `150,000/hr` |
| Margin vs threshold | `+2,653,902/hr` |
| `%` of threshold | `1869.3%` |
| `pg_postmaster_start_time()` | `2026-06-15 09:56:28.874687+00:00` |

## Notes

- This was the first clean post-restart hourly verdict after the baseline-only recovery captured in [BUY-51638](/BUY/issues/BUY-51638).
- The hour-bucket `COUNT(*)` verification for `2026-06-15T14:00:00Z` → `2026-06-15T15:00:00Z` still timed out at `30s` under maglev contention.
- The pass result is therefore based on the canonical `pg_stat_user_tables.products.n_tup_ins` delta, which was monotonic across the full sample window and safely postdated the current postmaster start time.

## Outcome

- No failure child issue should exist for the `14:00–15:00 UTC` window.
- `data/.throughput_state.json` was advanced to the new post-15:00 baseline so the next hourly routine fire can compute the next delta from a valid anchor.
