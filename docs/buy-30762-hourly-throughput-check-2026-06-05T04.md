# BUY-30762 — Hourly sustained-throughput check (2026-06-05 03:00–04:00 UTC)

**Result: PASS — 202,843 ≥ 150,000. Consecutive PASS count: 1/12.**

## Just-completed hour: 2026-06-05T03:00:00+00:00 → 2026-06-05T04:00:00+00:00

| Metric | Value |
|---|---|
| Rows inserted (`products.created_at` in window) | **202,843** |
| Threshold | 150,000 |
| Margin | **+52,843 (+35.2%)** |
| Disposition | **PASS** |

DB proof: `SELECT COUNT(*) FROM products WHERE created_at >= '2026-06-05 03:00:00+00' AND created_at < '2026-06-05 04:00:00+00';` against `data/.catalog_db_url` (maglev) → `202843`.

## Consecutive-hours-clear count toward 12

| Hour (UTC) | Rows | Disposition |
|---|---:|---|
| 2026-06-05 00:00–01:00 | 208,694 | PASS |
| 2026-06-05 01:00–02:00 | 312,321 | PASS |
| 2026-06-05 02:00–03:00 | 98,001 | **FAIL — streak reset** |
| **2026-06-05 03:00–04:00** | **202,843** | **PASS** |

**Streak after 03:00 hour: 1/12.** 11 more consecutive PASS hours required to close BUY-30590.

## Process audit

| Process | PID | Etime | Status | Action |
|---|---|---|---|---|
| `buy30331-sustained-loop.mjs` | 3271146 | 11h12m | running | none |
| `buy30331-ingest-stream.mjs` | 826619 | 8m42s | running (cycle 698) | none |
| `buy30727-lane-supervisor.mjs` | 787316 | 29m | running, TARGET_ACTIVE=5 | none |
| CC-MAIN per-lane workers | various | <60s each | spawning, saturating with `new_merchants=0` | upstream pool exhausted — see BUY-30727 |
| `cc-shopify-s3cdx` (standalone) | n/a | n/a | not present | superseded by supervisor |
| BUY-30618/30619/30620 per-lane workers | n/a | n/a | not present | folded into supervisor |

CC-MAIN pool exhaustion is captured under [BUY-30727](/BUY/issues/BUY-30727) (lane supervisor) — not a fresh blocker. The supervisor is cycling 5 active lanes with N+2 headroom and 3-second respawn; no dead-lane restart action this hour.

## Source mix (per BUY-30757 same-hour breakdown)

| Source | Rows | Share |
|---|---:|---:|
| shopify (sustained-loop) | 144,699 | 71.3% |
| google_shopping | 47,205 | 23.3% |
| shopify_carbon38 | 5,840 | 2.9% |
| other long-tail shopify | balance | — |

## Team status

| Agent | Status | Note |
|---|---|---|
| Oracle | running | this run |
| Hex | running | active assignments |
| Shopper | running | google_shopping batches under [BUY-30620](/BUY/issues/BUY-30620) |
| **Dash** | **idle (0 open work)** | sub-issue created restating directive |

## Action taken

- Posted hour-proof + streak count to [BUY-30590](/BUY/issues/BUY-30590).
- Created sub-issue assigning Dash to contribute a producer lane (Dash idle, streak at 1/12).
- BUY-30762 closed `done`.

## Escalation

No real infrastructure cap named by Dash/Hex/Shopper this hour. CC-MAIN pool exhaustion is a content-source cap, not a DB/R2/Railway cap — handled under [BUY-30727](/BUY/issues/BUY-30727), not escalated to Rich.

## Routine

Hourly routine continues; next fire at 05:00 UTC will measure 04:00–05:00.
