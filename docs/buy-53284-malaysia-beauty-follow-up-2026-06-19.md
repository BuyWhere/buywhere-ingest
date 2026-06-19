# BUY-53284 Malaysia beauty follow-up lane

Date: 2026-06-19

## Outcome

- `Guardian MY` is the fastest ingestible Malaysia beauty lane from this environment.
- `Watsons MY` and `Sephora MY` are currently blocked by Akamai at the edge before sitemap or product-surface access.

## Guardian MY

- Merchant: `https://www.guardian.com.my/`
- Implementation path:
  - Replaced the placeholder `GuardianMYScraper` subclass with a live GraphQL-backed scraper in [src/scrapers/guardian_my.py](/paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default/src/scrapers/guardian_my.py).
  - The scraper reads Guardian MY's public `/graphql` catalogue, extracts product metadata, and normalizes beauty-facing categories.
- Verification:
  - `python3 -m py_compile src/scrapers/guardian_my.py src/scrapers/__init__.py`
  - Live smoke run returned `7,241` beauty-leaning products.
- Sample output:
  - `Glad2Glow Damask Rose Brightening Gel Mask 50g` -> `28.00 MYR` -> `['Beauty', 'Skin Care']`
  - `Tresemme Keratin Smooth Serum 30Ml` -> `22.50 MYR` -> `['Beauty', 'Hair Care']`
  - `Cezanne Mascara Remover` -> `49.90 MYR` -> `['Beauty', 'Cosmetics']`
- Top categories from the smoke run:
  - `Skin Care`: `2,542`
  - `Cosmetics`: `2,008`
  - `Hair Care`: `1,408`
  - `Personal Care`: `990`
  - `Fragrance`: `97`

## Watsons MY

- Merchant: `https://www.watsons.com.my/`
- Current status: blocked
- Evidence:
  - Direct `curl` to homepage, `robots.txt`, and `sitemap.xml` returned `403 Access Denied`.
  - Playwright-rendered fetch also returned `403 Access Denied`.
- Practical implication:
  - No catalog or sitemap path is currently reachable from this environment without a separate anti-bot bypass route.

## Sephora MY

- Merchant: `https://www.sephora.my/`
- Current status: blocked
- Evidence:
  - Direct `curl` to homepage, `robots.txt`, and `sitemap.xml` returned `403 Access Denied`.
  - Playwright-rendered fetch also returned `403 Access Denied`.
- Practical implication:
  - Prestige recovery remains desirable, but this is not an immediately ingestible lane from the current runtime.

## Infra note

- `SCRAPERAPI_KEY` is present in the environment, but ScraperAPI returned `403` with an exhausted-credit billing message, so it is not a viable unblock for Watsons or Sephora today.

## Recommendation

- Ship `Guardian MY` as the Malaysia beauty lane now.
- Track `Watsons MY` and `Sephora MY` as separate anti-bot follow-up work rather than holding this lane open.
