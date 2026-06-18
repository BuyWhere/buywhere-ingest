# BUY-49861 — Hourly throughput check (2026-06-14 20:00 UTC fire, 19:00–20:00 UTC window)

**Result: PASS — ~304,334 / 150,000 (202.9% of threshold; +154,334 above bar). No failure child was filed under [BUY-29861](/BUY/issues/BUY-29861).**

## Rule

- From [BUY-29861](/BUY/issues/BUY-29861): if net products added to canonical PostgreSQL in the just-completed hour are below `150,000`, create a user-assigned failure issue. Otherwise do not create one.

## Evidence

| Signal | Value |
|---|---|
| Throughput source | `n_tup_ins_delta` |
| Prior baseline `n_tup_ins` | `57,500,833 @ 2026-06-14T19:03:44.688552+00:00` |
| Current sample `n_tup_ins` | `57,801,175 @ 2026-06-14T20:02:57.471474+00:00` |
| Delta rows | `300,342` |
| Delta hours | `0.986884145` |
| Annualized rate | `304,334/hr` |
| Threshold | `150,000/hr` |
| `n_live_tup` at sample | `89,006,755` |
| `pg_postmaster_start_time()` | `2026-06-08 10:21:09.112373+00:00` |
| Canonical DB | `maglev.proxy.rlwy.net:31310/railway` |

The dispatcher refreshed `data/.throughput_state.json` for the `2026-06-14T19:00:00Z` to `2026-06-14T20:00:00Z` hour and recorded:

```json
{
  "last_check_result": "PASS",
  "last_check_real_rows": 304334,
  "last_check_source": "n_tup_ins_delta",
  "last_hour_window_start": "2026-06-14T19:00:00+00:00",
  "last_hour_window_end": "2026-06-14T20:00:00+00:00",
  "last_issue_identifier": null
}
```

## Outcome

- The just-completed hour cleared the BUY-29861 threshold by `154,334 rows/hr`.
- No failure-report child was created.
- This routine execution can close at `done`.
