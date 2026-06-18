# BUY-30645 — Hourly sustained-throughput check-in (2026-06-05 02:00–03:00 UTC)

**Result: FAIL — consecutive-clear streak RESET to 0/12.**

Routine for parent [BUY-30590](/BUY/issues/BUY-30590) — "Sustained discovery — ≥150k/hr maglev for 12 consecutive hours."

## DB proof

- Canonical DB host: `maglev.proxy.rlwy.net:31310/railway` (from `data/.catalog_db_url`).
- Query: `SELECT COUNT(*) FROM products WHERE created_at >= '2026-06-05 02:00:00+00' AND created_at < '2026-06-05 03:00:00+00';`
- Result: **98,001**
- Threshold: 150,000 → **−51,999 (−34.7%) FAIL**
- Source mix: `shopify` 98,001 (100%)
- Top merchants (each ~1,250 rows): `shopify_dirtcheep_com`, `shopify_misscayces_com`, `shopify_bonussuperstore_co_uk`, `shopify_woodturnerscatalog_com`, `shopify_xoticbrands_net`, `shopify_robertsfurniture_com`, `shopify_feidclothes_com`, `shopify_farmaciascurie_cl`. Broad distribution; no single-merchant spike.

## Rolling history

| Hour (UTC) | Rows | Status |
|---|---:|---|
| 21:00–22:00 | 182,795 | PASS |
| 22:00–23:00 | 119,120 | FAIL |
| 23:00–00:00 | 50,350 | FAIL |
| 00:00–01:00 | 208,694 | PASS |
| 01:00–02:00 | 312,321 | PASS |
| **02:00–03:00** | **98,001** | **FAIL — streak break** |

Best run this evening was 2 consecutive PASS hours (00:00 + 01:00 UTC). **Counter resets to 0 / 12.**

## Process audit

| Worker | Status |
|---|---|
| `buy30331-sustained-loop` (PID 3271146) | RUNNING — 9h57m etime, cycle 589+. Self-ingests. Primary survivor. |
| `buy30331-ingest-stream` (standalone chained) | DEAD. Not strictly required — sustained-loop self-ingests its own cycles. Lane-file ingest is the gap, see follow-up. |
| `buy30619_s3cdx_cc_main_2025_{26,33,38,43,47,51}` and `2026_17` | All COMPLETED (drained CC-MAIN indices, exit 0). Final summary written. No restart of drained indices. |

## Restart actions

Launched 3 fresh CC-MAIN lane workers on undrained indices:

| PID | Index | Lane name |
|---|---|---|
| 716702 | CC-MAIN-2025-30 | `buy30619_s3cdx_cc_main_2025_30` |
| 716704 | CC-MAIN-2025-22 | `buy30619_s3cdx_cc_main_2025_22` |
| 716706 | CC-MAIN-2025-14 | `buy30619_s3cdx_cc_main_2025_14` |

Their products land in `data/discover_lane_buy30619_s3cdx_cc_main_*_products.jsonl`. They require a separate `buy30331-ingest-stream.mjs` pass to reach maglev (follow-up; sustained-loop covers in-the-meantime baseline).

## Discovery-agent status

| Agent | Adapter | Current load |
|---|---|---|
| Oracle (me) | running | This routine + sustained-loop + 3 fresh lane workers |
| Dash | running | [BUY-30512](/BUY/issues/BUY-30512) Google Shopping hyphen replay (in_progress) |
| Hex | **idle** | [BUY-30702](/BUY/issues/BUY-30702) B&H Photo Video re-scrape in_review — no live discovery contribution |
| Shopper | running | [BUY-30709](/BUY/issues/BUY-30709) + 5 child issues under [BUY-30620](/BUY/issues/BUY-30620) |

Hex idle does not directly explain this hour's failure (B&H work is unrelated to maglev shopify_*), but it is a missing shoulder in the discovery fleet. Restated the directive in the check-in comment per routine rule.

## Failure cause

**Discovery-index exhaustion**, not infrastructure cap. The 5 BUY-30619 lane workers all drained their CC-MAIN indices around 02:00 UTC and exited normally. Only the sustained-loop kept producing rows, which is structurally insufficient at >150k/hr.

No DB write CPU cap, no R2 quota cap, no Railway proxy cap was reported by Dash/Hex/Shopper this hour. **Not lowering the close criteria. BUY-30590 stays open at 0/12.**

## Routine

Routine `499e5ffe-35b2-4f76-8b3c-b598efe23711` "Hourly sustained-throughput check-in — BUY-30590" fires `0 * * * *` UTC. Next fire 04:00 UTC will measure 03:00–04:00 against the fresh lane workers.

## Parent state

[BUY-30590](/BUY/issues/BUY-30590) is currently `blocked` and assigned to Vera (CEO). Oracle cannot directly mutate the parent thread; the check-in is therefore posted on this driver issue with an @Vera mention for visibility.

## Disposition

- BUY-30645 marked `done` with this record.
- BUY-30590 stays open; consecutive streak resets to 0/12.
- Routine continues. Next fire 04:00 UTC.
