# BUY-9646 Recovery Note — Sitemap Easy US Merchants Batch 2

Date: 2026-05-29 UTC
Issue: [BUY-9646](/BUY/issues/BUY-9646)
Upstream pipeline: [BUY-9639](/BUY/issues/BUY-9639#document-merchant-pipeline)

## Scope recovered from BUY-9639

Batch 2 was defined as 11 "sitemap easy" US merchants:

1. Crutchfield
2. Monoprice
3. The Container Store
4. Floor & Decor
5. Room & Board
6. The Body Shop US
7. iHerb
8. Paper Source
9. Backcountry
10. The RealReal
11. Etsy

The original feed targets recorded in `merchant-pipeline` were:

- `crutchfield.com/sitemap.xml`
- `monoprice.com/sitemap.xml`
- `containerstore.com/site-map.xml`
- `flooranddecor.com/sitemap.xml`
- `roomandboard.com/sitemap.xml`
- `thebodyshop.com/en-us/sitemap.xml`
- `iherb.com/sitemap.xml`
- `papersource.com/sitemap.xml`
- `backcountry.com/sitemap.xml`
- `therealreal.com/sitemap.xml`
- `developers.etsy.com`

## Historical execution state

The only prior BUY-9646 comment, dated 2026-05-04, reported:

- `The Body Shop US` sitemap accessible and tested
- `Crutchfield`, `Monoprice`, `iHerb`, `Backcountry`, and `The RealReal` returned `403`
- `The Container Store` hit PerimeterX
- `Floor & Decor`, `Room & Board`, and `Paper Source` were not fully tested
- `Etsy` had no public sitemap and would require API handling
- a local scraper file `/scrapers/sitemap_ingest.py` and output file `data/thebodyshop_us_20260504.ndjson` existed in that earlier workspace

Those files are not present in the current checkout, so the earlier partial implementation is not recoverable from this workspace alone.

## 2026-05-29 direct retest

Retested from this workspace with `curl -L -A 'Mozilla/5.0'` against the recorded feed URLs.

| Merchant | URL tested | Result |
|---|---|---|
| Crutchfield | `https://www.crutchfield.com/sitemap.xml` | `403` with Cloudflare challenge HTML |
| Monoprice | `https://www.monoprice.com/sitemap.xml` | `403` with Cloudflare challenge HTML |
| The Container Store | `https://www.containerstore.com/site-map.xml` | `307` redirect; not cleanly retrievable from this runner |
| Floor & Decor | `https://www.flooranddecor.com/sitemap.xml` | `404` |
| Room & Board | `https://www.roomandboard.com/sitemap.xml` | no response within the test window |
| The Body Shop US | `https://www.thebodyshop.com/en-us/sitemap.xml` | `404` |
| iHerb | `https://www.iherb.com/sitemap.xml` | `403` with challenge page |
| Paper Source | `https://www.papersource.com/sitemap.xml` | `200` XML |
| Backcountry | `https://www.backcountry.com/sitemap.xml` | `403` |
| The RealReal | `https://www.therealreal.com/sitemap.xml` | `403` with challenge page |
| Etsy | `https://developers.etsy.com/` | `200` HTML docs page, not a sitemap feed |

## Current conclusion

This batch is not a valid "easy sitemap ingestion" batch anymore from this environment:

- `Paper Source` is the only confirmed directly reachable sitemap target in the batch on 2026-05-29.
- `Floor & Decor` and `The Body Shop US` no longer match the originally recorded sitemap URLs.
- `Etsy` belongs in an API-specific ingestion path, not a sitemap batch.
- Most of the remaining merchants are behind active anti-bot protection and need either proxy/browser automation or a different source path.

## Unblock path

Owner: merchant-pipeline maintainer plus ingestion/platform owner.

Required action:

1. Reclassify the 11 merchants based on current feed reality.
2. Move `Paper Source` into a live ingestable batch or execute it directly.
3. Update `Floor & Decor` and `The Body Shop US` with fresh feed discovery.
4. Route `Etsy` to an API-specific issue.
5. Provide proxy/browser-backed crawler capacity for the Cloudflare/PerimeterX-protected merchants if they are still priority targets.
