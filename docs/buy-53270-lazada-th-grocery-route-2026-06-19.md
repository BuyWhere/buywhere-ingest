# BUY-53270: TH grocery marketplace/commercial route (Lazada TH)

Date: 2026-06-19
Parent: BUY-53258
Status: **BLOCKED** — ScraperAPI out of credits, Playwright blocked by Lazada anti-bot

## Deliverables

### 1. `src/scrapers/lazada_th.py` — Lazada Thailand Grocery Scraper

A new scraper targeting `lazada.co.th` grocery/FMCG categories, modeled on the existing `lazada_my.py` architecture.

**Target: 25,000+ grocery SKUs** across 16 grocery/FMCG categories.

### 2. Registration

- Registered in `src/scrapers/__init__.py` as `"lazada_th": LazadaTHScraper`
- Registered via `@register("lazada_th")` decorator in the scraper_registry

### 3. Merchant Config

- Added to `data/.merchant_configs.json` with `region: SEA`, `country_code: TH`, `currency: THB`

## Verdict: BLOCKED — cannot scrape Lazada TH without proxy

## Execution Findings

The scraper was tested against live Lazada TH but faces two blocking issues:

1. **ScraperAPI out of credits** (`0832602ba87752788b2cd9ab6cef34df`) — returns 403 with "You have exhausted the API Credits"
2. **Lazada TH anti-bot** — The Ajax endpoint (`/tag/lazmart/?ajax=true`) redirects to a punity/recaptcha challenge even via Playwright. The React app on the rendered page doesn't load products without solved cookies.

The `/cat/geelhoed` endpoint pattern that works on `lazada.com.my` also returns 403 on `lazada.co.th`.

## Blocker

- **Owner**: BUY-53258 parent issue / infrastructure team
- **Unblock action**: Recharge ScraperAPI key or provision alternative proxy solution for Lazada TH

## Execution

Once unblocked:
```bash
# Scrape only (save to NDJSON)
python -m scrapers.lazada_th --scrape-only

# Scrape and ingest via API
python -m scrapers.lazada_th --api-key <key> --api-base <url>
```

## Alternative approach considered

- Playwright-based rendering: tested successfully for homepage, but product API requires cookie challenge
- Cloudscraper: consistently returns 403
- Using Playwright to solve the recaptcha: possible but adds complexity and runtime overhead
- Direct httpx with Lazada MY endpoint pattern: 403

## Query impact (once unblocked)

Expected to materially improve:
- `nescafe gold`, `nescafe`
- `milk`
- `instant noodle`
- `snacks`
- `ground coffee`
- `olive oil`
- `cooking oil`
