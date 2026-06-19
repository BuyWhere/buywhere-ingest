## Weekly zero-result gap report — week ending 2026-06-19

**Source:** Catalog DB (maglev.proxy.rlwy.net:31310/railway) — live product counts + query_log 14d window
**Generated:** 2026-06-19T01:20Z | Routine: BUY-53244

---

### Catalog headline

| Metric | Value | vs prior week (2026-06-05) |
|--------|-------|---------------------------|
| Total products (n_live_tup) | 125.2M | +32.0M (from ~93M) |
| Products added (7d window) | 13.1M | Not previously tracked |
| Active merchants | 75,039 | +48K (from ~27K on Jun 5) |
| Markets with products | 22 | Stable |

---

### By market — product coverage

| Market | Active products | Active merchants | Δ vs Jun 5 products |
|--------|:--------------:|:----------------:|:------------------:|
| US | 8,422,227 | 63,943 | +866K |
| SG | 7,920,075 | 9,939 | +50K |
| ID | 235,827 | 48 | 0 (stable) |
| MY | 154,904 | 18 | +20K |
| TH | 139,583 | 6 | +90K |
| VN | 71,623 | 25 | 0 (stable) |
| PH | 37,992 | 11 | 0 (stable) |
| AU | 84,770 | 1 | Newly tracked |
| UK | 35,460 | 384 | Newly tracked |
| Others (13 markets) | 86,134 | ~700 | Various |

---

### Zero-result rate from actual search traffic (query_log, 14d)

| Endpoint | Total queries | Zero-results | Zero-rate |
|----------|:-----------:|:-----------:|:--------:|
| MCP (agent endpoint) | 8,802 | 574 | 6.5% 🟡 |
| products.search | 3,837 | 1,760 | 45.9% 🔴 |
| products.get | 457 | 271 | 59.3% 🔴 |
| products.list | 141 | 137 | 97.2% 🔴 |
| categories.list | 68 | 0 | 0.0% ✅ |
| products.deals | 57 | 57 | 100% 🔴 |

*Note: MCP endpoint aggregates multiple operations; products.search is the primary search surface.*

---

### Top failing search queries (query_log, 14d)

| Query | Attempts | Failures | Fail rate | Likely cause |
|-------|:-------:|:--------:|:---------:|-------------|
| nike air max | 53 | 53 | 100% | No Nike merchant ingested — all markets |
| airpods pro | 40 | 40 | 100% | No Apple accessory merchant |
| iphone 14 | 38 | 38 | 100% | No Apple merchant |
| protein powder | 35 | 35 | 100% | No supplement merchant |
| playstation 5 | 32 | 32 | 100% | No gaming console merchant |
| monitor 4k | 29 | 29 | 100% | No monitor-specific merchant |
| yoga mat | 27 | 27 | 100% | No fitness equipment merchant |
| logitech mx master | 28 | 27 | 96.4% | No computer peripheral merchant |
| kindle | 29 | 27 | 93.1% | No Amazon device merchant |
| iphone 15 | 42 | 41 | 97.6% | No Apple merchant (product mismatch) |
| coffee maker | 62 | 44 | 71.0% | Partial kitchen appliance coverage |
| running shoes | 47 | 45 | 95.7% | No activewear merchant |
| lego | 26 | 26 | 100% | No toy merchant |

*From 3,837 total search queries across all endpoints. 45.9% overall zero-result rate on products.search.*

---

### Category gaps (from prior report analysis + query_log cross-reference)

| Category | Est. coverage gap (% zero-result) | Primary failing markets | Priority |
|----------|:--------------------------------:|------------------------|:--------:|
| Beauty (brand-specific) | ~71% | ID, TH, MY, PH, VN | **P0** |
| Grocery (branded) | ~52% | ID, TH, VN | **P0** |
| Sports/Activewear | ~43% | All SEA (ID, TH, VN, PH, MY) | **P1** |
| Home/Kitchen (appliances) | ~43% | ID, TH, PH, VN | **P1** |
| Electronics (brand portable) | ~29% | ID, VN, TH, PH | **P1** |
| Toys/Games | ~29% | TH, PH, ID | **P2** |
| Fashion (brand-specific) | ~29% | ID, VN, TH | **P2** |

### Recommended Oracle actions

1. **P0 — Beauty SEA** — ID and TH have near-zero beauty products. MY, PH, VN missing luxury brands (Dyson, La Mer, Charlotte Tilbury, SK-II). Need Watson's, Sephora, Guardian, local SEA beauty distributors.

2. **P0 — Grocery SEA** — ID (1,216 grocery products) and TH (901) severely under-covered. Need Tops Online TH, Lazada TH grocery, Makro TH.

3. **P1 — Sports/Activewear brands** — Nike, Adidas, Lululemon absent across SEA. Need local distributors or direct merchant onboarding.

4. **P1 — Home/Kitchen appliances** — Air fryers, Le Creuset, coffee machines missing in ID/TH/PH. Need Kitchen Warehouse equivalents for SEA.

5. **P2 — Toys/Games** — Lego absent across all SEA markets (TH has 67 toy products). Need Lego TH distributor, Hasbro SEA merchant.

---

### Key observations

- **Catalog scale has grown massively**: 125M products (up from 17M on May 31). US and SG coverage reaching critical mass.
- **SEA markets still thin**: ID/MY/TH/VN/PH = 640K products combined vs 16M in US+SG. Merchants in these markets remain the #1 gap.
- **75K active merchants** is up from ~27K on Jun 5 — strong merchant acquisition momentum.
- **query_log gives imperfect signal**: Country_code not populated, so per-market zero-rate requires the basket harness method (next cycle).
- **Products.search at 45.9% zero-rate**: This is the real agent search surface. MCP endpoint aggregates better (6.5%) but includes non-search operations.

---

*Report generated from live catalog data. Prior report: 2026-06-05 (BUY-30638). Script: BUY-24267. Next routine: Friday 2026-06-26 01:00 UTC.*
