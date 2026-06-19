# BUY-53484 Watsons MY + Sephora MY anti-bot investigation

Date: 2026-06-19

## Outcome

- No reachable Watsons MY or Sephora MY catalog surface was found from this runtime.
- Both merchants are protected by Akamai before storefront, sitemap, and likely app-facing API layers.
- The cheapest realistic unblock is to restore an anti-bot-capable residential/mobile proxy path and then retry the shared app/API hosts.

## Watsons MY

- Storefront host: `https://www.watsons.com.my/`
- API host discovered from DNS / TLS: `https://api.watsons.com.my/`
- Result from this runtime:
  - `403 Access Denied` on homepage, `robots.txt`, `sitemap.xml`, brand list, and sample brand page.
  - `403 Access Denied` on `api.watsons.com.my` root and guessed OCC-style endpoints, including:
    - `/occ/v2`
    - `/occ/v2/basesites`
    - `/occ/v2/{site}/products/search?...`
    - `/graphql`
- Architecture clue:
  - `api.watsons.com.my` returns CORS / exposed-header names like `occ-personalization-id`, which strongly suggests a SAP Commerce / OCC backend exists behind Akamai.
  - That backend is still edge-blocked from this environment, so there is no usable direct-ingest path today.

## Sephora MY

- Storefront host: `https://www.sephora.my/`
- Shared service hosts exposed by TLS:
  - `https://api.sephora.sg/`
  - `https://content-platform.sephora.sg/`
  - `https://retail-stores.sephora.sg/`
  - `https://tr.sephora.my/`
- Result from this runtime:
  - `403 Access Denied` on homepage, `robots.txt`, `sitemap.xml`, sample brand page, and sample product page.
  - `403 Access Denied` on the shared API / content / retail-store hosts above.
- Practical implication:
  - Sephora MY appears to rely on shared regional services, but those services are also Akamai-protected from this runtime.
  - I did not find a separate public sitemap, GraphQL, or catalog endpoint that avoids the same edge controls.

## Supporting evidence

- Search-engine indexing still shows current Watsons MY and Sephora MY pages, including Watsons brand pages and Sephora MY brand/product pages.
- From this runtime, those same direct URLs return Akamai `403`, which means indexability elsewhere does not translate into a reachable ingest path here.
- The Watsons MY mobile app is publicly listed as `com.watsons.mcommerce`, which makes app-traffic capture a plausible second-step after proxy restoration, but not a cheaper first move than restoring working anti-bot egress.

## Cheapest realistic unblock

1. Restore a working anti-bot-capable fetch path:
   - top up or replace the exhausted ScraperAPI route, or
   - provide a residential / mobile proxy egress that Akamai accepts for MY traffic.
2. Re-test the smallest set of high-value hosts:
   - `www.watsons.com.my`
   - `api.watsons.com.my`
   - `www.sephora.my`
   - `api.sephora.sg`
3. If Watsons API access opens:
   - enumerate the OCC base site and product search endpoints first, since that is the most likely structured ingest surface.
4. If Sephora storefront opens but the API remains opaque:
   - capture frontend network traffic from a browser session behind the restored proxy and promote the first JSON catalog endpoint that returns product payloads.

## Recommendation

- Close this investigation as complete.
- Hand off one infra/proxy follow-up to restore an anti-bot-capable egress path for both merchants, then retry the identified app/API hosts before spending time on scraper implementation.
