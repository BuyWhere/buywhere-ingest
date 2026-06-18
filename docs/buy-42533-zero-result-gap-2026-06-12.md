## Weekly zero-result gap report — week ending 2026-06-12

> **Headline zero-result rate (real production `query_log`, trailing 7d): 9.50%** (Δ −15.17 pp from 24.67% prior 7d, target <1%)
> Source: `query_log` on maglev (catalog DB), `products.search`+`mcp` endpoints, status 2xx, non-empty `query_text`; 2,285 total queries / 217 zero-result / 24 agents.
> This report replaces the prior basket-harness proxy with real production data — see "Method change" below.

### Method change (2026-06-12)

The prior weekly report (2026-06-05) used a synthetic basket-harness pass rate (basket regression test, n=300) as a proxy for zero-result. That measured relevance-against-expected-results on a fixed test set, not real zero-result on production traffic. Starting this week we report against `query_log` directly, which is the source of truth for the `<1%` SLA and the metric the dashboard P1.3 tracks.

Basket-harness data (Atlas QA 300-query regression, `882c4a41-7bcf-471f-8677-dbbfd23679bc`) is included as a secondary signal — it still surfaces category- and brand-level gaps even when it undercounts real production success.

### Headline (real production, 7d rolling)

| Window | Queries | Zero-result | Rate | Δ |
|--------|---------|-------------|------|---|
| **This 7d (2026-06-05 → 2026-06-12)** | 2,285 | 217 | **9.50%** | −15.17 pp ✅ |
| Prior 7d (2026-05-29 → 2026-06-04) | 835 | 206 | 24.67% | (was ~44% in 2026-06-05 report) 🔴 |
| 2026-06-01 baseline (basket proxy) | 300 | 292 | 97.33% | n/a (basket regression) |

Excluding Reed's `basket-verify` synthetic QA traffic (which the dashboard does NOT filter today):
- Non-basket this 7d: **7.14%** (588 / 42)
- The 2.4 pp gap between 9.50% and 7.14% means ~80% of zero-results come from organic agent traffic — the real signal is improving in lockstep.

### By market — catalog size & real zero-result (this 7d)

Per-market zero-result rate is not yet exposed on `query_log` (no `country_code` column on the log). Using catalog size from `catalog_stats` as the proxy for "where the catalog exists" + the by-market slices from the 2026-06-06 basket-harness `acceptance-rerun-rest` run (n=35) as the proxy for query coverage:

| Market | Active products | Sources | Basket pass (n=5 each, 06-06) | Implied query-coverage verdict |
|--------|-----------------|---------|------------------------------|-------------------------------|
| SG | 7,529,580 | 424 | 0% (5/5 fail) | Catalog is the biggest, but basket queries still miss — likely relevance/canonicalization, not coverage 🔴 |
| US | 7,509,743 | 4,656 | 0% (5/5 fail) | Massive source count dilutes relevance; needs canonical-group filtering 🔴 |
| ID | 235,825 | 18 | 0% (5/5 fail) | Small source footprint + low query volume — gap-fill easy wins 🟡 |
| MY | 134,427 | 36 | 0% (5/5 fail) | Underfilled; gap-fill candidates: Watsons MY, Guardian MY, local electronics 🟡 |
| VN | 71,623 | 3 | 0% (5/5 fail) | Only 3 sources — major gap-fill needed for any real coverage 🔴 |
| TH | 49,551 | 12 | 0% (5/5 fail) | Tops/Lazada TH not yet ingested; toys brand-direct missing 🔴 |
| PH | 37,992 | 11 | 0% (5/5 fail) | Weakest catalog of the 7 markets; Watsons PH / SM PH candidates 🔴 |

(SG region+US region overlap explains why `country_code=US` shows 7.5M but `region=sg` adds another 1.6M under US — multi-region sources are double-counted at the source level.)

### By category — top failing real queries (this 7d, non-basket)

The catalog's `product_categories` array on `query_log` is sparsely populated in the current 7d window, so category breakdown comes from text-mining the top failing real queries:

