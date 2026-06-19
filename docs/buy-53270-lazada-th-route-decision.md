# BUY-53270 — Lazada TH Grocery Route Decision

**Status:** `DECIDED — FALLBACK AFTER MERCHANT-DIRECT WAVE`
**Date:** 2026-06-19
**Author:** Echo (codex_local)

---

## Decision

**Lazada TH** → **Marketplace extraction lane (deferred)**.
Defer active extraction until after the merchant-direct TH wave (Tops Online TH, Makro PRO TH) lands and proves stable throughput. Treat Lazada TH as the **next priority layer** when merchant-direct fills are exhausted or show coverage gaps.

Do **not** pursue a commercial/partnership route this cycle. The engineering cost is high (anti-bot), the commercial overhead is higher, and the merchant-direct wave directly addresses the #1 zero-result gap for less effort.

---

## Analysis

### Route 1: Partnership / Commercial Ingestion

| Factor | Assessment |
|---|---|
| Data quality | Highest — official feed, structured, normalized |
| Commercial overhead | **Prohibitive this cycle.** No existing Lazada TH relationship. Lead time for partnership outreach + legal + data sharing agreement is 4–12 weeks minimum |
| Policy risk | Grocery/near-expiry products may have different liability terms |
| **Verdict** | **Defer.** Too slow for the P0 gap deadline. Revisit as a Q3 strategic initiative |

### Route 2: Marketplace Extraction (technical)

| Factor | Assessment |
|---|---|
| Breadth | **High.** ~42,500 grocery SKU target across 16 categories |
| Bypass difficulty | **Blocked.** All Lazada TH API endpoints redirect to reCAPTCHA/punity. ScraperAPI key exhausted |
| Data quality | Medium — HTML extraction, no structured feed, normalization needed |
| Maintenance burden | Medium-high — anti-bot arms race |
| **Verdict** | **Blocked on proxy.** Viable once a working proxy is provisioned. Estimated ~$50–100/mo in proxy credits for full extraction |

### Route 3: Merchant-Direct TH Wave (Tops + Makro)

| Factor | Assessment |
|---|---|
| Breadth | Medium — branded grocery, SKU count TBD but likely < Lazada |
| Bypass difficulty | **Working.** Makro PRO TH via httpx (no bot wall). Tops Online TH with Playwright (Cloudflare, but bypassable) |
| Data quality | **Highest.** Official merchant inventory, real-time stock/POS data |
| Maintenance burden | Low — direct merchant feeds |
| **Verdict** | **Active now.** BUY-53269 is implementing both scrapers |

---

## Recommendation

1. **Ship the merchant-direct wave first** (BUY-53269 — Tops + Makro). This solves the P0 TH grocery gap with the lowest risk and fastest time-to-value.
2. **File a deferred implementation issue** for Lazada TH marketplace extraction. Link it to the proxy-provisioning dependency (ScraperAPI recharge / BrightData). When the proxy is available, the scraper in `src/scrapers/lazada_th.py` is complete and ready to run with `python -m src.scrapers.lazada_th --scrape-only`.
3. **Close BUY-53270 as blocked** with the deferred child issue as the continuation path.

---

## Files / Artifacts

- `src/scrapers/lazada_th.py` — Complete Lazada TH scraper (16 categories, 42.5K target)
- `scripts/discover_lazada_th_sitemaps.py` — Lazada TH sitemap discovery
- `scripts/ingest_th_grocery.py` — merchant-direct wave runner (Tops, Makro)
- `src/scrapers/tops_th.py` — Tops Online TH scraper
- `src/scrapers/makro_pro_th.py` — Makro PRO TH scraper
