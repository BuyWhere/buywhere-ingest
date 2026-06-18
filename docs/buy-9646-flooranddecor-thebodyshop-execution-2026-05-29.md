# BUY-9646 Floor & Decor + The Body Shop Execution Note

Date: 2026-05-29 UTC
Issue: [BUY-9646](/BUY/issues/BUY-9646)

## What landed

- Added `src/scrapers/floor_and_decor.py`
- Added `src/scrapers/the_body_shop.py`
- Registered both scrapers in `src/scrapers/__init__.py`
- Wrote sample product output to:
  - `merchants/floor_and_decor_2026-05-29.ndjson`
  - `merchants/the_body_shop_2026-05-29.ndjson`

## Feed paths used

- Floor & Decor:
  - sitemap index: `https://www.flooranddecor.com/sitemap_index.xml`
  - product sitemap: `https://www.flooranddecor.com/sitemap-PDP.xml`
- The Body Shop:
  - confirmed product sitemap: `https://www.thebodyshop.com/sitemap_products_1.xml?from=9282908455177&to=15564785287433`

## Sample run result

- Floor & Decor sample size: `3` products
  - `Kent 24 in. White Linen Tower` — `$790`
  - `Honeycomb 94in. Vinyl Quarter Round` — `$15.99`
  - `Peachtree 33 in. Painted Bright White Lift Up Wall Cabinet` — `$370`
- The Body Shop sample size: `5` products
  - `Vitamin E Gentle Face Wash` — `GBP 13.0`
  - `Moringa Body Butter` — `GBP 7.0`
  - `Pink Grapefruit Body Yogurt` — `GBP 14.0`

## Remaining gap

BUY-9646 now has three merchants executed from the original batch:

- `Paper Source`
- `Floor & Decor`
- `The Body Shop`

The remaining merchants still need separate handling:

- `Etsy` is not a sitemap merchant and needs API routing
- `Crutchfield`, `Monoprice`, `The Container Store`, `Room & Board`, `iHerb`, `Backcountry`, and `The RealReal` still require proxy/browser-backed collection
