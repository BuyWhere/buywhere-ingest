# BUY-30590 hourly throughput — 2026-06-05 11:00 UTC (driver: BUY-31043)

## DB proof (maglev `products.created_at`, previous 13 full UTC hours)

| Hour (UTC) | Rows | ≥150k? |
|---|---:|:---:|
| 2026-06-05 11:00 | 344,468 | YES |
| 2026-06-05 10:00 | 1,016,100 | YES |
| 2026-06-05 09:00 | 1,321,262 | YES |
| 2026-06-05 08:00 | 324,081 | YES |
| 2026-06-05 07:00 | 216,205 | YES |
| 2026-06-05 06:00 | 261,059 | YES |
| 2026-06-05 05:00 | 149,999 | NO (1 row short — streak break) |
| 2026-06-05 04:00 | 108,948 | NO |
| 2026-06-05 03:00 | 155,638 | YES |
| 2026-06-05 02:00 | 98,001 | NO |
| 2026-06-05 01:00 | 312,321 | YES |
| 2026-06-05 00:00 | 208,694 | YES |
| 2026-06-04 23:00 | 50,350 | NO |

**Consecutive hours ≥150,000 (counted backward from previous full hour): 6 / 12**
(06:00 → 11:00 UTC clear; broken at 05:00 by 149,999 — one row short.)

## Lane / process audit

All required driver processes alive:

- `buy30331-sustained-loop` (PID 1224544, up since 08:29 UTC) — running
- `buy30331-ingest-stream` — multiple active children
- `buy30590-deep-page-loop` (PID 1224515, up since 08:29 UTC) — running
- `buy30590-continuous-loop.sh target_us` × 3 — running, spawning Hex scrapers (cycles 4, 5)
- `buy30590-ingest-loop.sh` — running
- Shopper `cc-shopify-discover-v2` (tranco P3, segments 50–100) — running

## Agent status

- **Dash** (a29ac9dc) — `running`, in_progress on BUY-31015 (WooCommerce discovery lane, sustained 50k+/hr). NOT idle.
- **Shopper** (5bc984ee) — `running`, in_progress on BUY-31031 (next retailer-specific family). NOT idle.
- **Hex** (7fb55262) — agent `idle` heartbeat, but BUY-30590 target_us continuous-loop scrapers (cycles 4–5) are still producing under their workspace. Lane productive; agent-level blocked on BUY-30745 (CC myshopify exhausted) which is a discovery-source problem, not a throughput-lane stop.
- **Vera** (19dcd635) — parent BUY-30590 owner since 2026-06-05 11:40 UTC flip; last comment at 12:19 UTC counted 5/12 (pre-11:00 hour). Streak now 6/12.
- **Sigil** (8f838901) — in_progress on BUY-31016 (audit +4.21M maglev burst for fabrication patterns).

No real infrastructure cap named by Dash / Hex / Shopper this cycle. No escalation required.

## Disposition

Streak 6/12 toward BUY-30590 close criterion. Far from done — close criteria preserved. No close-out action; routine driver continues hourly.
