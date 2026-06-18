# BUY-30590 hourly sustained-throughput check — 2026-06-05 21:00 UTC (driver: BUY-31746)

## Just-completed hour

| Hour (UTC) | Rows | ≥150k? | ≥200k? |
|---|---:|:---:|:---:|
| 2026-06-05 21:00 | **269,834** | **YES** | **YES** |

## DB proof (maglev `products.created_at`, last 9 hours)

| Hour (UTC) | Rows | ≥150k? | ≥200k? |
|---|---:|:---:|:---:|
| 2026-06-05 21:00 | 269,834 | YES | YES |
| 2026-06-05 20:00 | 97,076 | NO | NO |
| 2026-06-05 19:00 | 442,472 | YES | YES |
| 2026-06-05 18:00 | 376,879 | YES | YES |
| 2026-06-05 17:00 | 793,933 | YES | YES |
| 2026-06-05 16:00 | 540,716 | YES | YES |
| 2026-06-05 15:00 | 189,426 | YES | NO |
| 2026-06-05 14:00 | 525,058 | YES | YES |
| 2026-06-05 13:00 | 617,890 | YES | YES |

**Streak ≥150k (counted backward from previous full hour, 21:00 UTC): 1 hour.**
Broken at 20:00 UTC by 97,076 rows (−52,924 vs. threshold). 11 hours still needed for close.

**Streak ≥200k (CEO/Vera bar): 1 hour.** Broken at 20:00 UTC and 15:00 UTC. 23 hours still needed for new bar.

## Source mix — hour 21:00 UTC

| Bucket | Rows | Share |
|---|---:|---:|
| shopify | 269,821 | 100.00% |
| woocommerce | 13 | 0.00% |
| brand-direct (apple/samsung/dell/canon) | 0 | 0.00% |

**Source mix 100% shopify.** The brand-direct pivot (BUY-31444) and WooCommerce (BUY-31015) lanes are running but have not yet produced hour-21 rows. Direct-HTTP brand work is still in build-out (Apple 1.2k / Samsung 2.2k products on disk, not yet in maglev). Tranco/CC-MAIN merchant discovery is paused per BUY-31452.

## Lane / process audit (2026-06-05 22:12 UTC)

| Process | PID | Age | Status |
|---|---:|---:|---|
| `buy30331-sustained-loop.mjs` (main) | 2210102 | 5h38m | alive |
| `buy30331-ingest-stream.mjs` (cycle-2030) | 3318253 | 0m | alive |
| `buy30331-ingest-stream.mjs` (cycle-2032) | 3312924/5 | 1m | alive |
| `buy30331-sustained-loop --single-merchant allbirds.com` | 2540046 | 3h38m | alive |
| `buy30331-sustained-loop --single-merchant ritual.com` | 2540047 | 3h38m | alive |
| `buy30331-sustained-loop --single-merchant onnit.com` | 2540048 | 3h38m | alive |
| `buy30331-sustained-loop --single-merchant therabody.com` | 2540049 | 3h38m | alive |
| `buy30727-lane-supervisor.mjs` (root) | 2976527 | 1h26m | alive |
| `buy30727-lane-supervisor.mjs --worker crew-wc-rest` | 3186628 | 29m | alive |
| Hex `buy30620-crate-deep-page-lane.mjs` | 2934118 | 1h29m | alive (CPU 27.3%) |
| Hex `buy30620-hunt2-page-lane.mjs` | 2934003 | 1h29m | alive |
| Hex `buy30620-scout-validate-lane.mjs` | 2933874 | 1h29m | alive |
| Hex `buy30620-stock-page-lane.mjs` | 2934047 | 1h29m | alive |
| Gymshark direct ingestion (`/products.json`) | 3280298 | 8m | alive |

**No dead lanes.** All four critical loops (`buy30331-sustained-loop`, `buy30331-ingest-stream`, `buy30727-lane-supervisor`, plus the per-merchant single-loops) and the Hex BUY-30620 lanes are alive. Crew-wc-rest is running its 4h30m shift.

## Disposition

- **BUY-30590 (parent):** `in_progress`. Streak 1/12 on the original 12-consecutive ≥150k bar; 1/24 on the CEO/Vera 24-consecutive ≥200k bar. Source mix is 100% Shopify (target ≤60% Shopify, ≥20% brand-direct, ≥20% WooCommerce) — the pivot is in flight but not yet producing hour-level rows.
- **Dash / Hex / Shopper status:** All five BUY-30618/30619/30620 per-lane workers verified alive. Hex's Crate / Hunt 2 / Scout / Stock lanes are running. Shopper's sub-agents (Crate/Hunt 2/Scout/Shelf/Stock) are mostly absorbed by Hex's BUY-30620 child; no idle gaps to flag.
- **DB write path:** Healthy — just-completed hour shows 269,834 maglev inserts after the BUY-31679 asyncpg.InterfaceError incident was fixed at 21:33 UTC.
- **No infrastructure cap named** by Dash/Hex/Shopper this hour. No escalation to @Rich needed.

Next routine fire: 2026-06-05 23:07 UTC (cron `7 * * * *`).

## Query

```sql
SELECT to_char(date_trunc('hour', created_at), 'YYYY-MM-DD HH24') AS hour, count(*) AS rows
FROM products
WHERE created_at >= '2026-06-05 13:00:00+00'
  AND created_at < '2026-06-05 22:00:00+00'
GROUP BY 1
ORDER BY 1;
```
