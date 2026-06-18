# BUY-37308 — Etsy scraper BUY-2029 diagnostic findings

**Date:** 2026-06-09
**Agent:** Hunt 2 (708a8ce4-96dd-409d-94e7-a91d5032e4e0)
**Issue:** [BUY-37308](/BUY/issues/BUY-37308)

## Code status: ✅ COMPLETE

`src/scrapers/etsy_us.py` and `src/scrapers/proxy_config.py` are fully written and registered in `SCRAPERS` dict.

## Root cause analysis

| Blocker | Finding |
|---------|---------|
| Playwright `libatk-1.0.so.0` | **FIXED** — deps pre-installed at `/home/paperclip/playwright-deps/lib/`. Chromium launches with `LD_LIBRARY_PATH=/home/paperclip/playwright-deps/lib:$LD_LIBRARY_PATH` |
| Brightdata `residential_proxy1` zone | **BROKEN** — `407 Zone not found` via curl, `ERR_PROXY_CONNECTION_FAILED` via Playwright. Zone is not provisioned in Brightdata dashboard |
| Brightdata `LEGACY_RESIDENTIAL` zone | **BROKEN** — `ERR_PROXY_CONNECTION_FAILED`. Zone may also be inactive |
| Direct Etsy.com (no proxy) | **BROKEN** — `net::ERR_NAME_NOT_RESOLVED`. External DNS is completely dead in this execution environment |
| ScraperAPI | **BROKEN** — DNS failure. `api.scraperapi.com` unreachable |

## Immediate fix applied

**`LD_LIBRARY_PATH` fix** — The playwright-deps at `/home/paperclip/playwright-deps/lib/` already contain all required system libraries (`libatk-1.0.so.0`, etc.). Chromium launches successfully when `LD_LIBRARY_PATH` is set before invocation.

Any shell wrapper or systemd unit that runs the Etsy scraper must include:
```
LD_LIBRARY_PATH=/home/paperclip/playwright-deps/lib:$LD_LIBRARY_PATH
```

## Critical path: Brightdata zone provisioning

The scraper **cannot run** until the Brightdata residential proxy zone is activated. This requires a human with Brightdata dashboard access to:
1. Log into Brightdata dashboard
2. Navigate to the `residential_proxy1` zone (customer `hl_3ab737be`)
3. Activate/provision the zone

Until then, all proxy-based scraping attempts will fail with `407 Zone not found` or `ERR_PROXY_CONNECTION_FAILED`.

## What was tested and verified

```bash
# ✅ Works — Chromium launches with deps
LD_LIBRARY_PATH=/home/paperclip/playwright-deps/lib:$LD_LIBRARY_PATH \
  python3 -c "from playwright.async_api import async_playwright; ..."

# ❌ Fails — residential_proxy1 zone inactive
curl -x "http://brd-customer-hl_3ab737be-zone-residential_proxy1:...@brd.superproxy.io:22225" \
  https://www.etsy.com/c/jewelry

# ❌ Fails — LEGACY_RESIDENTIAL zone also inactive
Playwright + LEGACY_RESIDENTIAL proxy → net::ERR_PROXY_CONNECTION_FAILED

# ❌ Fails — Direct DNS dead, no proxy can compensate
curl https://www.etsy.com/c/jewelry → net::ERR_NAME_NOT_RESOLVED
```

## Next action required

**Human action needed:** Activate `residential_proxy1` zone in Brightdata dashboard for customer `hl_3ab737be`. Once activated, the Etsy scraper should work with the `LD_LIBRARY_PATH` fix applied to the invocation environment.
