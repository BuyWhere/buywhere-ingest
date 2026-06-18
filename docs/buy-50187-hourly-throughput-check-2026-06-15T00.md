# BUY-50187 Hourly Throughput Check

Window checked: `2026-06-14T23:00:00Z` -> `2026-06-15T00:00:00Z`

Result: `FAIL` via the canonical maglev fast path.

## DB-proof numbers

| Signal | Value |
|---|---|
| Prior baseline source | `data/.throughput_state.json` from late BUY-50078 closeout |
| Prior baseline timestamp | `2026-06-14T23:38:28.894076+00:00` |
| Prior baseline `n_tup_ins` | `57,811,184` |
| Current sample timestamp | `2026-06-15T00:08:14.979873+00:00` |
| Current sample `n_tup_ins` | `57,823,398` |
| Current sample `n_live_tup` | `89,028,978` |
| Delta rows | `12,214` |
| Delta window | `0.496135h` (`29m46s`) |
| Implied rate | `24,618/hr` |
| Threshold | `150,000/hr` |
| Gap to threshold | `-125,382/hr` |
| `pg_postmaster_start_time()` | `2026-06-08 10:21:09.112373+00:00` |

## Notes

- Canonical DB access worked against `maglev.proxy.rlwy.net:31310/railway` via `data/.catalog_db_url`.
- `SELECT MAX(created_at) FROM products` timed out at `8s`.
- Hour-bucket `COUNT(*)` for `2026-06-14T23:00:00Z` -> `2026-06-15T00:00:00Z` timed out at `30s`.
- The prior routine execution `BUY-50078` ran late and only closed at `2026-06-14T23:39:46Z`, so the persisted baseline for this check starts mid-hour rather than exactly at `23:00:00Z`.
- Even with that limitation, the observed rate is still far below the threshold, so this fire should file a failure child under `BUY-29861`.
