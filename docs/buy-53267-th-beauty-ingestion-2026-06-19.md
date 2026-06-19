# BUY-53267 Thailand beauty ingestion lane

Date: 2026-06-19

## Summary

- Added a live EVEANDBOY Thailand ingestion lane using the public sitemap at `https://eveandboy.com/sitemap.xml`.
- The scraper walks `/product/` URLs and extracts stable PDP metadata from page meta tags plus the SKU suffix embedded in the product URL.
- Wired the lane into `scripts/catalog_live_ingest.py` and `data/.merchant_configs.json` so it can run through the existing live-ingest path.

## Merchant status

### EVEANDBOY

- Status: live path landed
- Discovery path: sitemap-driven
- PDP access: fetchable from this workspace
- Coverage expectation:
  - Broad Thai-market cosmetics, skincare, haircare, fragrance, and beauty tools
  - Strong local-market breadth beyond prestige-only retailers

### Sephora Thailand

- Status: blocked
- Current blocker: `https://www.sephora.co.th/` returns `403` from Akamai for baseline HTTP from this workspace, including homepage and sitemap attempts
- Unblock owner/action: infrastructure/proxy owner to provide a higher-trust fetch path or anti-bot-capable proxy

### Konvy

- Status: partial / not yet landed
- Homepage access is available from this workspace, but `https://www.konvy.com/sitemap.xml` returns `403 Forbidden`
- Likely next path: category or search crawl instead of sitemap, or a proxy-backed crawl if category discovery also gets rate-limited

## Notes on data shape

- EVEANDBOY PDPs do not expose straightforward JSON-LD product payloads.
- The page is Nuxt-rendered and exposes stable meta tags such as `og:title`, `og:url`, `og:image`, and `og:image:alt`.
- SKU is recoverable from the canonical product URL suffix, which is sufficient for the current live ingest path.
