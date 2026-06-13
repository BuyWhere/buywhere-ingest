# Hourly throughput check — 2026-06-13 00:00–01:00 UTC

**Source issue:** [BUY-45125](/BUY/issues/BUY-45125) (parent [BUY-29861](/BUY/issues/BUY-29861), dispatcher [BUY-33694](/BUY/issues/BUY-33694))
**Failure child issue filed:** [BUY-45134](/BUY/issues/BUY-45134) (assignee Rich, priority `critical`, status `todo`)
**Fire timestamp:** 2026-06-13T01:04:21Z (manual heartbeat; auto-dispatcher cron still broken per [BUY-33694](/BUY/issues/BUY-33694) feedback)
**DB host:** maglev.proxy.rlwy.net:31310/railway (PRIMARY signal under maglev contention)
**Result: FAIL** — 79,813 / 150,000 rows/hr (53.2% of target, -70,187 rows/hr)

## DB-proof numbers (from pg_stat_user_tables on maglev)

| Signal | Value |
|---|---|
| Open anchor (S4, 2026-06-13T00:04:28+00:00) | `n_tup_ins = 50,656,943` |
| Close sample (S5, 2026-06-13T01:04:21+00:00) | `n_tup_ins = 50,736,601` |
| Delta (S5 − S4) | **79,658 rows** |
| Window | 0:59:53 = 0.9981h |
| Rate | **79,813 rows/hr** |
| Threshold | 150,000 rows/hr |
| % of target | **53.2%** (-70,187 rows/hr) |
| `n_live_tup` (S4 → S5) | 81,873,186 → 81,952,445 (Δ 79,259 = 79,413/hr) |
| `pg_postmaster_start_time` | 2026-06-08T10:21:09Z (4.6d prior, no restart in window → n_tup_ins delta method valid) |
| `pg_class.reltuples` (ANALYZE) | 77,343,112 |

## Signal cross-check

- **PRIMARY** — `pg_stat_user_tables.n_tup_ins` delta: **79,813/hr** (canonical signal per [BUY-33694](/BUY/issues/BUY-33694)).
- **SECONDARY** — `n_live_tup` delta: **79,413/hr** — corroborates the shortfall is real, not a pg_stat counter artifact.
- Hour-bucket `COUNT(*)` and `MAX(created_at)` skipped — maglev contention ([BUY-30590](/BUY/issues/BUY-30590) / [BUY-32878](/BUY/issues/BUY-32878) invalid index) causes timeouts on the secondary path.

## Prior hour context (recent hourly children of BUY-29861)

| Hour (UTC) | Rate | Identifier | Result |
|---|---|---|---|
| 16:00–17:00 | 285,136 rows/hr | [BUY-44277](/BUY/issues/BUY-44277) | PASS |
| 17:00–18:00 | 148,358 rows/hr | [BUY-44395](/BUY/issues/BUY-44395) | **FAIL** |
| 18:00–19:00 | 341,493 rows/hr | [BUY-44486](/BUY/issues/BUY-44486) | PASS |
| 19:00–20:00 | 237,309 rows/hr | [BUY-44582](/BUY/issues/BUY-44582) | PASS |
| 20:00–21:00 | 264,054 rows/hr | [BUY-44685](/BUY/issues/BUY-44685) | PASS |
| 21:00–22:00 | 270,277 rows/hr | [BUY-44788](/BUY/issues/BUY-44788) | PASS |
| 22:00–23:00 | 238,979 rows/hr | [BUY-44888](/BUY/issues/BUY-44888) | PASS |
| 23:00–00:00 | 117,352 rows/hr | [BUY-45014](/BUY/issues/BUY-45014) | **FAIL** |
| **00:00–01:00** | **79,813 rows/hr** | **[BUY-45134](/BUY/issues/BUY-45134)** | **FAIL** |

## Trend

**2 consecutive hourly FAILs** (23:00–24:00Z = 117,352/hr; 00:00–01:00Z = 79,813/hr). 4 of the prior 6 hours passed at >200K/hr — the rate drop is concentrated in the last two hours. The shortfall is on the maglev primary write path and the count is moving in the right direction (n_tup_ins gaining ~80K rows/hr) but well below the 150K/hr bar.

## What this means for the 06-30 goal

- Daily target: ~1.2M inserts/day. Today is 2026-06-13; 17 days remain to 2026-06-30.
- Recent closed day 2026-06-11 was a NOT A MISS (closed +14,355,924 inserts = 839% of start-of-day required pace per [BUY-42444](/BUY/issues/BUY-42444)).
- Two consecutive sub-bar hours do not yet threaten the daily target (other lanes still running), but the maglev read/write contention cap ([BUY-30590](/BUY/issues/BUY-30590)) and the `products_created_at_idx` INVALID block ([BUY-32878](/BUY/issues/BUY-32878)) remain the named ceilings on the 150K/hr sustained bar.

## Remediation pointers

- [BUY-30590](/BUY/issues/BUY-30590) — named maglev products DB read/write contention cap blocking 150K/hr (per [BUY-33624](/BUY/issues/BUY-33624)).
- [BUY-32878](/BUY/issues/BUY-32878) — `products_created_at_idx` INVALID (no-DDL-on-maglev rule per [BUY-33897](/BUY/issues/BUY-33897) per [BUY-33973](/BUY/issues/BUY-33973) central tracker).
- [BUY-33694](/BUY/issues/BUY-33694) — dispatcher parent; n_tup_ins delta is the canonical signal under maglev contention.

## Source

Oracle agent (`3ec8f6dd-1735-4479-9825-a2c42edac34c`), wake BUY-45125. Manual heartbeat at 2026-06-13T01:04:21Z (auto-dispatcher cron still broken per [BUY-33694](/BUY/issues/BUY-33694) feedback). State file `data/.throughput_state.json` updated to record this fire as the canonical 00:00–01:00Z record.
