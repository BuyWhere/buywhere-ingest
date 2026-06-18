# BUY-33947 / BUY-11030: CJ Affiliate Wayfair Application - Form Data

## Status (2026-06-15, Lyra): UNBLOCKED on env, BLOCKED on CAPTCHA + email verification

### Original blocker (Echo 2026-06-07) — RESOLVED
Playwright/Chromium system libraries are now available at `/home/paperclip/playwright-deps/lib/` and the headless Chromium binary is at `/home/paperclip/.cache/ms-playwright/chromium_headless_shell-1223/chrome-headless-shell-linux64/chrome-headless-shell`. Smoke test against example.com passed. Run via:

```
source /home/paperclip/playwright-deps/env.sh
export PLAYWRIGHT_BROWSERS_PATH=/home/paperclip/.cache/ms-playwright
python3 scripts/cj_affiliate_application.py
```

### New blocker (Lyra 2026-06-15) — NOT resolvable headlessly
- **reCAPTCHA v2** on every step of the CJ publisher signup (site key `6LcUhyETAAAAAO2TSmGq_vu46qPBpJdxHGHeV6Dp`). Image challenge is not solvable by the headless agent.
- **Email verification** required before any advertiser-specific application can be submitted. The agent does not have an email account it can receive the verification link on.
- **Multi-step flow** continues past step 1 (company info, address, tax info, payment method, then "Apply to Wayfair" inside CJ Member area, then Wayfair approval).

See `data/buy11030_wayfair_application_run_2026-06-15.md` for the full run summary, page map, and hand-off steps.

## Application URL
https://public.cj.com/signup/publisher?advertiserId=5206455

## Form Data to Submit

### Company Information
| Field | Value |
|-------|-------|
| Company Name | BuyWhere Technologies Pte. Ltd. |
| Website | https://buywhere.ai |
| Business Type | Technology / Software / Product data API / Commerce technology |
| Primary Market | Singapore |
| Secondary Markets | Southeast Asia |

### Descriptions
**Short Description (Website Description / About):**
BuyWhere is an agent-native product catalog API for AI commerce, starting in Singapore. We index, normalize, and serve structured product data so AI shopping assistants and autonomous agents can discover, compare, and recommend products.

**Long Description (Business Description):**
BuyWhere Technologies Pte. Ltd. builds the definitive product catalog API for AI agent commerce, starting with Singapore. We integrate merchant and marketplace product data into a unified, structured catalog for AI shopping assistants, developer platforms, and commerce agents.

### Promotion & Traffic
| Field | Value |
|-------|-------|
| Promotion Methods | Product catalog API, AI shopping assistant recommendations, developer integrations |
| Traffic Sources | Organic, direct, developer/platform partnerships, API customers |
| Audience | AI agent developers, shopping assistant builders, merchants, commerce-data partners |

### Compliance Notes (DO NOT select these)
- Do NOT claim coupon/cashback/loyalty activity
- Do NOT claim toolbar/paid-search activity
- Do NOT commit to production traffic volume or conversion guarantees

## Automation Script
Located at: `scripts/cj_affiliate_application.py`
Requires: System libraries listed above installed via apt-get

## Resolution Path
1. **Option A (Preferred):** Operator with sudo installs deps: `sudo apt-get install libatk1.0-0 libatk-bridge2.0-0 libcups2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2 libatspi2.0-0`
2. **Option B:** Manual submission using the form data above
3. **Option C:** Use a remote browser automation service (e.g., Browserless, ScrapingBee)

## Deliverables (Pending)
- [ ] Complete CJ Affiliate publisher signup
- [ ] Capture confirmation/reference number
- [ ] Return: confirmation received, date submitted, follow-up instructions
