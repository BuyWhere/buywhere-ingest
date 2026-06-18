# BUY-53060 — Hourly throughput check (2026-06-18 18:08 UTC fire, 17:00–18:00 UTC window)

**Result: PASS — 671,205 / 150,000 (447.5% of threshold) via the canonical maglev `n_tup_ins` fast path. No failure child was filed under [BUY-29861](/BUY/issues/BUY-29861).**

## Rule

- From [BUY-29861](/BUY/issues/BUY-29861): if net products added to canonical PostgreSQL in the just-completed hour are below `150,000`, create a user-assigned failure issue with DB-proof numbers. Otherwise do not create one.

## DB-proof numbers

| Signal | Value |
|---|---|
| Canonical DB | `maglev.proxy.rlwy.net:31310/railway` via `data/.catalog_db_url` |
| Prior baseline timestamp | `2026-06-18T16:42:18.792588+00:00` |
| Prior baseline `n_tup_ins` | `29,188,596` |
| Current sample timestamp | `2026-06-18T18:08:39.640822+00:00` |
| Current sample `n_tup_ins` | `30,154,544` |
| Current sample `n_live_tup` | `125,873,568` |
| Delta rows | `965,948` |
| Delta window | `1.439h` |
| Implied rate | `671,205/hr` |
| Threshold | `150,000/hr` |
| Margin vs threshold | `+521,205/hr` |
| `%` of threshold | `447.5%` |
| `pg_postmaster_start_time()` | `2026-06-16 08:52:01.162919+00:00` (unchanged since prior fire) |
| Hour-bucket `COUNT(*)` | timed out at `30s` (maglev contention; `last_check_source=n_tup_ins_delta`) |

## Notes

- Run executed at `2026-06-18 18:08:39Z` by `Dash` (codex_local) via `python3 scripts/hourly_throughput_dispatcher.py` from heartbeat BUY-53060.
- The dispatcher was last invoked at `2026-06-18T16:42:18Z` (BUY-52972 incident response) and produced a 15:00-16:00Z PASS. The 18:08Z fire evaluates the just-completed 17:00-18:00Z window.
- `n_tup_ins` advanced `965,948` rows in `1.439h` since the previous fire, implying a sustained `~671k/hr` insert rate.
- `n_live_tup` is `125,873,568` — `+966,004` since the prior fire (matches the `n_tup_ins` delta and confirms no offsetting deletion on the catalog).
- The `COUNT(*)` verification for the 17:00-18:00Z window timed out at `30s` under maglev contention, as expected; the fast-path delta is the canonical verdict (per BUY-33694 dispatcher design and the BUY-51747 closeout format).
- `pg_postmaster_start_time()` is unchanged from the prior fire, so the delta is purely within the same postmaster session — no stats reset has occurred.

## Outcome

- No failure child issue should exist for the `17:00–18:00 UTC` window.
- `data/.throughput_state.json` was advanced to the new post-18:00 baseline so the next hourly routine fire can compute the next delta from a valid anchor (`last_n_tup_ins=30,154,544` at `2026-06-18T18:08:39Z`).
- Dispatcher remains healthy and idempotent; BUY-52687 dedup fix still in effect (parentId-scoped child lookup keyed on the en-dash window tag).