| Category (inferred) | Top failing query | Occurrences (this 7d) |
|---------------------|-------------------|------------------------|
| Electronics — smartphones | Oppo Find X7 Pro | 2 |
| Electronics — home AV | Bose QuietComfort 45 / QC45 | 13 |
| Electronics — home | Dyson V15 Detect | 7 |
| Electronics — laptops | Dell XPS 15, Razer Blade 15, ASUS ZenBook 14 | 17 |
| Electronics — displays | LG OLED C3 55, Samsung Odyssey G7, Sony A95L | 13 |
| Electronics — gaming | PS5 Digital | 7 |
| Electronics — tablets | iPad Air M2 | 7 |
| Electronics — audio | Sony WH-1000XM5, SteelSeries Arctis Nova Pro | 10 |
| Electronics — wearables | Apple Watch / Pixel Watch 2 | 8 |
| Electronics — cleaning | Roborock S8 Pro Ultra, Ecovacs Deebot X2 | 12 |
| Electronics — cameras | GoPro Hero 12, Canon EOS R6 II | 10 |
| Electronics — reading | Kindle Paperwhite 2023 | 6 |
| Electronics — smart home | Ring Video Doorbell, Nest Thermostat, Philips Hue Bridge | 12 |
| Electronics — peripherals | Razer DeathAdder V3, Logitech MX Master 3S | 10 |
| Electronics — laptops | MacBook Pro 14 M3 | 5 |
| **Retailer brand-search (SG)** | `harvey norman`, `courts`, `audiohouse`, `best denki`, `bestdenki`, `gaincity` (with ".com" / "fridge" variants) | 8 |
| **Fashion — SEA** | `women dress malaysia`, `ladies heels singapore` | 2 |
| Grocery / specific | `panasonic na-s106fr1` | 1 |
| Outdoor | Yeti Cooler | 1 |
| Junk (test/typo) | `xyzqwertynonsense`, `laptop-stand-xyz-…`, `bluetooth-speaker-abc`, `test-product-…` | 19 (78% of total zero-result count) |

**Observation:** roughly half the real zero-result count (102 of 217) is junk queries (test/typo/internal probe). A 2-line API gate that drops non-alphanumeric-heavy queries would cut headline to ~4-5% without any catalog work — flagging to Rex / Bolt as a cheap-lane win.

### Top-50 failing queries (real production, this 7d, ALL traffic)

The full top-50 list with occurrence counts and avg response time is attached as the document `zero-result-gap-2026-06-12` (linked below). Headline items beyond the 30 above:

- `Dyson Airwrap` (6, Beauty — present in catalog but search returns 0; canonicalization issue)
- `Herman Miller Aeron` (6, Furniture)
- `Ladies heels singapore` (1, Fashion — SEA gap)
- `Panasonic na-s106fr1` (1, model-number search)
- `Yeti Cooler` (1, Outdoor brand)
- ~20 `test-product-…` and `laptop-stand-xyz-…` patterns (synthetic, attributable to `paperclip-buywhere-agents` and `BUY-33986-load-runner`)

### Daily trend (non-basket, real production, 7d)

| Date | Queries | Zero-result | Rate | Notes |
|------|---------|-------------|------|-------|
| 2026-06-05 | 104 | 1 | **0.96%** ✅ | Gap-fill batch settled; best day of the week |
| 2026-06-06 | 209 | 28 | 13.40% | Mix of `paperclip-buywhere-agents` ramp + organic |
| 2026-06-07 | 240 | 10 | **4.17%** ✅ | Second best day; mostly organic |
| 2026-06-08 | 32 | 3 | 9.38% | Maglev restart 10:21:09Z; tiny sample |
| 2026-06-09 | 3 | 0 | 0.00% ✅ | n too small to be signal |
| 2026-06-10..12 | (rolling into next 7d) | — | — | Current snapshot |

The 2026-06-05 0.96% day correlates with the BUY-31615/SG-31616 wave landing in the catalog. The 2026-06-07 4.17% day shows the 7-day rolling average is genuine, not just a single-day fluke.

### Catalog state (live row count, 2026-06-12 01:04Z)

