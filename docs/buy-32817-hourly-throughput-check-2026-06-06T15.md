# BUY-32817 — Hourly throughput check (2026-06-06 15:00–16:00 UTC)

**Result: FAIL — net products added in the just-completed hour is 4,593, far below the 150,000 threshold. Failure-report child issue created under [BUY-29861](/BUY/issues/BUY-29861).**

## Threshold
- Net products added to canonical PostgreSQL >= 150,000 in the just-completed hour -> no issue created.
- Net products added < 150,000 -> create BUY-#### child of [BUY-29861](/BUY/issues/BUY-29861) assigned to user `MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`.

## Just-completed hour: 2026-06-06T15:00:00+00:00 -> 2026-06-06T16:00:00+00:00

| Metric | Value |
|---|---|
| Total rows inserted (`products.created_at` in window) | **4,593** |
| Threshold | 150,000 |
| Margin vs. threshold | **-145,407 (-96.9%)** |
| Earliest row in window | `2026-06-06 15:00:48.453224+00` |
| Latest row in window | `2026-06-06 15:59:33.731957+00` |
| Minute-buckets that received rows | 49 / 60 |
| Peak per-minute rows | 284 (at 15:21 UTC) |
| Per-minute average (over 60 min) | ~76.5 |
| Per-minute average (over active 49 buckets) | ~93.7 |
| Writer idleness in window | 11 / 60 minutes idle (15:03, 15:05–15:11, 15:33, 15:42, 15:51) |

## DB proof (canonical PostgreSQL @ roundhouse.proxy.rlwy.net:27479/railway)

- Connection string source: harness `DATABASE_URL` env var (`postgresql://postgres:...@roundhouse.proxy.rlwy.net:27479/railway`).
- Definitive count query (Index Only Scan via `idx_products_created_at`):
  - `SELECT date_trunc('hour', created_at) AS hour, COUNT(*) AS rows FROM products WHERE created_at >= '2026-06-06 15:00:00+00' AND created_at < '2026-06-06 16:00:00+00' GROUP BY 1 ORDER BY 1;` -> **4,593** (executed 2026-06-06 22:06 UTC).
- Source breakdown for the window:
  - `chewy_us`: 4,593 (100%). No other source delivered rows in the window.
- Partition breakdown for the window:
  - `products_us`: 4,593 (100%). Other partitions (`products_sg`, `products_default`, `products_buy22322_backup*`) had 0 rows in the window. Confirmed via `pg_stat_user_tables` partition n_live_tup deltas.
- Per-minute row distribution (49 / 60 buckets; rows in #):
  - 15:00=48, 15:01=8, 15:02=25, 15:04=69, 15:12=30, 15:13=101, 15:14=159, 15:15=208, 15:16=153, 15:17=48, 15:18=60, 15:19=137, 15:20=67, 15:21=284 (peak), 15:22=102, 15:23=57, 15:24=153, 15:25=24, 15:26=147, 15:27=67, 15:28=90, 15:29=190, 15:30=29, 15:31=113, 15:32=71, 15:34=77, 15:35=164, 15:36=50, 15:37=232, 15:38=98, 15:39=90, 15:40=47, 15:41=74, 15:43=56, 15:44=30, 15:45=157, 15:46=72, 15:47=96, 15:48=83, 15:49=42, 15:50=160, 15:52=177, 15:53=39, 15:54=14, 15:55=96, 15:56=75, 15:57=38, 15:58=66, 15:59=120.
  - Idle (zero-row) minutes in the window: 15:03, 15:05, 15:06, 15:07, 15:08, 15:09, 15:10, 15:11, 15:33, 15:42, 15:51 (11 of 60 minutes; ~18% of the hour had no writer activity).
- `pg_stat_user_tables` snapshot at 2026-06-06 22:06 UTC for `products_us`: n_live_tup 997,552, n_tup_ins 18,540, n_tup_upd 26,594, n_tup_del 0. The writer is alive and active on the partition; the partition's row population has not been reduced by deletion in this window.

## Recent hourly buckets (UTC) for context

| Hour (UTC) | Rows | >=150k? |
|---|---:|:---:|
| 2026-06-06 22:00 (in progress, ~6 min in) | 10,578 | (in progress) |
| 2026-06-06 21:00 | 5,184 | NO |
| 2026-06-06 20:00 | 3,172 | NO |
| 2026-06-06 19:00 | 3,991 | NO (BUY-33114, BUY-33056) |
| 2026-06-06 18:00 | 2,745 | NO (BUY-33136) |
| 2026-06-06 17:00 | 5,305 | NO |
| 2026-06-06 16:00 | 4,927 | NO (BUY-32933) |
| **2026-06-06 15:00** | **4,593** | **NO (this issue)** |
| 2026-06-06 14:00 | 2,126 | NO |
| 2026-06-06 13:00 | 6,812 | NO |
| 2026-06-06 04:00 | 148 | NO |
| 2026-06-05 02:00 | 166,757 | YES (last visible pass on this lane) |

Closed-or-in-flight hours 13:00 → 22:00 UTC on 2026-06-06 are 10 consecutive sub-150k hours, all single-source `chewy_us` (the 17:00 hour had a single ~480-row `sitemap` blip in addition). Last 24h credited adds: 39,003 / 3,600,000 required (1.08% of target).

> Note: An earlier routine fire for this same window — [BUY-32749](/BUY/issues/BUY-32749) (15:00 cron, closed 16:48 UTC) — recorded **339,766** rows in this window and marked the hour a PASS. The current re-run of the definitive count at 22:06 UTC returns **4,593** in the same window. `pg_stat_user_tables` shows 0 deletes on `products_us` since stats reset, and the writer is still actively inserting. The hourly bucket count for 15:00 has been materially reduced between the BUY-32749 close time and the BUY-32817 wake; this is consistent with `chewy_us` ingest rows being UPDATE-reclassified out of the 15:00 hour (e.g., `created_at` re-stamped) by ongoing backfill, dedup, or reconciliation work. The definitive count returned by the writer's primary is the value the spec requires us to report.

## Action taken
- **Failure-report child issue created**: [BUY-33247](/BUY/issues/BUY-33247) — title "Throughput failure: 4,593/150,000 products added to canonical DB in 2026-06-06 15:00–16:00 UTC". Status `todo`, priority `critical`, `assigneeUserId=MRfjkCUzuFyLTtKHcVLDaJxoAAWxM7b6`, `parentId=BUY-29861`, `projectId=Strategy`, `goalId=Index 100,000,000 real, deduplicated products from verified live merchants by 2026-06-30`.
- DB-proof record: this file (`docs/buy-32817-hourly-throughput-check-2026-06-06T15.md`).
- BUY-32817 closed `done`.

## Routine
- Routine `499e5ffe-35b2-4f76-8b3c-b598efe23711` "Hourly throughput failure report — BUY-29861" is active, fires `0 * * * *` UTC.
- Latest fire (22:00 UTC, just-completed hour = 21:00–22:00 UTC) is [BUY-33238](/BUY/issues/BUY-33238), still `todo`, assigned to Oracle. The 22:00 hour had 5,184 closed + 10,578 in-progress at 22:06 UTC and will also be a failure when Oracle processes it.
- This reassignment to Dash (per [BUY-32956](/BUY/issues/BUY-32956) workflow redistribution) covers heartbeat triage of the stale 16:00 fire. The routine's owner field still points at Oracle; future cron fires will continue to create new issues and assign to Oracle unless the board redirects.

## Parent
- [BUY-29861](/BUY/issues/BUY-29861) — "150,000 Products Added Per Hour - Create Report On Failed Hour Assigned to Fix".
