# BUY-31238 Brand-Direct SG Probe — 2026-06-06

## Scope

- Apple SG `buy.xml` lane
- Samsung SG B2C sitemap and first verified product batch

## Artifacts

- `merchants/apple_sg_2026-06-06.ndjson`
- `merchants/apple_sg_buy_xml_2026-06-06.ndjson`
- `merchants/samsung_sg_2026-06-06.ndjson`
- `data/brand_direct/apple_sg_brand_probe_2026-06-06.json`
- `data/brand_direct/samsung_sg_brand_probe_2026-06-06.json`
- `data/brand_direct/samsung_sg_candidates_2026-06-06.ndjson`
- `scripts/brand_direct_sg_probe.py`

## Results

- Apple SG `buy.xml` responded live and exposed `1,055` SG product URLs.
- Apple first-batch artifact contains `40` verified rows with `40` unique SKUs/part numbers.
- Samsung SG `sitemap.xml` resolved to `b2c-sitemap.xml` plus `5` child product sitemaps.
- Samsung SG candidate detection found `2,397` product-like PDP URLs.
- Samsung SG first verified batch contains `120` rows.

## Samsung Batch Notes

- Dominant categories in the first verified batch:
  - `mobile-accessories`: `109`
  - `audio-sound`: `11`
- Sample verified rows:
  - `SM-R400NZAAASA` — `https://www.samsung.com/sg/audio-sound/galaxy-buds/galaxy-buds-fe-graphite-sm-r400nzaaasa/`
  - `SM-R420NZKAASA` — `https://www.samsung.com/sg/audio-sound/galaxy-buds/galaxy-buds3-fe-black-sm-r420nzkaasa/`
  - `SM-R630NZWAASA` — `https://www.samsung.com/sg/audio-sound/galaxy-buds/galaxy-buds3-pro-white-sm-r630nzwaasa/`

## Apple Batch Notes

- Sample verified rows:
  - `MXNC3ZP/A` — `https://www.apple.com/sg/shop/buy-ipad/ipad-mini/256gb-blue-wifi`
  - `MFYY4X/A` is present on live iPhone PDP JSON-LD and confirms the lane exposes real Apple part numbers.
  - Configured iMac rows in the first batch also expose live SG pricing and Apple bundle SKUs from JSON-LD.

## Decision

- Samsung SG sitemap/product URL detection is now workable from this environment and yields a real first batch.
- Apple SG should continue from the `buy.xml` lane rather than marketing-page discovery because the sitemap is complete and SKU-bearing.