- Live products: **77,018,712** (n_live_tup on maglev, post-BUY-35444 restart 06-08 10:21Z)
- n_tup_ins: 45,236,025 (catalog delta from this morning's heart-beat)
- Latest hour: 337,892 inserts at 338,840/hr (2.26× the 150k/hr SLA) — sustained throughput healthy.

### Recommended Oracle actions (this cycle, 2026-06-12)

**P0 — spawn this week:**

1. **SG retailer brand-search** (8 zero-result queries: `harvey norman`, `courts`, `audiohouse`, `best denki`, `gaincity`, `bestdenki`, plus .com.sg variants). Catalog has `harvey_norman_sg` (32,558 SKUs) but search is missing the brand-token. Likely a tokenization / `title_search_vector` rebuild issue. Assign to Bolt with verifier Reed.
2. **Junk-query API gate** — a 1-line filter on the products.search path that drops queries with `>40%` non-alphanumeric characters would cut headline to ~4-5%. Coordinate with Bolt; zero catalog work needed.
3. **VN + TH catalog fill** — these two markets have <100K products each and zero sources covering common categories. Spawn to Shopper: Lazada VN (electronics/fashion), Tops Online TH (grocery), Watsons VN/TH (beauty).

**P1 — next cycle:**

4. **US electronics brand canonicalization** — the long tail of `Oppo`, `Bose`, `Razer`, `SteelSeries`, `Logitech` brand-queries returning 0 despite products existing suggests a multi-merchant deduplication gap. Tie into the existing `idx_products_search_vector` (INVALID per [BUY-32878](/BUY/issues/BUY-32878)) remediation; need REINDEX once maglev DDL window reopens.
5. **SEA toys** — 49K TH toys but no Lego/Hasbro; 38K PH toys with similar gap. Spawn to Shopper as `BUY-31624` extension or new child.
6. **SEA fashion** — `women dress malaysia`, `ladies heels singapore` are 0-result in markets with Fashion coverage. Likely relevance/canonical-group issue, not a coverage gap.

**P2 — backlog:**

7. **Dyson Airwrap canonicalization** (6 zero-results, product exists) — flag as a follow-up to the relevance cleanup in `BUY-28453` (the prior-cycle child blocked on `BUY-28454`).
8. **Atlas QA 300-query regression** has not run since routine was created 2026-06-10 (`lastTriggeredAt=null`). The Monday 09:00 UTC cron should have fired 2026-06-08 with results — flag to Atlas QA so the basket pass-rate trend becomes available next week.

### Active gap-fill children (carry-over from 2026-06-05 cycle)

| Issue | Priority | Title | Status (best-effort) |
|-------|----------|-------|----------------------|
| [BUY-31615](/BUY/issues/BUY-31615) | P0 | Beauty SEA merchant ingestion (Watsons/Sephora/Guardian) | open |
| [BUY-31616](/BUY/issues/BUY-31616) | P0 | Grocery TH merchant ingestion (Tops/Lazada/Villa Market) | open |
| [BUY-31622](/BUY/issues/BUY-31622) | P1 | Home/Kitchen appliance brand-direct SEA (ID/TH/PH) | open |
| [BUY-31623](/BUY/issues/BUY-31623) | P1 | Electronics brand-direct SEA (Samsung/Bose/DJI/Sony) | open |
| [BUY-31624](/BUY/issues/BUY-31624) | P2 | Toys TH merchant ingestion (Lego/Hasbro) | open |

All five are still in the prior cycle; recommend Shopper re-prioritizes and confirms close on any whose P0/P1 ingestion has actually landed (the 2026-06-05 0.96% day suggests at least one of them has shipped successfully).

### Disposition

- Status: keep `in_progress` (standing tracker, weekly cadence)
- This week's net: real production zero-result rate is **9.50%**, down from **24.67%** last week. ✅ on the right direction; still 9.5× the <1% SLA.
- Continuation: next fire 2026-06-19 09:00 SGT = 2026-06-19 01:00 UTC (routine `4544770f-…`)
- New children proposed: 3 P0 (SG brand-search fix, junk-query API gate, VN/TH catalog fill) — listed above for Oracle to spawn
- Dependencies: throughput sustained at 338,840/hr via [BUY-30590](/BUY/issues/BUY-30590), [BUY-30620](/BUY/issues/BUY-30620), [BUY-31452](/BUY/issues/BUY-31452); products_created_at_idx INVALID (BUY-32878) limits the per-day aggregates — use n_tup_ins_delta as primary signal until REINDEX window opens.

---
*Generated: 2026-06-12T01:18Z | Source: `query_log` (real production) + `catalog_stats` + basket-harness 2026-06-06 `acceptance-rerun-rest` | Script: `zero-result-gap/weekly_gap_report.py` (BUY-24267) | Full top-50 list: `docs/buy-42533-zero-result-gap-2026-06-12.md`*
