# BUY-9646 Paper Source Execution Note

Date: 2026-05-29 UTC
Issue: [BUY-9646](/BUY/issues/BUY-9646)

## What landed

- Added `src/scrapers/paper_source.py`
- Registered `PaperSourceScraper` in `src/scrapers/__init__.py`
- Wrote sample product output to `merchants/paper_source_2026-05-29.ndjson`

## Extraction path

- Public sitemap index: `https://www.papersource.com/sitemap.xml`
- Product sitemap family: `sitemap_products_*.xml`
- Product pages expose structured `Product` JSON-LD in the `googleRichSnippet` script block

## Sample run result

- Sample size: `10` products
- Output format: newline-delimited JSON
- Example products:
  - `Pure White 4 Bar Folded Cards` — `$7.50`
  - `Superfine White A9 Note Cards` — `$8.50`
  - `Superfine White A6 Folded Cards` — `$11.00`

## Remaining gap

This executes the only directly ingestable merchant left in the original Batch 2 routing. The rest of BUY-9646 still requires separate follow-up for:

- `Etsy` API routing
- fresh feed discovery for `Floor & Decor` and `The Body Shop US`
- proxy/browser-backed collection for the seven anti-bot-protected merchants
