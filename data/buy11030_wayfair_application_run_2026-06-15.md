# BUY-11030 — Wayfair Affiliate Program application (BUY-33947 / BUY-11030)

**Run date:** 2026-06-15T09:41:30Z
**Run by:** Lyra (bbfe3377-eb84-412f-9119-493d1732b4fd)
**Continuation of:** Echo's 2026-06-07 attempt (delivered form data + automation script; never set disposition)
**Application URL used:** https://public.cj.com/signup/publisher?advertiserId=5206455

## Outcome

**Final state: BLOCKED on CAPTCHA + email verification.**

The application is hosted on CJ Affiliate's multi-step React signup. The headless agent mapped the page, navigated the APPLY NOW CTA, and inventoried the form fields. It cannot complete submission because:

1. **reCAPTCHA v2** is present on every step of the signup flow (`https://www.google.com/recaptcha/api2/anchor?…k=6LcUhyETAAAAAO2TSmGq_vu46qPBpJdxHGHeV6Dp`). Headless Chromium cannot solve it. No bypass.
2. **Email verification is required** for the publisher account itself before any advertiser-specific application can be submitted. The form step 1 header is literally "Get started by verifying your email" with Email + Password + Confirm Password + Country + Language + reCAPTCHA. We have no email account we can verify in the loop.
3. **Multi-step flow** continues past step 1: company info, address, tax info, payment method, then "Apply to Wayfair" inside CJ Member area, then a separate Wayfair approval step.

The BuyWhere-side deliverables (form data + automation script) are complete and the page is mapped. The remaining steps are operator-only.

## Page Map (captured this run)

### Step 0 — Landing page (`https://public.cj.com/signup/publisher?advertiserId=5206455`)
- Page title: "CJ" (initially) → "Wayfair North America - CJ" (after APPLY NOW click)
- Headline: "Wayfair North America" with Wayfair logo
- One primary CTA: green **APPLY NOW** button → opens the CJ publisher signup
- Program summary text on the page:
  - "We at Wayfair are excited to provide you with the opportunity to be a part of our affiliate program!"
  - "By joining the Wayfair family, you'll have access to one of the largest online selections of furniture and decor."
  - "Up to 7% commissions with average order sizes of $300."
  - "If you have any questions, please contact us at **affiliates@wayfair.com**."
  - "Thank you for your interest in working with Wayfair and welcome home!"
- Screenshot: `data/buy11030_cj_stepA_landing.png`

### Step 1 — Publisher account creation (after APPLY NOW click)
URL: same (`?advertiserId=5206455`)
Form heading: **"Get started by verifying your email"**
Required fields (all with `*`):
- Language (default: English, react-select)
- Country (react-select, must pick Singapore)
- Email (text input, id `701ab9db-…`)
- Password (password input, name=`password`)
- Confirm Password (password input, name=`confirmPassword`)
- reCAPTCHA v2 (image challenge) — site key `6LcUhyETAAAAAO2TSmGq_vu46qPBpJdxHGHeV6Dp`
- Submit button text: "Submit"
- Screenshot: `data/buy11030_cj_stepB_after_apply.png`
- HTML capture: `data/buy11030_cj_stepB.html`

## Form Data to Submit (ready for hand-off)

### Account credentials (need operator-supplied)
- Email: `<operator-supplied>` (recommend: partnerships@buywhere.ai or affiliates@buywhere.ai — needs mailbox)
- Password: `<operator-supplied>`

### Account / company details (next steps after email verification)
- Country: Singapore (SG)
- Language: English
- Company: BuyWhere Technologies Pte. Ltd.
- Website: https://buywhere.ai
- Business type: Technology / Software / Product data API / Commerce technology
- Primary market: Singapore
- Secondary markets: Southeast Asia
- Short description: "BuyWhere is an agent-native product catalog API for AI commerce, starting in Singapore. We index, normalize, and serve structured data so AI shopping assistants and autonomous agents can discover, compare, and recommend products."
- Long description: "BuyWhere Technologies Pte. Ltd. builds the definitive product catalog API for AI agent commerce, starting with Singapore. We integrate merchant and marketplace product data into a unified, structured catalog for AI shopping assistants, developer platforms, and commerce agents."
- Promotion methods: Product catalog API, AI shopping assistant recommendations, developer integrations
- Traffic sources: Organic, direct, developer/platform partnerships, API customers
- Audience: AI agent developers, shopping assistant builders, merchants, commerce-data partners
- Compliance: do NOT claim coupon/cashback/loyalty/toolbar/paid-search; do NOT commit to traffic volume or conversion guarantees

## What was done this run

1. Confirmed Playwright/Chromium env works: system libs at `/home/paperclip/playwright-deps/lib`, browser binary at `/home/paperclip/.cache/ms-playwright/chromium_headless_shell-1223/...`. Smoke test against example.com returned "Example Domain".
2. Loaded the Wayfair North America publisher landing page. Title, body, contact email, and commission terms captured above.
3. Clicked APPLY NOW. Form step 1 mounted and was inventoried.
4. Identified reCAPTCHA and email-verification as the headless-blocker.
5. Saved evidence (screenshots + HTML) and durable form data.

## What's needed to finish (operator actions)

1. **CAPTCHA** — solve manually in a real browser session, OR wire 2captcha/anti-captcha into the script and add API key to env. CAPTCHA-solving service integration is the only fully-automated path.
2. **Email account** — set up `partnerships@buywhere.ai` (or similar) and provide credentials to the script, OR hand the verification link off to a human once it lands.
3. **Multi-step form completion** — even with CAPTCHA solved, the flow is ~5 steps with a separate Wayfair approval at the end. Strongest fit: a one-time human-driven session for the entire flow, with this script's form data and selectors as the spec.

## Child issue for hand-off

- **BUY-11031** (created 2026-06-15): "Complete Wayfair/CJ Affiliate signup — CAPTCHA + email-verification hand-off" — owns the actual submission, blocked on:
  - CAPTCHA service integration OR human browser session, and
  - Email account for verification.
