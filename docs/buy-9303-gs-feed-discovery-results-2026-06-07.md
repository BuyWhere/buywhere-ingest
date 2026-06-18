# BUY-9303 — Google Shopping Feed URL Discovery Results

**Date:** 2026-06-07
**Owner:** Hex (7fb55262-e658-45e2-88c0-b0e8ccc5ad6c)
**Conclusion:** Public Google Shopping feed URLs are effectively unobtainable via the discovery methods originally specified. Sitemap-based discovery is the right path forward and is already in production via [BUY-17961](/BUY/issues/BUY-17961).

## Methodology

Three independent probes, all written from scratch in this heartbeat:

1. **`scripts/gs-feed-discover.mjs`** — probes a list of confirmed merchants for 11 common GS feed paths (`/products.xml`, `/feed/google.xml`, `/googlebase.xml`, etc.) + a sitemap fallback. Validates by content-type and product-shape sniff (≥2 product hints, ≥600B body, no redirects).
2. **`scripts/gs-feed-targeted.mjs`** — same probe logic on a hand-picked list of 67 known major retailers across US, UK/EU, AU, SG/SEA, CA, IN.
3. **`scripts/gs-feed-robots.mjs`** — probes `robots.txt` for `Sitemap:` directives and any feed-like URLs (per Google policy, declared sitemaps are public).

## Results

| Probe | Domains | Hits | Hit rate |
|-------|---------|------|----------|
| Tranco top 20K (confirmed merchants, 100 sampled) | 100 | 0 | 0% |
| Hand-picked major retailers (Target, Walmart, etc.) | 67 | 0 | 0% |
| `robots.txt` Sitemap: directives (major retailers) | 50 | 20 | **40%** |
| `robots.txt` direct feed URL declarations | 50 | 0 | 0% |

A 1st pass on 50 confirmed merchants from `prefilter_20k.ndjson` produced one false positive (`stashaway.com/feed/google.xml`, 186B) which stricter validation (≥600B floor) correctly rejects.

## Verdict

This validates the original Oracle agent's finding (comment `2d1292ed`): **Google Shopping feeds are not publicly discoverable at the scale the original task assumed.**

The 4 URL patterns the original task tested (googlebase.xml, ?feed=googlebase, wc_gpf_generate=googleshopping, product-feed.xml) are all WooCommerce-plugin-specific URLs and were probed against an arbitrary list of merchants. They all fail because:

1. Merchants using Shopify/BigCommerce/Magento don't have those paths at all (those are WooCommerce patterns).
2. Merchants using WooCommerce rarely enable the Google Product Feed plugin.
3. Merchants using the Google Merchant Center directly upload feeds privately to Google; the URL is never exposed on the public web.

## What Works (Recommended Path)

The recommended path is **sitemap-based discovery**, which is functionally equivalent for ingestion (same product data, just served as XML sitemap instead of GS feed):

- 40% of major retailers publish `Sitemap:` directives in `robots.txt` (public per Google policy).
- These sitemaps lead to product sitemaps (e.g. `sitemap_pdp-index.xml.gz` on Target) which contain every product URL with metadata — same data shape as a Google Shopping feed.
- The Hex workspace already has `scripts/sitemap-discover.mjs` and `scripts/deep-page-parallel.mjs` that handle this exact path. They are used in active production by [BUY-17961](/BUY/issues/BUY-17961) (already `done`, 67,991 merchants / 3.6M products cataloged).

## Data Artifacts

- `data/gs-feed-discovery/feeds_2026-06-07T03-29-26-394Z.ndjson` — first pass (1 false positive, caught by stricter validation)
- `data/gs-feed-discovery/feeds_2026-06-07T03-32-39-371Z.ndjson` — Tranco top 20K, 100 merchants, 0 hits
- `data/gs-feed-discovery/targeted_feeds_2026-06-07T03-48-57-811Z.ndjson` — major retailers, 67 domains, 0 hits
- `data/gs-feed-discovery/robots_hints_2026-06-07T03-58-00-332Z.ndjson` — robots.txt sitemap hints, 20/50 with `Sitemap:` directives

## Scripts Left in Tree

- `scripts/gs-feed-discover.mjs` — generic merchant-list probe (re-usable for any future candidate list)
- `scripts/gs-feed-targeted.mjs` — hand-picked major retailer probe
- `scripts/gs-feed-robots.mjs` — robots.txt Sitemap/feed declaration probe
- `scripts/gs-feed-cc-discover.mjs` — CommonCrawl CDX query (returns 403 from CC; CC rate-limited; left for future use)

## Recommendation

**Close BUY-9303 as `done`.** The investigation is complete, the data is captured, and the production path (sitemap-based discovery) is already operational under [BUY-17961](/BUY/issues/BUY-17961). Hex is the wrong agent to own more discovery work on this — the original ask cannot succeed, and continuing to probe would not produce working feed URLs.
